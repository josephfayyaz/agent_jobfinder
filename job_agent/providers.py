"""Shared provider-mode normalization and display helpers."""

from __future__ import annotations

from typing import Any

from job_agent.config import settings

VALID_PROVIDER_MODES = {"openai", "anthropic", "lm_studio", "ollama", "mixed"}


def normalize_provider_mode(value: str | None, *, default: str = "openai") -> str:
    mode = str(value or "").strip().lower()
    if mode == "local":
        return "lm_studio"
    if mode in VALID_PROVIDER_MODES:
        return mode
    return default


def provider_readiness_snapshot() -> dict[str, bool]:
    return {
        "openai_ready": bool(settings.openai_api_key.strip()),
        "anthropic_ready": bool(settings.anthropic_api_key.strip()),
        "lm_studio_ready": bool(
            settings.lm_studio_base_url.strip()
            and settings.lm_studio_small_model.strip()
            and settings.lm_studio_writer_model.strip()
        ),
        "ollama_ready": bool(
            getattr(settings, "ollama_base_url", "").strip()
            and getattr(settings, "ollama_fast_model", "").strip()
            and getattr(settings, "ollama_writer_model", "").strip()
        ),
    }


def provider_setup_status() -> dict[str, Any]:
    mode = normalize_provider_mode(getattr(settings, "llm_provider_mode", "openai"))
    readiness = provider_readiness_snapshot()
    configured = any(readiness.values())

    if mode == "openai":
        ready = readiness["openai_ready"]
    elif mode == "anthropic":
        ready = readiness["anthropic_ready"]
    elif mode == "ollama":
        ready = readiness["ollama_ready"]
    elif mode == "mixed":
        ready = any(readiness.values())
    else:
        ready = readiness["lm_studio_ready"]

    return {
        "mode": mode,
        "configured": configured,
        "ready": ready,
        **readiness,
    }


def provider_display(mode: str | None = None) -> tuple[str, str]:
    normalized = normalize_provider_mode(mode or getattr(settings, "llm_provider_mode", "openai"))
    if normalized == "mixed":
        return ("Mixed", "Local-first workflow with cloud fallback")
    if normalized == "openai":
        return ("OpenAI", "Cloud workflow active")
    if normalized == "anthropic":
        return ("Claude", "Anthropic workflow active")
    if normalized == "ollama":
        return ("Ollama", "Local Ollama workflow")
    return ("LM Studio", "Local LM Studio workflow")
