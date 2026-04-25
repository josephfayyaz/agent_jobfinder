"""Thesis and traineeship outreach email generator."""

from __future__ import annotations

from datetime import datetime, timezone
import logging

from sqlalchemy.orm import Session

from job_agent.llm import LLMRouter
from job_agent.models import ContactEvent, MasterProfile, OutreachDraft, ThesisTarget
from job_agent.services.prompts import (
    build_thesis_outreach_system_prompt,
    build_thesis_outreach_user_prompt,
    build_thesis_revision_prompt,
)

logger = logging.getLogger(__name__)


class ThesisOutreachService:
    def __init__(self, router: LLMRouter | None = None) -> None:
        self.router = router or LLMRouter()

    def generate_email(self, target_id: int, session: Session) -> OutreachDraft:
        """Generate and store a new outreach draft for a thesis target."""
        target = session.query(ThesisTarget).filter_by(id=target_id).first()
        if target is None:
            raise ValueError(f"ThesisTarget {target_id} not found")

        profile = self._get_profile(session)
        if profile is None:
            raise ValueError("MasterProfile not found — run fact sheet ingestion first")

        profile_dict = {
            "full_name": profile.full_name,
            "location": profile.location,
            "public_brand_summary": profile.public_brand_summary,
            "experiences": profile.experiences or [],
            "projects": profile.projects or [],
            "education": profile.education or [],
        }
        target_dict = {
            "type": target.type,
            "name": target.name,
            "institution": target.institution,
            "department": target.department,
            "country": target.country,
            "research_area": target.research_area,
            "notes": target.notes,
        }

        result = self.router.generate(
            role="writer",
            system_prompt=build_thesis_outreach_system_prompt(),
            user_prompt=build_thesis_outreach_user_prompt(profile_dict, target_dict),
            temperature=0.3,
        )

        subject = result.get("subject") or f"Master's Thesis Inquiry — {target.research_area}"
        body = result.get("body") or ""
        if not body:
            body = self._heuristic_email(profile_dict, target_dict)
            subject = f"Master's Thesis Collaboration — {target.research_area} — {profile.full_name}"

        draft = OutreachDraft(
            target_id=target_id,
            subject=subject,
            body_text=body,
            provider="lm_studio_writer",
            status="draft",
            approved=None,
        )
        session.add(draft)
        target.status = "email_drafted"
        target.updated_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(draft)
        logger.info("Outreach draft %s created for thesis target %s", draft.id, target_id)
        return draft

    def revise_email(self, draft_id: int, feedback: str, session: Session) -> OutreachDraft:
        """Create a new revision of an existing outreach draft."""
        original = session.query(OutreachDraft).filter_by(id=draft_id).first()
        if original is None:
            raise ValueError(f"OutreachDraft {draft_id} not found")

        result = self.router.generate(
            role="writer",
            system_prompt=build_thesis_outreach_system_prompt(),
            user_prompt=build_thesis_revision_prompt(original.subject, original.body_text, feedback),
            temperature=0.3,
        )
        subject = result.get("subject") or original.subject
        body = result.get("body") or original.body_text

        revised = OutreachDraft(
            target_id=original.target_id,
            subject=subject,
            body_text=body,
            provider="lm_studio_writer",
            status="draft",
            approved=None,
            feedback=feedback,
        )
        session.add(revised)
        session.commit()
        session.refresh(revised)
        logger.info("Outreach draft %s revised into draft %s", draft_id, revised.id)
        return revised

    def mark_sent(self, draft_id: int, session: Session) -> OutreachDraft:
        """Mark an outreach draft as sent and log a contact event."""
        draft = session.query(OutreachDraft).filter_by(id=draft_id).first()
        if draft is None:
            raise ValueError(f"OutreachDraft {draft_id} not found")

        draft.status = "sent"
        draft.sent_at = datetime.now(timezone.utc)

        target = session.query(ThesisTarget).filter_by(id=draft.target_id).first()
        if target is not None:
            target.status = "email_sent"
            target.updated_at = datetime.now(timezone.utc)

        event = ContactEvent(
            target_id=draft.target_id,
            direction="outbound",
            channel="email",
            event_type="sent",
            subject=draft.subject,
            snippet=draft.body_text[:500],
        )
        session.add(event)
        session.commit()
        session.refresh(draft)
        logger.info("Outreach draft %s marked sent", draft_id)
        return draft

    def _get_profile(self, session: Session) -> MasterProfile | None:
        getter = getattr(session, "get", None)
        if callable(getter):
            return getter(MasterProfile, 1)
        return session.query(MasterProfile).filter_by(id=1).first()

    def _heuristic_email(self, profile: dict, target: dict) -> str:
        """Fallback outreach email when the LLM returns an empty body."""
        name = profile.get("full_name", "Candidate")
        research_area = target.get("research_area", "your research area")
        institution = target.get("institution", "your institution")
        target_name = target.get("name", "Professor")
        degree = profile.get("current_degree") or "a graduate student"
        graduation = profile.get("graduation_date") or "the coming academic cycle"
        background = (
            profile.get("public_brand_summary")
            or profile.get("brand_summary")
            or "relevant academic and project experience"
        )
        return (
            f"Dear {target_name},\n\n"
            f"My name is {name}, and I am {degree}, expecting to finish in {graduation}.\n\n"
            f"I am writing to inquire about thesis or traineeship opportunities related to "
            f"{research_area} at {institution}. My background in {background} "
            "aligns closely with this area, and I would welcome the chance to contribute.\n\n"
            "Would you be open to a brief 15-minute call, or alternatively, I am happy to "
            "answer any questions by email.\n\n"
            f"Thank you for your time.\n\nBest regards,\n{name}"
        )
