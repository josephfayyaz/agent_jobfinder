"""Tests for thesis outreach prompt building and draft lifecycle."""

from __future__ import annotations

from datetime import datetime, timezone

from job_agent.models import ContactEvent, MasterProfile, OutreachDraft, ThesisTarget
from job_agent.services.prompts import build_thesis_outreach_user_prompt
from job_agent.services.thesis_outreach import ThesisOutreachService


class _FakeRouter:
    def __init__(self, result: dict[str, object]) -> None:
        self.result = result

    def generate(self, **_kwargs: object) -> dict[str, object]:
        return dict(self.result)


class _FakeQuery:
    def __init__(self, items: list[object]) -> None:
        self._items = list(items)

    def filter_by(self, **kwargs: object) -> "_FakeQuery":
        filtered = [
            item
            for item in self._items
            if all(getattr(item, field) == value for field, value in kwargs.items())
        ]
        return _FakeQuery(filtered)

    def first(self):
        return self._items[0] if self._items else None


class _FakeSession:
    def __init__(self) -> None:
        self.profiles: list[MasterProfile] = []
        self.targets: list[ThesisTarget] = []
        self.drafts: list[OutreachDraft] = []
        self.events: list[ContactEvent] = []

    def add(self, obj: object) -> None:
        if isinstance(obj, MasterProfile):
            self.profiles.append(obj)
        elif isinstance(obj, ThesisTarget):
            obj.created_at = obj.created_at or datetime.now(timezone.utc)
            obj.updated_at = obj.updated_at or datetime.now(timezone.utc)
            self.targets.append(obj)
        elif isinstance(obj, OutreachDraft):
            if obj.id is None:
                obj.id = len(self.drafts) + 1
            obj.status = obj.status or "draft"
            obj.created_at = obj.created_at or datetime.now(timezone.utc)
            self.drafts.append(obj)
        elif isinstance(obj, ContactEvent):
            if obj.id is None:
                obj.id = len(self.events) + 1
            obj.event_at = obj.event_at or datetime.now(timezone.utc)
            self.events.append(obj)

    def commit(self) -> None:
        return None

    def refresh(self, _obj: object) -> None:
        return None

    def query(self, model):
        if model is MasterProfile:
            return _FakeQuery(self.profiles)
        if model is ThesisTarget:
            return _FakeQuery(self.targets)
        if model is OutreachDraft:
            return _FakeQuery(self.drafts)
        raise AssertionError(f"Unsupported model {model}")

    def get(self, model, key):
        if model is MasterProfile:
            for profile in self.profiles:
                if profile.id == key:
                    return profile
        return None


def test_build_thesis_outreach_user_prompt_includes_target_context(sample_profile):
    target = {
        "type": "professor",
        "name": "Prof. Ada Lovelace",
        "institution": "PoliTo",
        "department": "Computer Engineering",
        "country": "Italy",
        "research_area": "Federated Learning",
        "notes": "Recent work on privacy-preserving ML systems.",
    }

    prompt = build_thesis_outreach_user_prompt(sample_profile, target)

    assert "Prof. Ada Lovelace" in prompt
    assert "Federated Learning" in prompt
    assert "privacy-preserving ML systems" in prompt
    assert "Test User" in prompt


def test_generate_email_creates_outreach_draft():
    session = _FakeSession()
    session.add(
        MasterProfile(
            id=1,
            full_name="Test User",
            location="Turin, Italy",
            public_brand_summary="Data engineer focused on ML systems.",
            experiences=[],
            projects=[],
            education=[],
        )
    )
    target = ThesisTarget(
        id=1,
        type="professor",
        name="Prof. Ada Lovelace",
        institution="PoliTo",
        country="Italy",
        research_area="Federated Learning",
    )
    session.add(target)

    service = ThesisOutreachService(
        router=_FakeRouter(
            {"subject": "Thesis Inquiry", "body": "Hello Professor,\n\nI am writing...", "key_alignment_points": []}
        )
    )
    draft = service.generate_email(1, session)

    assert draft.id == 1
    assert draft.subject == "Thesis Inquiry"
    assert target.status == "email_drafted"
    assert len(session.drafts) == 1


def test_revise_and_mark_sent_updates_history():
    session = _FakeSession()
    session.add(
        MasterProfile(
            id=1,
            full_name="Test User",
            public_brand_summary="ML systems profile",
        )
    )
    target = ThesisTarget(
        id=1,
        type="lab",
        name="Systems Lab",
        institution="ETH Zurich",
        country="Switzerland",
        research_area="Distributed ML",
        status="email_drafted",
    )
    original = OutreachDraft(
        id=1,
        target_id=1,
        subject="Original Subject",
        body_text="Original body",
        provider="lm_studio_writer",
        status="draft",
    )
    session.add(target)
    session.add(original)

    service = ThesisOutreachService(
        router=_FakeRouter(
            {"subject": "Revised Subject", "body": "Revised body", "key_alignment_points": []}
        )
    )

    revised = service.revise_email(1, "Make it more specific", session)
    sent = service.mark_sent(revised.id, session)

    assert revised.id == 2
    assert revised.feedback == "Make it more specific"
    assert sent.status == "sent"
    assert target.status == "email_sent"
    assert len(session.events) == 1
    assert session.events[0].subject == "Revised Subject"
