from __future__ import annotations

from typing import Any, Callable

import httpx


def _provider_error(
    provider_error_cls: type[Exception],
    message: str,
    *,
    provider: str = "",
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


def generate_gemini_json(
    *,
    api_key: str,
    model: str,
    timeout_seconds: float,
    system_prompt: str,
    user_prompt: str,
    include_usage: bool,
    api_url_builder: Callable[[str], str],
    payload_builder: Callable[..., dict[str, Any]],
    text_from_response: Callable[[dict[str, Any]], str],
    body_preview: Callable[[httpx.Response], str],
    size_or_context_issue: Callable[[str], bool],
    trim_prompt_for_retry: Callable[[str], str],
    json_extractor: Callable[[str], dict[str, Any]],
    usage_builder: Callable[..., dict[str, Any]],
    provider_error_cls: type[Exception],
) -> dict[str, Any] | tuple[dict[str, Any], dict[str, Any]]:
    request_headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }
    json_mode_payload = payload_builder(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        json_mode=True,
    )
    plain_text_payload = payload_builder(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        json_mode=False,
    )

    try:
        response = httpx.post(
            api_url_builder(model),
            params={"key": api_key},
            headers=request_headers,
            json=json_mode_payload,
            timeout=timeout_seconds,
        )
        if response.is_success:
            data = response.json()
            payload = json_extractor(text_from_response(data))
            if not include_usage:
                return payload
            usage = data.get("usageMetadata") or {}
            return payload, usage_builder(
                "gemini",
                model=model,
                total_tokens=int(usage.get("totalTokenCount", 0) or 0),
                input_tokens=int(usage.get("promptTokenCount", 0) or 0),
                output_tokens=int(usage.get("candidatesTokenCount", 0) or 0),
            )

        preview_text = body_preview(response).lower()
        should_retry_shorter = response.status_code in {400, 413} and size_or_context_issue(preview_text)
        if should_retry_shorter:
            trimmed_prompt = trim_prompt_for_retry(user_prompt)
            shortened_payload = payload_builder(
                system_prompt=system_prompt,
                user_prompt=trimmed_prompt,
                json_mode=False,
            )
            retry_response = httpx.post(
                api_url_builder(model),
                params={"key": api_key},
                headers=request_headers,
                json=shortened_payload,
                timeout=timeout_seconds,
            )
            if not retry_response.is_success:
                retry_response.raise_for_status()
            retry_data = retry_response.json()
            payload = json_extractor(text_from_response(retry_data))
            if not include_usage:
                return payload
            usage = retry_data.get("usageMetadata") or {}
            return payload, usage_builder(
                "gemini",
                model=model,
                total_tokens=int(usage.get("totalTokenCount", 0) or 0),
                input_tokens=int(usage.get("promptTokenCount", 0) or 0),
                output_tokens=int(usage.get("candidatesTokenCount", 0) or 0),
            )

        should_retry_plain = response.status_code == 400 and (
            "responsemimetype" in preview_text
            or "response mime type" in preview_text
            or "invalid_argument" in preview_text
        )
        if should_retry_plain:
            retry_response = httpx.post(
                api_url_builder(model),
                params={"key": api_key},
                headers=request_headers,
                json=plain_text_payload,
                timeout=timeout_seconds,
            )
            if not retry_response.is_success:
                retry_response.raise_for_status()
            retry_data = retry_response.json()
            payload = json_extractor(text_from_response(retry_data))
            if not include_usage:
                return payload
            usage = retry_data.get("usageMetadata") or {}
            return payload, usage_builder(
                "gemini",
                model=model,
                total_tokens=int(usage.get("totalTokenCount", 0) or 0),
                input_tokens=int(usage.get("promptTokenCount", 0) or 0),
                output_tokens=int(usage.get("candidatesTokenCount", 0) or 0),
            )

        response.raise_for_status()
        raise AssertionError("unreachable")
    except provider_error_cls:
        raise
    except httpx.ReadTimeout as exc:
        raise _provider_error(
            provider_error_cls,
            f"Gemini request timed out for model '{model}': {type(exc).__name__}: {str(exc)[:200]}",
            provider="gemini",
            category="timeout",
            retryable=True,
        ) from exc
    except httpx.TimeoutException as exc:
        raise _provider_error(
            provider_error_cls,
            f"Gemini request timed out for model '{model}': {type(exc).__name__}: {str(exc)[:200]}",
            provider="gemini",
            category="timeout",
            retryable=True,
        ) from exc
    except httpx.HTTPStatusError as exc:
        preview = body_preview(exc.response)
        detail = f" ({preview[:300]})" if preview else ""
        status = int(getattr(exc.response, "status_code", 0) or 0)
        category = "unavailable"
        retryable = False
        if status in {401, 403}:
            category = "auth"
        elif status == 429:
            lowered_preview = preview.lower()
            if "quota" in lowered_preview or "billing" in lowered_preview or "exceeded your current quota" in lowered_preview:
                category = "quota"
                retryable = False
            else:
                category = "rate_limit"
                retryable = True
        elif status >= 500:
            category = "service_unavailable"
            retryable = True
        elif size_or_context_issue(preview):
            category = "context_too_large"
            retryable = True
        raise _provider_error(
            provider_error_cls,
            f"Gemini request failed for model '{model}': {type(exc).__name__}: {str(exc)[:200]}{detail}",
            provider="gemini",
            category=category,
            retryable=retryable,
        ) from exc
    except Exception as exc:
        raise _provider_error(
            provider_error_cls,
            f"Gemini request failed for model '{model}': {type(exc).__name__}: {str(exc)[:200]}",
            provider="gemini",
            category="unavailable",
        ) from exc
