from __future__ import annotations

from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
from urllib.parse import parse_qs
from urllib.parse import urlparse
from uuid import UUID

from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from job_agent.config import settings
from job_agent.db import get_db, prepare_database
from job_agent.llm import LLMRouter, ProviderUnavailableError
from job_agent.models import (
    Application,
    Candidate,
    CandidateIntakeDraft,
    CareerPageScanLog,
    CareerPageSource,
    CommunicationEvent,
    CsvExport,
    FactSource,
    JobPost,
    JobSource,
    JobTrackScore,
    MasterProfile,
    MatchProfile,
    ContactEvent,
    OutreachDraft,
    ResumeDraft,
    ResumeTrack,
    ThesisTarget,
    WorkflowTask,
    EnhancementProposal,
)
from job_agent.schemas import (
    ApplyEnhancementsRequest,
    ApplicationCreate,
    ApplicationOut,
    ApplicationUpdate,
    CommunicationEventCreate,
    CommunicationEventOut,
    ContactEventCreate,
    ContactEventOut,
    CsvExportOut,
    FactSheetIngestRequest,
    FactSheetIngestResponse,
    JobSourceOut,
    JobPostCreate,
    JobPostOut,
    MasterProfileIn,
    MasterProfileOut,
    OutreachDraftOut,
    OutreachDraftRevisionRequest,
    ResumeDraftOut,
    ResumeTrackOut,
    ThesisTargetCreate,
    ThesisTargetOut,
    ThesisTargetUpdate,
    WorkflowTaskCreate,
    WorkflowTaskOut,
)
from job_agent.seed import seed_reference_data
from job_agent.services.exporters import CsvExportService
from job_agent.services.fact_ingestion import FactSheetIngestionService
from job_agent.services.career_scanner import CareerPageScanner
from job_agent.services.fact_sheet_json import FactSheetJsonIngestionService
from job_agent.services.intake import FactSheetIntakeService, UploadedFile as IntakeUploadedFile, store_uploaded_files
from job_agent.services.gmail import GmailService
from job_agent.services.job_fetcher import JobFetcher
from job_agent.services.jobspy_service import JobSpyService
from job_agent.services.matching import score_tracks_for_job
from job_agent.services.rejection_analytics import RejectionAnalyticsService
from job_agent.services.thesis_outreach import ThesisOutreachService
from job_agent.services.workflows import CVWorkflowService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)
VALID_ATS_TYPES = {"greenhouse", "lever", "ashby"}
_USER_SETTINGS_FILE = Path("config/user_settings.yml")


def _log_startup_config_warning() -> None:
    if not settings.default_candidate_id.strip():
        logger.warning(
            "DEFAULT_CANDIDATE_ID is not set. CV workflow will fall back to MasterProfile(id=1). "
            "Set DEFAULT_CANDIDATE_ID=<uuid> in .env to use Candidate-based profiles."
        )


def _onboarding_complete() -> bool:
    return _USER_SETTINGS_FILE.exists()


def _ui_context(request: Request, title: str, **extra: object) -> dict[str, object]:
    context: dict[str, object] = {
        "request": request,
        "title": title,
        "onboarding_complete": _onboarding_complete(),
    }
    context.update(extra)
    return context


@asynccontextmanager
async def lifespan(app: FastAPI):
    del app
    prepare_database()
    if not _onboarding_complete():
        logger.warning(
            "config/user_settings.yml not found. "
            "Run 'python -m job_agent.onboard' to configure the system."
        )
    _log_startup_config_warning()
    with next(get_db()) as db:
        seed_reference_data(db)
    yield


app = FastAPI(title="Job Agent API", version="0.1.0", lifespan=lifespan)
templates = Jinja2Templates(directory="job_agent/templates")
app.mount("/static", StaticFiles(directory="job_agent/static"), name="static")


def _get_dashboard_data(db: Session) -> dict[str, object]:
    """
    Daily status summary for the current state of the job search.
    Shared by the JSON dashboard endpoint and the local web UI.
    """
    import httpx

    from job_agent.services.documents import check_pdflatex

    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(hours=24)

    new_jobs_24h = db.query(JobPost).filter(JobPost.created_at >= yesterday).count()

    high_match_count = (
        db.query(JobPost.id)
        .join(JobTrackScore, JobPost.id == JobTrackScore.job_post_id)
        .filter(JobTrackScore.score >= settings.match_min_score)
        .distinct()
        .count()
    )

    needs_enrichment = (
        db.query(JobPost)
        .filter(
            (JobPost.description == "") | (JobPost.description.is_(None)),
            JobPost.source_url.is_not(None),
        )
        .count()
    )

    pending_cv_approvals = (
        db.query(ResumeDraft)
        .filter(
            ResumeDraft.approved.is_(False),
            ResumeDraft.status != "approved",
        )
        .count()
    )

    pending_enhancement_approvals = (
        db.query(EnhancementProposal)
        .filter(EnhancementProposal.approved.is_(None))
        .count()
    )

    approved_no_cover_letter = (
        db.query(ResumeDraft)
        .filter(
            ResumeDraft.approved.is_(True),
            (ResumeDraft.cover_letter_text == "") | (ResumeDraft.cover_letter_text.is_(None)),
        )
        .count()
    )

    thesis_rows = (
        db.query(ThesisTarget.status, func.count(ThesisTarget.id))
        .group_by(ThesisTarget.status)
        .all()
    )
    thesis_status_counts = {status: count for status, count in thesis_rows}

    app_rows = (
        db.query(Application.status, func.count(Application.id))
        .group_by(Application.status)
        .all()
    )
    app_status_counts = {status: count for status, count in app_rows}

    pdf_ok, pdf_path = check_pdflatex()

    lm_studio_online = False
    try:
        response = httpx.get(f"{settings.lm_studio_base_url}/models", timeout=2)
        lm_studio_online = response.is_success
    except Exception:
        pass

    latest_job = db.query(JobPost).order_by(JobPost.created_at.desc()).first()
    last_job_ingested = latest_job.created_at.isoformat() if latest_job else None

    return {
        "jobs": {
            "new_24h": new_jobs_24h,
            "high_match": high_match_count,
            "needs_enrichment": needs_enrichment,
        },
        "cv": {
            "pending_approvals": pending_cv_approvals,
            "pending_enhancement_approvals": pending_enhancement_approvals,
            "approved_without_cover_letter": approved_no_cover_letter,
        },
        "thesis": thesis_status_counts,
        "applications": app_status_counts,
        "config": {
            "target_seniority": settings.target_job_seniority,
            "match_min_score": settings.match_min_score,
            "cv_pass_score": settings.cv_pass_score,
            "semantic_weight": settings.semantic_matching_weight,
        },
        "system": {
            "pdflatex_available": pdf_ok,
            "pdflatex_path": pdf_path,
            "lm_studio_online": lm_studio_online,
            "last_job_ingested": last_job_ingested,
        },
    }


def _score_rows_for_jobs(db: Session, job_ids: list[UUID]) -> dict[UUID, list[JobTrackScore]]:
    if not job_ids:
        return {}

    score_rows = (
        db.query(JobTrackScore)
        .options(joinedload(JobTrackScore.resume_track))
        .filter(JobTrackScore.job_post_id.in_(job_ids))
        .order_by(JobTrackScore.score.desc())
        .all()
    )
    grouped: dict[UUID, list[JobTrackScore]] = defaultdict(list)
    for row in score_rows:
        grouped[row.job_post_id].append(row)
    return grouped


def _build_job_ui_payload(job: JobPost, score_row: JobTrackScore | None) -> dict[str, object]:
    best_score = int(round(score_row.score)) if score_row is not None else 0
    best_track = score_row.resume_track.title if score_row and score_row.resume_track else None
    best_track_slug = (
        score_row.resume_track.slug
        if score_row and score_row.resume_track
        else (job.role_track_hint or None)
    )
    return {
        "id": str(job.id),
        "title": job.title,
        "company": job.company,
        "status": job.status,
        "source_url": job.source_url,
        "company_url": job.company_url,
        "best_score": best_score,
        "best_track": best_track,
        "best_track_slug": best_track_slug,
        "created_at": job.created_at,
    }


def _get_recent_jobs_with_scores(db: Session, limit: int = 8) -> list[dict[str, object]]:
    jobs = db.query(JobPost).order_by(JobPost.created_at.desc()).limit(limit).all()
    score_map = _score_rows_for_jobs(db, [job.id for job in jobs])
    return [
        _build_job_ui_payload(job, score_map.get(job.id, [None])[0] if score_map.get(job.id) else None)
        for job in jobs
    ]


def _query_jobs_for_ui(
    db: Session,
    min_score: int | None = None,
    track_id: str | None = None,
    status: str | None = None,
    show_all: bool = False,
) -> list[dict[str, object]]:
    threshold = 0 if show_all else (min_score if min_score is not None else settings.match_min_score)
    normalized_track_id = track_id.strip() if track_id else None

    query = db.query(JobPost)
    if status:
        query = query.filter(JobPost.status == status)
    jobs = query.order_by(JobPost.created_at.desc()).all()

    score_map = _score_rows_for_jobs(db, [job.id for job in jobs])
    rows: list[dict[str, object]] = []
    for job in jobs:
        scores = score_map.get(job.id, [])
        visible_scores = scores
        if normalized_track_id is not None:
            visible_scores = [score for score in scores if str(score.resume_track_id) == normalized_track_id]

        display_score = visible_scores[0] if visible_scores else None
        if threshold > 0 and (display_score.score if display_score else 0) < threshold:
            continue
        rows.append(_build_job_ui_payload(job, display_score))

    rows.sort(key=lambda item: (item["best_score"], item["created_at"]), reverse=True)
    return rows


def _default_jobspy_query(db: Session) -> str:
    track = (
        db.query(ResumeTrack)
        .filter(ResumeTrack.active.is_(True))
        .order_by(ResumeTrack.created_at.asc())
        .first()
    )
    if track is None:
        return "Data Engineer"
    primary_title = track.title.split("/")[0].strip()
    return primary_title.removeprefix("Junior ").strip() or "Data Engineer"


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


def _merge_inferred_additions(content: dict[str, object], additions: list[dict[str, object]]) -> dict[str, object]:
    merged = dict(content or {})
    selected_skills = [str(item) for item in (merged.get("selected_skills") or [])]
    selected_experiences = [dict(item) for item in (merged.get("selected_experiences") or [])]
    selected_projects = [dict(item) for item in (merged.get("selected_projects") or [])]
    tailoring_notes = [str(item) for item in (merged.get("tailoring_notes") or [])]
    summary = str(merged.get("professional_summary") or merged.get("summary") or "")

    for item in additions:
        text = str(item.get("text", "") or "").strip()
        attached_to = str(item.get("attached_to", "") or "").strip()
        if not text:
            continue
        if attached_to == "summary":
            if text.lower() not in summary.lower():
                summary = f"{summary.rstrip('. ')}. {text}".strip(". ")
        elif attached_to == "skills":
            _append_unique(selected_skills, text)
        elif attached_to.startswith("experience[") and attached_to.endswith("]"):
            try:
                index = int(attached_to[len("experience["):-1])
            except ValueError:
                _append_unique(tailoring_notes, text)
                continue
            if 0 <= index < len(selected_experiences):
                bullets = [str(bullet) for bullet in (selected_experiences[index].get("bullets") or [])]
                _append_unique(bullets, text)
                selected_experiences[index]["bullets"] = bullets
        elif attached_to.startswith("projects[") and attached_to.endswith("]"):
            try:
                index = int(attached_to[len("projects["):-1])
            except ValueError:
                _append_unique(tailoring_notes, text)
                continue
            if 0 <= index < len(selected_projects):
                bullets = [str(bullet) for bullet in (selected_projects[index].get("bullets") or [])]
                _append_unique(bullets, text)
                selected_projects[index]["bullets"] = bullets
        else:
            _append_unique(tailoring_notes, text)

    merged["professional_summary"] = summary
    merged["selected_skills"] = selected_skills
    merged["selected_experiences"] = selected_experiences
    merged["selected_projects"] = selected_projects
    merged["tailoring_notes"] = tailoring_notes
    return merged


def _rerender_draft_tex(draft: ResumeDraft, db: Session) -> None:
    from job_agent.services.documents import render_resume_tex

    profile = db.get(MasterProfile, 1)
    if profile is None or draft.job_post is None or draft.resume_track is None:
        return

    draft.tex_path = render_resume_tex(
        profile={
            "full_name": profile.full_name,
            "email": profile.email,
            "phone": profile.phone,
            "location": profile.location,
            "linkedin_url": profile.linkedin_url,
            "github_url": profile.github_url,
        },
        job={
            "company": draft.job_post.company,
            "title": draft.job_post.title,
        },
        track={
            "baseline_summary": draft.resume_track.baseline_summary,
        },
        content=draft.content or {},
        draft_id=str(draft.id),
    )


class JobDiscoverRequest(BaseModel):
    query: str
    location: str = "Italy"
    sources: list[str] = ["linkedin"]
    limit: int = 50


class JobTextCreateRequest(BaseModel):
    text: str


class JobUrlCreateRequest(BaseModel):
    url: str


class DraftGenerateRequest(BaseModel):
    job_id: UUID
    track_slug: str | None = None
    force_cloud_review: bool = False


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    from job_agent.services.documents import check_pdflatex

    pdf_ok, pdf_path = check_pdflatex()
    return {
        "status": "ok",
        "pdflatex": {"available": pdf_ok, "path": pdf_path},
    }


@app.get("/providers")
def providers() -> dict:
    return LLMRouter().provider_status()


@app.get("/lm-studio/models")
def lm_studio_models(base_url: str | None = None) -> dict[str, object]:
    target_url = (base_url or settings.lm_studio_base_url).rstrip("/")
    try:
        response = httpx.get(f"{target_url}/models", timeout=3)
        if response.is_success:
            data = response.json()
            models = [item["id"] for item in data.get("data", []) if isinstance(item, dict) and item.get("id")]
            return {"models": models, "online": True}
    except Exception:
        pass
    return {"models": [], "online": False}


@app.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db)) -> dict[str, object]:
    return _get_dashboard_data(db)


@app.get("/ui", include_in_schema=False)
def ui_dashboard(request: Request, db: Session = Depends(get_db)):
    dash = _get_dashboard_data(db)
    stat_cards = [
        {"label": "New Jobs (24h)", "value": dash["jobs"]["new_24h"], "color": "text-blue-600"},
        {"label": "High Match", "value": dash["jobs"]["high_match"], "color": "text-green-600"},
        {"label": "Pending Approvals", "value": dash["cv"]["pending_approvals"], "color": "text-yellow-600"},
        {
            "label": "Active Applications",
            "value": sum(dash["applications"].values()),
            "color": "text-indigo-600",
        },
    ]
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=_ui_context(
            request,
            "Dashboard",
            stat_cards=stat_cards,
            recent_jobs=_get_recent_jobs_with_scores(db, limit=8),
            system=dash["system"],
            config=dash["config"],
        ),
    )


@app.get("/ui/jobs", include_in_schema=False)
def ui_jobs(
    request: Request,
    db: Session = Depends(get_db),
    min_score: int | None = None,
    track_id: str | None = None,
    status: str | None = None,
    show_all: bool = False,
):
    return templates.TemplateResponse(
        request=request,
        name="jobs.html",
        context=_ui_context(
            request,
            "Jobs",
            jobs=_query_jobs_for_ui(
                db,
                min_score=min_score,
                track_id=track_id,
                status=status,
                show_all=show_all,
            ),
            tracks=(
                db.query(ResumeTrack)
                .filter(ResumeTrack.active.is_(True))
                .order_by(ResumeTrack.title.asc())
                .all()
            ),
            filters={
                "min_score": min_score if min_score is not None else settings.match_min_score,
                "track_id": track_id,
                "status": status or "",
                "show_all": show_all,
            },
            config={"use_jobspy": getattr(settings, "use_jobspy", False)},
        ),
    )


@app.post("/ui/jobs/discover", include_in_schema=False)
def ui_discover_jobs(db: Session = Depends(get_db)) -> Response:
    if not settings.use_jobspy:
        raise HTTPException(status_code=400, detail="JobSpy is disabled. Set USE_JOBSPY=true in .env.")

    JobSpyService().discover(
        query=_default_jobspy_query(db),
        location="Italy",
        limit=settings.jobspy_default_limit,
        session=db,
    )
    return Response(status_code=204)


@app.post("/ui/jobs/{job_id}/queue-cv", include_in_schema=False)
def ui_queue_cv_workflow(
    job_id: UUID,
    resume_track_slug: str | None = None,
    db: Session = Depends(get_db),
) -> Response:
    job = db.get(JobPost, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job post not found.")

    track_slug = resume_track_slug or job.role_track_hint
    if not track_slug:
        top_score = (
            db.query(JobTrackScore)
            .options(joinedload(JobTrackScore.resume_track))
            .filter(JobTrackScore.job_post_id == job_id)
            .order_by(JobTrackScore.score.desc())
            .first()
        )
        if top_score is not None and top_score.resume_track is not None:
            track_slug = top_score.resume_track.slug
    if not track_slug:
        raise HTTPException(status_code=400, detail="No resume track is available for this job.")

    CVWorkflowService(db).queue_cv_workflow(
        job_post_id=job_id,
        resume_track_slug=track_slug,
        force_cloud_review=False,
    )
    return Response(status_code=204)


@app.post("/ui/jobs/{job_id}/enrich-row", include_in_schema=False)
def ui_enrich_job_row(
    request: Request,
    job_id: UUID,
    db: Session = Depends(get_db),
):
    job = db.get(JobPost, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    JobFetcher().enrich_job(job, db)
    db.commit()
    score_map = _score_rows_for_jobs(db, [job.id])
    job_payload = _build_job_ui_payload(job, score_map.get(job.id, [None])[0] if score_map.get(job.id) else None)
    return templates.TemplateResponse(
        request=request,
        name="partials/job_row.html",
        context={"request": request, "job": job_payload},
    )


@app.get("/ui/drafts", include_in_schema=False)
def ui_drafts(request: Request, db: Session = Depends(get_db)):
    drafts = (
        db.query(ResumeDraft)
        .options(joinedload(ResumeDraft.job_post), joinedload(ResumeDraft.resume_track))
        .order_by(ResumeDraft.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        request=request,
        name="drafts.html",
        context=_ui_context(request, "CV Drafts", drafts=drafts),
    )


@app.get("/ui/drafts/{draft_id}", include_in_schema=False)
def ui_draft_detail(draft_id: UUID, request: Request, db: Session = Depends(get_db)):
    draft = db.get(ResumeDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")
    job = db.get(JobPost, draft.job_post_id)
    track = db.get(ResumeTrack, draft.resume_track_id)
    feedback = draft.review_feedback or {}
    return templates.TemplateResponse(
        request=request,
        name="draft_detail.html",
        context=_ui_context(
            request,
            "Draft Detail",
            draft=draft,
            job=job,
            track=track,
            content=draft.content or {},
            review_feedback=feedback,
            compliance_matrix=feedback.get("compliance_matrix"),
            ranked_keywords=feedback.get("ranked_keywords") or [],
        ),
    )


@app.post("/ui/drafts/{draft_id}/approve", include_in_schema=False)
def ui_approve_draft(draft_id: UUID, db: Session = Depends(get_db)) -> Response:
    draft = db.get(ResumeDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")
    draft.approved = True
    draft.status = "approved"
    db.commit()
    return Response(status_code=204)


@app.post("/ui/drafts/{draft_id}/reject", include_in_schema=False)
def ui_reject_draft(draft_id: UUID, db: Session = Depends(get_db)) -> Response:
    draft = db.get(ResumeDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")
    draft.approved = False
    draft.status = "rejected"
    db.commit()
    return Response(status_code=204)


@app.get("/ui/thesis", include_in_schema=False)
def ui_thesis(request: Request, db: Session = Depends(get_db)):
    targets = db.query(ThesisTarget).order_by(ThesisTarget.priority.asc(), ThesisTarget.name.asc()).all()
    return templates.TemplateResponse(
        request=request,
        name="thesis.html",
        context=_ui_context(request, "Thesis Targets", targets=targets),
    )


@app.post("/ui/thesis-targets", include_in_schema=False)
async def ui_create_thesis_target(request: Request, db: Session = Depends(get_db)) -> Response:
    form_data = await _parse_urlencoded_body(request)
    payload = ThesisTargetCreate(
        type=form_data.get("type", "professor"),
        name=form_data.get("name", ""),
        institution=form_data.get("institution", ""),
        department=_blank_to_none(form_data.get("department")),
        country=form_data.get("country", "Italy"),
        city=_blank_to_none(form_data.get("city")),
        research_area=form_data.get("research_area", ""),
        email=_blank_to_none(form_data.get("email")),
        profile_url=_blank_to_none(form_data.get("profile_url")),
        notes=_blank_to_none(form_data.get("notes")),
        priority=int(form_data.get("priority", "3") or 3),
    )
    target = ThesisTarget(**payload.model_dump())
    db.add(target)
    db.commit()
    return Response(status_code=204)


@app.post("/ui/thesis-targets/{target_id}/email-preview", include_in_schema=False)
def ui_generate_email_preview(
    request: Request,
    target_id: int,
    db: Session = Depends(get_db),
):
    try:
        draft = ThesisOutreachService().generate_email(target_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return templates.TemplateResponse(
        request=request,
        name="partials/email_preview.html",
        context={"request": request, "draft": draft},
    )


@app.get("/ui/applications", include_in_schema=False)
def ui_applications(request: Request, db: Session = Depends(get_db)):
    apps = (
        db.query(Application)
        .options(joinedload(Application.job_post))
        .order_by(Application.applied_at.desc(), Application.updated_at.desc())
        .all()
    )
    apps_by_status: dict[str, list[Application]] = {
        "applied": [],
        "phone_screen": [],
        "interview": [],
        "offer": [],
        "rejected": [],
    }
    for application in apps:
        if application.status in apps_by_status:
            apps_by_status[application.status].append(application)
    return templates.TemplateResponse(
        request=request,
        name="applications.html",
        context=_ui_context(request, "Applications", apps_by_status=apps_by_status),
    )


@app.post("/ui/applications/{application_id}/advance", include_in_schema=False)
def ui_advance_application(application_id: UUID, db: Session = Depends(get_db)) -> Response:
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found.")

    next_statuses = {
        "applied": "phone_screen",
        "phone_screen": "interview",
        "interview": "offer",
    }
    next_status = next_statuses.get(application.status)
    if next_status is None:
        raise HTTPException(status_code=400, detail="Application cannot be advanced from its current status.")

    application.status = next_status
    db.commit()
    return Response(status_code=204)


@app.get("/ui/settings", include_in_schema=False)
def ui_settings(request: Request):
    from job_agent.user_config import EDITABLE_FIELDS, USER_SETTINGS_PATH, read_user_settings

    user_yml = read_user_settings()
    lm_models_payload = lm_studio_models()
    current: dict[str, object] = {}
    for field in EDITABLE_FIELDS:
        value = getattr(settings, field, None)
        if field.endswith("api_key") and value:
            current[field] = "***"
        else:
            current[field] = value

    if settings.use_openai_review and settings.use_claude_final_review:
        provider_mode = "mixed"
    elif settings.use_openai_review:
        provider_mode = "openai"
    elif settings.use_claude_final_review:
        provider_mode = "anthropic"
    else:
        provider_mode = "local"

    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context=_ui_context(
            request,
            "Settings",
            current=current,
            lm_models=lm_models_payload["models"],
            lm_online=lm_models_payload["online"],
            openai_configured=bool(settings.openai_api_key),
            anthropic_configured=bool(settings.anthropic_api_key),
            candidate_id=settings.default_candidate_id,
            yaml_exists=USER_SETTINGS_PATH.exists(),
            provider_mode=provider_mode,
            user_yml=user_yml,
        ),
    )


@app.get("/onboarding/status")
def onboarding_status() -> dict[str, bool]:
    return {
        "configured": _onboarding_complete(),
        "candidate_id_set": bool(settings.default_candidate_id.strip()),
    }


@app.get("/settings/current")
def settings_current() -> dict[str, object]:
    """Return user-editable settings with current values; API keys are masked."""
    from job_agent.user_config import EDITABLE_FIELDS, USER_SETTINGS_PATH

    data: dict[str, object] = {}
    for field in EDITABLE_FIELDS:
        value = getattr(settings, field, None)
        if field.endswith("api_key") and value:
            data[field] = "***"
        else:
            data[field] = value
    data["_yaml_exists"] = USER_SETTINGS_PATH.exists()
    data["default_candidate_id"] = settings.default_candidate_id
    return data


@app.post("/settings/save")
def settings_save(updates: dict) -> dict[str, object]:
    """Write updates to config/user_settings.yml and reload in-process settings."""
    from job_agent.config import load_user_settings_overlay, settings as settings_singleton
    from job_agent.user_config import EDITABLE_FIELDS, USER_SETTINGS_PATH, write_user_settings

    invalid = [key for key in updates if key not in EDITABLE_FIELDS]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Unknown fields: {invalid}")

    sanitized_updates = dict(updates)
    for key in ("openai_api_key", "anthropic_api_key"):
        value = sanitized_updates.get(key)
        if isinstance(value, str) and not value.strip():
            sanitized_updates.pop(key)

    write_user_settings(sanitized_updates)
    load_user_settings_overlay(settings_singleton, path=USER_SETTINGS_PATH)
    return {"status": "saved", "fields_updated": list(sanitized_updates.keys())}


@app.post("/settings/reload")
def settings_reload() -> dict[str, str]:
    """Re-apply config/user_settings.yml to the in-process settings singleton."""
    from job_agent.config import load_user_settings_overlay, settings as settings_singleton
    from job_agent.user_config import USER_SETTINGS_PATH

    load_user_settings_overlay(settings_singleton, path=USER_SETTINGS_PATH)
    return {"status": "reloaded"}


@app.get("/exports/csv/download", include_in_schema=False)
def download_csv(db: Session = Depends(get_db)):
    from fastapi.responses import FileResponse

    export = CsvExportService(db).export_jobs_snapshot()
    file_path = Path(export.file_path)
    return FileResponse(file_path, media_type="text/csv", filename=file_path.name)


@app.post("/fact-sources/ingest-default", include_in_schema=False)
def ingest_default_fact_sheet(db: Session = Depends(get_db)) -> dict[str, str]:
    fact_path = Path("/Users/youseffayyaz/Polito/Resume-CV/fact_sheet/master_fact_sheet.txt")
    if not fact_path.exists():
        raise HTTPException(status_code=404, detail=f"Fact sheet not found: {fact_path}")

    FactSheetIngestionService(db).ingest(path=str(fact_path))
    return {"status": "ok", "message": "Fact sheet re-ingested"}


@app.get("/tracks", response_model=list[ResumeTrackOut])
def list_tracks(db: Session = Depends(get_db)) -> list[ResumeTrack]:
    return db.query(ResumeTrack).filter(ResumeTrack.active.is_(True)).order_by(ResumeTrack.title.asc()).all()


@app.get("/job-sources", response_model=list[JobSourceOut])
def list_job_sources(db: Session = Depends(get_db)) -> list[JobSource]:
    return db.query(JobSource).filter(JobSource.active.is_(True)).order_by(JobSource.priority.asc()).all()


@app.get("/fact-sources/latest")
def latest_fact_source(db: Session = Depends(get_db)) -> dict:
    latest = db.query(FactSource).order_by(FactSource.imported_at.desc()).first()
    if latest is None:
        raise HTTPException(status_code=404, detail="No fact source has been ingested yet.")
    return {
        "id": str(latest.id),
        "source_path": latest.source_path,
        "source_hash": latest.source_hash,
        "imported_at": latest.imported_at.isoformat(),
        "parsed_metadata": latest.parsed_metadata,
    }


@app.post("/fact-sources/ingest", response_model=FactSheetIngestResponse)
def ingest_fact_source(payload: FactSheetIngestRequest, db: Session = Depends(get_db)) -> dict:
    service = FactSheetIngestionService(db)
    return service.ingest(path=payload.path, content=payload.content, source_path=payload.source_path)


@app.get("/profile", response_model=MasterProfileOut)
def get_profile(db: Session = Depends(get_db)) -> MasterProfile:
    profile = db.get(MasterProfile, 1)
    if profile is None:
        raise HTTPException(status_code=404, detail="Master profile not found.")
    return profile


@app.put("/profile", response_model=MasterProfileOut)
def put_profile(payload: MasterProfileIn, db: Session = Depends(get_db)) -> MasterProfile:
    profile = db.get(MasterProfile, 1)
    if profile is None:
        profile = MasterProfile(id=1)
        db.add(profile)

    for key, value in payload.model_dump().items():
        setattr(profile, key, value)

    db.commit()
    db.refresh(profile)
    return profile


@app.post("/candidates")
async def create_candidate(request: Request, db: Session = Depends(get_db)) -> dict[str, str | bool | None]:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
    else:
        body = dict(await request.form())
    full_name = str(body.get("full_name", "")).strip()
    if not full_name:
        raise HTTPException(status_code=422, detail="full_name is required")

    candidate = Candidate(
        full_name=full_name,
        preferred_name=body.get("preferred_name"),
        email=body.get("email"),
        active=bool(body.get("active", True)),
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return {
        "id": candidate.id,
        "full_name": candidate.full_name,
        "preferred_name": candidate.preferred_name,
        "email": candidate.email,
        "active": candidate.active,
    }


async def _request_payload(request: Request) -> dict:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        return await request.json()
    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        data: dict[str, object] = {}
        answers: dict[str, str] = {}
        for key, value in form.multi_items():
            if key.startswith("answers[") and key.endswith("]"):
                answers[key[8:-1]] = str(value)
            else:
                data[key] = value
        if answers:
            data["answers"] = answers
        return data
    return {}


@app.get("/candidates")
def list_candidates(db: Session = Depends(get_db)) -> list[dict[str, str | bool | None]]:
    candidates = db.query(Candidate).order_by(Candidate.created_at.asc()).all()
    return [
        {
            "id": candidate.id,
            "full_name": candidate.full_name,
            "preferred_name": candidate.preferred_name,
            "email": candidate.email,
            "active": candidate.active,
        }
        for candidate in candidates
    ]


@app.get("/candidates/{candidate_id}")
def get_candidate(candidate_id: str, db: Session = Depends(get_db)) -> dict:
    if db.get(Candidate, candidate_id) is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return FactSheetJsonIngestionService(db).export_json(candidate_id)


@app.post("/candidates/{candidate_id}/fact-sheet-json")
def ingest_fact_sheet_json(candidate_id: str, body: dict, db: Session = Depends(get_db)) -> dict:
    if db.get(Candidate, candidate_id) is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    result = FactSheetJsonIngestionService(db).ingest_json(candidate_id=candidate_id, fact_sheet=body)
    return {
        "candidate_id": result.candidate_id,
        "counts": result.counts,
        "conflicts": len(result.conflicts),
        "missing": result.missing,
    }


@app.get("/candidates/{candidate_id}/fact-sheet-json")
def export_fact_sheet_json(candidate_id: str, db: Session = Depends(get_db)) -> dict:
    try:
        return FactSheetJsonIngestionService(db).export_json(candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/candidates/{candidate_id}/fact-sheet-text")
def export_fact_sheet_text(candidate_id: str, db: Session = Depends(get_db)) -> PlainTextResponse:
    try:
        text = FactSheetJsonIngestionService(db).export_text(candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PlainTextResponse(text)


@app.post("/candidates/{candidate_id}/sources/upload")
async def upload_candidate_sources(
    candidate_id: str,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
) -> dict:
    if db.get(Candidate, candidate_id) is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    uploaded_files = [
        IntakeUploadedFile(
            filename=upload.filename or "upload.bin",
            content=await upload.read(),
            content_type=upload.content_type,
        )
        for upload in files
    ]
    stored_rows = store_uploaded_files(db, candidate_id, uploaded_files)
    db.commit()
    return {
        "uploaded": len(stored_rows),
        "files": [
            {
                "filename": row.original_name,
                "chars_extracted": len(row.extracted_text or ""),
            }
            for row in stored_rows
        ],
    }


@app.post("/candidates/{candidate_id}/intake/start")
async def start_candidate_intake(candidate_id: str, request: Request, db: Session = Depends(get_db)) -> dict:
    if db.get(Candidate, candidate_id) is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    body = await _request_payload(request)
    try:
        result = FactSheetIntakeService(db, LLMRouter()).start_intake(
            candidate_id=candidate_id,
            uploaded_files=[],
            profile_notes=str(body.get("profile_notes", "")) or None,
        )
    except ProviderUnavailableError:
        raise HTTPException(
            status_code=503,
            detail="LM Studio is not responding. Open LM Studio, load the small model, and try again.",
        )
    return {
        "status": result.status,
        "questions": result.questions,
        "fact_sheet": result.fact_sheet,
        "iteration": result.iteration,
    }


@app.post("/candidates/{candidate_id}/intake/answer")
async def answer_candidate_intake(candidate_id: str, request: Request, db: Session = Depends(get_db)) -> dict:
    if db.get(Candidate, candidate_id) is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    body = await _request_payload(request)
    try:
        result = FactSheetIntakeService(db, LLMRouter()).answer_questions(
            candidate_id=candidate_id,
            answers={str(key): str(value) for key, value in dict(body.get("answers", {})).items()},
        )
    except ProviderUnavailableError:
        raise HTTPException(
            status_code=503,
            detail="LM Studio is not responding. Open LM Studio, load the small model, and try again.",
        )
    return {
        "status": result.status,
        "questions": result.questions,
        "fact_sheet": result.fact_sheet,
        "iteration": result.iteration,
    }


@app.get("/candidates/{candidate_id}/intake/status")
def get_candidate_intake_status(candidate_id: str, db: Session = Depends(get_db)) -> dict:
    if db.get(Candidate, candidate_id) is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    draft = db.query(CandidateIntakeDraft).filter_by(candidate_id=candidate_id).first()
    if draft is None:
        return {"status": "not_started", "iteration": 0}
    if draft.pending_questions:
        return {
            "status": "questions_needed",
            "questions": draft.pending_questions,
            "iteration": draft.iteration,
        }
    return {
        "status": "complete",
        "fact_sheet": draft.partial_fact_sheet,
        "iteration": draft.iteration,
    }


@app.get("/ui/onboarding", response_class=HTMLResponse)
def onboarding_page(request: Request) -> Response:
    return templates.TemplateResponse(
        request=request,
        name="onboarding.html",
        context=_ui_context(request, "Onboarding"),
    )


def _create_job_post(payload: JobPostCreate, db: Session) -> JobPost:
    payload_data = payload.model_dump()
    tracks = db.query(ResumeTrack).filter(ResumeTrack.active.is_(True)).order_by(ResumeTrack.title.asc()).all()
    track_scores = score_tracks_for_job(payload_data, tracks)
    extracted_metadata = dict(payload_data.get("extracted_metadata", {}))
    extracted_metadata["track_scores"] = track_scores
    if payload_data["role_track_hint"] == "" and track_scores:
        payload_data["role_track_hint"] = track_scores[0]["slug"]
    if payload_data["role_family"] == "" and track_scores:
        payload_data["role_family"] = track_scores[0]["role_family"]
    if payload_data["match_notes"] == "" and track_scores:
        top = track_scores[0]
        payload_data["match_notes"] = (
            f"Top track {top['slug']} matched keywords: {', '.join(top['matched_keywords']) or 'none'}."
        )
    if payload_data["canonical_apply_url"] == "":
        payload_data["canonical_apply_url"] = payload_data["source_url"]
    if not payload_data.get("company_url"):
        from job_agent.services.company_resolver import find_company_url

        resolved_company_url = find_company_url(
            company_name=payload_data.get("company", ""),
            location=payload_data.get("location", ""),
            description=payload_data.get("description", ""),
        )
        if resolved_company_url:
            payload_data["company_url"] = resolved_company_url
    payload_data["extracted_metadata"] = extracted_metadata

    job = JobPost(**payload_data)
    db.add(job)
    db.flush()
    for track_score in track_scores:
        track = next((item for item in tracks if item.slug == track_score["slug"]), None)
        if track is None:
            continue
        db.add(
            JobTrackScore(
                job_post_id=job.id,
                resume_track_id=track.id,
                score=float(track_score["score"]),
                matched_keywords=track_score["matched_keywords"],
            )
        )
    db.commit()
    db.refresh(job)
    return job


def _normalize_company_from_url(url: str) -> str:
    host = urlparse(url).netloc.lower().replace("www.", "")
    if not host:
        return "Unknown Company"
    root = host.split(".")[0].replace("-", " ").replace("_", " ").strip()
    return root.title() or "Unknown Company"


def _infer_job_fields_from_text(text: str) -> dict[str, str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = "Unknown Role"
    company = "Unknown Company"
    location = ""

    def _extract(prefixes: tuple[str, ...]) -> str | None:
        for line in lines[:15]:
            lower = line.lower()
            for prefix in prefixes:
                if lower.startswith(prefix):
                    return line.split(":", 1)[1].strip() if ":" in line else line[len(prefix):].strip()
        return None

    title = _extract(("title:", "role:", "position:")) or title
    company = _extract(("company:", "employer:", "organization:")) or company
    location = _extract(("location:", "city:", "country:")) or location

    if title == "Unknown Role" and lines:
        first = lines[0]
        if len(first) <= 120 and "http" not in first.lower():
            title = first
    if company == "Unknown Company" and len(lines) > 1:
        second = lines[1]
        if len(second) <= 120 and "http" not in second.lower() and ":" not in second:
            company = second

    return {
        "title": title,
        "company": company,
        "location": location,
    }


@app.post("/jobs", response_model=JobPostOut)
def create_job(payload: JobPostCreate, db: Session = Depends(get_db)) -> JobPost:
    return _create_job_post(payload, db)


@app.post("/jobs/from-text")
def jobs_from_text(payload: JobTextCreateRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="text is required")

    inferred = _infer_job_fields_from_text(text)
    job = _create_job_post(
        JobPostCreate(
            company=inferred["company"],
            title=inferred["title"],
            location=inferred["location"],
            source_name="manual_text",
            source_url="",
            canonical_apply_url="",
            description=text,
        ),
        db,
    )
    return {
        "job_id": str(job.id),
        "title": job.title,
        "company": job.company,
        "location": job.location,
    }


@app.post("/jobs/add")
def jobs_add(payload: JobUrlCreateRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    url = payload.url.strip()
    if not url:
        raise HTTPException(status_code=422, detail="url is required")

    from job_agent.services.job_fetcher import fetch_job_description

    fetched_description = fetch_job_description(url)

    inferred = _infer_job_fields_from_text(fetched_description or "")
    title = inferred["title"] if inferred["title"] != "Unknown Role" else Path(urlparse(url).path).name.replace("-", " ").title()
    if not title:
        title = "Imported Job"

    job = _create_job_post(
        JobPostCreate(
            company=_normalize_company_from_url(url),
            title=title,
            location=inferred["location"],
            source_name="manual_url",
            source_url=url,
            canonical_apply_url=url,
            description=fetched_description or f"Imported job from {url}",
        ),
        db,
    )
    return {
        "job_id": str(job.id),
        "title": job.title,
        "company": job.company,
        "source_url": job.source_url,
    }


@app.post("/jobs/{job_id}/resolve-company-url")
def resolve_job_company_url(job_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    job = db.get(JobPost, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job.company_url:
        return {
            "job_post_id": str(job.id),
            "company_url": job.company_url,
            "resolved": False,
        }

    from job_agent.services.company_resolver import find_company_url

    resolved = find_company_url(
        company_name=job.company,
        location=job.location or "",
        description=job.description or "",
    )
    if resolved:
        job.company_url = resolved
        db.commit()
        db.refresh(job)

    return {
        "job_post_id": str(job.id),
        "company_url": job.company_url,
        "resolved": bool(resolved),
    }


@app.get("/jobs", response_model=list[JobPostOut])
def list_jobs(
    show_all: bool = False,
    min_score: int | None = None,
    candidate_id: str | None = None,
    db: Session = Depends(get_db),
) -> list[JobPost]:
    """
    List job posts.
    By default, only shows jobs with max track score >= MATCH_MIN_SCORE (default 75).
    Use ?show_all=true to bypass the filter.
    Use ?min_score=50 to override the threshold for this request.
    """
    threshold = 0 if show_all else (min_score if min_score is not None else settings.match_min_score)

    if threshold > 0:
        from sqlalchemy import func

        subq = (
            db.query(
                JobTrackScore.job_post_id,
                func.max(JobTrackScore.score).label("max_score"),
            )
            .group_by(JobTrackScore.job_post_id)
            .subquery()
        )
        jobs = (
            db.query(JobPost)
            .join(subq, JobPost.id == subq.c.job_post_id)
            .filter(subq.c.max_score >= threshold)
            .order_by(subq.c.max_score.desc())
            .all()
        )
    else:
        jobs = db.query(JobPost).order_by(JobPost.created_at.desc()).all()

    if candidate_id:
        match_profile = db.query(MatchProfile).filter_by(candidate_id=candidate_id).first()
        if match_profile and match_profile.target_roles:
            allowed = [role.lower() for role in match_profile.target_roles if isinstance(role, str) and role.strip()]
            if allowed:
                jobs = [job for job in jobs if any(role in (job.title or "").lower() for role in allowed)]

    return jobs


@app.get("/jobs/{job_id}/track-fit")
def job_track_fit(job_id: str, db: Session = Depends(get_db)) -> dict:
    job = db.get(JobPost, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job post not found.")
    tracks = db.query(ResumeTrack).filter(ResumeTrack.active.is_(True)).order_by(ResumeTrack.title.asc()).all()
    return {
        "job_post_id": str(job.id),
        "recommended_tracks": score_tracks_for_job(
            {"title": job.title, "description": job.description},
            tracks,
        ),
    }


@app.post("/jobs/sync-gmail")
def sync_jobs_from_gmail(db: Session = Depends(get_db)) -> dict[str, object]:
    posts = GmailService().sync_jobs(db)
    return {
        "created": len(posts),
        "job_ids": [str(post.id) for post in posts],
    }


@app.post("/jobs/{job_id}/enrich")
def enrich_job(job_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    job = db.get(JobPost, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    success = JobFetcher().enrich_job(job, db)
    db.commit()
    return {"enriched": success, "description_length": len(job.description or "")}


@app.post("/jobs/enrich-pending")
def enrich_pending_jobs(limit: int = 20, db: Session = Depends(get_db)) -> dict[str, int]:
    count = JobFetcher().enrich_pending(db, limit=limit)
    return {"enriched": count}


@app.post("/jobs/{job_id}/rejection-risk")
def predict_rejection_risk(job_id: UUID, db: Session = Depends(get_db)) -> dict:
    """
    Predict likely rejection risk factors for a job post before applying.
    Stores result in job.extracted_metadata["rejection_risks"].
    """
    from job_agent.services.rejection_prediction import RejectionPredictionService

    service = RejectionPredictionService(db)
    try:
        prediction = service.predict(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return prediction


@app.get("/jobs/{job_id}/rejection-risk")
def get_rejection_risk(job_id: UUID, db: Session = Depends(get_db)) -> dict:
    job = db.get(JobPost, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    risks = (job.extracted_metadata or {}).get("rejection_risks")
    if risks is None:
        raise HTTPException(
            status_code=404,
            detail="No prediction generated. POST to /jobs/{id}/rejection-risk first.",
        )
    return risks


@app.post("/jobs/discover")
def discover_jobs(body: JobDiscoverRequest, db: Session = Depends(get_db)) -> dict[str, int]:
    """
    Discover new jobs via JobSpy (requires USE_JOBSPY=true in .env).
    Reads LinkedIn's public guest job board with no login required.
    """
    if not settings.use_jobspy:
        raise HTTPException(status_code=400, detail="JobSpy is disabled. Set USE_JOBSPY=true in .env.")

    count = JobSpyService().discover(
        query=body.query,
        location=body.location,
        session=db,
        limit=body.limit,
        sources=body.sources,
    )
    return {"new_jobs": count}


@app.post("/career-pages", status_code=201)
def create_career_page(
    company: str,
    career_url: str,
    country: str = "Italy",
    css_selector: str | None = None,
    ats_type: str | None = None,
    ats_slug: str | None = None,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Add a new company career page to scan."""
    normalized_ats_type = ats_type.strip().lower() if ats_type else None
    if normalized_ats_type and normalized_ats_type not in VALID_ATS_TYPES:
        raise HTTPException(status_code=400, detail="Invalid ats_type. Must be greenhouse, lever, or ashby.")

    source = CareerPageSource(
        company=company,
        career_url=career_url,
        country=country,
        css_selector=css_selector,
        ats_type=normalized_ats_type,
        ats_slug=ats_slug.strip() if ats_slug else None,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return {
        "id": source.id,
        "company": source.company,
        "career_url": source.career_url,
        "ats_type": source.ats_type,
        "ats_slug": source.ats_slug,
    }


@app.get("/career-pages")
def list_career_pages(limit: int | None = None, db: Session = Depends(get_db)) -> list[dict[str, object]]:
    """List all career page sources."""
    query = db.query(CareerPageSource).order_by(CareerPageSource.company)
    if limit is not None:
        query = query.limit(limit)
    return [
        {
            "id": source.id,
            "company": source.company,
            "career_url": source.career_url,
            "css_selector": source.css_selector,
            "ats_type": source.ats_type,
            "ats_slug": source.ats_slug,
            "country": source.country,
            "active": source.active,
            "last_checked_at": source.last_checked_at,
            "last_new_jobs": source.last_new_jobs,
            "notes": source.notes,
            "created_at": source.created_at,
        }
        for source in query.all()
    ]


@app.post("/career-pages/{source_id}/toggle-active", status_code=204)
def toggle_career_page_active(source_id: int, db: Session = Depends(get_db)) -> Response:
    source = db.get(CareerPageSource, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Career page source not found.")
    if source.ats_type and source.ats_type not in VALID_ATS_TYPES:
        raise HTTPException(status_code=400, detail="Invalid ats_type on source.")
    source.active = not source.active
    db.add(source)
    db.commit()
    return Response(status_code=204)


@app.delete("/career-pages/{source_id}", status_code=204)
def delete_career_page(source_id: int, db: Session = Depends(get_db)) -> Response:
    source = db.get(CareerPageSource, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Career page source not found.")
    db.delete(source)
    db.commit()
    return Response(status_code=204)


@app.get("/ui/companies", include_in_schema=False)
def ui_companies(request: Request, db: Session = Depends(get_db)):
    sources = (
        db.query(CareerPageSource)
        .order_by(CareerPageSource.active.desc(), CareerPageSource.company.asc())
        .all()
    )
    return templates.TemplateResponse(
        request=request,
        name="companies.html",
        context=_ui_context(
            request,
            "Companies Watchlist",
            sources=sources,
            ats_types=sorted(VALID_ATS_TYPES),
        ),
    )


@app.post("/jobs/scan-career-pages")
def scan_career_pages(db: Session = Depends(get_db)) -> dict[str, int]:
    """Trigger a manual scan of all active career pages."""
    count = CareerPageScanner().scan_all(db)
    return {"new_jobs": count}


@app.get("/analytics/posting-velocity")
def posting_velocity(days: int = 7, db: Session = Depends(get_db)) -> dict[str, object]:
    """
    Return recent scan logs grouped by company, showing velocity over last N days.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    logs = (
        db.query(CareerPageScanLog)
        .filter(CareerPageScanLog.scanned_at >= cutoff)
        .order_by(CareerPageScanLog.scanned_at.desc())
        .all()
    )

    grouped = defaultdict(lambda: {"new_jobs": 0, "scans": 0, "last_scan": None})
    for log in logs:
        source = db.get(CareerPageSource, log.source_id)
        if source is None:
            continue
        key = source.company
        grouped[key]["company"] = source.company
        grouped[key]["career_url"] = source.career_url
        grouped[key]["ats_type"] = source.ats_type
        grouped[key]["new_jobs"] += log.new_jobs
        grouped[key]["scans"] += 1
        if grouped[key]["last_scan"] is None or log.scanned_at > grouped[key]["last_scan"]:
            grouped[key]["last_scan"] = log.scanned_at

    companies = sorted(grouped.values(), key=lambda item: item["new_jobs"], reverse=True)
    for item in companies:
        last_scan = item.get("last_scan")
        item["last_scan"] = last_scan.isoformat() if last_scan else None
    return {"days": days, "companies": companies}


@app.post("/tasks/cv-workflow", response_model=WorkflowTaskOut)
def queue_cv_workflow(payload: WorkflowTaskCreate, db: Session = Depends(get_db)) -> WorkflowTask:
    track = (
        db.query(ResumeTrack)
        .filter(ResumeTrack.slug == payload.resume_track_slug, ResumeTrack.active.is_(True))
        .first()
    )
    if track is None:
        raise HTTPException(status_code=404, detail="Resume track not found.")
    job = db.get(JobPost, payload.job_post_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job post not found.")
    service = CVWorkflowService(db)
    return service.queue_cv_workflow(
        job_post_id=payload.job_post_id,
        resume_track_slug=payload.resume_track_slug,
        force_cloud_review=payload.force_cloud_review,
    )


@app.post("/drafts/generate")
def generate_draft(payload: DraftGenerateRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    job = db.get(JobPost, payload.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job post not found.")

    track_slug = payload.track_slug or job.role_track_hint
    if not track_slug:
        best_score = (
            db.query(JobTrackScore)
            .filter(JobTrackScore.job_post_id == payload.job_id)
            .order_by(JobTrackScore.score.desc())
            .first()
        )
        if best_score and best_score.resume_track:
            track_slug = best_score.resume_track.slug
    if not track_slug:
        fallback_track = db.query(ResumeTrack).filter(ResumeTrack.active.is_(True)).order_by(ResumeTrack.title.asc()).first()
        if fallback_track is None:
            raise HTTPException(status_code=404, detail="Resume track not found.")
        track_slug = fallback_track.slug

    task = CVWorkflowService(db).queue_cv_workflow(
        job_post_id=payload.job_id,
        resume_track_slug=track_slug,
        force_cloud_review=payload.force_cloud_review,
    )
    return {
        "task_id": str(task.id),
        "job_id": str(payload.job_id),
        "resume_track_slug": track_slug,
        "status": task.status,
    }


@app.get("/tasks", response_model=list[WorkflowTaskOut])
def list_tasks(db: Session = Depends(get_db)) -> list[WorkflowTask]:
    return db.query(WorkflowTask).order_by(WorkflowTask.created_at.desc()).all()


@app.get("/tasks/{task_id}", response_model=WorkflowTaskOut)
def get_task(task_id: str, db: Session = Depends(get_db)) -> WorkflowTask:
    task = db.get(WorkflowTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return task


@app.get("/drafts", response_model=list[ResumeDraftOut])
def list_drafts(db: Session = Depends(get_db)) -> list[ResumeDraft]:
    return db.query(ResumeDraft).order_by(ResumeDraft.created_at.desc()).all()


@app.get("/drafts/{draft_id}", response_model=ResumeDraftOut)
def get_draft(draft_id: str, db: Session = Depends(get_db)) -> ResumeDraft:
    draft = db.get(ResumeDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")
    return draft


@app.get("/drafts/{draft_id}/compliance-matrix")
def get_compliance_matrix(draft_id: UUID, db: Session = Depends(get_db)) -> dict:
    draft = db.get(ResumeDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    matrix = (draft.review_feedback or {}).get("compliance_matrix")
    if matrix is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Compliance matrix not yet generated. "
                "POST to /drafts/{id}/compliance-matrix to generate."
            ),
        )
    return matrix


@app.post("/drafts/{draft_id}/compliance-matrix")
def generate_compliance_matrix(draft_id: UUID, db: Session = Depends(get_db)) -> dict:
    from job_agent.services.compliance_matrix import ComplianceMatrixService

    service = ComplianceMatrixService(db)
    try:
        matrix = service.generate(draft_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return matrix


@app.post("/drafts/{draft_id}/clarify")
def start_bullet_clarify(draft_id: UUID, db: Session = Depends(get_db)):
    from job_agent.services.bullet_clarify import BulletClarifyService

    svc = BulletClarifyService(db)
    try:
        clarification = svc.start_clarification(draft_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "clarification_id": str(clarification.id),
        "status": clarification.status,
        "language_map": clarification.language_map,
        "questions": clarification.questions,
    }


@app.post("/drafts/{draft_id}/clarify/{clarification_id}/answer")
def answer_bullet_clarify(
    draft_id: UUID,
    clarification_id: UUID,
    body: dict,
    db: Session = Depends(get_db),
):
    del draft_id
    from job_agent.services.bullet_clarify import BulletClarifyService

    svc = BulletClarifyService(db)
    try:
        clarification = svc.submit_answers(clarification_id, body.get("answers", []))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "clarification_id": str(clarification.id),
        "status": clarification.status,
        "rewritten_bullets": clarification.rewritten_bullets,
    }


@app.get("/drafts/{draft_id}/inferred-additions")
def get_inferred_additions(draft_id: UUID, db: Session = Depends(get_db)) -> dict[str, object]:
    draft = db.get(ResumeDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")
    return {"inferred_additions": draft.inferred_additions or []}


@app.post("/drafts/{draft_id}/inferred-additions/accept")
def accept_inferred_additions(
    draft_id: UUID,
    body: dict,
    db: Session = Depends(get_db),
) -> dict[str, int]:
    draft = db.get(ResumeDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")

    accepted_ids = set(body.get("accepted_ids", []))
    pending = list(draft.inferred_additions or [])
    accepted = [item for item in pending if item.get("id") in accepted_ids]
    remaining = [item for item in pending if item.get("id") not in accepted_ids]

    draft.content = _merge_inferred_additions(draft.content or {}, accepted)
    draft.accepted_inferred_additions = list(draft.accepted_inferred_additions or []) + accepted
    draft.inferred_additions = remaining
    _rerender_draft_tex(draft, db)
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return {"accepted": len(accepted), "remaining": len(remaining)}


@app.post("/drafts/{draft_id}/inferred-additions/reject")
def reject_inferred_additions(
    draft_id: UUID,
    body: dict,
    db: Session = Depends(get_db),
) -> dict[str, int]:
    draft = db.get(ResumeDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")

    rejected_ids = set(body.get("rejected_ids", []))
    pending = list(draft.inferred_additions or [])
    remaining = [item for item in pending if item.get("id") not in rejected_ids]
    draft.inferred_additions = remaining
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return {"remaining": len(remaining)}


@app.post("/drafts/{draft_id}/approve", response_model=ResumeDraftOut)
def approve_draft(draft_id: str, db: Session = Depends(get_db)) -> ResumeDraft:
    draft = db.get(ResumeDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")
    draft.approved = True
    draft.status = "approved"
    db.commit()
    db.refresh(draft)
    return draft


@app.post("/drafts/{draft_id}/propose-enhancements")
def propose_enhancements(draft_id: UUID, db: Session = Depends(get_db)):
    """Generate expert enhancement proposals for a draft (human approval required)."""
    from job_agent.schemas import EnhancementProposalOut

    service = CVWorkflowService(session=db)
    try:
        proposals = service.generate_enhancement_proposals(draft_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [EnhancementProposalOut.model_validate(proposal) for proposal in proposals]


@app.get("/drafts/{draft_id}/pending-approvals")
def get_pending_approvals(draft_id: UUID, db: Session = Depends(get_db)):
    """List enhancement proposals awaiting user approval for a draft."""
    from job_agent.models import EnhancementProposal
    from job_agent.schemas import EnhancementProposalOut

    proposals = (
        db.query(EnhancementProposal)
        .filter(
            EnhancementProposal.draft_id == draft_id,
            EnhancementProposal.approved.is_(None),
        )
        .all()
    )
    return [EnhancementProposalOut.model_validate(proposal) for proposal in proposals]


@app.post("/drafts/{draft_id}/apply-enhancements")
def apply_enhancements(
    draft_id: UUID,
    body: ApplyEnhancementsRequest,
    db: Session = Depends(get_db),
):
    """Apply user-approved enhancement proposals to the draft content."""
    service = CVWorkflowService(session=db)
    try:
        updated_draft = service.apply_approved_enhancements(
            draft_id, body.approved_proposal_ids
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"draft_id": str(updated_draft.id), "status": "enhancements_applied"}


@app.get("/drafts/{draft_id}/pdf")
def download_draft_pdf(draft_id: UUID, db: Session = Depends(get_db)):
    """Compile the draft's .tex file to PDF and return it for download."""
    from fastapi.responses import FileResponse

    from job_agent.services.documents import compile_pdf

    draft = db.get(ResumeDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    if not draft.tex_path:
        raise HTTPException(status_code=400, detail="Draft has no .tex file")

    try:
        pdf_path = compile_pdf(draft.tex_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"resume_{draft_id}.pdf",
    )


@app.post("/drafts/{draft_id}/cover-letter")
def generate_cover_letter(
    draft_id: UUID,
    company_url: str | None = None,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """
    Generate a cover letter for a resume draft.
    Optionally provide company_url to fetch company context for personalization.
    """
    from job_agent.services.cover_letter import CoverLetterService

    try:
        draft = CoverLetterService(db).generate_cover_letter(draft_id, company_url=company_url)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "draft_id": str(draft.id),
        "subject": draft.cover_letter_subject or "",
        "body": draft.cover_letter_text or "",
    }


@app.post("/drafts/{draft_id}/cover-letter-html", include_in_schema=False)
def generate_cover_letter_html(
    request: Request,
    draft_id: UUID,
    db: Session = Depends(get_db),
):
    from job_agent.services.cover_letter import CoverLetterService

    target = (request.headers.get("HX-Target") or "").strip()
    template_name = "partials/cover_letter_detail.html" if target == "cl-detail" else "partials/cover_letter.html"

    try:
        draft = CoverLetterService(db).generate_cover_letter(draft_id)
    except ValueError as exc:
        return templates.TemplateResponse(
            request=request,
            name=template_name,
            context={
                "request": request,
                "draft_id": str(draft_id),
                "subject": "Error",
                "body": str(exc),
                "now": "",
            },
            status_code=404,
        )

    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context={
            "request": request,
            "draft_id": str(draft.id),
            "subject": draft.cover_letter_subject or "",
            "body": draft.cover_letter_text or "",
            "now": datetime.now(timezone.utc).strftime("%d %b %Y %H:%M"),
        },
    )


@app.get("/drafts/{draft_id}/cover-letter")
def get_cover_letter(draft_id: UUID, db: Session = Depends(get_db)) -> dict[str, str]:
    """Return the stored cover letter for a draft."""
    draft = db.get(ResumeDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    if not draft.cover_letter_text:
        raise HTTPException(
            status_code=404,
            detail="No cover letter generated yet. POST /drafts/{id}/cover-letter first.",
        )
    return {
        "draft_id": str(draft.id),
        "subject": draft.cover_letter_subject or "",
        "body": draft.cover_letter_text,
    }


@app.post("/applications", response_model=ApplicationOut)
def create_application(payload: ApplicationCreate, db: Session = Depends(get_db)) -> Application:
    job = db.get(JobPost, payload.job_post_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job post not found.")

    resume_track_id = None
    if payload.resume_track_slug:
        track = (
            db.query(ResumeTrack)
            .filter(ResumeTrack.slug == payload.resume_track_slug, ResumeTrack.active.is_(True))
            .first()
        )
        if track is None:
            raise HTTPException(status_code=404, detail="Resume track not found.")
        resume_track_id = track.id

    application = Application(
        job_post_id=payload.job_post_id,
        resume_track_id=resume_track_id,
        resume_draft_id=payload.resume_draft_id,
        status=payload.status,
        next_action=payload.next_action,
        notes=payload.notes,
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@app.get("/applications", response_model=list[ApplicationOut])
def list_applications(db: Session = Depends(get_db)) -> list[Application]:
    return db.query(Application).order_by(Application.updated_at.desc()).all()


@app.get("/analytics/rejection-patterns")
def rejection_patterns(db: Session = Depends(get_db)) -> dict:
    """
    Analyse application outcomes for patterns and recommendations.
    Returns 200 with analysis or 200 with insufficient_data status.
    """
    service = RejectionAnalyticsService(db)
    try:
        return service.analyse()
    except ValueError as exc:
        if "insufficient_data" in str(exc):
            count = db.query(Application).filter(Application.status.notin_(["pending"])).count()
            return {"status": "insufficient_data", "required": 5, "current": count}
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/ui/analytics", include_in_schema=False)
def ui_analytics(request: Request, db: Session = Depends(get_db)):
    analytics: dict[str, object] | None = None
    insufficient = False

    def _as_int(value: object) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    try:
        raw = RejectionAnalyticsService(db).aggregate(db)
    except ValueError as exc:
        if "insufficient_data" in str(exc):
            insufficient = True
            raw = None
        else:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    if isinstance(raw, dict):
        funnel_raw = raw.get("funnel")
        funnel_data = funnel_raw if isinstance(funnel_raw, dict) else {}
        applied = _as_int(funnel_data.get("applied") or funnel_data.get("discovered"))
        discovered = _as_int(funnel_data.get("discovered") or funnel_data.get("total") or applied)
        responded = _as_int(funnel_data.get("responded"))
        offer = _as_int(funnel_data.get("offer"))
        rejected = _as_int(funnel_data.get("rejected"))
        conversion_pct = round((responded / applied) * 100.0, 1) if applied > 0 else 0.0
        funnel_stages = [
            {"label": "discovered", "count": discovered, "border": "border-blue-400"},
            {"label": "applied", "count": applied, "border": "border-indigo-500"},
            {"label": "responded", "count": responded, "border": "border-yellow-500"},
            {"label": "offer", "count": offer, "border": "border-green-500"},
            {"label": "rejected", "count": rejected, "border": "border-red-500"},
        ]

        score_buckets: dict[str, int] = {
            "90-100": 0,
            "75-89": 0,
            "50-74": 0,
            "below-50": 0,
        }
        score_bucket_raw = raw.get("score_buckets")
        if isinstance(score_bucket_raw, dict):
            for key in score_buckets:
                score_buckets[key] = _as_int(score_bucket_raw.get(key))
        else:
            score_analysis = raw.get("score_analysis")
            bucket_rows = (
                score_analysis.get("buckets", [])
                if isinstance(score_analysis, dict)
                else []
            )
            if isinstance(bucket_rows, list):
                for row in bucket_rows:
                    if not isinstance(row, dict):
                        continue
                    label = str(row.get("range", "")).strip()
                    count = _as_int(row.get("count"))
                    if label in {"90-100", "85-100"}:
                        score_buckets["90-100"] += count
                    elif label in {"75-89", "75-84"}:
                        score_buckets["75-89"] += count
                    elif label in {"50-74", "60-74"}:
                        score_buckets["50-74"] += count
                    elif label in {"below-50", "< 60", "<60", "< 50", "<50"}:
                        score_buckets["below-50"] += count

        max_bucket = max(score_buckets.values()) if any(score_buckets.values()) else 0
        score_rows = []
        for label, color in [
            ("90-100", "bg-green-500"),
            ("75-89", "bg-indigo-500"),
            ("50-74", "bg-yellow-500"),
            ("below-50", "bg-red-500"),
        ]:
            count = score_buckets[label]
            width_pct = round((count / max_bucket) * 100.0, 2) if max_bucket > 0 else 0.0
            score_rows.append({"label": label, "count": count, "width_pct": width_pct, "color": color})

        skill_gaps = []
        skill_gap_rows = raw.get("skill_gaps")
        if isinstance(skill_gap_rows, list):
            for row in skill_gap_rows:
                if not isinstance(row, dict):
                    continue
                keyword = str(row.get("keyword") or row.get("gap") or "").strip()
                miss_count = _as_int(row.get("miss_count") or row.get("occurrences"))
                if keyword:
                    skill_gaps.append({"keyword": keyword, "miss_count": miss_count})
        skill_gaps = skill_gaps[:8]

        weekly_activity = []
        weekly_rows = raw.get("weekly_activity")
        if isinstance(weekly_rows, list):
            for row in weekly_rows:
                if not isinstance(row, dict):
                    continue
                week = str(row.get("week") or "").strip()
                count = _as_int(row.get("count") or row.get("applied"))
                if week:
                    weekly_activity.append({"week": week, "count": count})
        weekly_activity = weekly_activity[-8:]

        analytics = {
            "funnel_stages": funnel_stages,
            "response_conversion_pct": conversion_pct,
            "score_rows": score_rows,
            "skill_gaps": skill_gaps,
            "weekly_activity": weekly_activity,
        }

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    logs = (
        db.query(CareerPageScanLog)
        .filter(CareerPageScanLog.scanned_at >= cutoff)
        .order_by(CareerPageScanLog.new_jobs.desc())
        .limit(10)
        .all()
    )
    velocity = []
    for log in logs:
        source = db.get(CareerPageSource, log.source_id)
        velocity.append(
            {
                "company": source.company if source else "unknown",
                "new_jobs": log.new_jobs,
                "scanned_at": log.scanned_at.strftime("%d %b %Y %H:%M") if log.scanned_at else "",
            }
        )

    return templates.TemplateResponse(
        request=request,
        name="analytics.html",
        context=_ui_context(
            request,
            "Analytics",
            analytics=analytics,
            insufficient=insufficient,
            velocity=velocity,
        ),
    )


@app.patch("/applications/{application_id}", response_model=ApplicationOut)
def update_application(application_id: str, payload: ApplicationUpdate, db: Session = Depends(get_db)) -> Application:
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(application, key, value)
    db.commit()
    db.refresh(application)
    return application


@app.post("/applications/{application_id}/communications", response_model=CommunicationEventOut)
def add_communication_event(
    application_id: str,
    payload: CommunicationEventCreate,
    db: Session = Depends(get_db),
) -> CommunicationEvent:
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found.")
    event = CommunicationEvent(
        application_id=application.id,
        channel=payload.channel,
        direction=payload.direction,
        event_type=payload.event_type,
        sender_name=payload.sender_name,
        sender_email=payload.sender_email,
        subject=payload.subject,
        snippet=payload.snippet,
        event_at=payload.event_at or datetime.now(timezone.utc),
    )
    db.add(event)
    application.last_email_at = event.event_at
    db.commit()
    db.refresh(event)
    return event


@app.get("/applications/{application_id}/communications", response_model=list[CommunicationEventOut])
def list_communication_events(application_id: str, db: Session = Depends(get_db)) -> list[CommunicationEvent]:
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found.")
    return (
        db.query(CommunicationEvent)
        .filter(CommunicationEvent.application_id == application.id)
        .order_by(CommunicationEvent.event_at.desc())
        .all()
    )


@app.post("/exports/jobs-csv", response_model=CsvExportOut)
def export_jobs_csv(db: Session = Depends(get_db)) -> CsvExport:
    service = CsvExportService(db)
    return service.export_jobs_snapshot()


@app.get("/exports", response_model=list[CsvExportOut])
def list_exports(db: Session = Depends(get_db)) -> list[CsvExport]:
    return db.query(CsvExport).order_by(CsvExport.created_at.desc()).all()


@app.post("/thesis-targets", response_model=ThesisTargetOut, status_code=201)
def create_thesis_target(payload: ThesisTargetCreate, db: Session = Depends(get_db)) -> ThesisTarget:
    target = ThesisTarget(**payload.model_dump())
    db.add(target)
    db.commit()
    db.refresh(target)
    return target


@app.get("/thesis-targets", response_model=list[ThesisTargetOut])
def list_thesis_targets(
    status: str | None = None,
    country: str | None = None,
    type: str | None = None,
    db: Session = Depends(get_db),
) -> list[ThesisTarget]:
    query = db.query(ThesisTarget)
    if status:
        query = query.filter(ThesisTarget.status == status)
    if country:
        query = query.filter(ThesisTarget.country == country)
    if type:
        query = query.filter(ThesisTarget.type == type)
    return query.order_by(ThesisTarget.priority.asc(), ThesisTarget.created_at.desc()).all()


@app.get("/thesis-targets/{target_id}", response_model=ThesisTargetOut)
def get_thesis_target(target_id: int, db: Session = Depends(get_db)) -> ThesisTarget:
    target = db.query(ThesisTarget).filter_by(id=target_id).first()
    if target is None:
        raise HTTPException(status_code=404, detail="Thesis target not found.")
    return target


@app.patch("/thesis-targets/{target_id}", response_model=ThesisTargetOut)
def update_thesis_target(
    target_id: int,
    payload: ThesisTargetUpdate,
    db: Session = Depends(get_db),
) -> ThesisTarget:
    target = db.query(ThesisTarget).filter_by(id=target_id).first()
    if target is None:
        raise HTTPException(status_code=404, detail="Thesis target not found.")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(target, field, value)
    target.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(target)
    return target


@app.delete("/thesis-targets/{target_id}", status_code=204)
def archive_thesis_target(target_id: int, db: Session = Depends(get_db)) -> Response:
    target = db.query(ThesisTarget).filter_by(id=target_id).first()
    if target is None:
        raise HTTPException(status_code=404, detail="Thesis target not found.")
    target.status = "archived"
    target.updated_at = datetime.now(timezone.utc)
    db.commit()
    return Response(status_code=204)


@app.post("/thesis-targets/{target_id}/communications", response_model=ContactEventOut, status_code=201)
def log_contact_event(
    target_id: int,
    payload: ContactEventCreate,
    db: Session = Depends(get_db),
) -> ContactEvent:
    target = db.query(ThesisTarget).filter_by(id=target_id).first()
    if target is None:
        raise HTTPException(status_code=404, detail="Thesis target not found.")
    event = ContactEvent(
        target_id=target_id,
        **payload.model_dump(exclude_none=True, exclude={"event_at"}),
        event_at=payload.event_at or datetime.now(timezone.utc),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@app.get("/thesis-targets/{target_id}/communications", response_model=list[ContactEventOut])
def list_contact_events(target_id: int, db: Session = Depends(get_db)) -> list[ContactEvent]:
    return (
        db.query(ContactEvent)
        .filter_by(target_id=target_id)
        .order_by(ContactEvent.event_at.desc())
        .all()
    )


@app.get("/thesis-targets/{target_id}/outreach-drafts", response_model=list[OutreachDraftOut])
def list_outreach_drafts(target_id: int, db: Session = Depends(get_db)) -> list[OutreachDraft]:
    return (
        db.query(OutreachDraft)
        .filter_by(target_id=target_id)
        .order_by(OutreachDraft.created_at.desc())
        .all()
    )


@app.post("/outreach-drafts/{draft_id}/approve", response_model=OutreachDraftOut)
def approve_outreach_draft(draft_id: int, db: Session = Depends(get_db)) -> OutreachDraft:
    draft = db.query(OutreachDraft).filter_by(id=draft_id).first()
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")
    draft.approved = True
    draft.status = "approved"

    siblings = (
        db.query(OutreachDraft)
        .filter(OutreachDraft.target_id == draft.target_id, OutreachDraft.id != draft_id)
        .all()
    )
    for sibling in siblings:
        sibling.approved = False
        if sibling.status == "approved":
            sibling.status = "rejected"

    target = db.query(ThesisTarget).filter_by(id=draft.target_id).first()
    if target is not None and target.status == "email_drafted":
        target.status = "email_approved"
        target.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(draft)
    return draft


@app.post("/thesis-targets/{target_id}/generate-email", response_model=OutreachDraftOut, status_code=201)
def generate_outreach_email(target_id: int, db: Session = Depends(get_db)) -> OutreachDraft:
    try:
        return ThesisOutreachService().generate_email(target_id, db)
    except ValueError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@app.post("/outreach-drafts/{draft_id}/revise", response_model=OutreachDraftOut)
def revise_outreach_draft(
    draft_id: int,
    payload: OutreachDraftRevisionRequest,
    db: Session = Depends(get_db),
) -> OutreachDraft:
    try:
        return ThesisOutreachService().revise_email(draft_id, payload.feedback, db)
    except ValueError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@app.post("/outreach-drafts/{draft_id}/mark-sent", response_model=OutreachDraftOut)
def mark_outreach_draft_sent(draft_id: int, db: Session = Depends(get_db)) -> OutreachDraft:
    try:
        return ThesisOutreachService().mark_sent(draft_id, db)
    except ValueError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
