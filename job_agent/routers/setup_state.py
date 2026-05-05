"""Single-user setup state, ownership, and verified-fact helpers."""

from __future__ import annotations

from urllib.parse import quote

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from job_agent.config import settings
from job_agent.models import (
    Candidate,
    EducationFact,
    ExperienceFact,
    FactSource,
    ProjectFact,
    VerifiedCandidateFact,
)
from job_agent.providers import provider_setup_status
from job_agent.runtime_paths import user_settings_path
from job_agent.search_preferences import MAX_DISCOVERY_ROLES
from job_agent.services.fact_sheet_readiness import fact_sheet_is_ground_truth_ready
from job_agent.services.fact_sheet_json import FactSheetJsonIngestionService

VALID_VERIFIED_FACT_TYPES = {
    "achievement",
    "general",
    "language",
    "metric",
    "project",
    "responsibility",
    "skill",
    "tool",
}
_USER_SETTINGS_FILE = user_settings_path()


def _user_settings_file():
    return _USER_SETTINGS_FILE


def _onboarding_complete() -> bool:
    return _user_settings_file().exists()


def _provider_setup_status() -> dict[str, object]:
    snapshot = provider_setup_status()
    return {
        "mode": snapshot["mode"],
        "configured": snapshot["configured"],
        "ready": snapshot["ready"],
        "openai_ready": snapshot["openai_ready"],
        "gemini_ready": snapshot["gemini_ready"],
        "anthropic_ready": snapshot["anthropic_ready"],
        "local_ready": snapshot["lm_studio_ready"],
        "lm_studio_ready": snapshot["lm_studio_ready"],
        "ollama_ready": snapshot["ollama_ready"],
    }


def _owner_candidate(db: Session) -> Candidate | None:
    candidate_id = settings.default_candidate_id.strip()
    if candidate_id:
        candidate = db.get(Candidate, candidate_id)
        if candidate is not None:
            return candidate

    fallback = db.query(Candidate).order_by(Candidate.created_at.asc()).first()
    if fallback is not None and fallback.id != candidate_id:
        _persist_default_candidate_id(fallback.id)
    return fallback


def _active_candidate_id(db: Session) -> str | None:
    candidate = _owner_candidate(db)
    return candidate.id if candidate is not None else None


def _setup_status_payload(db: Session) -> dict[str, object]:
    provider = _provider_setup_status()
    candidate = _owner_candidate(db)
    candidate_id = candidate.id if candidate is not None else settings.default_candidate_id.strip()
    identity_ready = bool(candidate and candidate.full_name.strip() and (candidate.email or "").strip())

    fact_sheet_ready = False
    evidence_count = 0
    fact_source_count = 0
    if candidate is not None:
        fact_source_count = db.query(FactSource).filter(FactSource.candidate_id == candidate.id).count()
        experience_count = db.query(ExperienceFact).filter(ExperienceFact.candidate_id == candidate.id).count()
        project_count = db.query(ProjectFact).filter(ProjectFact.candidate_id == candidate.id).count()
        education_count = db.query(EducationFact).filter(EducationFact.candidate_id == candidate.id).count()
        skills = candidate.skills_json if isinstance(candidate.skills_json, dict) else {}
        skills_count = sum(len(value or []) for value in skills.values() if isinstance(value, list))
        evidence_count = experience_count + project_count + education_count + skills_count
        fact_sheet_ready = fact_source_count > 0 and evidence_count > 0
        if fact_sheet_ready:
            try:
                fact_sheet_ready = fact_sheet_is_ground_truth_ready(
                    FactSheetJsonIngestionService(db).export_json(candidate.id)
                )
            except ValueError:
                fact_sheet_ready = False

    search_focus = [query for query in settings.jobspy_discover_queries[:MAX_DISCOVERY_ROLES] if str(query).strip()]
    search_focus_ready = bool(search_focus)
    missing_steps: list[str] = []
    if not provider["ready"]:
        missing_steps.append("Connect an AI provider")
    if not identity_ready:
        missing_steps.append("Create your candidate profile")
    if not fact_sheet_ready:
        missing_steps.append("Build your fact sheet")
    if not search_focus_ready:
        missing_steps.append("Choose target roles")

    complete = bool(provider["ready"] and identity_ready and fact_sheet_ready and search_focus_ready)
    return {
        "complete": complete,
        "configured": _onboarding_complete(),
        "provider": provider,
        "candidate_id": candidate.id if candidate else "",
        "candidate_name": candidate.full_name if candidate else "",
        "candidate_email": candidate.email if candidate else "",
        "candidate_id_set": bool(candidate_id),
        "candidate_exists": candidate is not None,
        "identity_ready": identity_ready,
        "fact_sheet_ready": fact_sheet_ready,
        "fact_source_count": fact_source_count,
        "evidence_count": evidence_count,
        "search_focus_ready": search_focus_ready,
        "search_focus": search_focus,
        "missing_steps": missing_steps,
    }


def _setup_gate_enabled() -> bool:
    return settings.app_env.strip().lower() != "test"


def _redirect_if_setup_required(request: Request, db: Session) -> RedirectResponse | None:
    if not _setup_gate_enabled():
        return None
    setup_status = _setup_status_payload(db)
    if setup_status["complete"]:
        return None
    target = request.url.path
    if request.url.query:
        target = f"{target}?{request.url.query}"
    return RedirectResponse(
        url=f"/ui/setup-required?next={quote(target, safe='')}",
        status_code=303,
    )


def _raise_if_setup_required(db: Session) -> None:
    if not _setup_gate_enabled():
        return
    setup_status = _setup_status_payload(db)
    if not setup_status["complete"]:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "setup_required",
                "message": "Finish the quick setup first so Job Agent has a candidate profile and target roles.",
                "setup": setup_status,
            },
        )


def _verified_fact_scope_filter(candidate_id: str | None):
    if candidate_id:
        return (
            (VerifiedCandidateFact.candidate_id == candidate_id)
            | (VerifiedCandidateFact.candidate_id.is_(None))
        )
    return VerifiedCandidateFact.candidate_id.is_(None)


def _verified_fact_key(gap_label: str, evidence: str) -> str:
    return f"{gap_label.strip().casefold()}||{evidence.strip().casefold()}"


def _sanitize_verified_fact_type(value: object) -> str:
    fact_type = str(value or "general").strip().lower().replace(" ", "_")
    return fact_type if fact_type in VALID_VERIFIED_FACT_TYPES else "general"


def _persist_default_candidate_id(candidate_id: str) -> None:
    from job_agent.config import settings as settings_singleton
    from job_agent.user_config import write_user_settings

    write_user_settings({"default_candidate_id": candidate_id})
    # Keep runtime overrides intact (notably app_env in tests) and only update
    # the field we just persisted.
    object.__setattr__(settings_singleton, "default_candidate_id", candidate_id)
