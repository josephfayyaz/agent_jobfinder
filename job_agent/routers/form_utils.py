"""Small request/form helpers shared across routers."""

from __future__ import annotations

from urllib.parse import parse_qs

from fastapi import Request


async def _parse_urlencoded_body(request: Request) -> dict[str, str]:
    raw_body = (await request.body()).decode("utf-8")
    parsed = parse_qs(raw_body, keep_blank_values=True)
    return {key: values[-1] for key, values in parsed.items()}


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _append_unique(items: list[str], value: str) -> None:
    normalized = value.strip()
    if not normalized:
        return
    if any(existing.lower() == normalized.lower() for existing in items):
        return
    items.append(normalized)

