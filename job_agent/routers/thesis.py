"""Thesis targets, outreach drafts, and thesis UI routes."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from job_agent.db import get_db
from job_agent.models import ContactEvent, OutreachDraft, ThesisTarget
from job_agent.schemas import (
    ContactEventCreate,
    ContactEventOut,
    OutreachDraftOut,
    OutreachDraftRevisionRequest,
    ThesisTargetCreate,
    ThesisTargetOut,
    ThesisTargetUpdate,
)
from job_agent.services.thesis_outreach import ThesisOutreachService

from job_agent.routers.form_utils import _blank_to_none, _parse_urlencoded_body
from job_agent.routers.setup_state import (
    _raise_if_setup_required,
    _redirect_if_setup_required,
)
from job_agent.routers.templates import templates
from job_agent.routers.ui_context import _ui_context

router = APIRouter()


@router.post("/thesis-targets", response_model=ThesisTargetOut, status_code=201)
def create_thesis_target(payload: ThesisTargetCreate, db: Session = Depends(get_db)) -> ThesisTarget:
    target = ThesisTarget(**payload.model_dump())
    db.add(target)
    db.commit()
    db.refresh(target)
    return target


@router.get("/thesis-targets", response_model=list[ThesisTargetOut])
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


@router.get("/thesis-targets/{target_id}", response_model=ThesisTargetOut)
def get_thesis_target(target_id: int, db: Session = Depends(get_db)) -> ThesisTarget:
    target = db.query(ThesisTarget).filter_by(id=target_id).first()
    if target is None:
        raise HTTPException(status_code=404, detail="Thesis target not found.")
    return target


@router.patch("/thesis-targets/{target_id}", response_model=ThesisTargetOut)
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


@router.delete("/thesis-targets/{target_id}", status_code=204)
def archive_thesis_target(target_id: int, db: Session = Depends(get_db)) -> Response:
    target = db.query(ThesisTarget).filter_by(id=target_id).first()
    if target is None:
        raise HTTPException(status_code=404, detail="Thesis target not found.")
    target.status = "archived"
    target.updated_at = datetime.now(timezone.utc)
    db.commit()
    return Response(status_code=204)


@router.post("/thesis-targets/{target_id}/communications", response_model=ContactEventOut, status_code=201)
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


@router.get("/thesis-targets/{target_id}/communications", response_model=list[ContactEventOut])
def list_contact_events(target_id: int, db: Session = Depends(get_db)) -> list[ContactEvent]:
    return (
        db.query(ContactEvent)
        .filter_by(target_id=target_id)
        .order_by(ContactEvent.event_at.desc())
        .all()
    )


@router.get("/thesis-targets/{target_id}/outreach-drafts", response_model=list[OutreachDraftOut])
def list_outreach_drafts(target_id: int, db: Session = Depends(get_db)) -> list[OutreachDraft]:
    return (
        db.query(OutreachDraft)
        .filter_by(target_id=target_id)
        .order_by(OutreachDraft.created_at.desc())
        .all()
    )


@router.post("/outreach-drafts/{draft_id}/approve", response_model=OutreachDraftOut)
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


@router.post("/thesis-targets/{target_id}/generate-email", response_model=OutreachDraftOut, status_code=201)
def generate_outreach_email(target_id: int, db: Session = Depends(get_db)) -> OutreachDraft:
    try:
        return ThesisOutreachService().generate_email(target_id, db)
    except ValueError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.post("/outreach-drafts/{draft_id}/revise", response_model=OutreachDraftOut)
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


@router.post("/outreach-drafts/{draft_id}/mark-sent", response_model=OutreachDraftOut)
def mark_outreach_draft_sent(draft_id: int, db: Session = Depends(get_db)) -> OutreachDraft:
    try:
        return ThesisOutreachService().mark_sent(draft_id, db)
    except ValueError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


# ── Thesis UI pages ────────────────────────────────────────────────────────────

@router.get("/ui/thesis", include_in_schema=False)
def ui_thesis(request: Request, db: Session = Depends(get_db)):
    if redirect := _redirect_if_setup_required(request, db):
        return redirect
    targets = db.query(ThesisTarget).order_by(ThesisTarget.priority.asc(), ThesisTarget.name.asc()).all()
    return templates.TemplateResponse(
        request=request,
        name="thesis.html",
        context=_ui_context(request, "Thesis Targets", targets=targets),
    )


@router.post("/ui/thesis-targets", include_in_schema=False)
async def ui_create_thesis_target(request: Request, db: Session = Depends(get_db)) -> Response:
    _raise_if_setup_required(db)
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


@router.post("/ui/thesis-targets/{target_id}/email-preview", include_in_schema=False)
def ui_generate_email_preview(
    request: Request,
    target_id: int,
    db: Session = Depends(get_db),
):
    _raise_if_setup_required(db)
    try:
        draft = ThesisOutreachService().generate_email(target_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return templates.TemplateResponse(
        request=request,
        name="partials/email_preview.html",
        context={"request": request, "draft": draft},
    )
