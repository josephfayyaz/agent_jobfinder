"""Jobs, career pages, apply flow, and job UI routes."""

from __future__ import annotations

from datetime import date, datetime, timezone
import json
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Form, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from job_agent.config import settings
from job_agent.db import get_db
from job_agent.llm import LLMRouter, ProviderUnavailableError
from job_agent.models import (
    CareerPageScanLog,
    CareerPageSource,
    CandidateIntakeDraft,
    FactSource,
    JobPost,
    JobSource,
    JobTrackScore,
    ResumeDraft,
    ResumeTrack,
    WorkflowTask,
)
from job_agent.providers import normalize_provider_mode
from job_agent.schemas import FactSheetIngestRequest, JobPostCreate, JobPostOut, JobSourceOut, ResumeTrackOut
from job_agent.services.career_scanner import CareerPageScanner
from job_agent.services.company_snapshot import CompanySnapshotService
from job_agent.services.discovery_hub import (
    find_existing_job,
    merge_duplicate_job,
    record_discovery_event,
    source_profile,
    stamp_job_metadata,
)
from job_agent.services.gmail import GmailService
from job_agent.services.job_signals import JobSignalService
from job_agent.services.job_fetcher import JobFetcher
from job_agent.services.fact_sheet_json import FactSheetJsonIngestionService
from job_agent.services.job_fit_scoring import JobFitScoringService, effective_job_fit_score
from job_agent.services.matching import score_tracks_for_job
from job_agent.services.workflows import CVWorkflowService
from job_agent.search_preferences import (
    MAX_DISCOVERY_ROLES,
    detect_job_languages,
    normalize_role_list,
    primary_search_country,
)

from job_agent.routers.job_views import (
    _job_row_payload,
    _job_rows_for_ui,
    _query_jobs_for_ui,
    _queue_counts,
)
from job_agent.routers.setup_state import _active_candidate_id, _raise_if_setup_required, _redirect_if_setup_required
from job_agent.routers.templates import templates
from job_agent.routers.ui_context import _ui_context

router = APIRouter()

VALID_ATS_TYPES = {"greenhouse", "lever", "ashby"}
VALID_QUEUE_STATES = {"new", "shortlisted", "saved", "passed"}


class JobDiscoverRequest(BaseModel):
    query: str = ""
    location: str = "Italy"
    sources: list[str] = ["linkedin"]
    limit: int = 50


class JobTextCreateRequest(BaseModel):
    text: str


class JobUrlCreateRequest(BaseModel):
    url: str


def _empty_discovery_counts() -> dict[str, int]:
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
        "saved_jobs": 0,
        "visible_after_threshold": 0,
        "visible_in_default_view": 0,
    }


def _queue_job_discovery_task(db: Session) -> WorkflowTask:
    if not settings.use_jobspy:
        raise HTTPException(
            status_code=409,
            detail="Job discovery is disabled. Enable Automatic JobSpy in Settings > Job Discovery first.",
        )
    roles = normalize_role_list(settings.jobspy_discover_queries)[:MAX_DISCOVERY_ROLES]
    if not roles:
        raise HTTPException(status_code=400, detail="Set at least one desired role before running discovery.")

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
            "include_ats": True,
            "limit": int(settings.jobspy_default_limit),
            "threshold": int(settings.discovery_min_fit_score),
            "visible_cap": int(settings.discovery_max_visible_jobs),
        },
        result={
            "source": "hybrid_discovery",
            "stage": "pending",
            "message": "Discovery task queued.",
            "counts": _empty_discovery_counts(),
        },
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


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

    return {"title": title, "company": company, "location": location}


def _set_job_queue_state(job: JobPost, state: str) -> None:
    normalized = state.strip().lower()
    if normalized not in VALID_QUEUE_STATES:
        raise HTTPException(status_code=422, detail="Invalid queue state.")
    job.queue_state = normalized
    if job.status != "applied":
        job.status = "new" if normalized == "new" else "reviewed"


def _default_fact_sheet_path(db: Session) -> Path:
    configured = Path(str(settings.fact_sheet_path or "").strip()).expanduser()
    if str(settings.fact_sheet_path or "").strip():
        configured = configured.resolve()
        if configured.exists():
            return configured

    latest = (
        db.query(FactSource)
        .filter(FactSource.source_path.is_not(None), FactSource.source_path != "")
        .order_by(FactSource.imported_at.desc())
        .first()
    )
    if latest and latest.source_path:
        latest_path = Path(latest.source_path).expanduser().resolve()
        if latest_path.exists():
            return latest_path

    detail = "No default fact sheet is available. Upload one first or set fact_sheet_path in Settings."
    raise HTTPException(status_code=404, detail=detail)


def _create_job_post(payload: JobPostCreate, db: Session) -> JobPost:
    payload_data = payload.model_dump()
    source_name = str(payload_data.get("source_name") or "manual")
    source_url = str(payload_data.get("source_url") or "")
    canonical_apply_url = str(payload_data.get("canonical_apply_url") or source_url)
    dedupe = find_existing_job(
        db,
        canonical_apply_url=canonical_apply_url,
        source_url=source_url,
        company=str(payload_data.get("company") or ""),
        title=str(payload_data.get("title") or ""),
        location=str(payload_data.get("location") or ""),
    )
    source_meta = source_profile(source_name, source_url)
    if dedupe.job is not None:
        payload_data.setdefault("last_seen_at", datetime.now(timezone.utc))
        merge_duplicate_job(dedupe.job, payload_data)
        stamp_job_metadata(
            dedupe.job,
            source_name=source_name,
            source_url=source_url,
            canonical_apply_url=canonical_apply_url,
            company=str(payload_data.get("company") or ""),
            title=str(payload_data.get("title") or ""),
            location=str(payload_data.get("location") or ""),
            canonical_reason=dedupe.reason,
        )
        record_discovery_event(
            db,
            source_name=source_name,
            source_url=source_url,
            outcome="duplicate",
            reason=dedupe.reason,
            acquisition_path=str(source_meta["path"]),
            canonical_key=dedupe.canonical_key,
            job_post_id=dedupe.job.id,
        )
        db.add(dedupe.job)
        db.commit()
        db.refresh(dedupe.job)
        return dedupe.job

    tracks = db.query(ResumeTrack).filter(ResumeTrack.active.is_(True)).order_by(ResumeTrack.title.asc()).all()
    track_scores = score_tracks_for_job(payload_data, tracks)
    extracted_metadata = dict(payload_data.get("extracted_metadata", {}))
    detected_job_languages = detect_job_languages(str(payload_data.get("description") or ""))
    if detected_job_languages:
        extracted_metadata["detected_job_languages"] = detected_job_languages
    extracted_metadata["track_scores"] = [
        {
            **track_score,
            "track_id": str(track_score["track_id"]) if track_score.get("track_id") is not None else None,
        }
        for track_score in track_scores
    ]
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
    payload_data.setdefault("queue_state", "new")
    desc_text = str(payload_data.get("description") or "").strip()
    source_url = str(payload_data.get("source_url") or "").strip()
    payload_data.setdefault(
        "enrichment_status",
        (
            "ok"
            if desc_text and len(desc_text) >= 400
            else "partial"
            if desc_text
            else "pending"
            if source_url
            else "needs_input"
        ),
    )

    job = JobPost(**payload_data)
    stamp_job_metadata(
        job,
        source_name=source_name,
        source_url=source_url,
        canonical_apply_url=payload_data.get("canonical_apply_url", source_url),
        company=job.company,
        title=job.title,
        location=job.location,
        canonical_reason="new_import",
    )
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
    record_discovery_event(
        db,
        source_name=source_name,
        source_url=source_url,
        outcome="ingested",
        reason="new_import",
        acquisition_path=str(source_meta["path"]),
        canonical_key=str(dict(job.extracted_metadata or {}).get("canonical_key") or ""),
        job_post_id=job.id,
    )
    JobFitScoringService(db).score_and_persist(
        job,
        candidate_id=_active_candidate_id(db) or settings.default_candidate_id.strip() or None,
        force=True,
        commit=False,
    )
    db.commit()
    db.refresh(job)
    return job


# ── Tracks and sources ─────────────────────────────────────────────────────────

@router.get("/tracks", response_model=list[ResumeTrackOut])
def list_tracks(db: Session = Depends(get_db)) -> list[ResumeTrack]:
    return db.query(ResumeTrack).filter(ResumeTrack.active.is_(True)).order_by(ResumeTrack.title.asc()).all()


@router.get("/job-sources", response_model=list[JobSourceOut])
def list_job_sources(db: Session = Depends(get_db)) -> list[JobSource]:
    return db.query(JobSource).filter(JobSource.active.is_(True)).order_by(JobSource.priority.asc()).all()


@router.get("/fact-sources/latest")
def latest_fact_source(db: Session = Depends(get_db)) -> dict:
    from job_agent.models import FactSource

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


@router.post("/fact-sources/ingest-default", include_in_schema=False)
def ingest_default_fact_sheet(response: Response, db: Session = Depends(get_db)) -> dict[str, str]:
    from job_agent.services.fact_ingestion import FactSheetIngestionService

    candidate_id = settings.default_candidate_id.strip() or None
    if candidate_id:
        draft = (
            db.query(CandidateIntakeDraft)
            .filter(CandidateIntakeDraft.candidate_id == candidate_id)
            .order_by(CandidateIntakeDraft.updated_at.desc())
            .first()
        )
        if draft and isinstance(draft.partial_fact_sheet, dict) and draft.partial_fact_sheet:
            FactSheetJsonIngestionService(db).ingest_json(
                candidate_id=candidate_id,
                fact_sheet=draft.partial_fact_sheet,
                source_name="intake_rebuild",
            )
            response.headers["X-Toast-Success"] = "Stored fact sheet rebuilt from the latest intake draft."
            return {"status": "ok", "message": "Fact sheet rebuilt from latest intake draft"}

        latest_json_source = (
            db.query(FactSource)
            .filter(FactSource.candidate_id == candidate_id)
            .order_by(FactSource.imported_at.desc())
            .first()
        )
        if latest_json_source and str(latest_json_source.source_path or "").startswith(f"candidate://{candidate_id}/"):
            try:
                fact_sheet = json.loads(latest_json_source.raw_content or "{}")
            except json.JSONDecodeError as exc:
                raise HTTPException(status_code=422, detail="Latest stored fact sheet is not valid JSON.") from exc
            FactSheetJsonIngestionService(db).ingest_json(
                candidate_id=candidate_id,
                fact_sheet=fact_sheet,
                source_name="stored_fact_sheet",
            )
            response.headers["X-Toast-Success"] = "Stored fact sheet rebuilt from the latest saved JSON snapshot."
            return {"status": "ok", "message": "Fact sheet rebuilt from latest saved snapshot"}

    fact_path = _default_fact_sheet_path(db)
    FactSheetIngestionService(db).ingest(path=str(fact_path))
    response.headers["X-Toast-Success"] = "Fact sheet re-ingested from the configured source file."
    return {"status": "ok", "message": "Fact sheet re-ingested from configured source file"}


@router.post("/fact-sources/ingest")
def ingest_fact_source(payload: FactSheetIngestRequest, db: Session = Depends(get_db)) -> dict:
    from job_agent.services.fact_ingestion import FactSheetIngestionService

    service = FactSheetIngestionService(db)
    return service.ingest(path=payload.path, content=payload.content, source_path=payload.source_path)


# ── Jobs CRUD ──────────────────────────────────────────────────────────────────

@router.post("/jobs", response_model=JobPostOut)
def create_job(payload: JobPostCreate, db: Session = Depends(get_db)) -> JobPost:
    return _create_job_post(payload, db)


@router.post("/jobs/from-text")
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


@router.post("/jobs/add")
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


@router.post("/jobs/{job_id}/resolve-company-url")
def resolve_job_company_url(job_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    job = db.get(JobPost, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job.company_url:
        return {"job_post_id": str(job.id), "company_url": job.company_url, "resolved": False}

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
    return {"job_post_id": str(job.id), "company_url": job.company_url, "resolved": bool(resolved)}


@router.get("/jobs", response_model=list[JobPostOut])
def list_jobs(
    show_all: bool = False,
    min_score: int | None = None,
    candidate_id: str | None = None,
    db: Session = Depends(get_db),
) -> list[JobPost]:
    from job_agent.models import MatchProfile
    threshold = 0 if show_all else (min_score if min_score is not None else settings.discovery_min_fit_score)
    active_candidate_id = candidate_id or settings.default_candidate_id.strip() or None
    jobs = db.query(JobPost).order_by(JobPost.created_at.desc()).all()
    score_rows = (
        db.query(JobTrackScore)
        .filter(JobTrackScore.job_post_id.in_([job.id for job in jobs]))
        .order_by(JobTrackScore.score.desc())
        .all()
        if jobs
        else []
    )
    score_map: dict[UUID, list[JobTrackScore]] = {}
    for row in score_rows:
        score_map.setdefault(row.job_post_id, []).append(row)

    if candidate_id:
        match_profile = db.query(MatchProfile).filter_by(candidate_id=candidate_id).first()
        if match_profile and match_profile.target_roles:
            allowed = [role.lower() for role in match_profile.target_roles if isinstance(role, str) and role.strip()]
            if allowed:
                jobs = [job for job in jobs if any(role in (job.title or "").lower() for role in allowed)]

    filtered_jobs: list[tuple[JobPost, int]] = []
    for job in jobs:
        fit_score = effective_job_fit_score(
            job,
            candidate_id=active_candidate_id,
            score_rows=score_map.get(job.id),
        )
        if threshold > 0 and fit_score < threshold:
            continue
        filtered_jobs.append((job, fit_score))

    filtered_jobs.sort(
        key=lambda item: (
            item[1],
            getattr(item[0], "created_at", datetime.min.replace(tzinfo=timezone.utc)),
        ),
        reverse=True,
    )
    jobs = [job for job, _score in filtered_jobs]
    if not show_all:
        jobs = jobs[: int(settings.discovery_max_visible_jobs)]

    dirty = False
    for job in jobs:
        if not str(getattr(job, "queue_state", "") or "").strip():
            job.queue_state = "new"
            dirty = True
    if dirty:
        db.commit()

    return jobs


@router.get("/jobs/{job_id}/track-fit")
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


@router.post("/jobs/{job_id}/queue-state")
def set_job_queue_state(job_id: UUID, state: str, db: Session = Depends(get_db)) -> dict[str, str]:
    job = db.get(JobPost, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    _set_job_queue_state(job, state)
    db.add(job)
    db.commit()
    return {"job_post_id": str(job.id), "queue_state": job.queue_state}


@router.post("/jobs/sync-gmail")
def sync_jobs_from_gmail(db: Session = Depends(get_db)) -> dict[str, object]:
    posts = GmailService().sync_jobs(db)
    return {"created": len(posts), "job_ids": [str(post.id) for post in posts]}


@router.post("/jobs/{job_id}/enrich")
def enrich_job(job_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    job = db.get(JobPost, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    success = JobFetcher().enrich_job(job, db)
    db.commit()
    return {"enriched": success, "description_length": len(job.description or "")}


@router.post("/jobs/enrich-pending")
def enrich_pending_jobs(limit: int = 20, db: Session = Depends(get_db)) -> dict[str, int]:
    count = JobFetcher().enrich_pending(db, limit=limit)
    return {"enriched": count}


@router.post("/jobs/{job_id}/rejection-risk")
def predict_rejection_risk(job_id: UUID, db: Session = Depends(get_db)) -> dict:
    from job_agent.services.rejection_prediction import RejectionPredictionService

    service = RejectionPredictionService(db)
    try:
        prediction = service.predict(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return prediction


@router.get("/jobs/{job_id}/rejection-risk")
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


@router.get("/jobs/{job_id}/fit-gaps")
def job_fit_gaps(job_id: UUID, request: Request, db: Session = Depends(get_db)):
    candidate_id = settings.default_candidate_id.strip()
    if not candidate_id:
        data = {"rows": [], "summary": {"strong": 0, "close": 0, "thin": 0, "missing": 0}}
    else:
        from job_agent.services.fit_gap import FitGapService

        data = FitGapService(session=db, router=LLMRouter()).get_or_compute(
            job_id=job_id,
            candidate_id=candidate_id,
        )

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            request=request,
            name="partials/fit_gaps.html",
            context={"fit_gaps": data, "job_id": str(job_id)},
        )
    return data


@router.post("/jobs/{job_id}/fit-gaps/clear")
def job_fit_gaps_clear(job_id: UUID, db: Session = Depends(get_db)) -> dict[str, bool]:
    job = db.get(JobPost, job_id)
    if job is not None:
        meta = dict(job.extracted_metadata or {})
        meta.pop("fit_gaps", None)
        job.extracted_metadata = meta
        db.add(job)
        db.commit()
    return {"cleared": True}


@router.post("/jobs/discover")
def discover_jobs(body: JobDiscoverRequest | None = None, db: Session = Depends(get_db)) -> dict[str, object]:
    del body
    task = _queue_job_discovery_task(db)
    return {
        "task_id": str(task.id),
        "status": task.status,
        "kind": task.kind,
    }


# ── Career pages ───────────────────────────────────────────────────────────────

@router.post("/career-pages", status_code=201)
def create_career_page(
    company: str,
    career_url: str,
    country: str = "Italy",
    css_selector: str | None = None,
    ats_type: str | None = None,
    ats_slug: str | None = None,
    db: Session = Depends(get_db),
) -> dict[str, object]:
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


@router.get("/career-pages")
def list_career_pages(limit: int | None = None, db: Session = Depends(get_db)) -> list[dict[str, object]]:
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


@router.get("/career-pages/velocity/bulk")
def career_pages_velocity_bulk(db: Session = Depends(get_db)) -> dict[str, list[int]]:
    from sqlalchemy import text
    from datetime import timedelta

    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    rows = db.execute(
        text("""
            SELECT source_id,
                   SUM(CASE WHEN new_jobs > 0 THEN 1 ELSE 0 END) AS surge_count
            FROM career_page_scan_logs
            WHERE scanned_at >= :cutoff
            GROUP BY source_id
            HAVING SUM(CASE WHEN new_jobs > 0 THEN 1 ELSE 0 END) >= 2
        """),
        {"cutoff": cutoff},
    ).fetchall()
    return {"surging": [int(row[0]) for row in rows]}


@router.get("/career-pages/{source_id}/velocity")
def career_page_velocity(source_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    from sqlalchemy import text
    from datetime import timedelta

    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    rows = db.execute(
        text("""
            SELECT scanned_at, jobs_found, new_jobs
            FROM career_page_scan_logs
            WHERE source_id = :source_id AND scanned_at >= :cutoff
            ORDER BY scanned_at DESC
            LIMIT 10
        """),
        {"source_id": source_id, "cutoff": cutoff},
    ).fetchall()

    scans = [
        {
            "scanned_at": row[0].isoformat() if hasattr(row[0], "isoformat") else row[0],
            "jobs_found": int(row[1] or 0),
            "new_jobs": int(row[2] or 0),
        }
        for row in rows
    ]
    surge_count = sum(1 for scan in scans if scan["new_jobs"] > 0)
    return {
        "source_id": source_id,
        "is_surging": surge_count >= 2,
        "surge_scans": surge_count,
        "recent_scans": scans,
    }


@router.post("/career-pages/{source_id}/toggle-active", status_code=204)
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


@router.delete("/career-pages/{source_id}", status_code=204)
def delete_career_page(source_id: int, db: Session = Depends(get_db)) -> Response:
    source = db.get(CareerPageSource, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Career page source not found.")
    db.delete(source)
    db.commit()
    return Response(status_code=204)


@router.post("/jobs/scan-career-pages")
def scan_career_pages(db: Session = Depends(get_db)) -> dict[str, int]:
    _raise_if_setup_required(db)
    count = CareerPageScanner().scan_all(db)
    return {"new_jobs": count}


@router.get("/analytics/posting-velocity")
def posting_velocity(days: int = 7, db: Session = Depends(get_db)) -> dict[str, object]:
    from collections import defaultdict
    from datetime import timedelta

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


# ── Apply flow ─────────────────────────────────────────────────────────────────

@router.post("/apply/parse")
async def apply_parse(job_text: str = Form(...), db: Session = Depends(get_db)) -> dict[str, object]:
    _raise_if_setup_required(db)
    from job_agent.services.resource_loader import ResourceLoader
    from start_apply.job_parser import parse_job_info
    from start_apply.scorer import score_match

    job = parse_job_info(job_text)
    fact_sheet = ResourceLoader(db).load_fact_sheet_text()
    result = score_match(job, fact_sheet)
    return {
        "job": job,
        "score": result["score"],
        "matched": result["matched"],
        "gaps": result["gaps"],
        "summary": result["summary"],
    }


@router.post("/apply/questions")
async def apply_questions(body: dict = Body(...), db: Session = Depends(get_db)) -> dict[str, list[dict]]:
    _raise_if_setup_required(db)
    from job_agent.services.resource_loader import ResourceLoader
    from start_apply.questioner import _SYSTEM_PROMPT, build_questioner_user_prompt

    job = dict(body.get("job") or {})
    gaps = list(body.get("gaps") or [])
    fact_sheet_excerpt = str(body.get("fact_sheet_excerpt") or "")
    if not fact_sheet_excerpt:
        fact_sheet_excerpt = ResourceLoader(db).load_fact_sheet_text()

    try:
        router_llm = LLMRouter()
        questions_raw = router_llm.generate_with_retry(
            role="small",
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=build_questioner_user_prompt(job=job, gaps=gaps, fact_sheet=fact_sheet_excerpt),
        )
        questions = list(questions_raw.get("questions") or [])[:3]
    except (ProviderUnavailableError, ValueError):
        questions = []
    return {"questions": questions}


@router.post("/apply/generate")
async def apply_generate(body: dict = Body(...), db: Session = Depends(get_db)) -> dict[str, str]:
    import uuid

    _raise_if_setup_required(db)
    job_data = dict(body.get("job") or {})
    company = str(job_data.get("company") or "Unknown")
    title = str(job_data.get("title") or "Unknown")
    location = str(job_data.get("location") or "")
    description = str(job_data.get("description") or "")
    source_url = str(job_data.get("url") or "")

    existing = db.query(JobPost).filter_by(company=company, title=title).first()
    if existing is not None:
        job = existing
    else:
        now = datetime.now(timezone.utc)
        job = JobPost(
            id=uuid.uuid4(),
            company=company,
            title=title,
            description=description,
            location=location,
            source_name="manual",
            source_url=source_url,
            canonical_apply_url=source_url,
            queue_state="new",
            created_at=now,
            last_seen_at=now,
        )
        db.add(job)
        db.commit()
        db.refresh(job)

    task = WorkflowTask(
        kind="cv_workflow",
        status="pending",
        payload={
            "job_post_id": str(job.id),
            "resume_track_slug": body.get("track_slug", ""),
            "confirmed_facts": body.get("answers", []),
        },
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return {"task_id": str(task.id), "job_id": str(job.id)}


@router.get("/apply/status/{task_id}")
async def apply_status(task_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    from uuid import UUID as UUIDType

    try:
        task_uuid = UUIDType(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Task not found.") from exc

    task = db.get(WorkflowTask, task_uuid)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")

    draft_id = None
    if task.status == "completed":
        job_post_id = task.payload.get("job_post_id")
        draft_query = db.query(ResumeDraft).order_by(ResumeDraft.created_at.desc())
        if job_post_id:
            try:
                draft_query = draft_query.filter_by(job_post_id=UUIDType(str(job_post_id)))
            except ValueError:
                draft_query = draft_query.filter_by(job_post_id=job_post_id)
        draft = draft_query.first()
        if draft is not None:
            draft_id = str(draft.id)
    return {"status": task.status, "draft_id": draft_id}


# ── Job UI pages ───────────────────────────────────────────────────────────────

@router.get("/ui/jobs", include_in_schema=False)
def ui_jobs(
    request: Request,
    db: Session = Depends(get_db),
    min_score: int | None = None,
    track_id: str | None = None,
    status: str | None = None,
    show_all: bool = False,
    posted_after: date | None = None,
    lane: str = "review",
):
    if redirect := _redirect_if_setup_required(request, db):
        return redirect
    all_rows = _job_rows_for_ui(
        db,
        min_score=min_score,
        track_id=track_id,
        status=status,
        show_all=show_all,
        posted_after=posted_after,
    )
    selected_lane = lane if lane in {"review", "shortlist", "saved", "passed", "applied", "all"} else "review"
    lane_rows = _query_jobs_for_ui(
        db,
        min_score=min_score,
        track_id=track_id,
        status=status,
        show_all=show_all,
        posted_after=posted_after,
        lane=selected_lane,
    )
    jobs = lane_rows if show_all else lane_rows[: int(settings.discovery_max_visible_jobs)]
    queue_threshold = min_score if min_score is not None else settings.discovery_min_fit_score
    latest_discovery_task = (
        db.query(WorkflowTask)
        .filter(WorkflowTask.kind == "job_discovery")
        .order_by(WorkflowTask.created_at.desc())
        .first()
    )
    return templates.TemplateResponse(
        request=request,
        name="jobs.html",
        context=_ui_context(
            request,
            "Jobs",
            jobs=jobs,
            tracks=(
                db.query(ResumeTrack)
                .filter(ResumeTrack.active.is_(True))
                .order_by(ResumeTrack.title.asc())
                .all()
            ),
            queue_counts=_queue_counts(all_rows),
            filters={
                "lane": selected_lane,
                "min_score": queue_threshold,
                "track_id": track_id,
                "status": status or "",
                "show_all": show_all,
                "posted_after": posted_after.isoformat() if posted_after else "",
            },
            config={
                "use_jobspy": getattr(settings, "use_jobspy", False),
                "discovery_min_fit_score": int(settings.discovery_min_fit_score),
                "discovery_max_visible_jobs": int(settings.discovery_max_visible_jobs),
                "target_job_seniority": str(settings.target_job_seniority or "junior"),
            },
            queue_view={
                "qualifying_count": len(lane_rows),
                "displayed_count": len(jobs),
                "threshold": int(queue_threshold),
                "show_all": show_all,
                "capped": (not show_all and len(lane_rows) > int(settings.discovery_max_visible_jobs)),
                "cap": int(settings.discovery_max_visible_jobs),
            },
            latest_discovery_task=(
                {
                    "id": str(latest_discovery_task.id),
                    "status": latest_discovery_task.status,
                    "result": latest_discovery_task.result,
                    "error_message": latest_discovery_task.error_message,
                }
                if latest_discovery_task is not None
                else None
            ),
            gmail_configured=GmailService().is_configured(),
        ),
    )


@router.get("/ui/apply", include_in_schema=False)
def ui_apply(request: Request, db: Session = Depends(get_db)):
    if redirect := _redirect_if_setup_required(request, db):
        return redirect
    tracks = db.query(ResumeTrack).filter_by(active=True).order_by(ResumeTrack.title).all()
    return templates.TemplateResponse(
        request=request,
        name="apply.html",
        context=_ui_context(request, "Apply", tracks=tracks),
    )


@router.post("/ui/jobs/discover", include_in_schema=False)
def ui_discover_jobs(db: Session = Depends(get_db)) -> dict[str, object]:
    _raise_if_setup_required(db)
    task = _queue_job_discovery_task(db)
    return {
        "task_id": str(task.id),
        "status": task.status,
        "result": task.result,
    }


@router.post("/ui/jobs/{job_id}/queue-cv", include_in_schema=False)
def ui_queue_cv_workflow(
    job_id: UUID,
    resume_track_slug: str | None = None,
    confirm: bool = False,
    db: Session = Depends(get_db),
) -> Response:
    _raise_if_setup_required(db)
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

    _set_job_queue_state(job, "shortlisted")
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


@router.post("/ui/jobs/{job_id}/queue-state", include_in_schema=False)
def ui_set_job_queue_state(job_id: UUID, state: str, db: Session = Depends(get_db)) -> Response:
    _raise_if_setup_required(db)
    job = db.get(JobPost, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    _set_job_queue_state(job, state)
    db.add(job)
    db.commit()
    label = {
        "new": "Moved back to review",
        "shortlisted": "Added to shortlist",
        "saved": "Saved for later",
        "passed": "Marked as not for you",
    }.get(job.queue_state, "Queue updated")
    return Response(status_code=204, headers={"HX-Refresh": "true", "X-Toast-Success": label})


@router.post("/ui/jobs/{job_id}/refresh-signals", include_in_schema=False)
def ui_refresh_job_signals(request: Request, job_id: UUID, db: Session = Depends(get_db)):
    _raise_if_setup_required(db)
    job = db.get(JobPost, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    JobSignalService(db).refresh_apply_link_check(job, force=True)
    db.commit()
    job_payload = _job_row_payload(db, job)
    return templates.TemplateResponse(
        request=request,
        name="partials/job_row.html",
        context={"request": request, "job": job_payload},
        headers={"X-Toast-Success": "Trust signals refreshed"},
    )


@router.post("/ui/jobs/{job_id}/enrich-row", include_in_schema=False)
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
    job_payload = _job_row_payload(db, job)
    return templates.TemplateResponse(
        request=request,
        name="partials/job_row.html",
        context={"request": request, "job": job_payload},
        headers={"X-Toast-Success": "Job description refreshed"},
    )


@router.get("/ui/jobs/{job_id}/package-check", include_in_schema=False)
def ui_job_package_check(request: Request, job_id: UUID, db: Session = Depends(get_db)):
    if redirect := _redirect_if_setup_required(request, db):
        return redirect
    job = db.get(JobPost, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    job_payload = _job_row_payload(db, job)
    return templates.TemplateResponse(
        request=request,
        name="partials/apply_package_check.html",
        context={"request": request, "job": job_payload},
    )


@router.get("/ui/jobs/{job_id}/snapshot", include_in_schema=False)
def ui_job_snapshot(request: Request, job_id: UUID, force: bool = False, db: Session = Depends(get_db)):
    if redirect := _redirect_if_setup_required(request, db):
        return redirect
    service = CompanySnapshotService(db)
    try:
        snapshot = service.get_or_build(job_id, force=force)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return templates.TemplateResponse(
        request=request,
        name="partials/company_snapshot.html",
        context={"request": request, "snapshot": snapshot.content, "snapshot_provider": snapshot.provider, "job_id": str(job_id)},
    )


@router.get("/ui/companies", include_in_schema=False)
def ui_companies(request: Request, db: Session = Depends(get_db)):
    if redirect := _redirect_if_setup_required(request, db):
        return redirect
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
