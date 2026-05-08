from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ProviderErrorInfo:
    provider: str
    category: str
    message: str
    retryable: bool = False


def error_info(provider: str, category: str, message: str, *, retryable: bool = False) -> ProviderErrorInfo:
    return ProviderErrorInfo(
        provider=str(provider or ""),
        category=str(category or "unavailable"),
        message=str(message or ""),
        retryable=bool(retryable),
    )
