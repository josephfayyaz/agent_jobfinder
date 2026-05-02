"""Drafts, tasks, clarifications, and draft UI routes."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from job_agent.config import settings
from job_agent.db import get_db
from job_agent.llm import ProviderUnavailableError
from job_agent.models import (
    ExperienceFact,
    FactSheetChangeLog,
    JobPost,
    ProjectFact,
    ResumeDraft,
    ResumeTrack,
    VerifiedCandidateFact,
    WorkflowTask,
)
from job_agent.schemas import (
    ApplyEnhancementsRequest,
    ResumeDraftOut,
    WorkflowTaskCreate,
    WorkflowTaskOut,
)
from job_agent.services.draft_preview import build_preview_annotations
from job_agent.services.job_target_profile import build_cv_target_fit
from job_agent.services.workflows import CVWorkflowService

from job_agent.routers.form_utils import _append_unique
from job_agent.routers.setup_state import (
    _raise_if_setup_required,
    _redirect_if_setup_required,
    _verified_fact_key,
)
from job_agent.routers.templates import templates
from job_agent.routers.ui_context import _ui_context

logger = logging.getLogger(__name__)
router = APIRouter()


class DraftGenerateRequest(BaseModel):
    job_id: UUID
    track_slug: str | None = None
    force_cloud_review: bool = False


# ── Draft helpers ──────────────────────────────────────────────────────────────

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

    track = draft.resume_track or db.get(ResumeTrack, draft.resume_track_id)
    job = draft.job_post or db.get(JobPost, draft.job_post_id)
    if track is None or job is None:
        return

    try:
        workflow = CVWorkflowService(db)
        context = workflow._load_context(
            str(job.id),
            track.slug,
            candidate_id=draft.candidate_id,
        )
        profile = workflow._context_profile_dict(context)
        draft.tex_path = render_resume_tex(
            profile=profile,
            job=workflow._job_dict(context.job),
            track=workflow._track_dict(context.track),
            content=draft.content or {},
            draft_id=str(draft.id),
        )
    except ValueError as exc:
        logger.warning("Skipping draft rerender for %s: %s", draft.id, exc)


def _refresh_draft_artifacts(draft: ResumeDraft, db: Session) -> bool:
    from job_agent.services.documents import compile_pdf

    _rerender_draft_tex(draft, db)
    if not draft.tex_path:
        return False
    try:
        compile_pdf(draft.tex_path)
        return True
    except Exception as exc:
        logger.warning("PDF refresh failed for draft %s: %s", draft.id, exc)
        return False


def _draft_context(draft: ResumeDraft, db: Session):
    """Reload workflow context using the candidate stored on the draft itself."""
    track = draft.resume_track or db.get(ResumeTrack, draft.resume_track_id)
    if track is None:
        raise HTTPException(status_code=404, detail="Resume track not found.")
    workflow = CVWorkflowService(db)
    context = workflow._load_context(
        str(draft.job_post_id),
        track.slug,
        candidate_id=draft.candidate_id,
    )
    return workflow, context


def _refresh_preview_feedback(draft: ResumeDraft, db: Session) -> dict[str, object]:
    """Rebuild readiness, fit, and preview metadata after a draft edit."""
    feedback = dict(draft.review_feedback or {})
    accepted = list(feedback.get("accepted_preview_item_ids") or [])
    try:
        workflow, context = _draft_context(draft, db)
    except ValueError as exc:
        logger.warning("Skipping preview feedback refresh for %s: %s", draft.id, exc)
        feedback["profile_readiness"] = {
            "status": "insufficient_profile_data",
            "reasons": ["Profile context is incomplete for this draft."],
            "warnings": [str(exc)],
        }
        feedback["target_fit_map"] = feedback.get("target_fit_map") or {"rows": [], "scores": {}}
        feedback["recommended_improvements"] = feedback.get("recommended_improvements") or []
        feedback["preview_annotations"] = build_preview_annotations(
            draft_content=draft.content or {},
            profile_data={},
            accepted_item_ids=accepted,
        )
        draft.review_feedback = feedback
        return feedback

    profile_data = workflow._context_profile_dict(context)
    feedback["profile_readiness"] = workflow.profile_readiness_for_context(context)
    feedback["target_fit_map"] = build_cv_target_fit(
        job_profile=workflow._ensure_job_target_profile(context.job),
        profile_data=profile_data,
        verified_facts=workflow._load_verified_facts_for_prompt(context),
    )
    feedback["recommended_improvements"] = feedback["target_fit_map"].get("recommended_improvements", [])
    feedback["preview_annotations"] = build_preview_annotations(
        draft_content=draft.content or {},
        profile_data=profile_data,
        accepted_item_ids=accepted,
    )
    draft.review_feedback = feedback
    return feedback


def _preview_pending_count(draft: ResumeDraft) -> int:
    preview = dict((draft.review_feedback or {}).get("preview_annotations") or {})
    return int(preview.get("pending_confirmation_count") or 0)


def _clarification_section_key(section: str) -> str | None:
    if section == "experience":
        return "selected_experiences"
    if section == "project":
        return "selected_projects"
    return None


def _apply_clarification_to_draft(draft: ResumeDraft, clarification, db: Session) -> bool:
    section_key = _clarification_section_key(clarification.target_section)
    if section_key is None:
        return False

    content = dict(draft.content or {})
    items = [dict(item) for item in (content.get(section_key) or [])]
    item_index = clarification.target_item_index
    bullet_index = clarification.target_bullet_index
    if item_index is None or bullet_index is None or not (0 <= item_index < len(items)):
        return False

    item = dict(items[item_index])
    bullets = [str(bullet) for bullet in (item.get("bullets") or [])]
    if not (0 <= bullet_index < len(bullets)):
        return False

    if bullets[bullet_index] != clarification.original_bullet:
        try:
            bullet_index = bullets.index(clarification.original_bullet)
        except ValueError:
            return False

    bullets[bullet_index] = clarification.suggested_rewrite
    item["bullets"] = bullets
    items[item_index] = item
    content[section_key] = items
    draft.content = content
    clarification.user_accepted = True
    _refresh_draft_artifacts(draft, db)
    return True


def _promote_clarification_to_fact_sheet(draft: ResumeDraft, clarification, db: Session) -> tuple[str, str]:
    candidate_id = (draft.candidate_id or "").strip() or settings.default_candidate_id.strip()
    if not candidate_id:
        raise HTTPException(
            status_code=409,
            detail="No candidate-linked fact sheet is active. Run onboarding or set DEFAULT_CANDIDATE_ID first.",
        )

    track = draft.resume_track or db.get(ResumeTrack, draft.resume_track_id)
    if track is None:
        raise HTTPException(status_code=404, detail="Resume track not found.")

    section_key = _clarification_section_key(clarification.target_section)
    if section_key is None:
        raise HTTPException(status_code=409, detail="Clarification is missing draft location metadata.")

    content = dict(draft.content or {})
    items = list(content.get(section_key) or [])
    item_index = clarification.target_item_index
    if item_index is None or not (0 <= item_index < len(items)):
        raise HTTPException(status_code=409, detail="Clarification target is no longer available in the draft.")

    item = dict(items[item_index])
    bullets = [str(bullet) for bullet in (item.get("bullets") or [])]
    if clarification.suggested_rewrite not in bullets:
        raise HTTPException(status_code=409, detail="Apply the rewrite to the draft before saving it for future drafts.")

    if clarification.target_section == "experience":
        title = str(item.get("title", "") or "")
        company = str(item.get("company", "") or "")
        query = db.query(ExperienceFact).filter(ExperienceFact.candidate_id == candidate_id, ExperienceFact.role_title == title)
        if company:
            query = query.filter(ExperienceFact.organization == company)
        record = query.first()
        if record is None:
            raise HTTPException(status_code=404, detail="Matching experience fact not found for this draft entry.")
        bank = dict(record.best_bullets_by_track or {})
        bank[track.slug] = bullets
        record.best_bullets_by_track = bank
        label = f"{title} at {company}".strip()
    else:
        name = str(item.get("name", "") or "")
        record = (
            db.query(ProjectFact)
            .filter(ProjectFact.candidate_id == candidate_id, ProjectFact.project_name == name)
            .first()
        )
        if record is None:
            raise HTTPException(status_code=404, detail="Matching project fact not found for this draft entry.")
        bank = dict(record.best_bullets_by_track or {})
        bank[track.slug] = bullets
        record.best_bullets_by_track = bank
        label = name

    clarification.promoted_to_fact_sheet = True
    db.add(
        FactSheetChangeLog(
            candidate_id=candidate_id,
            message=(
                f"Saved approved {clarification.target_section} bullets for track '{track.slug}' "
                f"from '{label}'."
            ),
        )
    )
    return track.slug, label


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
    feedback = _refresh_preview_feedback(draft, db)
    db.commit()
    return {
        "draft_id": str(draft.id),
        "profile_readiness": feedback.get("profile_readiness"),
        "target_fit_map": feedback.get("target_fit_map"),
        "recommended_improvements": feedback.get("recommended_improvements") or [],
        "preview_annotations": feedback.get("preview_annotations") or {},
    }


@router.post("/drafts/{draft_id}/preview/update")
def update_preview_state(draft_id: UUID, body: dict = Body(...), db: Session = Depends(get_db)) -> dict[str, object]:
    draft = db.get(ResumeDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")

    content = dict(draft.content or {})
    feedback = dict(draft.review_feedback or {})
    action = str(body.get("action") or "").strip().lower()

    if action == "summary":
        summary = str(body.get("professional_summary") or "").strip()
        if not summary:
            raise HTTPException(status_code=422, detail="professional_summary is required.")
        content["professional_summary"] = summary
    elif action == "remove_bullet":
        section = str(body.get("section") or "").strip()
        item_index = int(body.get("item_index"))
        bullet_index = int(body.get("bullet_index"))
        rows = [dict(item) for item in (content.get(section) or [])]
        if not (0 <= item_index < len(rows)):
            raise HTTPException(status_code=422, detail="item_index is out of range.")
        bullets = [str(item) for item in (rows[item_index].get("bullets") or [])]
        if not (0 <= bullet_index < len(bullets)):
            raise HTTPException(status_code=422, detail="bullet_index is out of range.")
        bullets.pop(bullet_index)
        rows[item_index]["bullets"] = bullets
        content[section] = rows
    elif action == "reorder_item":
        section = str(body.get("section") or "").strip()
        from_index = int(body.get("from_index"))
        to_index = int(body.get("to_index"))
        rows = [dict(item) for item in (content.get(section) or [])]
        if not rows or not (0 <= from_index < len(rows)) or not (0 <= to_index < len(rows)):
            raise HTTPException(status_code=422, detail="Invalid reorder indexes.")
        row = rows.pop(from_index)
        rows.insert(to_index, row)
        content[section] = rows
    elif action == "confirm_item":
        item_id = str(body.get("item_id") or "").strip()
        if not item_id:
            raise HTTPException(status_code=422, detail="item_id is required.")
        accepted = list(feedback.get("accepted_preview_item_ids") or [])
        if item_id not in accepted:
            accepted.append(item_id)
        feedback["accepted_preview_item_ids"] = accepted
    elif action == "reject_item":
        item_id = str(body.get("item_id") or "").strip()
        if not item_id:
            raise HTTPException(status_code=422, detail="item_id is required.")
        accepted = [item for item in (feedback.get("accepted_preview_item_ids") or []) if item != item_id]
        feedback["accepted_preview_item_ids"] = accepted
        if item_id == "summary":
            content["professional_summary"] = ""
        else:
            try:
                section, item_index, bullet_index = item_id.split(":")
                item_index_i = int(item_index)
                bullet_index_i = int(bullet_index)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail="Invalid item_id.") from exc
            rows = [dict(item) for item in (content.get(section) or [])]
            if 0 <= item_index_i < len(rows):
                bullets = [str(item) for item in (rows[item_index_i].get("bullets") or [])]
                if 0 <= bullet_index_i < len(bullets):
                    bullets.pop(bullet_index_i)
                    rows[item_index_i]["bullets"] = bullets
                    content[section] = rows
    else:
        raise HTTPException(status_code=422, detail="Unsupported preview action.")

    draft.content = content
    draft.review_feedback = feedback
    _refresh_preview_feedback(draft, db)
    _refresh_draft_artifacts(draft, db)
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return {
        "draft_id": str(draft.id),
        "preview_annotations": (draft.review_feedback or {}).get("preview_annotations") or {},
        "recommended_improvements": (draft.review_feedback or {}).get("recommended_improvements") or [],
        "content": draft.content or {},
    }


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
    from job_agent.models import BulletClarification

    rows = (
        db.query(BulletClarification)
        .filter(BulletClarification.draft_id == draft_id)
        .order_by(BulletClarification.created_at.desc())
        .all()
    )
    return [
        {
            "id": str(row.id),
            "original_bullet": row.original_bullet,
            "suggested_rewrite": row.suggested_rewrite,
            "user_accepted": row.user_accepted,
            "promoted_to_fact_sheet": row.promoted_to_fact_sheet,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


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

    accepted_ids = set(body.get("accepted_ids", []))
    pending = list(draft.inferred_additions or [])
    accepted = [item for item in pending if item.get("id") in accepted_ids]
    remaining = [item for item in pending if item.get("id") not in accepted_ids]

    draft.content = _merge_inferred_additions(draft.content or {}, accepted)
    draft.accepted_inferred_additions = list(draft.accepted_inferred_additions or []) + accepted
    draft.inferred_additions = remaining
    _rerender_draft_tex(draft, db)
    _refresh_preview_feedback(draft, db)
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return {"accepted": len(accepted), "remaining": len(remaining)}


@router.post("/drafts/{draft_id}/inferred-additions/reject")
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


@router.post("/drafts/{draft_id}/approve", response_model=ResumeDraftOut)
def approve_draft(draft_id: str, db: Session = Depends(get_db)) -> ResumeDraft:
    try:
        draft_key: UUID | str = UUID(str(draft_id))
    except ValueError:
        draft_key = draft_id
    draft = db.get(ResumeDraft, draft_key)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")
    _refresh_preview_feedback(draft, db)
    if _preview_pending_count(draft) > 0:
        raise HTTPException(
            status_code=409,
            detail="Review the remaining preview warnings before approving this draft.",
        )
    draft.approved = True
    draft.status = "approved"
    db.commit()
    db.refresh(draft)
    return draft


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
    from fastapi.responses import FileResponse
    from fastapi.responses import HTMLResponse
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
        message = str(exc)
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>PDF generation failed</title>
          <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background:#f8fafc; color:#0f172a; margin:0; }}
            main {{ max-width: 48rem; margin: 4rem auto; background:white; border:1px solid #e2e8f0; border-radius: 1rem; padding: 2rem; }}
            h1 {{ margin-top:0; font-size:1.5rem; }}
            p {{ line-height:1.6; }}
            code {{ background:#f1f5f9; padding:0.15rem 0.35rem; border-radius:0.35rem; }}
            .hint {{ margin-top:1rem; color:#475569; }}
          </style>
        </head>
        <body>
          <main>
            <h1>PDF generation failed</h1>
            <p>{message}</p>
            <p class="hint">The resume source file still exists at <code>{draft.tex_path}</code>. You can retry after fixing the local TeX setup.</p>
          </main>
        </body>
        </html>
        """
        return HTMLResponse(content=html, status_code=500)

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=Path(pdf_path).name,
    )


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
    confirmed_facts = []
    for fact in feedback.get("confirmed_facts") or []:
        gap = str(fact.get("gap") or "").strip()
        answer = str(fact.get("answer") or "").strip()
        if fact.get("confirmed") and gap and answer:
            confirmed_facts.append({**fact, "gap": gap, "answer": answer, "memory_key": _verified_fact_key(gap, answer)})
    promoted_fact_keys: set[str] = set()
    if confirmed_facts:
        promoted_facts = (
            db.query(VerifiedCandidateFact)
            .filter(
                VerifiedCandidateFact.source_draft_id == draft_id,
                VerifiedCandidateFact.is_active.is_(True),
            )
            .all()
        )
        promoted_fact_keys = {
            _verified_fact_key(fact.gap_label, fact.evidence)
            for fact in promoted_facts
        }
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
    _refresh_preview_feedback(draft, db)
    if _preview_pending_count(draft) > 0:
        return Response(
            status_code=409,
            headers={"X-Toast-Error": "Confirm or remove the remaining preview warnings before approving this draft."},
        )
    draft.approved = True
    draft.status = "approved"
    db.commit()
    fragment = (
        f'<div id="draft-actions-{draft_id}" class="flex flex-wrap gap-2 items-center">'
        f'<span class="px-3 py-1.5 text-sm bg-green-100 text-green-700 rounded font-medium">✓ Approved</span>'
        f'</div>'
    )
    return HTMLResponse(content=fragment, headers={"X-Toast-Success": "Draft approved"})


@router.post("/ui/drafts/{draft_id}/reject", include_in_schema=False)
def ui_reject_draft(draft_id: UUID, db: Session = Depends(get_db)) -> Response:
    _raise_if_setup_required(db)
    draft = db.get(ResumeDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")
    draft.approved = False
    draft.status = "rejected"
    db.commit()
    fragment = (
        f'<div id="draft-actions-{draft_id}" class="flex flex-wrap gap-2 items-center">'
        f'<span class="px-3 py-1.5 text-sm bg-red-100 text-red-600 rounded font-medium">✗ Rejected</span>'
        f'</div>'
    )
    return HTMLResponse(content=fragment, headers={"X-Toast-Success": "Draft rejected"})
