"""Candidate profiles, fact sheets, verified facts, and candidate UI routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Body, Depends, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from job_agent.db import get_db
from job_agent.llm import LLMRouter, ProviderUnavailableError
from job_agent.models import (
    Candidate,
    CandidateIntakeDraft,
    JobPost,
    MasterProfile,
    VerifiedCandidateFact,
)
from job_agent.schemas import (
    MasterProfileIn,
    MasterProfileOut,
)
from job_agent.services.fact_sheet_json import FactSheetJsonIngestionService
from job_agent.services.intake import (
    FactSheetIntakeService,
    UploadedFile as IntakeUploadedFile,
    store_uploaded_files,
)

from job_agent.routers.setup_state import (
    _active_candidate_id,
    _owner_candidate,
    _persist_default_candidate_id,
    _raise_if_setup_required,
    _redirect_if_setup_required,
    _sanitize_verified_fact_type,
    _verified_fact_scope_filter,
)
from job_agent.routers.templates import templates
from job_agent.routers.ui_context import _ui_context

router = APIRouter()


def _verified_fact_payload(fact: VerifiedCandidateFact, db: Session | None = None) -> dict[str, object]:
    job = db.get(JobPost, fact.source_job_id) if db is not None and fact.source_job_id else None
    return {
        "id": str(fact.id),
        "gap_label": fact.gap_label,
        "evidence": fact.evidence,
        "fact_type": fact.fact_type,
        "source_draft_id": str(fact.source_draft_id) if fact.source_draft_id else None,
        "source_job_id": str(fact.source_job_id) if fact.source_job_id else None,
        "source_job_company": job.company if job else None,
        "created_at": fact.created_at.isoformat() if fact.created_at else None,
        "is_active": fact.is_active,
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


# ── Profile ────────────────────────────────────────────────────────────────────

@router.get("/profile", response_model=MasterProfileOut)
def get_profile(db: Session = Depends(get_db)) -> MasterProfile:
    profile = db.get(MasterProfile, 1)
    if profile is None:
        raise HTTPException(status_code=404, detail="Master profile not found.")
    return profile


@router.put("/profile", response_model=MasterProfileOut)
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


# ── Candidates ─────────────────────────────────────────────────────────────────

@router.post("/candidates")
async def create_candidate(request: Request, db: Session = Depends(get_db)) -> dict[str, str | bool | None]:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
    else:
        body = dict(await request.form())
    full_name = str(body.get("full_name", "")).strip()
    if not full_name:
        first_name = str(body.get("first_name", "")).strip()
        last_name = str(body.get("last_name", "")).strip()
        full_name = " ".join(part for part in (first_name, last_name) if part).strip()
    if not full_name:
        raise HTTPException(status_code=422, detail="full_name is required")
    email = str(body.get("email", "") or "").strip()
    raw_active = body.get("active", True)
    active = (
        raw_active.strip().lower() not in {"0", "false", "no", "off"}
        if isinstance(raw_active, str)
        else bool(raw_active)
    )

    candidate = _owner_candidate(db)
    if candidate is None:
        candidate = Candidate(
            full_name=full_name,
            preferred_name=body.get("preferred_name"),
            email=email or None,
            active=active,
        )
        db.add(candidate)
    else:
        candidate.full_name = full_name
        candidate.preferred_name = body.get("preferred_name")
        candidate.email = email or None
        candidate.active = active
    db.commit()
    db.refresh(candidate)
    _persist_default_candidate_id(candidate.id)
    return {
        "id": candidate.id,
        "full_name": candidate.full_name,
        "preferred_name": candidate.preferred_name,
        "email": candidate.email,
        "active": candidate.active,
    }


@router.get("/candidates")
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


@router.get("/candidates/{candidate_id}")
def get_candidate(candidate_id: str, db: Session = Depends(get_db)) -> dict:
    if db.get(Candidate, candidate_id) is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return FactSheetJsonIngestionService(db).export_json(candidate_id)


@router.post("/candidates/{candidate_id}/fact-sheet-json")
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


@router.get("/candidates/{candidate_id}/fact-sheet-json")
def export_fact_sheet_json(candidate_id: str, db: Session = Depends(get_db)) -> dict:
    try:
        return FactSheetJsonIngestionService(db).export_json(candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/candidates/{candidate_id}/fact-sheet-text")
def export_fact_sheet_text(candidate_id: str, db: Session = Depends(get_db)) -> PlainTextResponse:
    try:
        text = FactSheetJsonIngestionService(db).export_text(candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PlainTextResponse(text)


@router.post("/candidates/{candidate_id}/sources/upload")
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


@router.post("/candidates/{candidate_id}/intake/start")
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
    except ProviderUnavailableError as exc:
        detail = str(exc)
        if detail.startswith("OPENAI_QUOTA_EXCEEDED:"):
            detail = "OpenAI quota reached. Top up billing or switch provider in Settings, then try intake again."
        else:
            detail = "The configured AI provider is not responding. Check Settings, then try intake again."
        raise HTTPException(
            status_code=503,
            detail=detail,
        )
    return {
        "status": result.status,
        "questions": result.questions,
        "fact_sheet": result.fact_sheet,
        "iteration": result.iteration,
    }


@router.post("/candidates/{candidate_id}/intake/answer")
async def answer_candidate_intake(candidate_id: str, request: Request, db: Session = Depends(get_db)) -> dict:
    if db.get(Candidate, candidate_id) is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    body = await _request_payload(request)
    try:
        result = FactSheetIntakeService(db, LLMRouter()).answer_questions(
            candidate_id=candidate_id,
            answers={str(key): str(value) for key, value in dict(body.get("answers", {})).items()},
        )
    except ProviderUnavailableError as exc:
        detail = str(exc)
        if detail.startswith("OPENAI_QUOTA_EXCEEDED:"):
            detail = "OpenAI quota reached. Top up billing or switch provider in Settings, then try intake again."
        else:
            detail = "The configured AI provider is not responding. Check Settings, then try intake again."
        raise HTTPException(
            status_code=503,
            detail=detail,
        )
    return {
        "status": result.status,
        "questions": result.questions,
        "fact_sheet": result.fact_sheet,
        "iteration": result.iteration,
    }


@router.get("/candidates/{candidate_id}/intake/status")
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


# ── Verified facts (Profile Memory) ───────────────────────────────────────────

@router.post("/verified-facts", status_code=201)
def create_verified_fact(
    response: Response,
    body: dict = Body(...),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    _raise_if_setup_required(db)
    gap_label = str(body.get("gap_label") or "").strip()[:200]
    evidence = str(body.get("evidence") or "").strip()[:2000]
    if not gap_label or not evidence:
        raise HTTPException(status_code=422, detail="gap_label and evidence are required.")

    source_draft_id = None
    source_job_id = None
    raw_draft_id = body.get("source_draft_id")
    if raw_draft_id:
        try:
            source_draft_id = UUID(str(raw_draft_id))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="source_draft_id must be a valid UUID.") from exc
        from job_agent.models import ResumeDraft

        draft = db.get(ResumeDraft, source_draft_id)
        if draft is None:
            raise HTTPException(status_code=404, detail="Source draft not found.")
        source_job_id = draft.job_post_id
    elif body.get("source_job_id"):
        try:
            source_job_id = UUID(str(body.get("source_job_id")))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="source_job_id must be a valid UUID.") from exc
        if db.get(JobPost, source_job_id) is None:
            raise HTTPException(status_code=404, detail="Source job not found.")

    candidate_id = _active_candidate_id(db)
    fact_type = _sanitize_verified_fact_type(body.get("fact_type"))
    notes = str(body.get("notes") or "").strip()[:2000] or None

    existing = (
        db.query(VerifiedCandidateFact)
        .filter(
            VerifiedCandidateFact.is_active.is_(True),
            _verified_fact_scope_filter(candidate_id),
            VerifiedCandidateFact.gap_label == gap_label,
            VerifiedCandidateFact.evidence == evidence,
        )
        .first()
    )
    if existing is not None:
        response.status_code = 200
        return _verified_fact_payload(existing, db)

    fact = VerifiedCandidateFact(
        candidate_id=candidate_id,
        gap_label=gap_label,
        evidence=evidence,
        fact_type=fact_type,
        source_draft_id=source_draft_id,
        source_job_id=source_job_id,
        notes=notes,
    )
    db.add(fact)
    db.commit()
    db.refresh(fact)
    return _verified_fact_payload(fact, db)


@router.get("/verified-facts/count")
def count_verified_facts(db: Session = Depends(get_db)) -> dict[str, int]:
    candidate_id = _active_candidate_id(db)
    count = (
        db.query(func.count(VerifiedCandidateFact.id))
        .filter(
            VerifiedCandidateFact.is_active.is_(True),
            _verified_fact_scope_filter(candidate_id),
        )
        .scalar()
    ) or 0
    return {"count": count}


@router.get("/verified-facts")
def list_verified_facts(db: Session = Depends(get_db)) -> list[dict[str, object]]:
    _raise_if_setup_required(db)
    candidate_id = _active_candidate_id(db)
    facts = (
        db.query(VerifiedCandidateFact)
        .filter(
            VerifiedCandidateFact.is_active.is_(True),
            _verified_fact_scope_filter(candidate_id),
        )
        .order_by(VerifiedCandidateFact.created_at.desc())
        .all()
    )
    return [_verified_fact_payload(fact, db) for fact in facts]


@router.delete("/verified-facts/{fact_id}", status_code=204)
def deactivate_verified_fact(fact_id: UUID, db: Session = Depends(get_db)) -> Response:
    _raise_if_setup_required(db)
    fact = db.get(VerifiedCandidateFact, fact_id)
    if fact is None:
        raise HTTPException(status_code=404, detail="Fact not found.")
    fact.is_active = False
    db.commit()
    return Response(status_code=204)


# ── Candidate UI pages ─────────────────────────────────────────────────────────

@router.get("/ui/onboarding", response_class=HTMLResponse)
def onboarding_page(request: Request) -> Response:
    return templates.TemplateResponse(
        request=request,
        name="onboarding.html",
        context=_ui_context(request, "Onboarding"),
    )


@router.get("/ui/verified-facts", include_in_schema=False)
def ui_verified_facts(request: Request, db: Session = Depends(get_db)):
    if redirect := _redirect_if_setup_required(request, db):
        return redirect
    candidate_id = _active_candidate_id(db)
    facts_raw = (
        db.query(VerifiedCandidateFact)
        .filter(
            VerifiedCandidateFact.is_active.is_(True),
            _verified_fact_scope_filter(candidate_id),
        )
        .order_by(VerifiedCandidateFact.created_at.desc())
        .all()
    )

    facts = []
    for fact in facts_raw:
        job = db.get(JobPost, fact.source_job_id) if fact.source_job_id else None
        facts.append(
            {
                "id": str(fact.id),
                "gap_label": fact.gap_label,
                "evidence": fact.evidence,
                "fact_type": fact.fact_type,
                "source_job_company": job.company if job else None,
                "created_at": fact.created_at.isoformat() if fact.created_at else "",
            }
        )

    return templates.TemplateResponse(
        request=request,
        name="verified_facts.html",
        context=_ui_context(request, "Profile Memory", facts=facts),
    )
