from __future__ import annotations

from uuid import uuid4

from job_agent.models import ResumeDraft


def test_ui_draft_detail_returns_200(client, db_session, db_job, db_track, db_profile):
    del db_profile
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
    assert "Profile Readiness" in response.text
    assert "Target Fit Map" in response.text


def test_ui_draft_detail_returns_404_for_unknown(client):
    response = client.get(f"/ui/drafts/{uuid4()}")
    assert response.status_code == 404


def test_ui_draft_detail_shows_compliance_matrix(client, db_session, db_job, db_track, db_profile):
    del db_profile
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


def test_ui_draft_detail_shows_token_usage_when_present(client, db_session, db_job, db_track, db_profile):
    del db_profile
    draft = ResumeDraft(
        id=uuid4(),
        job_post_id=db_job.id,
        resume_track_id=db_track.id,
        provider="test",
        status="drafted",
        score=84.0,
        content={},
        review_feedback={
            "token_usage": {
                "provider": "gemini",
                "keyword_extractor": 12,
                "writer": 40,
                "reviewer": 18,
                "reviser": 0,
                "total": 70,
            }
        },
        tex_path="",
    )
    db_session.add(draft)
    db_session.commit()

    response = client.get(f"/ui/drafts/{draft.id}")

    assert response.status_code == 200
    assert "Token Usage" in response.text
    assert "70 tokens" in response.text


def test_ui_draft_detail_shows_generate_button_when_no_matrix(client, db_session, db_job, db_track, db_profile):
    del db_profile
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


def test_ui_draft_detail_handles_project_bullets_without_loop_parent_crash(client, db_session, db_job, db_track, db_profile):
    del db_profile
    draft = ResumeDraft(
        id=uuid4(),
        job_post_id=db_job.id,
        resume_track_id=db_track.id,
        provider="test",
        status="drafted",
        score=82.0,
        content={
            "selected_projects": [
                {
                    "name": "Evidence Project",
                    "bullets": ["Built KPI dashboards", "Automated reporting checks"],
                }
            ],
        },
        review_feedback={},
        tex_path="",
    )
    db_session.add(draft)
    db_session.commit()

    response = client.get(f"/ui/drafts/{draft.id}")

    assert response.status_code == 200
    assert "Evidence Project" in response.text
    assert "Built KPI dashboards" in response.text


def test_draft_pdf_inline_route_uses_inline_preview(client, db_session, db_job, db_track, db_profile, monkeypatch, tmp_path):
    del db_profile
    draft = ResumeDraft(
        id=uuid4(),
        job_post_id=db_job.id,
        resume_track_id=db_track.id,
        provider="test",
        status="drafted",
        score=82.0,
        content={},
        review_feedback={},
        tex_path="fake.tex",
    )
    db_session.add(draft)
    db_session.commit()

    pdf_path = tmp_path / "fake-preview.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%fake\n")

    monkeypatch.setattr("job_agent.services.documents.compile_pdf", lambda _tex_path: str(pdf_path))

    response = client.get(f"/drafts/{draft.id}/pdf-inline")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.headers["content-disposition"].startswith("inline;")
