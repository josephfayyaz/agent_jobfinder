from __future__ import annotations

import logging
from typing import Any, Callable

import httpx

from job_agent.config import normalize_lm_studio_base_url

logger = logging.getLogger(__name__)


def _provider_error(
    provider_error_cls: type[Exception],
    message: str,
    *,
    provider: str,
    category: str = "unavailable",
    retryable: bool = False,
) -> Exception:
    try:
        return provider_error_cls(
            message,
            provider=provider,
            category=category,
            retryable=retryable,
        )
    except TypeError:
        return provider_error_cls(message)


def _call_openai_compatible_local(
    *,
    model: str,
    max_tokens: int,
    settings_obj: Any,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    provider_label: str,
    base_url: str | None,
    include_usage: bool,
    json_extractor: Callable[[str], dict[str, Any]],
    usage_builder: Callable[..., dict[str, Any]],
    provider_error_cls: type[Exception],
) -> dict[str, Any] | tuple[dict[str, Any], dict[str, Any]]:
    provider = "ollama" if provider_label.lower() == "ollama" else "lm_studio"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    def _shorten_prompt(text: str, max_chars: int = 12_000) -> str:
        raw = str(text or "")
        if len(raw) <= max_chars:
            return raw
        keep_head = int(max_chars * 0.65)
        keep_tail = max_chars - keep_head - 64
        keep_tail = max(0, keep_tail)
        omitted = len(raw) - keep_head - keep_tail
        marker = f"\n\n[... trimmed {omitted} chars for local model context ...]\n\n"
        tail = raw[-keep_tail:] if keep_tail else ""
        return f"{raw[:keep_head]}{marker}{tail}"

    try:
        with httpx.Client(timeout=settings_obj.lm_studio_request_timeout_seconds) as client:
            target_url = (
                f"{normalize_lm_studio_base_url(base_url or settings_obj.lm_studio_base_url).rstrip('/')}"
                "/chat/completions"
            )
            response = client.post(target_url, json=payload)
            if response.status_code == 400:
                detail = (response.text or "").lower()
                if any(token in detail for token in ("context", "prompt", "token", "length")):
                    reduced_payload = dict(payload)
                    reduced_payload["max_tokens"] = max(128, min(int(max_tokens), 768))
                    reduced_payload["messages"] = [
                        {"role": "system", "content": _shorten_prompt(system_prompt)},
                        {"role": "user", "content": _shorten_prompt(user_prompt)},
                    ]
                    logger.warning(
                        "Retrying local LLM call for model '%s' with trimmed prompt and max_tokens=%d",
                        model,
                        reduced_payload["max_tokens"],
                    )
                    response = client.post(target_url, json=reduced_payload)
                elif "temperature" in detail:
                    no_temp_payload = dict(payload)
                    no_temp_payload.pop("temperature", None)
                    logger.warning(
                        "Retrying local LLM call for model '%s' without temperature field",
                        model,
                    )
                    response = client.post(target_url, json=no_temp_payload)
            response.raise_for_status()

        body = response.json()
        choice = body["choices"][0]
        finish_reason = choice.get("finish_reason", "")

        if finish_reason == "length":
            raise _provider_error(
                provider_error_cls,
                (
                    f"Model '{model}' output was cut off at max_tokens={max_tokens}. "
                    "Increase LM_STUDIO_MAX_TOKENS_* in your .env or reduce the prompt size."
                ),
                provider=provider,
                category="context_too_large",
                retryable=True,
            )

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
            raise _provider_error(
                provider_error_cls,
                (
                    f"Model '{model}' returned empty content. "
                    f"Reasoning used {len(reasoning)} chars. "
                    f"Finish reason: {finish_reason}. "
                    "Increase the token budget or check model availability."
                ),
                provider=provider,
                category="empty_output",
            )

        parsed_payload = json_extractor(content)
        if not include_usage:
            return parsed_payload
        return parsed_payload, usage_builder(provider, model=model)
    except provider_error_cls:
        raise
    except httpx.HTTPStatusError as exc:
        body_preview = ""
        try:
            body_preview = (exc.response.text or "").strip()
        except Exception:
            body_preview = ""
        detail = f" ({body_preview[:300]})" if body_preview else ""
        category = "unavailable"
        retryable = False
        lowered = body_preview.lower()
        if int(getattr(exc.response, "status_code", 0) or 0) == 400 and any(
            token in lowered for token in ("context", "prompt", "token", "length")
        ):
            category = "context_too_large"
            retryable = True
        raise _provider_error(
            provider_error_cls,
            f"{provider_label} request failed for model '{model}': {type(exc).__name__}: {str(exc)[:200]}{detail}",
            provider=provider,
            category=category,
            retryable=retryable,
        ) from exc
    except Exception as exc:
        raise _provider_error(
            provider_error_cls,
            f"{provider_label} request failed for model '{model}': {type(exc).__name__}: {str(exc)[:200]}",
            provider=provider,
            category="unavailable",
        ) from exc


def generate_local_gateway_json(
    *,
    role: str,
    role_map: dict[str, tuple[str, str]],
    settings_obj: Any,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    include_usage: bool,
    json_extractor: Callable[[str], dict[str, Any]],
    usage_builder: Callable[..., dict[str, Any]],
    provider_error_cls: type[Exception],
) -> dict[str, Any] | tuple[dict[str, Any], dict[str, Any]]:
    model_attr, tokens_attr = role_map[role]
    model: str = getattr(settings_obj, model_attr)
    max_tokens: int = getattr(settings_obj, tokens_attr)

    if not model:
        raise _provider_error(
            provider_error_cls,
            (
                f"Model role '{role}' is not configured. "
                f"Set {model_attr.upper()} in your .env file."
            ),
            provider="lm_studio",
        )

    return _call_openai_compatible_local(
        model=model,
        max_tokens=max_tokens,
        settings_obj=settings_obj,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        provider_label="LM Studio",
        base_url=None,
        include_usage=include_usage,
        json_extractor=json_extractor,
        usage_builder=usage_builder,
        provider_error_cls=provider_error_cls,
    )


def generate_ollama_json(
    *,
    role: str,
    role_map: dict[str, tuple[str, str]],
    ollama_role_map: dict[str, str],
    settings_obj: Any,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    include_usage: bool,
    json_extractor: Callable[[str], dict[str, Any]],
    usage_builder: Callable[..., dict[str, Any]],
    provider_error_cls: type[Exception],
) -> dict[str, Any] | tuple[dict[str, Any], dict[str, Any]]:
    model_attr = ollama_role_map.get(role, "ollama_fast_model")
    model = getattr(settings_obj, model_attr, "")
    if not model:
        raise _provider_error(
            provider_error_cls,
            (
                f"Ollama model for role '{role}' is not configured. "
                f"Set {model_attr.upper()} in your settings."
            ),
            provider="ollama",
        )

    ollama_base = getattr(settings_obj, "ollama_base_url", "http://localhost:11434").rstrip("/")
    if not ollama_base:
        raise _provider_error(
            provider_error_cls,
            "Ollama base URL is not configured.",
            provider="ollama",
        )

    max_tokens = getattr(
        settings_obj,
        role_map.get(role, ("", "lm_studio_max_tokens_small"))[1],
        settings_obj.lm_studio_max_tokens_small,
    )
    return _call_openai_compatible_local(
        model=model,
        max_tokens=max_tokens,
        settings_obj=settings_obj,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        provider_label="Ollama",
        base_url=f"{ollama_base}/v1",
        include_usage=include_usage,
        json_extractor=json_extractor,
        usage_builder=usage_builder,
        provider_error_cls=provider_error_cls,
    )
