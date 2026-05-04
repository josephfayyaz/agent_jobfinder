"""Drafts, tasks, clarifications, and draft UI routes."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from job_agent.db import get_db
from job_agent.llm import ProviderUnavailableError
from job_agent.models import (
    JobPost,
    ResumeDraft,
    ResumeTrack,
    WorkflowTask,
)
from job_agent.schemas import (
    ApplyEnhancementsRequest,
    ResumeDraftOut,
    WorkflowTaskCreate,
    WorkflowTaskOut,
)
from job_agent.services.draft_preview import build_preview_annotations  # noqa: F401
from job_agent.services.workflows import CVWorkflowService
from job_agent.routers.draft_actions import (
    accept_inferred_additions_payload,
    apply_clarification_to_draft as _apply_clarification_to_draft,
    approve_draft_record,
    clarification_rows_payload,
    draft_pdf_response,
    preview_state_payload,
    promote_clarification_to_fact_sheet as _promote_clarification_to_fact_sheet,
    promoted_fact_keys_for_draft,
    refresh_preview_feedback as _refresh_preview_feedback,  # noqa: F401
    reject_inferred_additions_payload,
    ui_approve_fragment,
    ui_reject_fragment,
    update_preview_state_payload,
)
from job_agent.routers.setup_state import (
    _raise_if_setup_required,
    _redirect_if_setup_required,
)
from job_agent.routers.templates import templates
from job_agent.routers.ui_context import _ui_context

router = APIRouter()


class DraftGenerateRequest(BaseModel):
    job_id: UUID
    track_slug: str | None = None
    force_cloud_review: bool = False


# ── Tasks ──────────────────────────────────────────────────────────────────────

@router.post("/tasks/cv-workflow", response_model=WorkflowTaskOut)
def queue_cv_workflow(payload: WorkflowTaskCreate, db: Session = Depends(get_db)) -> WorkflowTask:
    _raise_if_setup_required(db)
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
    readiness = service.profile_readiness_for_job(str(payload.job_post_id), payload.resume_track_slug)
    if readiness["status"] == "insufficient_profile_data":
        raise HTTPException(
            status_code=409,
            detail={
                "error": "profile_readiness_block",
                "message": "Add more grounded profile evidence before generating a final CV.",
                "readiness": readiness,
            },
        )
    return service.queue_cv_workflow(
        job_post_id=payload.job_post_id,
        resume_track_slug=payload.resume_track_slug,
        force_cloud_review=payload.force_cloud_review,
    )


@router.get("/tasks", response_model=list[WorkflowTaskOut])
def list_tasks(db: Session = Depends(get_db)) -> list[WorkflowTask]:
    return db.query(WorkflowTask).order_by(WorkflowTask.created_at.desc()).all()


@router.get("/tasks/{task_id}", response_model=WorkflowTaskOut)
def get_task(task_id: str, db: Session = Depends(get_db)) -> WorkflowTask:
    try:
        task_key: UUID | str = UUID(str(task_id))
    except ValueError:
        task_key = task_id
    task = db.get(WorkflowTask, task_key)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return task


# ── Drafts CRUD ────────────────────────────────────────────────────────────────

@router.post("/drafts/generate")
def generate_draft(payload: DraftGenerateRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    _raise_if_setup_required(db)
    job = db.get(JobPost, payload.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job post not found.")

    from job_agent.models import JobTrackScore

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

    service = CVWorkflowService(db)
    readiness = service.profile_readiness_for_job(str(payload.job_id), track_slug)
    if readiness["status"] == "insufficient_profile_data":
        raise HTTPException(
            status_code=409,
            detail={
                "error": "profile_readiness_block",
                "message": "This profile is still too thin for a strong final CV draft.",
                "readiness": readiness,
            },
        )
    task = service.queue_cv_workflow(
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


@router.get("/drafts", response_model=list[ResumeDraftOut])
def list_drafts(db: Session = Depends(get_db)) -> list[ResumeDraft]:
    return db.query(ResumeDraft).order_by(ResumeDraft.created_at.desc()).all()


@router.get("/drafts/{draft_id}", response_model=ResumeDraftOut)
def get_draft(draft_id: str, db: Session = Depends(get_db)) -> ResumeDraft:
    try:
        draft_key: UUID | str = UUID(str(draft_id))
    except ValueError:
        draft_key = draft_id
    draft = db.get(ResumeDraft, draft_key)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")
    return draft


@router.get("/drafts/{draft_id}/preview-state")
def get_preview_state(draft_id: UUID, db: Session = Depends(get_db)) -> dict[str, object]:
    draft = db.get(ResumeDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")
    return preview_state_payload(draft, db)


@router.post("/drafts/{draft_id}/preview/update")
def update_preview_state(draft_id: UUID, body: dict = Body(...), db: Session = Depends(get_db)) -> dict[str, object]:
    draft = db.get(ResumeDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")
    return update_preview_state_payload(draft, body, db)


@router.get("/drafts/{draft_id}/compliance-matrix")
def get_compliance_matrix(draft_id: UUID, db: Session = Depends(get_db)) -> dict:
    draft = db.get(ResumeDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    matrix = (draft.review_feedback or {}).get("compliance_matrix")
    if matrix is None:
        raise HTTPException(
            status_code=404,
            detail="Compliance matrix not yet generated. POST to /drafts/{id}/compliance-matrix to generate.",
        )
    return matrix


@router.post("/drafts/{draft_id}/compliance-matrix")
def generate_compliance_matrix(draft_id: UUID, db: Session = Depends(get_db)) -> dict:
    from job_agent.services.compliance_matrix import ComplianceMatrixService

    service = ComplianceMatrixService(db)
    try:
        matrix = service.generate(draft_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return matrix


@router.get("/drafts/{draft_id}/clarifications")
def list_clarifications(draft_id: UUID, db: Session = Depends(get_db)) -> list[dict]:
    return clarification_rows_payload(draft_id, db)


@router.post("/drafts/{draft_id}/clarify")
def start_bullet_clarify(
    draft_id: UUID,
    body: dict | None = Body(default=None),
    db: Session = Depends(get_db),
):
    from job_agent.services.bullet_clarify import BulletClarifyService

    svc = BulletClarifyService(db)
    if isinstance(body, dict) and "bullet" in body:
        bullet = str(body.get("bullet", "") or "").strip()
        if not bullet:
            raise HTTPException(status_code=422, detail="bullet is required")
        target_section = str(body.get("target_section", "") or "")
        target_item_index = body.get("target_item_index")
        target_bullet_index = body.get("target_bullet_index")
        try:
            clarification = svc.suggest_bullet_rewrite(
                draft_id,
                bullet,
                target_section=target_section,
                target_item_index=target_item_index,
                target_bullet_index=target_bullet_index,
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ProviderUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return {
            "id": str(clarification.id),
            "suggested_rewrite": clarification.suggested_rewrite,
        }

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


@router.post("/drafts/{draft_id}/clarify/{clarification_id}/answer")
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


@router.post("/drafts/clarifications/{clar_id}/accept", status_code=204)
def accept_clarification(clar_id: UUID, db: Session = Depends(get_db)) -> Response:
    from job_agent.models import BulletClarification

    row = db.get(BulletClarification, clar_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Clarification not found.")
    draft = db.get(ResumeDraft, row.draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")
    if not _apply_clarification_to_draft(draft, row, db):
        raise HTTPException(status_code=409, detail="Could not apply clarification to the current draft.")
    _refresh_preview_feedback(draft, db)
    db.add(draft)
    db.add(row)
    db.commit()
    return Response(status_code=204)


@router.post("/drafts/clarifications/{clar_id}/promote")
def promote_clarification(clar_id: UUID, db: Session = Depends(get_db)) -> dict[str, str]:
    from job_agent.models import BulletClarification

    row = db.get(BulletClarification, clar_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Clarification not found.")
    if not row.user_accepted:
        raise HTTPException(status_code=409, detail="Apply the rewrite to the draft before saving it for future drafts.")
    draft = db.get(ResumeDraft, row.draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")
    track_slug, label = _promote_clarification_to_fact_sheet(draft, row, db)
    db.add(row)
    db.commit()
    return {"status": "saved", "track_slug": track_slug, "label": label}


@router.get("/drafts/{draft_id}/inferred-additions")
def get_inferred_additions(draft_id: UUID, db: Session = Depends(get_db)) -> dict[str, object]:
    draft = db.get(ResumeDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")
    return {"inferred_additions": draft.inferred_additions or []}


@router.post("/drafts/{draft_id}/inferred-additions/accept")
def accept_inferred_additions(
    draft_id: UUID,
    body: dict,
    db: Session = Depends(get_db),
) -> dict[str, int]:
    draft = db.get(ResumeDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")
    return accept_inferred_additions_payload(draft, body, db)


@router.post("/drafts/{draft_id}/inferred-additions/reject")
def reject_inferred_additions(
    draft_id: UUID,
    body: dict,
    db: Session = Depends(get_db),
) -> dict[str, int]:
    draft = db.get(ResumeDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")
    return reject_inferred_additions_payload(draft, body, db)


@router.post("/drafts/{draft_id}/approve", response_model=ResumeDraftOut)
def approve_draft(draft_id: str, db: Session = Depends(get_db)) -> ResumeDraft:
    try:
        draft_key: UUID | str = UUID(str(draft_id))
    except ValueError:
        draft_key = draft_id
    draft = db.get(ResumeDraft, draft_key)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")
    return approve_draft_record(draft, db)


@router.post("/drafts/{draft_id}/propose-enhancements")
def propose_enhancements(draft_id: UUID, db: Session = Depends(get_db)):
    from job_agent.schemas import EnhancementProposalOut

    service = CVWorkflowService(session=db)
    try:
        proposals = service.generate_enhancement_proposals(draft_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [EnhancementProposalOut.model_validate(proposal) for proposal in proposals]


@router.get("/drafts/{draft_id}/pending-approvals")
def get_pending_approvals(draft_id: UUID, db: Session = Depends(get_db)):
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


@router.post("/drafts/{draft_id}/apply-enhancements")
def apply_enhancements(
    draft_id: UUID,
    body: ApplyEnhancementsRequest,
    db: Session = Depends(get_db),
):
    service = CVWorkflowService(session=db)
    try:
        updated_draft = service.apply_approved_enhancements(draft_id, body.approved_proposal_ids)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"draft_id": str(updated_draft.id), "status": "enhancements_applied"}


@router.get("/drafts/{draft_id}/pdf")
def download_draft_pdf(draft_id: UUID, db: Session = Depends(get_db)):
    draft = db.get(ResumeDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft_pdf_response(draft)


@router.get("/drafts/{draft_id}/pdf-inline")
def preview_draft_pdf(draft_id: UUID, db: Session = Depends(get_db)):
    draft = db.get(ResumeDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft_pdf_response(draft, inline=True)


@router.post("/drafts/{draft_id}/cover-letter")
def generate_cover_letter(
    draft_id: UUID,
    company_url: str | None = None,
    db: Session = Depends(get_db),
) -> dict[str, str]:
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


@router.post("/drafts/{draft_id}/cover-letter-html", include_in_schema=False)
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


@router.get("/drafts/{draft_id}/cover-letter")
def get_cover_letter(draft_id: UUID, db: Session = Depends(get_db)) -> dict[str, str]:
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


# ── Draft UI pages ─────────────────────────────────────────────────────────────

@router.get("/ui/drafts", include_in_schema=False)
def ui_drafts(request: Request, db: Session = Depends(get_db)):
    if redirect := _redirect_if_setup_required(request, db):
        return redirect
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


@router.get("/ui/drafts/{draft_id}", include_in_schema=False)
def ui_draft_detail(draft_id: UUID, request: Request, db: Session = Depends(get_db)):
    if redirect := _redirect_if_setup_required(request, db):
        return redirect
    draft = db.get(ResumeDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")
    job = db.get(JobPost, draft.job_post_id)
    track = db.get(ResumeTrack, draft.resume_track_id)
    feedback = _refresh_preview_feedback(draft, db)
    db.commit()
    preview_lookup = {
        str(item.get("item_id")): item
        for item in ((feedback.get("preview_annotations") or {}).get("items") or [])
        if isinstance(item, dict) and item.get("item_id")
    }
    confirmed_facts, promoted_fact_keys = promoted_fact_keys_for_draft(draft, feedback, db)
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
            confirmed_facts=confirmed_facts,
            promoted_fact_keys=promoted_fact_keys,
            preview_lookup=preview_lookup,
        ),
    )


@router.post("/ui/drafts/{draft_id}/approve", include_in_schema=False)
def ui_approve_draft(draft_id: UUID, db: Session = Depends(get_db)) -> Response:
    _raise_if_setup_required(db)
    draft = db.get(ResumeDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")
    return ui_approve_fragment(draft, db)


@router.post("/ui/drafts/{draft_id}/reject", include_in_schema=False)
def ui_reject_draft(draft_id: UUID, db: Session = Depends(get_db)) -> Response:
    _raise_if_setup_required(db)
    draft = db.get(ResumeDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")
    return ui_reject_fragment(draft, db)
