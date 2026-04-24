"""Shared job list and dashboard query helpers for routers."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

import httpx
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from job_agent.config import settings
from job_agent.models import (
    Application,
    EnhancementProposal,
    JobPost,
    JobTrackScore,
    ResumeDraft,
    ResumeTrack,
    ThesisTarget,
)
from job_agent.search_preferences import detect_job_languages, job_matches_language_preferences


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


def _job_language_rows(job: JobPost) -> list[dict[str, object]]:
    metadata = dict(job.extracted_metadata or {})
    existing = metadata.get("detected_job_languages")
    if isinstance(existing, list) and existing:
        rows: list[dict[str, object]] = []
        for item in existing:
            if isinstance(item, dict):
                name = str(item.get("name") or "").strip()
                if not name:
                    continue
                rows.append(
                    {
                        "name": name,
                        "code": str(item.get("code") or name[:2]).lower(),
                        "score": int(item.get("score") or 0),
                    }
                )
            elif isinstance(item, str) and item.strip():
                rows.append({"name": item.strip(), "code": item.strip()[:2].lower(), "score": 0})
        if rows:
            return rows
    return detect_job_languages(job.description or "")


def _job_passes_language_filter(job: JobPost) -> bool:
    return job_matches_language_preferences(job.description or "", settings.job_search_languages)


def _build_job_ui_payload(
    job: JobPost,
    score_row: JobTrackScore | None,
    *,
    detected_languages: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    best_score = int(round(score_row.score)) if score_row is not None else 0
    best_track = score_row.resume_track.title if score_row and score_row.resume_track else None
    best_track_slug = (
        score_row.resume_track.slug
        if score_row and score_row.resume_track
        else (job.role_track_hint or None)
    )
    language_rows = detected_languages if detected_languages is not None else _job_language_rows(job)
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
        "job_languages": [str(item.get("name")) for item in language_rows if str(item.get("name") or "").strip()],
        "created_at": job.created_at,
    }


def _get_priority_jobs(db: Session) -> list[dict[str, object]]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    jobs = (
        db.query(JobPost)
        .filter(JobPost.status == "new", JobPost.created_at >= cutoff)
        .order_by(JobPost.created_at.desc())
        .limit(20)
        .all()
    )
    score_map = _score_rows_for_jobs(db, [job.id for job in jobs])
    rows = []
    for job in jobs:
        score_row = score_map.get(job.id, [None])[0] if score_map.get(job.id) else None
        payload = _build_job_ui_payload(job, score_row)
        if payload["best_score"] >= 75:
            rows.append(payload)
    rows.sort(key=lambda row: row["best_score"], reverse=True)
    return rows[:5]


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
    posted_after: date | None = None,
) -> list[dict[str, object]]:
    threshold = 0 if show_all else (min_score if min_score is not None else settings.match_min_score)
    normalized_track_id = track_id.strip() if track_id else None

    query = db.query(JobPost)
    if status:
        query = query.filter(JobPost.status == status)
    if posted_after is not None:
        cutoff = datetime.combine(posted_after, datetime.min.time())
        query = query.filter(JobPost.created_at >= cutoff)
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
        detected_languages = _job_language_rows(job)
        if not show_all and not _job_passes_language_filter(job):
            continue
        rows.append(_build_job_ui_payload(job, display_score, detected_languages=detected_languages))

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


def _get_dashboard_data(db: Session) -> dict[str, object]:
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

