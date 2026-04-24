"""Template context helpers for the web UI."""

from __future__ import annotations

from fastapi import Request

from job_agent.config import settings
from job_agent.db import SessionLocal
from job_agent.search_preferences import normalize_country_list, normalize_job_language_preferences

from job_agent.routers.setup_state import _onboarding_complete, _owner_candidate


def _ui_provider_mode() -> tuple[str, str]:
    provider_mode = getattr(settings, "llm_provider_mode", "openai").strip().lower()
    if provider_mode == "mixed":
        return ("Mixed", "Local drafting with cloud fallback")
    if provider_mode == "openai":
        return ("OpenAI", "Cloud workflow active")
    if provider_mode == "anthropic":
        return ("Claude", "Anthropic workflow active")
    if settings.use_openai_review and settings.use_claude_final_review:
        return ("Mixed", "Local drafting with cloud fallback")
    return ("Local", "LM Studio workflow")


def _get_candidate_display_name() -> str:
    try:
        with SessionLocal() as session:
            candidate = _owner_candidate(session)
            return candidate.full_name if candidate else ""
    except Exception:
        return ""


def _ui_context(request: Request, title: str, **extra: object) -> dict[str, object]:
    provider_label, provider_hint = _ui_provider_mode()
    search_focus = [query for query in settings.jobspy_discover_queries[:5] if query]
    candidate_id = settings.default_candidate_id.strip()
    search_countries = normalize_country_list(getattr(settings, "job_search_countries", None))
    search_languages = normalize_job_language_preferences(getattr(settings, "job_search_languages", None))
    context: dict[str, object] = {
        "request": request,
        "title": title,
        "onboarding_complete": _onboarding_complete(),
        "ui_provider_label": provider_label,
        "ui_provider_hint": provider_hint,
        "ui_candidate_id": candidate_id,
        "ui_candidate_name": _get_candidate_display_name(),
        "ui_language_label": "EN",
        "ui_search_focus": search_focus,
        "ui_search_countries": search_countries,
        "ui_job_search_languages": search_languages,
    }
    context.update(extra)
    return context

