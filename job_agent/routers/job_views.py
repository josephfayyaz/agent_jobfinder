"""Shared job list, queue, and dashboard query helpers for routers."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
import re
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from job_agent.config import normalize_lm_studio_base_url, settings
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
from job_agent.services.job_fit_scoring import effective_job_fit_details
from job_agent.services.job_signals import JobSignalService

QUEUE_STATE_LABELS = {
    "new": "Review now",
    "shortlisted": "Shortlist",
    "saved": "Save for later",
    "passed": "Not for me",
}
QUEUE_LANES = {
    "review": "New for you",
    "shortlist": "Shortlist",
    "saved": "Save for later",
    "passed": "Not for me",
    "applied": "Already applied",
    "all": "All jobs",
}
ENRICHMENT_LABELS = {
    "pending": "Pending enrichment",
    "ok": "Ready",
    "partial": "Partial",
    "needs_input": "Needs input",
    "failed": "Fetch failed",
}


def _source_trail(job: JobPost) -> dict[str, object]:
    metadata = dict(job.extracted_metadata or {})
    trail = metadata.get("source_trail")
    if not isinstance(trail, dict):
        return {
            "path": "manual_import",
            "path_label": "Imported",
            "confidence_label": "Imported",
            "tone": "neutral",
            "reasons": [],
        }
    return {
        "path": str(trail.get("path") or "manual_import"),
        "path_label": str(trail.get("path_label") or "Imported"),
        "confidence_label": str(trail.get("confidence_label") or "Imported"),
        "tone": str(trail.get("tone") or "neutral"),
        "reasons": list(trail.get("reasons") or []),
        "direct_company_source": bool(trail.get("direct_company_source")),
        "source_host": str(trail.get("source_host") or ""),
    }


def _package_summary(
    *,
    job: JobPost,
    best_score: int,
    queue_state: str,
    signal_data: dict[str, Any],
) -> dict[str, object]:
    strong_fit = best_score >= 85
    trust_ok = signal_data.get("confidence", {}).get("label") in {"Still active", "Recently seen", "Recently imported"}
    link_live = signal_data.get("link_check", {}).get("status") == "live"
    enrichment_ready = str(getattr(job, "enrichment_status", "") or "pending") in {"ok", "partial"}
    has_description = bool(str(job.description or "").strip())
    fast_lane = queue_state == "shortlisted" or (strong_fit and trust_ok and link_live and enrichment_ready and has_description)

    reasons: list[str] = []
    if not strong_fit:
        reasons.append("Fit is not yet in the strong-match range.")
    if not trust_ok:
        reasons.append("Trust signals still need a quick review.")
    if not link_live:
        reasons.append("Apply link has not been confirmed as live.")
    if not enrichment_ready or not has_description:
        reasons.append("Job description still needs stronger detail before drafting.")

    readiness = "Ready to spend tokens" if fast_lane else "Review before drafting"
    return {
        "fast_lane": fast_lane,
        "readiness_label": readiness,
        "fit_label": "Strong fit" if strong_fit else "Needs review",
        "trust_label": "Healthy trust" if trust_ok else "Verify first",
        "detail_label": "JD ready" if enrichment_ready and has_description else "Need more detail",
        "reasons": reasons,
    }


def _normalize_queue_state(job: JobPost) -> str:
    value = str(getattr(job, "queue_state", "") or "").strip().lower()
    return value if value in QUEUE_STATE_LABELS else "new"


def _application_rows_for_jobs(db: Session, job_ids: list[UUID]) -> dict[UUID, Application]:
    if not job_ids:
        return {}

    rows = (
        db.query(Application)
        .filter(Application.job_post_id.in_(job_ids))
        .order_by(Application.updated_at.desc(), Application.created_at.desc())
        .all()
    )
    grouped: dict[UUID, Application] = {}
    for row in rows:
        grouped.setdefault(row.job_post_id, row)
    return grouped


def _queue_lane_for_job(job: JobPost, application: Application | None) -> str:
    if application is not None or job.status == "applied":
        return "applied"
    queue_state = _normalize_queue_state(job)
    if queue_state == "shortlisted":
        return "shortlist"
    if queue_state == "saved":
        return "saved"
    if queue_state == "passed":
        return "passed"
    return "review"


def _review_priority(
    *,
    best_score: int,
    lane: str,
    signals: dict[str, Any],
    created_at: datetime | None,
) -> float:
    priority = float(best_score)
    if lane == "shortlist":
        priority += 12
    elif lane == "review":
        priority += 6
    elif lane == "saved":
        priority -= 4
    elif lane == "passed":
        priority -= 20

    freshness = signals.get("freshness", {})
    confidence = signals.get("confidence", {})
    link_check = signals.get("link_check", {})
    suspicion = signals.get("suspicion", {})
    enrichment_status = str(signals.get("enrichment_status") or "")

    if freshness.get("label") == "Fresh":
        priority += 12
    elif freshness.get("label") == "Recent":
        priority += 6
    elif freshness.get("label") == "Stale listing":
        priority -= 10

    if confidence.get("label") == "Still active":
        priority += 10
    elif confidence.get("label") == "Recently seen":
        priority += 6
    elif confidence.get("label") == "Needs verification":
        priority -= 8

    if signals.get("is_surging"):
        priority += 8
    if link_check.get("status") == "live":
        priority += 4
    elif link_check.get("status") == "unavailable":
        priority -= 16
    elif link_check.get("status") == "missing":
        priority -= 20
    if suspicion.get("label") == "Needs verification":
        priority -= 10
    if enrichment_status == "needs_input":
        priority -= 18
    elif enrichment_status == "failed":
        priority -= 12

    if created_at is not None:
        anchored = _coerce_datetime(created_at) or datetime.now(timezone.utc)
        hours_old = max(0.0, (datetime.now(timezone.utc) - anchored).total_seconds() / 3600)
        priority -= min(hours_old / 24.0, 10.0)

    return round(priority, 2)


def _coerce_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


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


def _description_snippet(description: str | None, *, max_chars: int = 420) -> str:
    text = re.sub(r"\s+", " ", str(description or "")).strip()
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def _build_job_ui_payload(
    job: JobPost,
    score_row: JobTrackScore | None,
    *,
    detected_languages: list[dict[str, object]] | None = None,
    application: Application | None = None,
    signals: dict[str, Any] | None = None,
) -> dict[str, object]:
    active_candidate_id = settings.default_candidate_id.strip() or None
    fit_details = effective_job_fit_details(
        job,
        candidate_id=active_candidate_id,
        score_rows=[score_row] if score_row is not None else None,
    )
    best_score = int(round(float(fit_details.get("fit_score") or 0)))
    best_track = score_row.resume_track.title if score_row and score_row.resume_track else None
    best_track_slug = (
        score_row.resume_track.slug
        if score_row and score_row.resume_track
        else (job.role_track_hint or None)
    )
    language_rows = detected_languages if detected_languages is not None else _job_language_rows(job)
    queue_state = _normalize_queue_state(job)
    lane = _queue_lane_for_job(job, application)
    signal_data = signals or {}
    created_at = _coerce_datetime(job.created_at)
    source_trail = _source_trail(job)
    return {
        "id": str(job.id),
        "title": job.title,
        "company": job.company,
        "has_description": bool(str(job.description or "").strip()),
        "description_snippet": _description_snippet(job.description),
        "status": job.status,
        "application_status": application.status if application is not None else "",
        "queue_state": queue_state,
        "queue_state_label": QUEUE_STATE_LABELS.get(queue_state, "Review now"),
        "lane": lane,
        "lane_label": QUEUE_LANES.get(lane, "New for you"),
        "source_url": job.source_url,
        "canonical_apply_url": job.canonical_apply_url,
        "company_url": job.company_url,
        "best_score": best_score,
        "fit_source": str(fit_details.get("score_source") or "fallback"),
        "fit_provider_mode": str(fit_details.get("provider_mode") or ""),
        "fit_short_reason": str(fit_details.get("short_reason") or ""),
        "fit_matched_evidence": list(fit_details.get("matched_evidence") or []),
        "fit_top_gaps": list(fit_details.get("top_gaps") or []),
        "language_assessment": dict(fit_details.get("language_assessment") or {}),
        "seniority_assessment": dict(fit_details.get("seniority_assessment") or {}),
        "best_track": best_track,
        "best_track_slug": best_track_slug,
        "job_languages": [str(item.get("name")) for item in language_rows if str(item.get("name") or "").strip()],
        "enrichment_status": str(getattr(job, "enrichment_status", "") or "pending"),
        "enrichment_label": ENRICHMENT_LABELS.get(str(getattr(job, "enrichment_status", "") or "pending"), "Pending enrichment"),
        "created_at": created_at,
        "signals": signal_data,
        "source_trail": source_trail,
        "canonical_reason": str(dict(job.extracted_metadata or {}).get("canonical_reason") or ""),
        "snapshot_unlocked": queue_state == "shortlisted" or best_score >= 85,
        "priority_score": _review_priority(
            best_score=best_score,
            lane=lane,
            signals={**signal_data, "enrichment_status": str(getattr(job, "enrichment_status", "") or "pending")},
            created_at=created_at,
        ),
        "package_summary": _package_summary(
            job=job,
            best_score=best_score,
            queue_state=queue_state,
            signal_data={**signal_data, "enrichment_status": str(getattr(job, "enrichment_status", "") or "pending")},
        ),
    }


def _get_priority_jobs(db: Session) -> list[dict[str, object]]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    jobs = (
        db.query(JobPost)
        .filter(JobPost.created_at >= cutoff)
        .order_by(JobPost.created_at.desc())
        .limit(20)
        .all()
    )
    score_map = _score_rows_for_jobs(db, [job.id for job in jobs])
    application_map = _application_rows_for_jobs(db, [job.id for job in jobs])
    signal_map = JobSignalService(db).evaluate_many(jobs)
    rows = []
    for job in jobs:
        score_row = score_map.get(job.id, [None])[0] if score_map.get(job.id) else None
        payload = _build_job_ui_payload(
            job,
            score_row,
            application=application_map.get(job.id),
            signals=signal_map.get(job.id),
        )
        if payload["best_score"] >= 75 and payload["lane"] == "review":
            rows.append(payload)
    rows.sort(key=lambda row: (row["priority_score"], row["best_score"]), reverse=True)
    return rows[:5]


def _get_recent_jobs_with_scores(db: Session, limit: int = 8) -> list[dict[str, object]]:
    jobs = db.query(JobPost).order_by(JobPost.created_at.desc()).limit(limit).all()
    score_map = _score_rows_for_jobs(db, [job.id for job in jobs])
    application_map = _application_rows_for_jobs(db, [job.id for job in jobs])
    signal_map = JobSignalService(db).evaluate_many(jobs)
    return [
        _build_job_ui_payload(
            job,
            score_map.get(job.id, [None])[0] if score_map.get(job.id) else None,
            application=application_map.get(job.id),
            signals=signal_map.get(job.id),
        )
        for job in jobs
    ]


def _job_rows_for_ui(
    db: Session,
    min_score: int | None = None,
    track_id: str | None = None,
    status: str | None = None,
    show_all: bool = False,
    posted_after: date | None = None,
) -> list[dict[str, object]]:
    threshold = 0 if show_all else (min_score if min_score is not None else settings.discovery_min_fit_score)
    normalized_track_id = track_id.strip() if track_id else None

    query = db.query(JobPost)
    if status:
        query = query.filter(JobPost.status == status)
    if posted_after is not None:
        cutoff = datetime.combine(posted_after, datetime.min.time(), tzinfo=timezone.utc)
        query = query.filter(JobPost.created_at >= cutoff)
    jobs = query.order_by(JobPost.created_at.desc()).all()

    score_map = _score_rows_for_jobs(db, [job.id for job in jobs])
    application_map = _application_rows_for_jobs(db, [job.id for job in jobs])
    signal_map = JobSignalService(db).evaluate_many(jobs)

    rows: list[dict[str, object]] = []
    for job in jobs:
        scores = score_map.get(job.id, [])
        visible_scores = scores
        if normalized_track_id is not None:
            visible_scores = [score for score in scores if str(score.resume_track_id) == normalized_track_id]

        display_score = visible_scores[0] if visible_scores else None
        if normalized_track_id is not None and display_score is None:
            continue
        detected_languages = _job_language_rows(job)
        payload = _build_job_ui_payload(
            job,
            display_score,
            detected_languages=detected_languages,
            application=application_map.get(job.id),
            signals=signal_map.get(job.id),
        )
        if threshold > 0 and int(payload["best_score"]) < threshold:
            continue
        rows.append(payload)

    return rows


def _queue_counts(rows: list[dict[str, object]]) -> dict[str, int]:
    counts = {lane: 0 for lane in QUEUE_LANES}
    for row in rows:
        counts["all"] += 1
        lane = str(row.get("lane") or "review")
        if lane in counts:
            counts[lane] += 1
    return counts


def _job_row_payload(db: Session, job: JobPost) -> dict[str, object]:
    score_map = _score_rows_for_jobs(db, [job.id])
    application_map = _application_rows_for_jobs(db, [job.id])
    signal_map = JobSignalService(db).evaluate_many([job])
    return _build_job_ui_payload(
        job,
        score_map.get(job.id, [None])[0] if score_map.get(job.id) else None,
        detected_languages=_job_language_rows(job),
        application=application_map.get(job.id),
        signals=signal_map.get(job.id),
    )


def _query_jobs_for_ui(
    db: Session,
    min_score: int | None = None,
    track_id: str | None = None,
    status: str | None = None,
    show_all: bool = False,
    posted_after: date | None = None,
    lane: str = "review",
) -> list[dict[str, object]]:
    rows = _job_rows_for_ui(
        db,
        min_score=min_score,
        track_id=track_id,
        status=status,
        show_all=show_all,
        posted_after=posted_after,
    )
    normalized_lane = lane if lane in QUEUE_LANES else "review"
    if normalized_lane != "all":
        rows = [row for row in rows if row["lane"] == normalized_lane]

    default_dt = datetime.min.replace(tzinfo=timezone.utc)
    if normalized_lane == "applied":
        rows.sort(key=lambda item: item["created_at"] or default_dt, reverse=True)
    else:
        rows.sort(
            key=lambda item: (float(item["priority_score"]), int(item["best_score"]), item["created_at"] or default_dt),
            reverse=True,
        )
    return rows


def _default_jobspy_query(db: Session) -> str:
    configured = [item.strip() for item in (settings.jobspy_discover_queries or []) if str(item).strip()]
    if configured:
        return configured[0]
    track = (
        db.query(ResumeTrack)
        .filter(ResumeTrack.active.is_(True))
        .order_by(ResumeTrack.created_at.asc())
        .first()
    )
    if track is None:
        return ""
    primary_title = track.title.split("/")[0].strip()
    return primary_title.removeprefix("Junior ").strip()


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
        response = httpx.get(f"{normalize_lm_studio_base_url(settings.lm_studio_base_url)}/models", timeout=2)
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
