from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from job_agent.models import ResumeDraft


def _make_draft(db_session, db_job, db_track, **overrides) -> ResumeDraft:
    values = {
        "id": uuid4(),
        "job_post_id": db_job.id,
        "resume_track_id": db_track.id,
        "provider": "test",
        "status": "drafted",
        "score": 81.0,
        "content": {},
        "review_feedback": {},
        "tex_path": "",
        "approved": False,
    }
    values.update(overrides)
    draft = ResumeDraft(**values)
    db_session.add(draft)
    db_session.commit()
    db_session.refresh(draft)
    return draft


def test_vue_draft_approve_missing_id_returns_contract_error(client):
    response = client.post(f"/api/vue/drafts/{uuid4()}/approve", json={"user_confirmed": True})

    assert response.status_code == 404
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "not_found"


def test_vue_draft_reject_missing_id_returns_contract_error(client):
    response = client.post(f"/api/vue/drafts/{uuid4()}/reject", json={"user_confirmed": True})

    assert response.status_code == 404
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "not_found"


def test_vue_draft_cover_letter_missing_id_returns_contract_error(client):
    response = client.post(f"/api/vue/drafts/{uuid4()}/cover-letter", json={})

    assert response.status_code == 404
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "not_found"


def test_vue_draft_approve_requires_confirmation(client, db_session, db_job, db_track):
    draft = _make_draft(db_session, db_job, db_track)

    response = client.post(f"/api/vue/drafts/{draft.id}/approve", json={"user_confirmed": False})

    assert response.status_code == 422
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "validation_error"


def test_vue_draft_approve_updates_status(client, db_session, db_job, db_track):
    draft = _make_draft(db_session, db_job, db_track)

    response = client.post(f"/api/vue/drafts/{draft.id}/approve", json={"user_confirmed": True})

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["draft_id"] == str(draft.id)
    assert payload["data"]["approved"] is True
    assert payload["data"]["status"] == "approved"


def test_vue_draft_reject_updates_status(client, db_session, db_job, db_track):
    draft = _make_draft(db_session, db_job, db_track, approved=True, status="approved")

    response = client.post(f"/api/vue/drafts/{draft.id}/reject", json={"user_confirmed": True})

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["draft_id"] == str(draft.id)
    assert payload["data"]["approved"] is False
    assert payload["data"]["status"] == "rejected"


def test_vue_draft_cover_letter_returns_contract_success(client, db_session, db_job, db_track, monkeypatch):
    draft = _make_draft(db_session, db_job, db_track)

    def fake_generate(self, draft_id):
        del self
        stored = db_session.get(ResumeDraft, draft_id)
        stored.cover_letter_subject = "Application for Data Engineer"
        stored.cover_letter_text = "Dear Hiring Team,\n\nThis is a Vue contract test cover letter."
        db_session.commit()
        db_session.refresh(stored)
        return stored

    monkeypatch.setattr("job_agent.services.cover_letter.CoverLetterService.generate_cover_letter", fake_generate)

    response = client.post(f"/api/vue/drafts/{draft.id}/cover-letter", json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["draft_id"] == str(draft.id)
    assert payload["data"]["subject"] == "Application for Data Engineer"
    assert "cover letter" in payload["data"]["cover_letter"].lower()


def test_draft_detail_source_contains_vue_draft_actions():
    source = Path("frontend/vue/src/pages/DraftDetailPage.vue").read_text()

    assert "Approve Draft" in source
    assert "Reject Draft" in source
    assert "Generate Cover Letter" in source
    assert "window.location.href" not in source
    assert 'window.location.href = "/ui/drafts/' not in source
    assert ":href=\"`/ui/drafts/${draftId}`\"" in source
    assert "Revise draft" in source
    assert "Polish draft" in source
    assert "Clarify bullets" in source
