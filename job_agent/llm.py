"""
LLM Router — single entry point for all model calls.

Supports three backends:
  1. LM Studio (or another OpenAI-compatible local server)
  2. Ollama (OpenAI-compatible local endpoint)
  3. Anthropic Claude API
  4. OpenAI API

MLX model quirks handled here so no other module needs to care:
  - MLX models do NOT support response_format=json_object (use json_schema or omit)
  - Thinking/reasoning models consume tokens in a reasoning phase before producing content;
    max_tokens must cover BOTH reasoning AND output — see config for per-role budgets
  - gpt-oss-20b emits a structured prefix before its JSON:
      <|channel|>final <|constrain|>JSON<|message|>{...}
    This is stripped automatically in _extract_json()

All callers receive a plain dict — backend quirks are invisible upstream.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from job_agent.config import settings
from job_agent.providers import normalize_provider_mode, provider_setup_status

logger = logging.getLogger(__name__)


class ProviderUnavailableError(RuntimeError):
    """Raised when a provider cannot be reached or returns an unexpected response."""


class LLMRouter:
    """Routes generation requests to the appropriate backend.

    Usage:
        router = LLMRouter()
        result = router.generate(role="writer", system_prompt=..., user_prompt=...)
        result = router.generate(role="small", system_prompt=..., user_prompt=...)
    """

    # Maps role names to (model_setting, max_tokens_setting) attribute names on Settings.
    # Add new roles here without touching the rest of the code.
    _ROLE_MAP: dict[str, tuple[str, str]] = {
        "small":  ("lm_studio_small_model",  "lm_studio_max_tokens_small"),
        "writer": ("lm_studio_writer_model", "lm_studio_max_tokens_writer"),
        "mid":    ("lm_studio_mid_model",    "lm_studio_max_tokens_mid"),
    }
    _OLLAMA_ROLE_MAP: dict[str, str] = {
        "small": "ollama_fast_model",
        "writer": "ollama_writer_model",
        "mid": "ollama_fast_model",
    }

    def __init__(self) -> None:
        self._openai_client = None
        self._anthropic_client = None

        if settings.openai_api_key:
            from openai import OpenAI
            self._openai_client = OpenAI(api_key=settings.openai_api_key)

        if settings.anthropic_api_key:
            import anthropic
            self._anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    # ── Public interface ──────────────────────────────────────────────────────

    def generate(
        self,
        *,
        role: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Generate a JSON response using the model assigned to `role`.

        Args:
            role: One of "small", "writer", "mid" (maps to config model/token settings).
            system_prompt: System instruction for the model.
            user_prompt: User message content.
            temperature: Sampling temperature (lower = more deterministic).

        Returns:
            Parsed JSON dict from the model response.

        Raises:
            ProviderUnavailableError: If the model is not configured or the request fails.
        """
        if role not in self._ROLE_MAP:
            raise ValueError(f"Unknown model role '{role}'. Valid roles: {list(self._ROLE_MAP)}")

        provider_mode = normalize_provider_mode(getattr(settings, "llm_provider_mode", "openai"))
        if provider_mode == "openai":
            return self.generate_with_openai(
                model=self._openai_model_for_role(role),
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        if provider_mode == "anthropic":
            return self.generate_with_claude(system_prompt=system_prompt, user_prompt=user_prompt)
        if provider_mode == "ollama":
            return self._generate_ollama(
                role=role,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
            )
        if provider_mode == "mixed":
            for attempt in ("lm_studio", "ollama"):
                try:
                    if attempt == "lm_studio":
                        return self._generate_local(
                            role=role,
                            system_prompt=system_prompt,
                            user_prompt=user_prompt,
                            temperature=temperature,
                        )
                    return self._generate_ollama(
                        role=role,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        temperature=temperature,
                    )
                except ProviderUnavailableError:
                    continue
            if self._openai_client is not None:
                return self.generate_with_openai(
                    model=self._openai_model_for_role(role),
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                )
            if self._anthropic_client is not None:
                return self.generate_with_claude(system_prompt=system_prompt, user_prompt=user_prompt)
            raise ProviderUnavailableError("Mixed mode: all configured providers failed or are unavailable.")

        return self._generate_local(
            role=role,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
        )

    def generate_with_retry(
        self,
        *,
        role: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Retry lightweight calls that can tolerate a short backoff."""
        max_attempts = max(1, getattr(settings, "llm_retry_attempts", 2))
        last_exc: Exception | None = None

        for attempt in range(max_attempts):
            try:
                return self.generate(
                    role=role,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                )
            except (ProviderUnavailableError, ValueError) as exc:
                last_exc = exc
                if attempt < max_attempts - 1:
                    import time

                    delay = 2 ** attempt
                    logger.warning(
                        "LLM call failed (attempt %d/%d); retrying in %ss: %s",
                        attempt + 1,
                        max_attempts,
                        delay,
                        exc,
                    )
                    time.sleep(delay)

        if last_exc is not None:
            raise last_exc
        raise ProviderUnavailableError("LLM call failed after retries.")

    def _generate_local(
        self,
        *,
        role: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
    ) -> dict[str, Any]:
        model_attr, tokens_attr = self._ROLE_MAP[role]
        model: str = getattr(settings, model_attr)
        max_tokens: int = getattr(settings, tokens_attr)

        if not model:
            raise ProviderUnavailableError(
                f"Model role '{role}' is not configured. "
                f"Set {model_attr.upper()} in your .env file."
            )

        return self._call_lm_studio(
            model=model,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
        )

    def _generate_ollama(
        self,
        *,
        role: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        model_attr = self._OLLAMA_ROLE_MAP.get(role, "ollama_fast_model")
        model = getattr(settings, model_attr, "")
        if not model:
            raise ProviderUnavailableError(
                f"Ollama model for role '{role}' is not configured. "
                f"Set {model_attr.upper()} in your settings."
            )

        ollama_base = getattr(settings, "ollama_base_url", "http://localhost:11434").rstrip("/")
        if not ollama_base:
            raise ProviderUnavailableError("Ollama base URL is not configured.")

        max_tokens = getattr(
            settings,
            self._ROLE_MAP.get(role, ("", "lm_studio_max_tokens_small"))[1],
            settings.lm_studio_max_tokens_small,
        )
        return self._call_lm_studio(
            model=model,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            provider_label="Ollama",
            base_url=f"{ollama_base}/v1",
        )

    def _openai_model_for_role(self, role: str) -> str:
        if role == "writer":
            return settings.openai_escalation_model
        return settings.openai_review_model

    def generate_with_claude(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        """Generate a JSON response using the configured Claude model.

        Raises:
            ProviderUnavailableError: If ANTHROPIC_API_KEY is not configured.
        """
        if self._anthropic_client is None:
            raise ProviderUnavailableError(
                "Anthropic API key is not configured. "
                "Set ANTHROPIC_API_KEY in your .env file."
            )
        try:
            response = self._anthropic_client.messages.create(
                model=settings.anthropic_model,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            text = response.content[0].text
            logger.debug("Claude response length: %d chars", len(text))
            return self._extract_json(text)
        except Exception as exc:
            raise ProviderUnavailableError(f"Claude request failed: {exc}") from exc

    def generate_with_openai(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        """Generate a JSON response using OpenAI (escalation path).

        Raises:
            ProviderUnavailableError: If OPENAI_API_KEY is not configured.
        """
        if self._openai_client is None:
            raise ProviderUnavailableError(
                "OpenAI API key is not configured. "
                "Set OPENAI_API_KEY in your .env file."
            )
        try:
            response = self._openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                timeout=settings.openai_request_timeout_seconds,
            )
            text = response.choices[0].message.content
            return self._extract_json(text)
        except Exception as exc:
            exc_str = str(exc).lower()
            if "429" in exc_str or "rate limit" in exc_str or "quota" in exc_str:
                raise ProviderUnavailableError(
                    "OPENAI_QUOTA_EXCEEDED: OpenAI rate limit or quota reached. "
                    "Check your billing or switch provider."
                ) from exc
            raise ProviderUnavailableError(f"OpenAI request failed: {exc}") from exc

    def provider_status(self) -> dict[str, Any]:
        """Return current provider configuration and reachability."""
        provider = provider_setup_status()
        return {
            "lm_studio": {
                "base_url": settings.lm_studio_base_url,
                "provider_mode": provider["mode"],
                "small_model_configured": bool(settings.lm_studio_small_model),
                "writer_model_configured": bool(settings.lm_studio_writer_model),
                "mid_model_configured": bool(settings.lm_studio_mid_model),
                "embedding_model_configured": bool(settings.lm_studio_embedding_model),
                "reachable": self._lm_studio_reachable(),
                "token_budgets": {
                    "small": settings.lm_studio_max_tokens_small,
                    "writer": settings.lm_studio_max_tokens_writer,
                    "mid": settings.lm_studio_max_tokens_mid,
                },
            },
            "ollama": {
                "base_url": getattr(settings, "ollama_base_url", "http://localhost:11434"),
                "fast_model": getattr(settings, "ollama_fast_model", ""),
                "writer_model": getattr(settings, "ollama_writer_model", ""),
                "reachable": self._ollama_reachable(),
            },
            "anthropic": {
                "enabled": bool(settings.anthropic_api_key),
                "model": settings.anthropic_model,
                "final_review_enabled": settings.use_claude_final_review,
            },
            "openai": {
                "enabled": bool(settings.openai_api_key),
                "review_enabled": settings.use_openai_review,
                "escalation_enabled": settings.use_openai_escalation,
                "review_model": settings.openai_review_model,
                "escalation_model": settings.openai_escalation_model,
            },
            "active": provider,
        }

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _lm_studio_reachable(self) -> bool:
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{settings.lm_studio_base_url}/models")
                response.raise_for_status()
            return True
        except Exception:
            return False

    def _ollama_reachable(self) -> bool:
        try:
            ollama_base = getattr(settings, "ollama_base_url", "").rstrip("/")
            if not ollama_base:
                return False
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{ollama_base}/api/tags")
                response.raise_for_status()
            return True
        except Exception:
            return False

    def _call_lm_studio(
        self,
        *,
        model: str,
        max_tokens: int,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        provider_label: str = "LM Studio",
        base_url: str | None = None,
    ) -> dict[str, Any]:
        """Send a chat completion request to the local LM Studio server.

        Notes on MLX model compatibility:
        - response_format=json_object is NOT supported by MLX models → omitted.
        - max_tokens must be large enough for reasoning tokens + actual output.
        - The JSON instruction is embedded in the system prompt instead.
        """
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            # Do NOT include response_format — MLX models reject json_object.
            # JSON output is enforced via the system prompt instruction.
        }
        try:
            with httpx.Client(timeout=settings.lm_studio_request_timeout_seconds) as client:
                response = client.post(
                    f"{(base_url or settings.lm_studio_base_url).rstrip('/')}/chat/completions",
                    json=payload,
                )
                response.raise_for_status()

            body = response.json()
            choice = body["choices"][0]
            finish_reason = choice.get("finish_reason", "")

            if finish_reason == "length":
                logger.warning(
                    "Model '%s' hit max_tokens=%d and was cut off. "
                    "Increase LM_STUDIO_MAX_TOKENS_* in .env if output is incomplete.",
                    model,
                    max_tokens,
                )

            # content holds the final answer; reasoning_content holds the thinking trace.
            # For thinking models content is empty until reasoning completes.
            content: str = choice["message"].get("content") or ""
            reasoning: str = choice["message"].get("reasoning_content") or ""

            logger.debug(
                "Model '%s' | finish=%s | content_len=%d | reasoning_len=%d",
                model,
                finish_reason,
                len(content),
                len(reasoning),
            )

            if not content.strip():
                raise ProviderUnavailableError(
                    f"Model '{model}' returned empty content. "
                    f"Reasoning used {len(reasoning)} chars. "
                    f"Finish reason: {finish_reason}. "
                    "Increase the token budget or check model availability."
                )

            return self._extract_json(content)

        except ProviderUnavailableError:
            raise
        except Exception as exc:
            raise ProviderUnavailableError(
                f"{provider_label} request failed for model '{model}': {exc}"
            ) from exc

    def _extract_json(self, text: str) -> dict[str, Any]:
        """Parse JSON from a model response, handling known output quirks.

        Handles:
        1. Plain JSON string (ideal case).
        2. gpt-oss-20b prefix: ``<|channel|>final <|constrain|>JSON<|message|>{...}``
        3. JSON wrapped in markdown code fences: ```json\\n{...}\\n```
        4. JSON embedded anywhere in surrounding prose.

        Raises:
            ValueError: If no valid JSON object can be extracted.
        """
        text = text.strip()

        # 1. gpt-oss-20b structured output prefix
        if "<|message|>" in text:
            text = text.split("<|message|>", 1)[-1].strip()

        # 2. Markdown code fences (```json ... ``` or ``` ... ```)
        fence_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
        if fence_match:
            text = fence_match.group(1)

        # 3. Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 4. Extract the outermost JSON object from prose
        brace_match = re.search(r"\{[\s\S]*\}", text)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        raise ValueError(
            f"Could not extract valid JSON from model response. "
            f"First 300 chars: {text[:300]!r}"
        )
