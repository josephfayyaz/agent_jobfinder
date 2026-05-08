"""
LLM Router — single entry point for all model calls.

Supports these backends:
  1. LM Studio (or another OpenAI-compatible local server)
  2. Ollama (OpenAI-compatible local endpoint)
  3. Anthropic Claude API
  4. OpenAI API
  5. Google Gemini API

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

from job_agent.config import normalize_lm_studio_base_url, settings
from job_agent.llm_adapters import (
    generate_claude_json,
    generate_gemini_json,
    generate_local_gateway_json,
    generate_ollama_json,
    generate_openai_json,
)
from job_agent.provider_errors import error_info
from job_agent.providers import (
    normalize_provider_mode,
    provider_capabilities,
    provider_setup_status,
)

logger = logging.getLogger(__name__)


class ProviderUnavailableError(RuntimeError):
    """Raised when a provider cannot be reached or returns an unexpected response."""

    def __init__(
        self,
        message: str,
        *,
        provider: str = "",
        category: str = "unavailable",
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.provider = str(provider or "")
        self.category = str(category or "unavailable")
        self.retryable = bool(retryable)


def _gemini_api_url(model: str) -> str:
    return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _gemini_text_from_response(data: dict[str, Any]) -> str:
    prompt_feedback = data.get("promptFeedback") or {}
    if prompt_feedback.get("blockReason"):
        info = error_info(
            "gemini",
            "blocked_content",
            f"Gemini blocked the prompt: {prompt_feedback.get('blockReason')}.",
        )
        raise ProviderUnavailableError(
            info.message,
            provider=info.provider,
            category=info.category,
            retryable=info.retryable,
        )

    candidates = data.get("candidates") or []
    if not candidates:
        info = error_info("gemini", "empty_output", "Gemini returned no candidates.")
        raise ProviderUnavailableError(
            info.message,
            provider=info.provider,
            category=info.category,
            retryable=info.retryable,
        )

    candidate = candidates[0] if isinstance(candidates[0], dict) else {}
    finish_reason = str(candidate.get("finishReason") or "").strip()
    content = candidate.get("content") or {}
    parts = content.get("parts") or []
    text = "".join(str(part.get("text") or "") for part in parts if isinstance(part, dict)).strip()
    if text:
        return text

    if finish_reason:
        info = error_info(
            "gemini",
            "empty_output",
            f"Gemini returned no text content (finish reason: {finish_reason}).",
        )
        raise ProviderUnavailableError(
            info.message,
            provider=info.provider,
            category=info.category,
            retryable=info.retryable,
        )
    info = error_info("gemini", "empty_output", "Gemini returned empty content.")
    raise ProviderUnavailableError(
        info.message,
        provider=info.provider,
        category=info.category,
        retryable=info.retryable,
    )


def _gemini_body_preview(response: httpx.Response) -> str:
    try:
        body_preview = (response.text or "").strip()
    except Exception:
        body_preview = ""
    return body_preview[:300]


def _gemini_payload(
    *,
    system_prompt: str,
    user_prompt: str,
    json_mode: bool,
) -> dict[str, Any]:
    system_text = system_prompt if json_mode else f"{system_prompt}\n\nReturn valid JSON only."
    generation_config: dict[str, Any] = {
        "temperature": 0.2,
    }
    if json_mode:
        generation_config["responseMimeType"] = "application/json"
    return {
        "system_instruction": {
            "parts": [{"text": system_text}],
        },
        "contents": [{"parts": [{"text": user_prompt}]}],
        "generationConfig": generation_config,
    }


def _gemini_size_or_context_issue(detail: str) -> bool:
    lowered = detail.casefold()
    return any(
        token in lowered
        for token in (
            "context",
            "token",
            "too long",
            "request too large",
            "payload too large",
            "prompt is too long",
            "maximum context",
            "input too long",
            "size exceeds",
        )
    )


def _trim_prompt_for_retry(text: str, *, max_chars: int = 12_000) -> str:
    cleaned = str(text or "").strip()
    if len(cleaned) <= max_chars:
        return cleaned
    keep_head = max_chars // 2
    keep_tail = max_chars - keep_head - 64
    head = cleaned[:keep_head].rstrip()
    tail = cleaned[-keep_tail:].lstrip() if keep_tail > 0 else ""
    return f"{head}\n\n[... truncated for Gemini retry ...]\n\n{tail}".strip()


def _usage_payload(
    provider: str,
    *,
    model: str = "",
    total_tokens: int = 0,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> dict[str, Any]:
    return {
        "provider": provider,
        "model": model,
        "tokens": max(int(total_tokens or 0), 0),
        "input_tokens": max(int(input_tokens or 0), 0),
        "output_tokens": max(int(output_tokens or 0), 0),
    }


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

    @staticmethod
    def _retry_delay_seconds(attempt: int, exc: Exception) -> int:
        if isinstance(exc, ProviderUnavailableError) and exc.retryable:
            if exc.category in {"timeout", "service_unavailable", "rate_limit"}:
                return min(30, 5 * (attempt + 1))
        return 2 ** attempt

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
        capabilities = provider_capabilities(provider_mode)
        logger.debug(
            "Provider '%s' selected (native_json=%s).",
            provider_mode,
            capabilities.get("supports_native_json"),
        )
        if provider_mode == "openai":
            return self.generate_with_openai(
                model=self._openai_model_for_role(role),
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        if provider_mode == "gemini":
            return self.generate_with_gemini(system_prompt=system_prompt, user_prompt=user_prompt)
        if provider_mode == "anthropic":
            return self.generate_with_claude(system_prompt=system_prompt, user_prompt=user_prompt)
        if provider_mode == "ollama":
            return self._generate_ollama(
                role=role,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
            )
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
        base_attempts = max(1, getattr(settings, "llm_retry_attempts", 2))
        max_attempts = base_attempts
        last_exc: Exception | None = None
        attempt = 0
        while attempt < max_attempts:
            try:
                return self.generate(
                    role=role,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                )
            except (ProviderUnavailableError, ValueError) as exc:
                last_exc = exc
                if (
                    isinstance(exc, ProviderUnavailableError)
                    and exc.retryable
                    and max_attempts == base_attempts
                ):
                    max_attempts = max(base_attempts, 3)
                if attempt < max_attempts - 1:
                    import time

                    delay = self._retry_delay_seconds(attempt, exc)
                    logger.warning(
                        "LLM call failed (attempt %d/%d); retrying in %ss: %s",
                        attempt + 1,
                        max_attempts,
                        delay,
                        exc,
                    )
                    time.sleep(delay)
                attempt += 1

        if last_exc is not None:
            raise last_exc
        raise ProviderUnavailableError("LLM call failed after retries.")

    def generate_with_usage(
        self,
        *,
        role: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if role not in self._ROLE_MAP:
            raise ValueError(f"Unknown model role '{role}'. Valid roles: {list(self._ROLE_MAP)}")

        provider_mode = normalize_provider_mode(getattr(settings, "llm_provider_mode", "openai"))
        capabilities = provider_capabilities(provider_mode)
        logger.debug(
            "Provider '%s' selected for usage metadata (supports_usage_metadata=%s).",
            provider_mode,
            capabilities.get("supports_usage_metadata"),
        )
        if provider_mode == "openai":
            return self.generate_with_openai(
                model=self._openai_model_for_role(role),
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                include_usage=True,
            )
        if provider_mode == "gemini":
            return self.generate_with_gemini(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                include_usage=True,
            )
        if provider_mode == "anthropic":
            return self.generate_with_claude(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                include_usage=True,
            )
        if provider_mode == "ollama":
            return self._generate_ollama(
                role=role,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                include_usage=True,
            )
        return self._generate_local(
            role=role,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            include_usage=True,
        )

    def generate_with_retry_usage(
        self,
        *,
        role: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        base_attempts = max(1, getattr(settings, "llm_retry_attempts", 2))
        max_attempts = base_attempts
        last_exc: Exception | None = None
        attempt = 0
        while attempt < max_attempts:
            try:
                return self.generate_with_usage(
                    role=role,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                )
            except (ProviderUnavailableError, ValueError) as exc:
                last_exc = exc
                if (
                    isinstance(exc, ProviderUnavailableError)
                    and exc.retryable
                    and max_attempts == base_attempts
                ):
                    max_attempts = max(base_attempts, 3)
                if attempt < max_attempts - 1:
                    import time

                    delay = self._retry_delay_seconds(attempt, exc)
                    logger.warning(
                        "LLM call failed (attempt %d/%d); retrying in %ss: %s",
                        attempt + 1,
                        max_attempts,
                        delay,
                        exc,
                    )
                    time.sleep(delay)
                attempt += 1

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
        include_usage: bool = False,
    ) -> dict[str, Any] | tuple[dict[str, Any], dict[str, Any]]:
        return generate_local_gateway_json(
            role=role,
            role_map=self._ROLE_MAP,
            settings_obj=settings,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            include_usage=include_usage,
            json_extractor=self._extract_json,
            usage_builder=_usage_payload,
            provider_error_cls=ProviderUnavailableError,
        )

    def _generate_ollama(
        self,
        *,
        role: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        include_usage: bool = False,
    ) -> dict[str, Any] | tuple[dict[str, Any], dict[str, Any]]:
        return generate_ollama_json(
            role=role,
            role_map=self._ROLE_MAP,
            ollama_role_map=self._OLLAMA_ROLE_MAP,
            settings_obj=settings,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            include_usage=include_usage,
            json_extractor=self._extract_json,
            usage_builder=_usage_payload,
            provider_error_cls=ProviderUnavailableError,
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
        include_usage: bool = False,
    ) -> dict[str, Any] | tuple[dict[str, Any], dict[str, Any]]:
        """Generate a JSON response using the configured Claude model.

        Raises:
            ProviderUnavailableError: If ANTHROPIC_API_KEY is not configured.
        """
        if self._anthropic_client is None:
            raise ProviderUnavailableError(
                "Anthropic API key is not configured. "
                "Set ANTHROPIC_API_KEY in your .env file."
            )
        return generate_claude_json(
            client=self._anthropic_client,
            model=settings.anthropic_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            include_usage=include_usage,
            json_extractor=self._extract_json,
            usage_builder=_usage_payload,
            provider_error_cls=ProviderUnavailableError,
        )

    def generate_with_openai(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        include_usage: bool = False,
    ) -> dict[str, Any] | tuple[dict[str, Any], dict[str, Any]]:
        """Generate a JSON response using OpenAI (escalation path).

        Raises:
            ProviderUnavailableError: If OPENAI_API_KEY is not configured.
        """
        if self._openai_client is None:
            raise ProviderUnavailableError(
                "OpenAI API key is not configured. "
                "Set OPENAI_API_KEY in your .env file.",
                provider="openai",
                category="auth",
            )
        return generate_openai_json(
            client=self._openai_client,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            timeout_seconds=settings.openai_request_timeout_seconds,
            include_usage=include_usage,
            json_extractor=self._extract_json,
            usage_builder=_usage_payload,
            provider_error_cls=ProviderUnavailableError,
        )

    def generate_with_gemini(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        include_usage: bool = False,
    ) -> dict[str, Any] | tuple[dict[str, Any], dict[str, Any]]:
        """Generate a JSON response using Google Gemini."""
        if not settings.gemini_api_key.strip():
            raise ProviderUnavailableError(
                "Gemini API key is not configured. Set GEMINI_API_KEY in your .env file.",
                provider="gemini",
                category="auth",
            )
        return generate_gemini_json(
            api_key=settings.gemini_api_key.strip(),
            model=settings.gemini_model,
            timeout_seconds=settings.openai_request_timeout_seconds,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            include_usage=include_usage,
            api_url_builder=_gemini_api_url,
            payload_builder=_gemini_payload,
            text_from_response=_gemini_text_from_response,
            body_preview=_gemini_body_preview,
            size_or_context_issue=_gemini_size_or_context_issue,
            trim_prompt_for_retry=_trim_prompt_for_retry,
            json_extractor=self._extract_json,
            usage_builder=_usage_payload,
            provider_error_cls=ProviderUnavailableError,
        )

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
            "gemini": {
                "enabled": bool(settings.gemini_api_key),
                "model": settings.gemini_model,
            },
            "active": provider,
        }

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _lm_studio_reachable(self) -> bool:
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{normalize_lm_studio_base_url(settings.lm_studio_base_url)}/models")
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

        repaired = self._repair_json_closers(text)
        if repaired != text:
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                pass

        # 4. Extract the outermost JSON object from prose
        brace_match = re.search(r"\{[\s\S]*\}", text)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                repaired = self._repair_json_closers(brace_match.group(0))
                if repaired != brace_match.group(0):
                    try:
                        return json.loads(repaired)
                    except json.JSONDecodeError:
                        pass

        raise ValueError(
            f"Could not extract valid JSON from model response. "
            f"First 300 chars: {text[:300]!r}"
        )

    @staticmethod
    def _repair_json_closers(text: str) -> str:
        """Repair simple truncated JSON by appending missing closing braces/brackets."""
        stack: list[str] = []
        in_string = False
        escaped = False

        for char in text:
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
            elif char == "{":
                stack.append("}")
            elif char == "[":
                stack.append("]")
            elif char in "}]":
                if stack and stack[-1] == char:
                    stack.pop()

        if in_string:
            text += '"'
        if stack:
            text += "".join(reversed(stack))
        return text
