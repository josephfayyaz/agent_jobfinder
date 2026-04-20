from __future__ import annotations

from uuid import uuid4

from job_agent.models import ResumeDraft


def test_ui_draft_detail_returns_200(client, db_session, db_job, db_track):
    draft = ResumeDraft(
        id=uuid4(),
        job_post_id=db_job.id,
        resume_track_id=db_track.id,
        provider="test",
        status="drafted",
        score=80.0,
        content={
            "professional_summary": "Test summary",
            "selected_skills": ["Python"],
            "selected_experiences": [],
            "selected_projects": [],
        },
        review_feedback={},
        tex_path="",
    )
    db_session.add(draft)
    db_session.commit()

    response = client.get(f"/ui/drafts/{draft.id}")

    assert response.status_code == 200
    assert "Test summary" in response.text


def test_ui_draft_detail_returns_404_for_unknown(client):
    response = client.get(f"/ui/drafts/{uuid4()}")
    assert response.status_code == 404


def test_ui_draft_detail_shows_compliance_matrix(client, db_session, db_job, db_track):
    draft = ResumeDraft(
        id=uuid4(),
        job_post_id=db_job.id,
        resume_track_id=db_track.id,
        provider="test",
        status="drafted",
        score=85.0,
        content={},
        review_feedback={
            "compliance_matrix": {
                "requirements": [{"id": "r1", "requirement": "Python required", "coverage": "strong"}],
                "strong_count": 1,
                "partial_count": 0,
                "missing_count": 0,
                "coverage_pct": 100.0,
            }
        },
        tex_path="",
    )
    db_session.add(draft)
    db_session.commit()

    response = client.get(f"/ui/drafts/{draft.id}")

    assert response.status_code == 200
    assert "100" in response.text
    assert "Python required" in response.text


def test_ui_draft_detail_shows_generate_button_when_no_matrix(client, db_session, db_job, db_track):
    draft = ResumeDraft(
        id=uuid4(),
        job_post_id=db_job.id,
        resume_track_id=db_track.id,
        provider="test",
        status="drafted",
        score=70.0,
        content={},
        review_feedback={},
        tex_path="",
    )
    db_session.add(draft)
    db_session.commit()

    response = client.get(f"/ui/drafts/{draft.id}")

    assert response.status_code == 200
    assert "compliance-matrix" in response.text
