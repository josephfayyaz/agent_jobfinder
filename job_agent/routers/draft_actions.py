"""State transitions and helper operations for draft routes.

The HTTP routes remain in ``drafts.py``. This module keeps draft mutation rules
centralized so preview edits, clarifications, and inferred additions are easier
to audit and test without expanding the router further.
"""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from job_agent.config import settings
from job_agent.models import (
    ExperienceFact,
    FactSheetChangeLog,
    JobPost,
    ProjectFact,
    ResumeDraft,
    ResumeTrack,
    VerifiedCandidateFact,
)
from job_agent.services.draft_preview import build_preview_annotations
from job_agent.services.job_target_profile import build_cv_target_fit
from job_agent.services.workflows import CVWorkflowService

from job_agent.routers.form_utils import _append_unique
from job_agent.routers.setup_state import _verified_fact_key

logger = logging.getLogger(__name__)


def merge_inferred_additions(content: dict[str, object], additions: list[dict[str, object]]) -> dict[str, object]:
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


def rerender_draft_tex(draft: ResumeDraft, db: Session) -> None:
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


def refresh_draft_artifacts(draft: ResumeDraft, db: Session) -> bool:
    from job_agent.services.documents import compile_pdf

    rerender_draft_tex(draft, db)
    if not draft.tex_path:
        return False
    try:
        compile_pdf(draft.tex_path)
        return True
    except Exception as exc:
        logger.warning("PDF refresh failed for draft %s: %s", draft.id, exc)
        return False


def draft_context(draft: ResumeDraft, db: Session):
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


def refresh_preview_feedback(draft: ResumeDraft, db: Session) -> dict[str, object]:
    # Preserve compatibility with tests and route-level overrides that patch
    # `job_agent.routers.drafts.build_preview_annotations`.
    from job_agent.routers import drafts as drafts_router

    preview_builder = getattr(drafts_router, "build_preview_annotations", build_preview_annotations)
    feedback = dict(draft.review_feedback or {})
    accepted = list(feedback.get("accepted_preview_item_ids") or [])
    try:
        workflow, context = draft_context(draft, db)
    except ValueError as exc:
        logger.warning("Skipping preview feedback refresh for %s: %s", draft.id, exc)
        feedback["profile_readiness"] = {
            "status": "insufficient_profile_data",
            "reasons": ["Profile context is incomplete for this draft."],
            "warnings": [str(exc)],
        }
        feedback["target_fit_map"] = feedback.get("target_fit_map") or {"rows": [], "scores": {}}
        feedback["recommended_improvements"] = feedback.get("recommended_improvements") or []
        feedback["preview_annotations"] = preview_builder(
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
    feedback["preview_annotations"] = preview_builder(
        draft_content=draft.content or {},
        profile_data=profile_data,
        accepted_item_ids=accepted,
    )
    draft.review_feedback = feedback
    return feedback


def preview_pending_count(draft: ResumeDraft) -> int:
    preview = dict((draft.review_feedback or {}).get("preview_annotations") or {})
    return int(preview.get("pending_confirmation_count") or 0)


def clarification_section_key(section: str) -> str | None:
    if section == "experience":
        return "selected_experiences"
    if section == "project":
        return "selected_projects"
    return None


def apply_clarification_to_draft(draft: ResumeDraft, clarification, db: Session) -> bool:
    section_key = clarification_section_key(clarification.target_section)
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
    refresh_draft_artifacts(draft, db)
    return True


def promote_clarification_to_fact_sheet(draft: ResumeDraft, clarification, db: Session) -> tuple[str, str]:
    candidate_id = (draft.candidate_id or "").strip() or settings.default_candidate_id.strip()
    if not candidate_id:
        raise HTTPException(
            status_code=409,
            detail="No candidate-linked fact sheet is active. Run onboarding or set DEFAULT_CANDIDATE_ID first.",
        )

    track = draft.resume_track or db.get(ResumeTrack, draft.resume_track_id)
    if track is None:
        raise HTTPException(status_code=404, detail="Resume track not found.")

    section_key = clarification_section_key(clarification.target_section)
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


def preview_state_payload(draft: ResumeDraft, db: Session) -> dict[str, object]:
    feedback = refresh_preview_feedback(draft, db)
    db.commit()
    return {
        "draft_id": str(draft.id),
        "profile_readiness": feedback.get("profile_readiness"),
        "target_fit_map": feedback.get("target_fit_map"),
        "recommended_improvements": feedback.get("recommended_improvements") or [],
        "preview_annotations": feedback.get("preview_annotations") or {},
    }


def update_preview_state_payload(draft: ResumeDraft, body: dict, db: Session) -> dict[str, object]:
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
    refresh_preview_feedback(draft, db)
    refresh_draft_artifacts(draft, db)
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return {
        "draft_id": str(draft.id),
        "preview_annotations": (draft.review_feedback or {}).get("preview_annotations") or {},
        "recommended_improvements": (draft.review_feedback or {}).get("recommended_improvements") or [],
        "content": draft.content or {},
    }


def clarification_rows_payload(draft_id: UUID, db: Session) -> list[dict]:
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


def accept_inferred_additions_payload(draft: ResumeDraft, body: dict, db: Session) -> dict[str, int]:
    accepted_ids = set(body.get("accepted_ids", []))
    pending = list(draft.inferred_additions or [])
    accepted = [item for item in pending if item.get("id") in accepted_ids]
    remaining = [item for item in pending if item.get("id") not in accepted_ids]

    draft.content = merge_inferred_additions(draft.content or {}, accepted)
    draft.accepted_inferred_additions = list(draft.accepted_inferred_additions or []) + accepted
    draft.inferred_additions = remaining
    rerender_draft_tex(draft, db)
    refresh_preview_feedback(draft, db)
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return {"accepted": len(accepted), "remaining": len(remaining)}


def reject_inferred_additions_payload(draft: ResumeDraft, body: dict, db: Session) -> dict[str, int]:
    rejected_ids = set(body.get("rejected_ids", []))
    pending = list(draft.inferred_additions or [])
    remaining = [item for item in pending if item.get("id") not in rejected_ids]
    draft.inferred_additions = remaining
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return {"remaining": len(remaining)}


def approve_draft_record(draft: ResumeDraft, db: Session) -> ResumeDraft:
    refresh_preview_feedback(draft, db)
    if preview_pending_count(draft) > 0:
        raise HTTPException(
            status_code=409,
            detail="Review the remaining preview warnings before approving this draft.",
        )
    draft.approved = True
    draft.status = "approved"
    db.commit()
    db.refresh(draft)
    return draft


def ui_approve_fragment(draft: ResumeDraft, db: Session) -> HTMLResponse:
    refresh_preview_feedback(draft, db)
    if preview_pending_count(draft) > 0:
        return HTMLResponse(
            status_code=409,
            content="",
            headers={"X-Toast-Error": "Confirm or remove the remaining preview warnings before approving this draft."},
        )
    draft.approved = True
    draft.status = "approved"
    db.commit()
    fragment = (
        f'<div id="draft-actions-{draft.id}" class="draft-action-bar" data-draft-action-group="primary">'
        f'<p class="job-action-label">Primary actions</p>'
        f'<div class="job-action-buttons">'
        f'<span class="rounded-full bg-green-100 px-4 py-2 text-sm font-semibold text-green-700">Approved</span>'
        f"</div></div>"
    )
    return HTMLResponse(content=fragment, headers={"X-Toast-Success": "Draft approved"})


def ui_reject_fragment(draft: ResumeDraft, db: Session) -> HTMLResponse:
    draft.approved = False
    draft.status = "rejected"
    db.commit()
    fragment = (
        f'<div id="draft-actions-{draft.id}" class="draft-action-bar" data-draft-action-group="primary">'
        f'<p class="job-action-label">Primary actions</p>'
        f'<div class="job-action-buttons">'
        f'<span class="rounded-full bg-red-100 px-4 py-2 text-sm font-semibold text-red-600">Rejected</span>'
        f"</div></div>"
    )
    return HTMLResponse(content=fragment, headers={"X-Toast-Success": "Draft rejected"})


def promoted_fact_keys_for_draft(
    draft: ResumeDraft,
    feedback: dict[str, object],
    db: Session,
) -> tuple[list[dict[str, object]], set[str]]:
    confirmed_facts: list[dict[str, object]] = []
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
                VerifiedCandidateFact.source_draft_id == draft.id,
                VerifiedCandidateFact.is_active.is_(True),
            )
            .all()
        )
        promoted_fact_keys = {
            _verified_fact_key(fact.gap_label, fact.evidence)
            for fact in promoted_facts
        }
    return confirmed_facts, promoted_fact_keys


def draft_pdf_response(draft: ResumeDraft, *, inline: bool = False):
    from fastapi.responses import FileResponse
    from job_agent.services.documents import compile_pdf

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

    preview_name = Path(pdf_path).name
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=None if inline else Path(pdf_path).name,
        content_disposition_type="inline" if inline else "attachment",
        headers={"Content-Disposition": f'inline; filename="{preview_name}"'} if inline else None,
    )
