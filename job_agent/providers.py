"""Shared provider-mode normalization and display helpers."""

from __future__ import annotations

from typing import Any

from job_agent.config import settings

VALID_PROVIDER_MODES = {"openai", "gemini", "anthropic", "lm_studio", "ollama"}
LEGACY_PROVIDER_PRIORITY = ("lm_studio", "ollama", "openai", "gemini", "anthropic")
PROVIDER_CAPABILITIES: dict[str, dict[str, Any]] = {
    "openai": {
        "label": "OpenAI",
        "supports_native_json": True,
        "supports_system_instruction": True,
        "supports_usage_metadata": True,
        "validation_probe": "live_generation",
        "workflow_prompt_char_limits": {
            "intake": 24_000,
            "jd_scoring": 18_000,
            "cv_writer": 20_000,
            "compliance_matrix": 18_000,
        },
    },
    "gemini": {
        "label": "Google Gemini",
        "supports_native_json": True,
        "supports_system_instruction": True,
        "supports_usage_metadata": True,
        "validation_probe": "live_generation",
        "workflow_prompt_char_limits": {
            "intake": 14_000,
            "jd_scoring": 16_000,
            "cv_writer": 18_000,
            "compliance_matrix": 16_000,
        },
    },
    "anthropic": {
        "label": "Claude",
        "supports_native_json": False,
        "supports_system_instruction": True,
        "supports_usage_metadata": True,
        "validation_probe": "models_list",
        "workflow_prompt_char_limits": {
            "intake": 22_000,
            "jd_scoring": 18_000,
            "cv_writer": 20_000,
            "compliance_matrix": 18_000,
        },
    },
    "lm_studio": {
        "label": "Local Gateway",
        "supports_native_json": False,
        "supports_system_instruction": False,
        "supports_usage_metadata": False,
        "validation_probe": "openai_chat_probe",
        "workflow_prompt_char_limits": {
            "intake": 12_000,
            "jd_scoring": 12_000,
            "cv_writer": 14_000,
            "compliance_matrix": 12_000,
        },
    },
    "ollama": {
        "label": "Ollama",
        "supports_native_json": False,
        "supports_system_instruction": False,
        "supports_usage_metadata": False,
        "validation_probe": "openai_chat_probe",
        "workflow_prompt_char_limits": {
            "intake": 10_000,
            "jd_scoring": 12_000,
            "cv_writer": 12_000,
            "compliance_matrix": 10_000,
        },
    },
}


def normalize_provider_mode(value: str | None, *, default: str = "openai") -> str:
    mode = str(value or "").strip().lower()
    if mode == "local":
        return "lm_studio"
    if mode == "mixed":
        return _resolve_legacy_mixed_provider(default)
    if mode in VALID_PROVIDER_MODES:
        return mode
    return default


def provider_readiness_snapshot() -> dict[str, bool]:
    return {
        "openai_ready": bool(settings.openai_api_key.strip()),
        "gemini_ready": bool(settings.gemini_api_key.strip()),
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


def _resolve_legacy_mixed_provider(default: str) -> str:
    fallback = normalize_provider_mode(default) if default != "mixed" else "openai"
    readiness = provider_readiness_snapshot()
    for mode in LEGACY_PROVIDER_PRIORITY:
        if readiness.get(f"{mode}_ready"):
            return mode
    return fallback


def provider_setup_status() -> dict[str, Any]:
    mode = normalize_provider_mode(getattr(settings, "llm_provider_mode", "openai"))
    readiness = provider_readiness_snapshot()
    configured = any(readiness.values())

    if mode == "openai":
        ready = readiness["openai_ready"]
    elif mode == "gemini":
        ready = readiness["gemini_ready"]
    elif mode == "anthropic":
        ready = readiness["anthropic_ready"]
    elif mode == "ollama":
        ready = readiness["ollama_ready"]
    elif mode == "lm_studio":
        ready = readiness["lm_studio_ready"]
    else:
        ready = False

    return {
        "mode": mode,
        "configured": configured,
        "ready": ready,
        "capabilities": provider_capabilities(mode),
        **readiness,
    }


def provider_display(mode: str | None = None) -> tuple[str, str]:
    normalized = normalize_provider_mode(mode or getattr(settings, "llm_provider_mode", "openai"))
    if normalized == "openai":
        return ("OpenAI", "Cloud workflow active")
    if normalized == "gemini":
        return ("Google Gemini", "Gemini workflow active")
    if normalized == "anthropic":
        return ("Claude", "Anthropic workflow active")
    if normalized == "ollama":
        return ("Ollama", "Local Ollama workflow")
    return ("Local Gateway", "OpenAI-compatible local workflow")


def provider_capabilities(mode: str | None = None) -> dict[str, Any]:
    normalized = normalize_provider_mode(mode or getattr(settings, "llm_provider_mode", "openai"))
    return dict(PROVIDER_CAPABILITIES.get(normalized) or PROVIDER_CAPABILITIES["openai"])


def provider_prompt_char_limit(workflow: str, mode: str | None = None, default: int = 12000) -> int:
    capabilities = provider_capabilities(mode)
    limits = dict(capabilities.get("workflow_prompt_char_limits") or {})
    return int(limits.get(workflow, default) or default)
