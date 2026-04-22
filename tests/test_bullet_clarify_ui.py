from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from job_agent.models import BulletClarification, Candidate, ExperienceFact, FactSource, ResumeDraft


def _create_draft(db_session, db_job, db_track) -> ResumeDraft:
    draft = ResumeDraft(
        id=uuid4(),
        job_post_id=db_job.id,
        resume_track_id=db_track.id,
        provider="test",
        status="drafted",
        score=80.0,
        content={
            "selected_experiences": [
                {
                    "title": "Data Engineer",
                    "company": "Acme Corp",
                    "bullets": ["Built pipelines."],
                }
            ],
            "selected_projects": [],
            "selected_skills": ["Python"],
        },
        review_feedback={},
        tex_path="fake.tex",
    )
    db_session.add(draft)
    db_session.commit()
    db_session.refresh(draft)
    return draft


def test_list_clarifications_empty(client, db_session, db_job, db_track):
    draft = _create_draft(db_session, db_job, db_track)

    response = client.get(f"/drafts/{draft.id}/clarifications")

    assert response.status_code == 200
    assert response.json() == []


def test_accept_clarification(client, db_session, db_job, db_track):
    draft = _create_draft(db_session, db_job, db_track)
    clarification = BulletClarification(
        id=uuid4(),
        draft_id=draft.id,
        original_bullet="Built pipelines.",
        suggested_rewrite="Built ETL pipelines reducing latency by 30%.",
        user_accepted=False,
        promoted_to_fact_sheet=False,
        target_section="experience",
        target_item_index=0,
        target_bullet_index=0,
        language_map={},
        questions=[],
        answers=[],
        rewritten_bullets={},
        status="complete",
    )
    db_session.add(clarification)
    db_session.commit()

    response = client.post(f"/drafts/clarifications/{clarification.id}/accept")

    assert response.status_code == 204
    db_session.refresh(clarification)
    db_session.refresh(draft)
    assert clarification.user_accepted is True
    assert draft.content["selected_experiences"][0]["bullets"][0] == "Built ETL pipelines reducing latency by 30%."


def test_api_clarify_endpoint_accepts_bullet_payload(client, db_session, db_job, db_track, monkeypatch):
    draft = _create_draft(db_session, db_job, db_track)
    fake = SimpleNamespace(id=uuid4(), suggested_rewrite="Built reliable ETL pipelines for recurring data loads.")
    monkeypatch.setattr(
        "job_agent.services.bullet_clarify.BulletClarifyService.suggest_bullet_rewrite",
        lambda self, draft_id, bullet, **kwargs: fake,
    )

    response = client.post(f"/drafts/{draft.id}/clarify", json={"bullet": "Built pipelines."})

    assert response.status_code == 200
    assert response.json() == {
        "id": str(fake.id),
        "suggested_rewrite": fake.suggested_rewrite,
    }


def test_ui_draft_detail_shows_bullet_rewrite_controls(client, db_session, db_job, db_track):
    draft = _create_draft(db_session, db_job, db_track)

    response = client.get(f"/ui/drafts/{draft.id}")

    assert response.status_code == 200
    assert "Bullet Rewrites" in response.text
    assert "✦ Rewrite" in response.text
    assert "Save for Future Drafts" in response.text


def test_promote_clarification_saves_track_bullets(client, db_session, db_job, db_track, monkeypatch):
    candidate = Candidate(full_name="Candidate User", email="candidate@example.com")
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)
    monkeypatch.setattr("job_agent.main.settings.default_candidate_id", candidate.id)

    source = FactSource(
        candidate_id=candidate.id,
        source_path="candidate://test/source.json",
        source_hash="hash",
        raw_content="{}",
    )
    db_session.add(source)
    db_session.flush()

    fact = ExperienceFact(
        candidate_id=candidate.id,
        fact_source_id=source.id,
        item_id="exp-1",
        section_name="experience",
        role_title="Data Engineer",
        organization="Acme Corp",
        verified_core_facts=["Built pipelines."],
        best_bullets_by_track={},
    )
    db_session.add(fact)
    draft = _create_draft(db_session, db_job, db_track)
    clarification = BulletClarification(
        id=uuid4(),
        draft_id=draft.id,
        original_bullet="Built pipelines.",
        suggested_rewrite="Built ETL pipelines reducing latency by 30%.",
        user_accepted=True,
        promoted_to_fact_sheet=False,
        target_section="experience",
        target_item_index=0,
        target_bullet_index=0,
        language_map={},
        questions=[],
        answers=[],
        rewritten_bullets={},
        status="complete",
    )
    draft.content["selected_experiences"][0]["bullets"][0] = clarification.suggested_rewrite
    db_session.add(clarification)
    db_session.commit()

    response = client.post(f"/drafts/clarifications/{clarification.id}/promote")

    assert response.status_code == 200
    db_session.refresh(clarification)
    db_session.refresh(fact)
    assert clarification.promoted_to_fact_sheet is True
    assert fact.best_bullets_by_track[db_track.slug] == [clarification.suggested_rewrite]
