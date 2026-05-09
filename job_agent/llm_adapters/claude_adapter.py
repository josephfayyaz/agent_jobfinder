from __future__ import annotations

from typing import Any, Callable


def _provider_error(provider_error_cls: type[Exception], message: str) -> Exception:
    try:
        return provider_error_cls(message)
    except TypeError:
        return provider_error_cls(str(message))


def generate_claude_json(
    *,
    client: Any,
    model: str,
    system_prompt: str,
    user_prompt: str,
    include_usage: bool,
    json_extractor: Callable[[str], dict[str, Any]],
    usage_builder: Callable[..., dict[str, Any]],
    provider_error_cls: type[Exception],
) -> dict[str, Any] | tuple[dict[str, Any], dict[str, Any]]:
    try:
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = response.content[0].text
        payload = json_extractor(text)
        if not include_usage:
            return payload
        usage = getattr(response, "usage", None)
        input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        return payload, usage_builder(
            "anthropic",
            model=model,
            total_tokens=input_tokens + output_tokens,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
    except Exception as exc:
        raise _provider_error(
            provider_error_cls,
            f"Claude request failed: {type(exc).__name__}: {str(exc)[:200]}",
        ) from exc
