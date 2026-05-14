"""Focused queue/discovery mutations used by the jobs router.

The public HTTP routes remain in ``jobs.py``. This helper module keeps the
mutation rules readable and reusable without changing route paths or tests.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, Request, Response
from sqlalchemy.orm import Session, joinedload

from job_agent.config import settings
from job_agent.models import JobPost, JobTrackScore, WorkflowTask
from job_agent.providers import normalize_provider_mode
from job_agent.routers.job_views import _job_row_payload
from job_agent.routers.setup_state import _active_candidate_id
from job_agent.routers.templates import templates
from job_agent.search_preferences import MAX_DISCOVERY_ROLES, normalize_role_list, primary_search_country
from job_agent.services.job_signals import JobSignalService
from job_agent.services.workflows import CVWorkflowService

VALID_QUEUE_STATES = {"new", "shortlisted", "saved", "passed"}


def empty_discovery_counts() -> dict[str, int]:
    return {
        "roles_queried": 0,
        "raw_hits": 0,
        "ats_sources_scanned": 0,
        "ats_raw_hits": 0,
        "duplicates": 0,
        "rejected_by_country": 0,
        "rejected_by_role": 0,
        "rejected_by_seniority": 0,
        "queued_for_scoring": 0,
        "scored_jobs": 0,
        "awaiting_enrichment_count": 0,
        "provider_scored_count": 0,
        "fallback_scored_count": 0,
        "ready_for_threshold_count": 0,
        "saved_jobs": 0,
        "visible_after_threshold": 0,
        "visible_in_default_view": 0,
    }


def queue_job_discovery_task(db: Session) -> WorkflowTask:
    if not settings.use_jobspy:
        raise HTTPException(
            status_code=409,
            detail="Job discovery is disabled. Enable JobSpy for explicit searches in Settings > Job Discovery first.",
            headers={"X-Toast-Error": "Job discovery is disabled. Enable JobSpy for explicit searches in Settings > Job Discovery first."},
        )
    roles = normalize_role_list(settings.jobspy_discover_queries)[:MAX_DISCOVERY_ROLES]
    if not roles:
        raise HTTPException(
            status_code=400,
            detail="Set at least one desired role before running discovery.",
            headers={"X-Toast-Error": "Set at least one desired role before running discovery."},
        )

    selected_country = primary_search_country(
        settings.job_search_countries,
        settings.jobspy_discover_location or "Italy",
    )
    task = WorkflowTask(
        kind="job_discovery",
        payload={
            "candidate_id": _active_candidate_id(db) or settings.default_candidate_id.strip() or None,
            "provider_mode": normalize_provider_mode(getattr(settings, "llm_provider_mode", "openai")),
            "country": selected_country,
            "roles": roles,
            "seniority": str(settings.target_job_seniority or "junior"),
            "location": selected_country,
            "sources": ["linkedin"],
            "source_policy": "job_boards_only",
            "include_ats": False,
            "include_direct_company_sources": False,
            "career_source_ids": [],
            "limit": int(settings.jobspy_default_limit),
            "threshold": int(settings.discovery_min_fit_score),
            "visible_cap": int(settings.discovery_max_visible_jobs),
        },
        result={
            "source": "user_initiated_discovery",
            "stage": "pending",
            "message": "Discovery task queued.",
            "counts": empty_discovery_counts(),
        },
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def set_job_queue_state(job: JobPost, state: str) -> None:
    normalized = state.strip().lower()
    if normalized not in VALID_QUEUE_STATES:
        raise HTTPException(status_code=422, detail="Invalid queue state.")
    job.queue_state = normalized
    if job.status != "applied":
        job.status = "new" if normalized == "new" else "reviewed"


def queue_cv_for_job(
    *,
    db: Session,
    job_id: UUID,
    resume_track_slug: str | None = None,
    confirm: bool = False,
) -> Response:
    job = db.get(JobPost, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job post not found.")
    if str(getattr(job, "enrichment_status", "pending") or "pending") == "needs_input" or not str(job.description or "").strip():
        return Response(
            status_code=409,
            headers={"X-Toast-Error": "This job still needs a real description before drafting is safe. Retry enrichment or add the JD manually."},
        )

    link_check = JobSignalService(db).refresh_apply_link_check(job)
    if link_check["status"] in {"missing", "unavailable"}:
        db.commit()
        return Response(
            status_code=409,
            headers={"X-Toast-Error": "Apply link is unavailable. Refresh or verify the job before drafting."},
        )

    job_payload = _job_row_payload(db, job)
    best_score = int(job_payload.get("best_score") or 0)
    minimum_queue_score = max(60, int(settings.discovery_min_fit_score) - 10)
    if best_score < minimum_queue_score:
        return Response(
            status_code=409,
            headers={
                "X-Toast-Error": (
                    f"This job is currently low fit ({best_score}%). "
                    f"Queueing is locked below {minimum_queue_score}% to avoid low-quality drafts."
                )
            },
        )
    package_summary = dict(job_payload.get("package_summary") or {})
    if not package_summary.get("fast_lane") and str(getattr(job, "queue_state", "") or "") != "shortlisted" and not confirm:
        return Response(
            status_code=409,
            headers={"X-Toast-Error": "Review the application snapshot first, then confirm before generating a package."},
        )

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

    readiness = CVWorkflowService(db).profile_readiness_for_job(str(job_id), track_slug)
    if readiness["status"] == "insufficient_profile_data":
        return Response(
            status_code=409,
            headers={
                "X-Toast-Error": (
                    "Your profile still needs more grounded evidence before Job Agent can safely produce a final CV."
                )
            },
        )

    set_job_queue_state(job, "shortlisted")
    CVWorkflowService(db).queue_cv_workflow(
        job_post_id=job_id,
        resume_track_slug=track_slug,
        force_cloud_review=False,
    )
    db.add(job)
    db.commit()
    return Response(
        status_code=204,
        headers={"HX-Refresh": "true", "X-Toast-Success": "Application package queued"},
    )


def queue_state_response(*, request: Request, db: Session, job_id: UUID, state: str):
    job = db.get(JobPost, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    set_job_queue_state(job, state)
    db.add(job)
    db.commit()
    label = {
        "new": "Moved back to review",
        "shortlisted": "Added to shortlist",
        "saved": "Saved for later",
        "passed": "Marked as not for you",
    }.get(job.queue_state, "Queue updated")
    job_payload = _job_row_payload(db, job)
    return templates.TemplateResponse(
        request=request,
        name="partials/job_row.html",
        context={"request": request, "job": job_payload},
        headers={"X-Toast-Success": label},
    )
