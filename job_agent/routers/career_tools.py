"""Interview bank and offer comparison UI."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from job_agent.config import settings
from job_agent.db import get_db
from job_agent.models import OfferDecision
from job_agent.routers.setup_state import _raise_if_setup_required, _redirect_if_setup_required
from job_agent.routers.templates import templates
from job_agent.routers.ui_context import _ui_context
from job_agent.services.interview_bank import InterviewBankService
from job_agent.services.offer_compass import DEFAULT_PRIORITIES, OfferCompassService

router = APIRouter()


def _candidate_scope() -> str | None:
    candidate_id = settings.default_candidate_id.strip()
    return candidate_id or None


def _matches_story_query(row: Any, query: str) -> bool:
    if not query:
        return True
    haystack = " ".join(
        [
            str(getattr(row, "title", "") or ""),
            str(getattr(row, "context", "") or ""),
            str(getattr(row, "action", "") or ""),
            str(getattr(row, "result", "") or ""),
            " ".join(getattr(row, "tools", []) or []),
            " ".join(getattr(row, "role_family_tags", []) or []),
        ]
    ).casefold()
    return query.casefold() in haystack


@router.post("/ui/story-bank/rebuild", include_in_schema=False)
def ui_story_bank_rebuild(db: Session = Depends(get_db)) -> Response:
    _raise_if_setup_required(db)
    created = InterviewBankService(db).rebuild(_candidate_scope())
    return Response(
        status_code=204,
        headers={
            "HX-Refresh": "true",
            "X-Toast-Success": f"Story Bank refreshed with {created} evidence item{'s' if created != 1 else ''}.",
        },
    )


@router.get("/ui/story-bank", include_in_schema=False)
def ui_story_bank(
    request: Request,
    role_family: str | None = None,
    confidence: str | None = None,
    q: str = "",
    db: Session = Depends(get_db),
):
    if redirect := _redirect_if_setup_required(request, db):
        return redirect

    service = InterviewBankService(db)
    candidate_id = _candidate_scope()
    stories = service.list_stories(candidate_id, role_family=role_family or None, confidence=confidence or None)
    if not stories:
        service.rebuild(candidate_id)
        stories = service.list_stories(candidate_id, role_family=role_family or None, confidence=confidence or None)

    query = q.strip()
    if query:
        stories = [story for story in stories if _matches_story_query(story, query)]

    role_options = sorted(
        {
            tag
            for story in service.list_stories(candidate_id)
            for tag in (story.role_family_tags or [])
            if str(tag).strip()
        }
    )
    confidence_options = [
        ("verified-memory", "Verified memory"),
        ("approved-draft", "Approved draft"),
        ("accepted-clarification", "Accepted clarification"),
    ]
    return templates.TemplateResponse(
        request=request,
        name="story_bank.html",
        context=_ui_context(
            request,
            "Story Bank",
            stories=stories,
            role_options=role_options,
            confidence_options=confidence_options,
            filters={"role_family": role_family or "", "confidence": confidence or "", "q": query},
        ),
    )


@router.get("/offers")
def list_offers(db: Session = Depends(get_db)) -> list[dict[str, object]]:
    rows = OfferCompassService(db).list_offers(_candidate_scope())
    return [
        {
            "id": str(row.id),
            "company": row.company,
            "title": row.title,
            "salary_text": row.salary_text,
            "location": row.location,
            "remote_policy": row.remote_policy,
            "visa_notes": row.visa_notes,
            "growth_notes": row.growth_notes,
            "learning_notes": row.learning_notes,
            "work_life_notes": row.work_life_notes,
            "negotiation_notes": row.negotiation_notes,
            "status": row.status,
            "metadata_json": row.metadata_json,
        }
        for row in rows
    ]


@router.post("/ui/offers/add", include_in_schema=False)
def ui_offer_add(
    company: str = Form(...),
    title: str = Form(""),
    salary_text: str = Form(""),
    location: str = Form(""),
    remote_policy: str = Form(""),
    visa_notes: str = Form(""),
    growth_notes: str = Form(""),
    learning_notes: str = Form(""),
    work_life_notes: str = Form(""),
    negotiation_notes: str = Form(""),
    db: Session = Depends(get_db),
):
    _raise_if_setup_required(db)
    offer = OfferDecision(
        candidate_id=_candidate_scope(),
        company=company.strip(),
        title=title.strip(),
        salary_text=salary_text.strip(),
        location=location.strip(),
        remote_policy=remote_policy.strip(),
        visa_notes=visa_notes.strip(),
        growth_notes=growth_notes.strip(),
        learning_notes=learning_notes.strip(),
        work_life_notes=work_life_notes.strip(),
        negotiation_notes=negotiation_notes.strip(),
    )
    db.add(offer)
    db.commit()
    return RedirectResponse(url="/ui/offers", status_code=303)


@router.post("/ui/offers/{offer_id}/delete", include_in_schema=False)
def ui_offer_delete(offer_id: UUID, db: Session = Depends(get_db)):
    _raise_if_setup_required(db)
    row = db.get(OfferDecision, offer_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Offer not found.")
    db.delete(row)
    db.commit()
    return RedirectResponse(url="/ui/offers", status_code=303)


@router.get("/ui/offers", include_in_schema=False)
def ui_offers(
    request: Request,
    compensation: int = DEFAULT_PRIORITIES["compensation"],
    location: int = DEFAULT_PRIORITIES["location"],
    learning: int = DEFAULT_PRIORITIES["learning"],
    visa: int = DEFAULT_PRIORITIES["visa"],
    work_life: int = DEFAULT_PRIORITIES["work_life"],
    db: Session = Depends(get_db),
):
    if redirect := _redirect_if_setup_required(request, db):
        return redirect

    service = OfferCompassService(db)
    priorities = service.priorities(
        {
            "compensation": compensation,
            "location": location,
            "learning": learning,
            "visa": visa,
            "work_life": work_life,
        }
    )
    ranked = service.compare(_candidate_scope(), priorities)
    return templates.TemplateResponse(
        request=request,
        name="offer_compass.html",
        context=_ui_context(
            request,
            "Offer Compass",
            priorities=priorities,
            ranked_offers=ranked,
        ),
    )
