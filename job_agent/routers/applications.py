"""Applications, analytics, exports, and their UI routes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session, joinedload

from job_agent.config import settings
from job_agent.db import get_db
from job_agent.models import (
    Application,
    CareerPageScanLog,
    CareerPageSource,
    CommunicationEvent,
    CsvExport,
    ResumeTrack,
)
from job_agent.schemas import (
    ApplicationCreate,
    ApplicationOut,
    ApplicationUpdate,
    CommunicationEventCreate,
    CommunicationEventOut,
    CsvExportOut,
)
from job_agent.services.discovery_hub import discovery_health
from job_agent.services.exporters import CsvExportService
from job_agent.services.rejection_analytics import RejectionAnalyticsService

from job_agent.routers.setup_state import _raise_if_setup_required, _redirect_if_setup_required
from job_agent.routers.templates import templates
from job_agent.routers.ui_context import _ui_context

router = APIRouter()


# ── Applications ───────────────────────────────────────────────────────────────

@router.post("/applications", response_model=ApplicationOut)
def create_application(payload: ApplicationCreate, db: Session = Depends(get_db)) -> Application:
    from job_agent.models import JobPost

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
    job.status = "applied"
    job.queue_state = "shortlisted"
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@router.get("/applications", response_model=list[ApplicationOut])
def list_applications(db: Session = Depends(get_db)) -> list[Application]:
    return db.query(Application).order_by(Application.updated_at.desc()).all()


@router.patch("/applications/{application_id}", response_model=ApplicationOut)
def update_application(application_id: str, payload: ApplicationUpdate, db: Session = Depends(get_db)) -> Application:
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(application, key, value)
    if application.job_post is not None:
        application.job_post.status = "applied"
        application.job_post.queue_state = "shortlisted"
    db.commit()
    db.refresh(application)
    return application


@router.post("/applications/{application_id}/communications", response_model=CommunicationEventOut)
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


@router.get("/applications/{application_id}/communications", response_model=list[CommunicationEventOut])
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


# ── Exports ────────────────────────────────────────────────────────────────────

@router.post("/exports/jobs-csv", response_model=CsvExportOut)
def export_jobs_csv(db: Session = Depends(get_db)) -> CsvExport:
    service = CsvExportService(db)
    return service.export_jobs_snapshot()


@router.get("/exports", response_model=list[CsvExportOut])
def list_exports(db: Session = Depends(get_db)) -> list[CsvExport]:
    return db.query(CsvExport).order_by(CsvExport.created_at.desc()).all()


# ── Analytics ──────────────────────────────────────────────────────────────────

@router.get("/analytics/rejection-patterns")
def rejection_patterns(db: Session = Depends(get_db)) -> dict:
    service = RejectionAnalyticsService(db)
    try:
        return service.analyse()
    except ValueError as exc:
        if "insufficient_data" in str(exc):
            count = db.query(Application).filter(Application.status.notin_(["pending"])).count()
            return {"status": "insufficient_data", "required": 5, "current": count}
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/analytics/skill-gaps")
def analytics_skill_gaps(
    request: Request,
    top_n: int = 20,
    db: Session = Depends(get_db),
):
    from job_agent.services.skill_gap_analytics import SkillGapAnalyticsService

    candidate_id = settings.default_candidate_id.strip()
    data = {
        "top_gaps": [],
        "total_drafts_analyzed": 0,
        "unique_missing_skills": 0,
    }
    if candidate_id:
        data = SkillGapAnalyticsService(session=db).compute(candidate_id=candidate_id, top_n=top_n)

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            request=request,
            name="partials/skill_gaps.html",
            context=data,
        )
    return data


@router.get("/analytics/discovery-health")
def analytics_discovery_health(request: Request, db: Session = Depends(get_db)):
    data = discovery_health(db)
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            request=request,
            name="partials/discovery_health.html",
            context=data,
        )
    return data


# ── Application UI pages ───────────────────────────────────────────────────────

@router.get("/ui/applications", include_in_schema=False)
def ui_applications(request: Request, db: Session = Depends(get_db)):
    if redirect := _redirect_if_setup_required(request, db):
        return redirect
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


@router.post("/ui/applications/{application_id}/advance", include_in_schema=False)
def ui_advance_application(application_id: UUID, db: Session = Depends(get_db)) -> Response:
    _raise_if_setup_required(db)
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


@router.get("/ui/analytics", include_in_schema=False)
def ui_analytics(request: Request, db: Session = Depends(get_db)):
    if redirect := _redirect_if_setup_required(request, db):
        return redirect
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
