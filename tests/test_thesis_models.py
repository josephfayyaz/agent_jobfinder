"""Tests for thesis target CRUD helpers and outreach approval flow."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Response

from job_agent.main import (
    approve_outreach_draft,
    archive_thesis_target,
    create_thesis_target,
    update_thesis_target,
)
from job_agent.models import OutreachDraft, ThesisTarget
from job_agent.schemas import ThesisTargetCreate, ThesisTargetUpdate


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

    def filter(self, *conditions: object) -> "_FakeQuery":
        filtered = []
        for item in self._items:
            if all(_matches_condition(item, condition) for condition in conditions):
                filtered.append(item)
        return _FakeQuery(filtered)

    def order_by(self, *_args: object) -> "_FakeQuery":
        return self

    def first(self):
        return self._items[0] if self._items else None

    def all(self) -> list[object]:
        return list(self._items)


class _FakeSession:
    def __init__(self) -> None:
        self.targets: list[ThesisTarget] = []
        self.drafts: list[OutreachDraft] = []

    def add(self, obj: object) -> None:
        if isinstance(obj, ThesisTarget):
            if obj.id is None:
                obj.id = len(self.targets) + 1
            if obj.status is None:
                obj.status = "identified"
            if obj.priority is None:
                obj.priority = 3
            obj.created_at = obj.created_at or datetime.now(timezone.utc)
            obj.updated_at = obj.updated_at or datetime.now(timezone.utc)
            self.targets.append(obj)
        elif isinstance(obj, OutreachDraft):
            if obj.id is None:
                obj.id = len(self.drafts) + 1
            if obj.status is None:
                obj.status = "draft"
            if obj.approved is None:
                obj.approved = None
            obj.created_at = obj.created_at or datetime.now(timezone.utc)
            self.drafts.append(obj)

    def commit(self) -> None:
        return None

    def refresh(self, _obj: object) -> None:
        return None

    def query(self, model):
        if model is ThesisTarget:
            return _FakeQuery(self.targets)
        if model is OutreachDraft:
            return _FakeQuery(self.drafts)
        raise AssertionError(f"Unsupported model {model}")


def _matches_condition(item: object, condition: object) -> bool:
    if not hasattr(condition, "left") or not hasattr(condition, "right") or not hasattr(condition, "operator"):
        return True
    field = condition.left.key
    expected = getattr(condition.right, "value", None)
    actual = getattr(item, field)
    operator_name = getattr(condition.operator, "__name__", "")
    if operator_name == "eq":
        return actual == expected
    if operator_name == "ne":
        return actual != expected
    raise AssertionError(f"Unsupported operator {operator_name}")


def test_create_and_update_thesis_target():
    session = _FakeSession()

    created = create_thesis_target(
        ThesisTargetCreate(
            type="professor",
            name="Prof. Ada Lovelace",
            institution="PoliTo",
            country="Italy",
            research_area="MLOps",
            priority=2,
        ),
        db=session,
    )

    assert created.id == 1
    assert created.status == "identified"

    updated = update_thesis_target(
        1,
        ThesisTargetUpdate(status="email_drafted", notes="Relevant lab fit"),
        db=session,
    )

    assert updated.status == "email_drafted"
    assert updated.notes == "Relevant lab fit"


def test_archive_thesis_target_sets_archived_status():
    session = _FakeSession()
    target = ThesisTarget(
        id=1,
        type="lab",
        name="Systems Lab",
        institution="TU Munich",
        country="Germany",
        research_area="Distributed Systems",
        status="identified",
    )
    session.add(target)

    response = archive_thesis_target(1, db=session)

    assert isinstance(response, Response)
    assert response.status_code == 204
    assert target.status == "archived"


def test_approve_outreach_draft_updates_parent_target():
    session = _FakeSession()
    target = ThesisTarget(
        id=1,
        type="professor",
        name="Prof. Ada Lovelace",
        institution="PoliTo",
        country="Italy",
        research_area="Federated Learning",
        status="email_drafted",
    )
    approved = OutreachDraft(
        id=1,
        target_id=1,
        subject="Thesis inquiry",
        body_text="Hello",
        provider="lm_studio_writer",
    )
    older = OutreachDraft(
        id=2,
        target_id=1,
        subject="Old draft",
        body_text="Old",
        provider="lm_studio_writer",
        status="approved",
        approved=True,
    )
    session.add(target)
    session.add(approved)
    session.add(older)

    draft = approve_outreach_draft(1, db=session)

    assert draft.approved is True
    assert draft.status == "approved"
    assert older.approved is False
    assert older.status == "rejected"
    assert target.status == "email_approved"
