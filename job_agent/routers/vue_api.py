"""Read-safe Vue API contracts for the migration shell."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, selectinload

from job_agent.config import settings
from job_agent.db import get_db
from job_agent.llm import ProviderUnavailableError
from job_agent.models import (
    Application,
    CareerPageSource,
    JobPost,
    ResumeDraft,
    ResumeTrack,
    ThesisTarget,
    VerifiedCandidateFact,
)
from job_agent.providers import normalize_provider_mode
from job_agent.routers import jobs as legacy_jobs
from job_agent.routers.draft_actions import approve_draft_record
from job_agent.routers.job_views import _get_dashboard_data
from job_agent.routers.setup_state import VALID_VERIFIED_FACT_TYPES, _onboarding_complete, _setup_status_payload
from job_agent.search_preferences import LANGUAGE_OPTIONS, LEVEL_OPTIONS
from job_agent.services.gmail_oauth import GmailOAuthService
from job_agent.services.interview_bank import InterviewBankService
from job_agent.services.offer_compass import OfferCompassService
from job_agent.services.rejection_analytics import RejectionAnalyticsService
from job_agent.services.cover_letter import CoverLetterService
from job_agent.services.workspace import (
    DELETE_CONFIRMATION_PHRASE,
    RESET_CONFIRMATION_PHRASE,
    SHARE_REPOSITORY_URL,
    workspace_status,
)

router = APIRouter(prefix="/api/vue", tags=["Vue API"])

_CONTRACT_VERSION = 1
_NOT_IMPLEMENTED_MESSAGE = (
    "This endpoint is defined as a Vue API contract but is not implemented yet."
)

_NAVIGATION_GROUPS = [
    {
        "label": "Main",
        "items": [
            {"label": "Dashboard", "to": "/dashboard"},
            {"label": "Jobs", "to": "/jobs"},
            {"label": "Companies", "to": "/companies"},
            {"label": "Apply", "to": "/apply"},
            {"label": "Applications", "to": "/applications"},
            {"label": "Drafts", "to": "/drafts"},
        ],
    },
    {
        "label": "Profile",
        "items": [
            {"label": "Onboarding", "to": "/onboarding"},
            {"label": "Verified Facts", "to": "/verified-facts"},
            {"label": "Settings", "to": "/settings"},
        ],
    },
    {
        "label": "Career Tools",
        "items": [
            {"label": "Story Bank", "to": "/story-bank"},
            {"label": "Offer Compass", "to": "/offer-compass"},
            {"label": "Thesis", "to": "/thesis"},
            {"label": "Analytics", "to": "/analytics"},
        ],
    },
    {
        "label": "Workspace",
        "items": [
            {"label": "Workspace Reset", "to": "/workspace-reset"},
            {"label": "Help", "to": "/help"},
            {"label": "About", "to": "/about"},
        ],
    }
]


class ApplyScoreRequest(BaseModel):
    job_description: str = Field(default="")
    source_url: str | None = None


class ApplyQuestionsRequest(BaseModel):
    job_data: dict[str, Any] | None = None
    gaps: list[Any] = Field(default_factory=list)
    answers: dict[str, Any] = Field(default_factory=dict)
    fact_sheet_excerpt: str = Field(default="")


class ApplyDraftRequest(BaseModel):
    job_data: dict[str, Any] | None = None
    questions: list[dict[str, Any]] = Field(default_factory=list)
    answers: dict[str, Any] = Field(default_factory=dict)
    track_slug: str = Field(default="")


class DraftPatchRequest(BaseModel):
    title: str | None = None
    notes: str | None = None


class DraftActionRequest(BaseModel):
    user_confirmed: bool
    notes: str | None = None


class WorkspaceResetPreviewRequest(BaseModel):
    include_generated_files: bool = False
    include_cached_results: bool = False


def _success_payload(
    data: dict[str, object],
    *,
    status: str | None = None,
    message: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "ok": True,
        "contract_version": _CONTRACT_VERSION,
        "data": data,
    }
    if status is not None:
        payload["status"] = status
    if message is not None:
        payload["message"] = message
    return payload


def _error_payload(code: str, message: str) -> dict[str, object]:
    return {
        "ok": False,
        "contract_version": _CONTRACT_VERSION,
        "error": {
            "code": code,
            "message": message,
        },
    }


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=_error_payload(code, message))


def _placeholder_list(message: str) -> dict[str, object]:
    return _success_payload(
        {"items": [], "total": 0},
        status="placeholder",
        message=message,
    )


def _placeholder_detail(resource_id: str, message: str) -> dict[str, object]:
    return _success_payload(
        {"id": resource_id},
        status="placeholder",
        message=message,
    )


def _not_implemented_response() -> JSONResponse:
    return _error_response(501, "not_implemented", _NOT_IMPLEMENTED_MESSAGE)


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _clean_text(value: object | None) -> str | None:
    text = str(value or "").strip()
    return text or None


def _candidate_scope() -> str | None:
    candidate_id = settings.default_candidate_id.strip()
    return candidate_id or None


def _non_empty_job_description_or_422(job_description: str) -> JSONResponse | None:
    if not job_description.strip():
        return _error_response(422, "validation_error", "job_description must not be empty.")
    return None


def _job_data_or_422(job_data: dict[str, Any] | None) -> JSONResponse | None:
    if not isinstance(job_data, dict) or not job_data:
        return _error_response(422, "validation_error", "job_data must be provided.")
    return None


def _http_exception_to_contract_response(exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    code = "request_failed"
    message = "The request could not be completed."
    if isinstance(detail, dict):
        code = str(detail.get("error") or detail.get("code") or code)
        message = str(detail.get("message") or detail.get("detail") or message)
    elif isinstance(detail, str) and detail.strip():
        message = detail
        if exc.status_code == 404:
            code = "not_found"
        elif exc.status_code == 422:
            code = "validation_error"
        elif exc.status_code == 409:
            code = "setup_required"
    elif exc.status_code == 404:
        code = "not_found"
        message = "Requested resource was not found."
    return _error_response(exc.status_code, code, message)


def _provider_unavailable_response(message: str) -> JSONResponse:
    return _error_response(503, "provider_unavailable", message)


def _apply_track_options(db: Session) -> list[dict[str, str]]:
    rows = db.query(ResumeTrack).filter_by(active=True).order_by(ResumeTrack.title.asc()).all()
    return [{"slug": str(row.slug or ""), "title": str(row.title or row.slug or "Untitled track")} for row in rows]


def _resolve_track_slug(db: Session, requested_slug: str) -> str | JSONResponse:
    slug = requested_slug.strip()
    if slug:
        exists = db.query(ResumeTrack).filter(ResumeTrack.slug == slug, ResumeTrack.active.is_(True)).first()
        if exists is None:
            return _error_response(422, "validation_error", "track_slug must reference an active resume track.")
        return slug

    fallback = db.query(ResumeTrack).filter_by(active=True).order_by(ResumeTrack.title.asc()).first()
    if fallback is None:
        return _error_response(422, "validation_error", "No active resume tracks are available.")
    return str(fallback.slug or "")


def _normalize_confirmed_facts(
    questions: list[dict[str, Any]],
    answers: dict[str, Any],
) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for index, question in enumerate(questions):
        question_id = str(question.get("id") or f"q{index}")
        raw_answer = answers.get(question_id)
        if raw_answer is None:
            raw_answer = answers.get(str(index))
        answer = str(raw_answer or "").strip()
        normalized.append(
            {
                "gap": str(question.get("gap") or question.get("question") or f"Question {index + 1}"),
                "question_id": question_id,
                "answer": answer,
                "confirmed": bool(answer),
            }
        )
    return normalized


def _task_status_message(status: str, draft_id: str | None) -> str:
    normalized = status.strip().lower()
    if normalized == "completed" and draft_id:
        return "Draft generation completed."
    if normalized == "completed":
        return "Task completed."
    if normalized == "failed":
        return "Draft generation failed."
    if normalized == "running":
        return "Draft generation is running."
    return "Draft generation is pending."


def _job_summary(job: JobPost) -> dict[str, object]:
    return {
        "id": str(job.id),
        "company": job.company,
        "title": job.title,
        "location": job.location,
        "status": job.status,
        "queue_state": job.queue_state,
        "source_name": job.source_name,
        "posted_date": job.posted_date,
        "created_at": _isoformat(job.created_at),
        "updated_at": _isoformat(job.last_seen_at),
    }


def _job_detail(job: JobPost) -> dict[str, object]:
    return {
        **_job_summary(job),
        "city": job.city,
        "country": job.country,
        "remote_policy": job.remote_policy,
        "salary_text": job.salary_text,
        "role_family": job.role_family,
        "role_track_hint": job.role_track_hint,
        "description": job.description,
        "source_url": job.source_url,
        "canonical_apply_url": job.canonical_apply_url,
        "company_url": job.company_url,
    }


def _company_summary(source: CareerPageSource) -> dict[str, object]:
    return {
        "id": str(source.id),
        "name": source.company,
        "company": source.company,
        "career_url": source.career_url,
        "career_page_url_available": bool(_clean_text(source.career_url)),
        "ats_type": source.ats_type,
        "country": source.country,
        "active": source.active,
        "last_new_jobs": source.last_new_jobs,
        "last_checked_at": _isoformat(source.last_checked_at),
    }


def _application_summary(application: Application) -> dict[str, object]:
    job = getattr(application, "job_post", None)
    return {
        "id": str(application.id),
        "job_id": str(application.job_post_id),
        "job_post_id": str(application.job_post_id),
        "title": _clean_text(job.title) if job is not None else None,
        "company": _clean_text(job.company) if job is not None else None,
        "location": _clean_text(job.location) if job is not None else None,
        "resume_track_id": str(application.resume_track_id) if application.resume_track_id else None,
        "draft_id": str(application.resume_draft_id) if application.resume_draft_id else None,
        "resume_draft_id": str(application.resume_draft_id) if application.resume_draft_id else None,
        "status": application.status,
        "next_action": application.next_action,
        "applied_at": _isoformat(application.applied_at),
        "created_at": _isoformat(application.created_at),
        "updated_at": _isoformat(application.updated_at),
    }


def _application_detail(application: Application) -> dict[str, object]:
    job = getattr(application, "job_post", None)
    draft = getattr(application, "resume_draft", None)
    return {
        **_application_summary(application),
        "job": _linked_job_metadata(job),
        "draft": {
            "id": str(draft.id),
            "status": str(draft.status or ""),
            "approved": bool(draft.approved),
            "title": _clean_text(getattr(getattr(draft, "job_post", None), "title", None)),
        } if draft is not None else None,
        "notes": application.notes,
        "last_email_at": _isoformat(application.last_email_at),
    }


def _draft_summary(draft: ResumeDraft) -> dict[str, object]:
    job = getattr(draft, "job_post", None)
    track = getattr(draft, "resume_track", None)
    related_application = _first_related_application(draft)
    return {
        "id": str(draft.id),
        "job_post_id": str(draft.job_post_id),
        "job_id": str(draft.job_post_id),
        "resume_track_id": str(draft.resume_track_id),
        "candidate_id": draft.candidate_id,
        "title": _clean_text(job.title) if job is not None else None,
        "role": _clean_text(track.title) if track is not None else None,
        "company": _clean_text(job.company) if job is not None else None,
        "location": _clean_text(job.location) if job is not None else None,
        "application_id": str(related_application.id) if related_application is not None else None,
        "provider": draft.provider,
        "status": draft.status,
        "score": draft.score,
        "approved": draft.approved,
        "created_at": _isoformat(draft.created_at),
        "updated_at": _isoformat(draft.updated_at),
    }


def _linked_job_metadata(job: JobPost | None) -> dict[str, object] | None:
    if job is None:
        return None
    return {
        "id": str(job.id),
        "title": _clean_text(job.title),
        "company": _clean_text(job.company),
        "location": _clean_text(job.location),
        "source": _clean_text(job.source_name),
        "status": _clean_text(job.status),
    }


def _company_record_summary(source: CareerPageSource | None) -> dict[str, object] | None:
    if source is None:
        return None
    return {
        "id": str(source.id),
        "name": _clean_text(source.company),
        "career_page_url_available": bool(_clean_text(source.career_url)),
    }


def _first_related_application(draft: ResumeDraft) -> Application | None:
    applications = list(getattr(draft, "applications", []) or [])
    if not applications:
        return None
    return sorted(
        applications,
        key=lambda app: (_isoformat(getattr(app, "created_at", None)) or "", str(app.id)),
    )[0]


def _find_company_record_for_name(db: Session | None, company_name: str | None) -> CareerPageSource | None:
    if not company_name:
        return None
    if db is None:
        return None
    return (
        db.query(CareerPageSource)
        .filter(CareerPageSource.company == company_name)
        .order_by(CareerPageSource.id.asc())
        .first()
    )


def _find_company_record(db: Session, job: JobPost | None) -> CareerPageSource | None:
    company_name = _clean_text(job.company) if job is not None else None
    return _find_company_record_for_name(db, company_name)


def _draft_detail(draft: ResumeDraft, db: Session) -> dict[str, object]:
    job = getattr(draft, "job_post", None)
    related_application = _first_related_application(draft)
    return {
        **_draft_summary(draft),
        "job": _linked_job_metadata(job),
        "application": {
            "id": str(related_application.id),
            "status": str(related_application.status or ""),
        } if related_application is not None else None,
        "company_record": _company_record_summary(_find_company_record(db, job)),
        "has_content": bool(draft.content),
        "has_cover_letter": bool(draft.cover_letter_text),
        "review_feedback_keys": sorted((draft.review_feedback or {}).keys()),
    }


def _draft_action_payload(draft: ResumeDraft) -> dict[str, object]:
    return {
        "draft_id": str(draft.id),
        "approved": bool(draft.approved),
        "status": str(draft.status or ""),
    }


def _cover_letter_payload(draft: ResumeDraft) -> dict[str, object]:
    return {
        "draft_id": str(draft.id),
        "subject": str(draft.cover_letter_subject or ""),
        "cover_letter": str(draft.cover_letter_text or ""),
    }


def _verified_fact_summary(fact: VerifiedCandidateFact) -> dict[str, object]:
    return {
        "id": str(fact.id),
        "gap_label": fact.gap_label,
        "evidence": fact.evidence,
        "fact_type": fact.fact_type,
        "source_draft_id": str(fact.source_draft_id) if fact.source_draft_id else None,
        "source_job_id": str(fact.source_job_id) if fact.source_job_id else None,
        "created_at": _isoformat(fact.created_at),
        "is_active": fact.is_active,
    }


def _safe_workspace_snapshot() -> dict[str, object]:
    snapshot = workspace_status()
    return {
        "local_first": True,
        "has_backupable_db": bool(snapshot.get("has_backupable_db")),
        "backup_count": int(snapshot.get("backup_count") or 0),
        "legacy_runtime_present": bool(snapshot.get("legacy_runtime_present")),
    }


def _get_job_or_404(db: Session, job_id: str) -> JobPost | JSONResponse:
    try:
        parsed = UUID(job_id)
    except ValueError:
        return _error_response(404, "not_found", "Resource not found.")
    job = db.get(JobPost, parsed)
    if job is None:
        return _error_response(404, "not_found", "Resource not found.")
    return job


def _get_draft_or_404(db: Session, draft_id: str) -> ResumeDraft | JSONResponse:
    try:
        parsed = UUID(draft_id)
    except ValueError:
        return _error_response(404, "not_found", "Resource not found.")
    draft = (
        db.query(ResumeDraft)
        .options(
            selectinload(ResumeDraft.job_post),
            selectinload(ResumeDraft.resume_track),
            selectinload(ResumeDraft.applications),
        )
        .filter(ResumeDraft.id == parsed)
        .first()
    )
    if draft is None:
        return _error_response(404, "not_found", "Resource not found.")
    return draft


def _get_application_or_404(db: Session, application_id: str) -> Application | JSONResponse:
    try:
        parsed = UUID(application_id)
    except ValueError:
        return _error_response(404, "not_found", "Resource not found.")
    application = (
        db.query(Application)
        .options(
            selectinload(Application.job_post),
            selectinload(Application.resume_draft).selectinload(ResumeDraft.job_post),
        )
        .filter(Application.id == parsed)
        .first()
    )
    if application is None:
        return _error_response(404, "not_found", "Resource not found.")
    return application


def _get_company_or_404(db: Session, company_id: str) -> CareerPageSource | JSONResponse:
    try:
        parsed = int(company_id)
    except ValueError:
        return _error_response(404, "not_found", "Resource not found.")
    company = db.get(CareerPageSource, parsed)
    if company is None:
        return _error_response(404, "not_found", "Resource not found.")
    return company


@router.get("/health")
def vue_health() -> dict[str, object]:
    return _success_payload(
        {
            "service": "vue-api",
            "status": "ok",
        }
    )


@router.get("/navigation")
def vue_navigation() -> dict[str, object]:
    return _success_payload({"groups": _NAVIGATION_GROUPS})


@router.get("/setup/state")
def vue_setup_state(db: Session = Depends(get_db)) -> dict[str, object]:
    setup = _setup_status_payload(db)
    data = {
        "loaded": True,
        "setup_complete": bool(setup["complete"]),
        "provider_configured": bool(setup["provider"]["configured"]),
        "requires_setup": not bool(setup["complete"]),
        "missing_steps": list(setup["missing_steps"]),
        "identity_ready": bool(setup["identity_ready"]),
        "fact_sheet_ready": bool(setup["fact_sheet_ready"]),
        "search_focus_ready": bool(setup["search_focus_ready"]),
    }
    return _success_payload(data)


@router.get("/session")
def vue_session(db: Session = Depends(get_db)) -> dict[str, object]:
    setup = _setup_status_payload(db)
    return _success_payload(
        {
            "authenticated": True,
            "local_first": True,
            "configured": bool(_onboarding_complete()),
            "setup_complete": bool(setup["complete"]),
            "secrets_exposed": False,
        }
    )


@router.get("/dashboard/summary")
def vue_dashboard_summary(db: Session = Depends(get_db)) -> dict[str, object]:
    dashboard = _get_dashboard_data(db)
    safe_system = {
        "pdflatex_available": bool(dashboard["system"].get("pdflatex_available")),
        "lm_studio_online": bool(dashboard["system"].get("lm_studio_online")),
        "last_job_ingested": dashboard["system"].get("last_job_ingested"),
    }
    safe_sections = {
        **dashboard,
        "system": safe_system,
    }
    cards = [
        {"key": "new_jobs_24h", "label": "New Jobs (24h)", "value": dashboard["jobs"]["new_24h"]},
        {"key": "high_match_jobs", "label": "High Match", "value": dashboard["jobs"]["high_match"]},
        {
            "key": "pending_approvals",
            "label": "Pending Approvals",
            "value": dashboard["cv"]["pending_approvals"],
        },
        {
            "key": "active_applications",
            "label": "Active Applications",
            "value": sum(dashboard["applications"].values()),
        },
    ]
    return _success_payload({"cards": cards, "sections": safe_sections})


@router.get("/jobs")
def vue_jobs(db: Session = Depends(get_db)) -> dict[str, object]:
    rows = db.query(JobPost).order_by(JobPost.created_at.desc()).all()
    items = [_job_summary(job) for job in rows]
    return _success_payload({"items": items, "total": len(items)})


@router.get("/jobs/{job_id}")
def vue_job_detail(job_id: str, db: Session = Depends(get_db)):
    job = _get_job_or_404(db, job_id)
    if isinstance(job, JSONResponse):
        return job
    company_record = _find_company_record(db, job)
    return _success_payload(
        {
            "item": {
                **_job_detail(job),
                "company_id": str(company_record.id) if company_record is not None else None,
                "company_record": _company_record_summary(company_record),
            }
        }
    )


@router.get("/companies")
def vue_companies(db: Session = Depends(get_db)) -> dict[str, object]:
    rows = db.query(CareerPageSource).order_by(CareerPageSource.created_at.desc()).all()
    items = [_company_summary(row) for row in rows]
    if not items:
        return _placeholder_list(
            "This list endpoint is ready for Vue migration but not wired to real data yet."
        )
    return _success_payload({"items": items, "total": len(items)})


@router.get("/companies/{company_id}")
def vue_company_detail(company_id: str, db: Session = Depends(get_db)):
    company = _get_company_or_404(db, company_id)
    if isinstance(company, JSONResponse):
        return company
    return _success_payload({"item": _company_summary(company)})


@router.post("/apply/score")
async def vue_apply_score(payload: ApplyScoreRequest, db: Session = Depends(get_db)):
    if response := _non_empty_job_description_or_422(payload.job_description):
        return response
    try:
        result = await legacy_jobs.apply_parse(job_text=payload.job_description.strip(), db=db)
    except ProviderUnavailableError:
        return _provider_unavailable_response("Job parsing or scoring is unavailable right now.")
    except ValueError as exc:
        return _error_response(422, "validation_error", str(exc))
    except HTTPException as exc:
        return _http_exception_to_contract_response(exc)

    raw_job = dict(result.get("job") or {})
    data = {
        "score": result.get("score"),
        "matched_skills": list(result.get("matched") or []),
        "gaps": list(result.get("gaps") or []),
        "summary": str(result.get("summary") or ""),
        "job_data": raw_job,
        "track_options": _apply_track_options(db),
        "raw": result,
    }
    return _success_payload(data)


@router.post("/apply/questions")
async def vue_apply_questions(payload: ApplyQuestionsRequest, db: Session = Depends(get_db)):
    if response := _job_data_or_422(payload.job_data):
        return response
    body = {
        "job": dict(payload.job_data or {}),
        "gaps": list(payload.gaps or []),
        "fact_sheet_excerpt": payload.fact_sheet_excerpt.strip(),
    }
    try:
        result = await legacy_jobs.apply_questions(body=body, db=db)
    except HTTPException as exc:
        return _http_exception_to_contract_response(exc)
    except ValueError as exc:
        return _error_response(422, "validation_error", str(exc))

    return _success_payload({"questions": list(result.get("questions") or [])})


@router.post("/apply/draft")
async def vue_apply_draft(payload: ApplyDraftRequest, db: Session = Depends(get_db)):
    if response := _job_data_or_422(payload.job_data):
        return response
    track_slug = _resolve_track_slug(db, payload.track_slug)
    if isinstance(track_slug, JSONResponse):
        return track_slug

    body = {
        "job": dict(payload.job_data or {}),
        "answers": _normalize_confirmed_facts(list(payload.questions or []), dict(payload.answers or {})),
        "track_slug": track_slug,
    }
    try:
        result = await legacy_jobs.apply_generate(body=body, db=db)
    except HTTPException as exc:
        return _http_exception_to_contract_response(exc)
    except ValueError as exc:
        return _error_response(422, "validation_error", str(exc))

    return _success_payload(
        {
            "task_id": str(result.get("task_id") or ""),
            "job_id": str(result.get("job_id") or ""),
        }
    )


@router.get("/apply/status/{task_id}")
async def vue_apply_status(task_id: str, db: Session = Depends(get_db)):
    try:
        result = await legacy_jobs.apply_status(task_id=task_id, db=db)
    except HTTPException as exc:
        return _http_exception_to_contract_response(exc)

    status = str(result.get("status") or "pending")
    draft_id = str(result.get("draft_id") or "") or None
    return _success_payload(
        {
            "status": status,
            "draft_id": draft_id,
            "message": _task_status_message(status, draft_id),
        }
    )


@router.get("/applications")
def vue_applications(db: Session = Depends(get_db)) -> dict[str, object]:
    rows = (
        db.query(Application)
        .options(
            selectinload(Application.job_post),
            selectinload(Application.resume_draft),
        )
        .order_by(Application.updated_at.desc())
        .all()
    )
    items = [_application_summary(row) for row in rows]
    return _success_payload({"items": items, "total": len(items)})


@router.get("/applications/{application_id}")
def vue_application_detail(application_id: str, db: Session = Depends(get_db)):
    application = _get_application_or_404(db, application_id)
    if isinstance(application, JSONResponse):
        return application
    return _success_payload({"item": _application_detail(application)})


@router.get("/drafts")
def vue_drafts(db: Session = Depends(get_db)) -> dict[str, object]:
    rows = (
        db.query(ResumeDraft)
        .options(
            selectinload(ResumeDraft.job_post),
            selectinload(ResumeDraft.resume_track),
        )
        .order_by(ResumeDraft.created_at.desc())
        .all()
    )
    items = [_draft_summary(row) for row in rows]
    return _success_payload({"items": items, "total": len(items)})


@router.get("/drafts/{draft_id}")
def vue_draft_detail(draft_id: str, db: Session = Depends(get_db)):
    draft = _get_draft_or_404(db, draft_id)
    if isinstance(draft, JSONResponse):
        return draft
    return _success_payload({"item": _draft_detail(draft, db)})


@router.patch("/drafts/{draft_id}")
def vue_patch_draft(draft_id: str, payload: DraftPatchRequest, db: Session = Depends(get_db)):
    del payload
    draft = _get_draft_or_404(db, draft_id)
    if isinstance(draft, JSONResponse):
        return draft
    return _not_implemented_response()


@router.post("/drafts/{draft_id}/revise")
def vue_revise_draft(draft_id: str, payload: DraftActionRequest, db: Session = Depends(get_db)):
    del payload
    draft = _get_draft_or_404(db, draft_id)
    if isinstance(draft, JSONResponse):
        return draft
    return _not_implemented_response()


@router.post("/drafts/{draft_id}/polish")
def vue_polish_draft(draft_id: str, payload: DraftActionRequest, db: Session = Depends(get_db)):
    del payload
    draft = _get_draft_or_404(db, draft_id)
    if isinstance(draft, JSONResponse):
        return draft
    return _not_implemented_response()


@router.post("/drafts/{draft_id}/approve")
def vue_approve_draft(draft_id: str, payload: DraftActionRequest, db: Session = Depends(get_db)):
    draft = _get_draft_or_404(db, draft_id)
    if isinstance(draft, JSONResponse):
        return draft
    if not payload.user_confirmed:
        return _error_response(422, "validation_error", "user_confirmed must be true.")
    try:
        approved = approve_draft_record(draft, db)
    except HTTPException as exc:
        return _http_exception_to_contract_response(exc)
    return _success_payload(_draft_action_payload(approved))


@router.post("/drafts/{draft_id}/reject")
def vue_reject_draft(draft_id: str, payload: DraftActionRequest, db: Session = Depends(get_db)):
    draft = _get_draft_or_404(db, draft_id)
    if isinstance(draft, JSONResponse):
        return draft
    if not payload.user_confirmed:
        return _error_response(422, "validation_error", "user_confirmed must be true.")
    draft.approved = False
    draft.status = "rejected"
    db.commit()
    db.refresh(draft)
    return _success_payload(_draft_action_payload(draft))


@router.post("/drafts/{draft_id}/cover-letter")
def vue_cover_letter(draft_id: str, db: Session = Depends(get_db)):
    draft = _get_draft_or_404(db, draft_id)
    if isinstance(draft, JSONResponse):
        return draft
    try:
        updated = CoverLetterService(db).generate_cover_letter(UUID(str(draft.id)))
    except ValueError as exc:
        return _error_response(404, "not_found", str(exc))
    return _success_payload(_cover_letter_payload(updated))


@router.get("/onboarding/state")
def vue_onboarding_state(db: Session = Depends(get_db)) -> dict[str, object]:
    setup = _setup_status_payload(db)
    data = {
        "configured": bool(_onboarding_complete()),
        "setup_complete": bool(setup["complete"]),
        "candidate_exists": bool(setup["candidate_exists"]),
        "identity_ready": bool(setup["identity_ready"]),
        "fact_sheet_ready": bool(setup["fact_sheet_ready"]),
        "search_focus_ready": bool(setup["search_focus_ready"]),
        "missing_steps": list(setup["missing_steps"]),
    }
    return _success_payload(data)


@router.get("/onboarding/steps")
def vue_onboarding_steps(db: Session = Depends(get_db)) -> dict[str, object]:
    setup = _setup_status_payload(db)
    steps = [
        {"key": "provider", "label": "Connect an AI provider", "complete": bool(setup["provider"]["ready"])},
        {"key": "identity", "label": "Confirm your identity", "complete": bool(setup["identity_ready"])},
        {"key": "facts", "label": "Build your fact sheet", "complete": bool(setup["fact_sheet_ready"])},
        {"key": "search", "label": "Choose target roles", "complete": bool(setup["search_focus_ready"])},
    ]
    return _success_payload({"items": steps, "total": len(steps)})


@router.get("/settings")
def vue_settings(db: Session = Depends(get_db)) -> dict[str, object]:
    setup = _setup_status_payload(db)
    gmail_state = GmailOAuthService(settings).status()
    workspace = workspace_status()
    provider_mode = normalize_provider_mode(getattr(settings, "llm_provider_mode", "openai"))
    provider = {
        "llm_provider_mode": provider_mode,
        "provider_ready": bool(setup["provider"]["ready"]),
        "provider_configured": bool(setup["provider"]["configured"]),
        "openai_configured": bool(settings.openai_api_key),
        "gemini_configured": bool(settings.gemini_api_key),
        "anthropic_configured": bool(settings.anthropic_api_key),
        "lm_studio_configured": bool(str(settings.lm_studio_base_url or "").strip()),
        "ollama_configured": bool(str(getattr(settings, "ollama_base_url", "") or "").strip()),
        "lm_studio_base_url": "",
        "ollama_base_url": "",
        "lm_studio_small_model": str(getattr(settings, "lm_studio_small_model", "") or ""),
        "lm_studio_writer_model": str(getattr(settings, "lm_studio_writer_model", "") or ""),
        "lm_studio_mid_model": str(getattr(settings, "lm_studio_mid_model", "") or ""),
        "ollama_fast_model": str(getattr(settings, "ollama_fast_model", "") or ""),
        "ollama_writer_model": str(getattr(settings, "ollama_writer_model", "") or ""),
    }
    search = {
        "target_job_seniority": str(getattr(settings, "target_job_seniority", "") or "junior"),
        "jobspy_discover_queries": list(getattr(settings, "jobspy_discover_queries", []) or []),
        "job_search_countries": list(getattr(settings, "job_search_countries", []) or []),
        "job_search_languages": list(getattr(settings, "job_search_languages", []) or []),
        "jobspy_discover_location": str(getattr(settings, "jobspy_discover_location", "") or ""),
        "use_jobspy": bool(getattr(settings, "use_jobspy", False)),
    }
    gmail = {
        "gmail_label_filter": str(getattr(settings, "gmail_label_filter", "") or "LinkedIn Jobs"),
        "gmail_auto_sync": bool(getattr(settings, "gmail_auto_sync", False)),
        "gmail_oauth_configured": bool(gmail_state["has_client_credentials"]),
        "gmail_connected": bool(gmail_state["connected"]),
        "gmail_legacy_configured": bool(settings.gmail_email and settings.gmail_app_password),
    }
    cv = {
        "cv_pass_score": int(getattr(settings, "cv_pass_score", 0) or 0),
        "cv_revise_score": int(getattr(settings, "cv_revise_score", 0) or 0),
        "bullet_clarify_word_limit": int(getattr(settings, "bullet_clarify_word_limit", 0) or 0),
    }
    discovery = {
        "match_min_score": int(getattr(settings, "match_min_score", 0) or 0),
        "discovery_min_fit_score": int(getattr(settings, "discovery_min_fit_score", 0) or 0),
        "discovery_max_visible_jobs": int(getattr(settings, "discovery_max_visible_jobs", 0) or 0),
    }
    data = {
        "provider": provider,
        "search": search,
        "language_options": LANGUAGE_OPTIONS,
        "language_level_options": LEVEL_OPTIONS,
        "gmail": gmail,
        "cv": cv,
        "discovery": discovery,
        "share_url": SHARE_REPOSITORY_URL,
        "active_candidate_id": settings.default_candidate_id.strip(),
        "maintenance": {
            "reset_phrase": RESET_CONFIRMATION_PHRASE,
            "delete_phrase": DELETE_CONFIRMATION_PHRASE,
            "backup_count": int(workspace.get("backup_count") or 0),
        },
        "provider_mode": provider_mode,
        "provider_ready": bool(setup["provider"]["ready"]),
        "provider_configured": bool(setup["provider"]["configured"]),
        "openai_configured": bool(settings.openai_api_key),
        "gemini_configured": bool(settings.gemini_api_key),
        "anthropic_configured": bool(settings.anthropic_api_key),
        "lm_studio_configured": bool(str(settings.lm_studio_base_url or "").strip()),
        "ollama_configured": bool(str(getattr(settings, "ollama_base_url", "") or "").strip()),
        "gmail_configured": bool(
            settings.gmail_email or str(getattr(settings, "gmail_oauth_client_id", "") or "").strip()
        ),
        "yaml_exists": bool(_onboarding_complete()),
        "job_search_role_count": len(getattr(settings, "jobspy_discover_queries", []) or []),
        "job_search_country_count": len(getattr(settings, "job_search_countries", []) or []),
    }
    return _success_payload(data)


@router.get("/verified-facts")
def vue_verified_facts(db: Session = Depends(get_db)) -> dict[str, object]:
    rows = (
        db.query(VerifiedCandidateFact)
        .filter(VerifiedCandidateFact.is_active.is_(True))
        .order_by(VerifiedCandidateFact.created_at.desc())
        .all()
    )
    items = [_verified_fact_summary(row) for row in rows]
    return _success_payload({"items": items, "total": len(items)})


@router.get("/verified-facts/schema")
def vue_verified_facts_schema() -> dict[str, object]:
    return _success_payload(
        {
            "fact_types": sorted(VALID_VERIFIED_FACT_TYPES),
            "fields": [
                {"key": "gap_label", "type": "string", "required": True},
                {"key": "evidence", "type": "string", "required": True},
                {"key": "fact_type", "type": "string", "required": True},
            ],
        }
    )


@router.get("/story-bank")
def vue_story_bank(db: Session = Depends(get_db)) -> dict[str, object]:
    rows = InterviewBankService(db).list_stories(_candidate_scope())
    items = [
        {
            "id": str(row.id),
            "title": row.title,
            "context": row.context,
            "confidence_source": row.confidence_source,
            "role_family_tags": row.role_family_tags or [],
            "updated_at": _isoformat(row.updated_at),
        }
        for row in rows
    ]
    if not items:
        return _placeholder_list(
            "This list endpoint is ready for Vue migration but not wired to real data yet."
        )
    return _success_payload({"items": items, "total": len(items)})


@router.get("/offer-compass")
def vue_offer_compass(db: Session = Depends(get_db)) -> dict[str, object]:
    service = OfferCompassService(db)
    ranked = service.compare(_candidate_scope(), service.priorities())
    items = [
        {
            "id": str(entry["offer"].id),
            "company": entry["offer"].company,
            "title": entry["offer"].title,
            "status": entry["offer"].status,
            "overall_score": entry["score"]["overall"],
        }
        for entry in ranked
    ]
    if not items:
        return _placeholder_list(
            "This list endpoint is ready for Vue migration but not wired to real data yet."
        )
    return _success_payload({"items": items, "total": len(items)})


@router.get("/analytics/summary")
def vue_analytics_summary(db: Session = Depends(get_db)) -> dict[str, object]:
    service = RejectionAnalyticsService(db)
    try:
        analytics = service.analyse()
    except ValueError:
        return _success_payload(
            {"items": [], "total": 0},
            status="placeholder",
            message="This API contract is reserved for future Vue migration.",
        )
    return _success_payload(
        {
            "funnel": analytics.get("funnel", {}),
            "score_analysis": analytics.get("score_analysis", {}),
            "skill_gaps": analytics.get("skill_gaps", []),
            "weekly_activity": analytics.get("weekly_activity", []),
        }
    )


@router.get("/thesis/targets")
def vue_thesis_targets(db: Session = Depends(get_db)) -> dict[str, object]:
    rows = db.query(ThesisTarget).order_by(ThesisTarget.updated_at.desc()).all()
    items = [
        {
            "id": str(row.id),
            "type": row.type,
            "name": row.name,
            "institution": row.institution,
            "country": row.country,
            "status": row.status,
            "priority": row.priority,
            "updated_at": _isoformat(row.updated_at),
        }
        for row in rows
    ]
    return _success_payload({"items": items, "total": len(items)})


@router.get("/workspace/status")
def vue_workspace_status() -> dict[str, object]:
    return _success_payload(_safe_workspace_snapshot())


@router.post("/workspace/backup")
def vue_workspace_backup():
    return _not_implemented_response()


@router.post("/workspace/reset-preview")
def vue_workspace_reset_preview(payload: WorkspaceResetPreviewRequest) -> dict[str, object]:
    snapshot = _safe_workspace_snapshot()
    return _success_payload(
        {
            "include_generated_files": payload.include_generated_files,
            "include_cached_results": payload.include_cached_results,
            "would_affect_generated_files": payload.include_generated_files,
            "would_affect_cached_results": payload.include_cached_results,
            "backup_count": snapshot["backup_count"],
            "has_backupable_db": snapshot["has_backupable_db"],
            "destructive_action_taken": False,
        }
    )


@router.get("/help")
def vue_help() -> dict[str, object]:
    return _success_payload(
        {
            "title": "Help",
            "sections": [
                "Legacy /ui pages remain active during the Vue migration.",
                "This contract layer exists so Vue pages can migrate gradually without changing business rules.",
            ],
        },
        status="placeholder",
        message="This API contract is reserved for future Vue migration.",
    )


@router.get("/about")
def vue_about() -> dict[str, object]:
    return _success_payload(
        {
            "title": "About",
            "summary": "Local-first job search and CV optimization for a single local user.",
            "local_first": True,
        },
        status="placeholder",
        message="This API contract is reserved for future Vue migration.",
    )
