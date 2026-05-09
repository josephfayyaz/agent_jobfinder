from __future__ import annotations

from typing import Any, Callable


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


def generate_openai_json(
    *,
    client: Any,
    model: str,
    system_prompt: str,
    user_prompt: str,
    timeout_seconds: float,
    include_usage: bool,
    json_extractor: Callable[[str], dict[str, Any]],
    usage_builder: Callable[..., dict[str, Any]],
    provider_error_cls: type[Exception],
) -> dict[str, Any] | tuple[dict[str, Any], dict[str, Any]]:
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            timeout=timeout_seconds,
        )
        text = response.choices[0].message.content
        payload = json_extractor(text)
        if not include_usage:
            return payload
        usage = getattr(response, "usage", None)
        input_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        total_tokens = int(getattr(usage, "total_tokens", 0) or 0) or (input_tokens + output_tokens)
        return payload, usage_builder(
            "openai",
            model=model,
            total_tokens=total_tokens,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
    except Exception as exc:
        exc_str = str(exc).lower()
        if "429" in exc_str or "rate limit" in exc_str or "quota" in exc_str:
            raise _provider_error(
                provider_error_cls,
                "OPENAI_QUOTA_EXCEEDED: OpenAI rate limit or quota reached. "
                "Check your billing or switch provider.",
                provider="openai",
                category="quota",
                retryable=False,
            ) from exc
        raise _provider_error(
            provider_error_cls,
            f"OpenAI request failed: {type(exc).__name__}: {str(exc)[:200]}",
        ) from exc
