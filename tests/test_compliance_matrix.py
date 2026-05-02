from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from job_agent.llm import ProviderUnavailableError
from job_agent.models import ResumeDraft
from job_agent.services.compliance_matrix import ComplianceMatrixService
from job_agent.services.prompts import build_compliance_matrix_prompt


def _create_draft(
    db_session,
    db_job,
    db_track,
    *,
    review_feedback: dict | None = None,
    content: dict | None = None,
) -> ResumeDraft:
    draft = ResumeDraft(
        id=uuid4(),
        job_post_id=db_job.id,
        resume_track_id=db_track.id,
        provider="test",
        status="drafted",
        score=80.0,
        content=content
        or {
            "professional_summary": "Built data platforms and MLOps pipelines.",
            "selected_skills": ["Python", "SQL", "Airflow"],
            "selected_experiences": [
                {
                    "title": "Data Engineer",
                    "company": "Acme",
                    "bullets": ["Built ETL pipelines using Python and Airflow."],
                }
            ],
            "selected_projects": [
                {"name": "Pipeline Project", "bullets": ["Implemented SQL quality checks."]}
            ],
        },
        review_feedback=review_feedback or {},
        tex_path="fake.tex",
    )
    db_session.add(draft)
    db_session.commit()
    db_session.refresh(draft)
    return draft


def test_generate_stores_matrix_in_review_feedback(
    db_session,
    db_job,
    db_profile,
    db_track,
    monkeypatch,
):
    del db_profile
    monkeypatch.setattr("job_agent.services.workflows.settings.default_candidate_id", "")
    draft = _create_draft(db_session, db_job, db_track)
    router = MagicMock()
    router.generate.return_value = {
        "requirements": [{"id": "r1", "requirement": "Python required", "coverage": "strong"}],
        "strong_count": 1,
        "partial_count": 0,
        "missing_count": 0,
        "coverage_pct": 100.0,
    }

    matrix = ComplianceMatrixService(db_session, router=router).generate(draft.id)

    db_session.refresh(draft)
    assert matrix["coverage_pct"] == 100.0
    assert draft.review_feedback["compliance_matrix"]["coverage_pct"] == 100.0


def test_generate_returns_empty_matrix_on_provider_error(
    db_session,
    db_job,
    db_profile,
    db_track,
    monkeypatch,
):
    del db_profile
    monkeypatch.setattr("job_agent.services.workflows.settings.default_candidate_id", "")
    draft = _create_draft(db_session, db_job, db_track)
    router = MagicMock()
    router.generate.side_effect = ProviderUnavailableError("offline")

    matrix = ComplianceMatrixService(db_session, router=router).generate(draft.id)

    assert matrix["coverage_pct"] == 0.0
    assert matrix["requirements"] == []


def test_generate_raises_for_missing_draft(db_session):
    with pytest.raises(ValueError, match="not found"):
        ComplianceMatrixService(db_session).generate(uuid4())


def test_compliance_matrix_prompt_includes_job_requirements():
    prompt = build_compliance_matrix_prompt(
        {"title": "Data Engineer", "company": "Acme", "description": "Python required. SQL required."},
        {
            "professional_summary": "",
            "selected_skills": [],
            "selected_experiences": [],
            "selected_projects": [],
        },
    )

    assert "Python required" in prompt


def test_compliance_matrix_prompt_filters_company_marketing_copy():
    prompt = build_compliance_matrix_prompt(
        {
            "title": "FP&A Analyst",
            "company": "AB Parfums",
            "description": (
                "Give Back Beauty.\n"
                "AB Parfums is a privately owned beauty group.\n"
                "About the role\n"
                "Support annual budgeting and periodic forecasting processes.\n"
                "Analyze variances between actuals, budget, and forecast.\n"
                "Excellent proficiency in Excel and Power BI.\n"
            ),
        },
        {
            "professional_summary": "",
            "selected_skills": [],
            "selected_experiences": [],
            "selected_projects": [],
        },
    )

    assert "Support annual budgeting" in prompt
    assert "Analyze variances between actuals" in prompt
    assert "Give Back Beauty" not in prompt


def test_get_endpoint_returns_404_when_not_generated(client, db_session, db_job, db_track):
    draft = _create_draft(db_session, db_job, db_track, review_feedback={})

    response = client.get(f"/drafts/{draft.id}/compliance-matrix")

    assert response.status_code == 404
    assert "not yet generated" in response.json()["detail"]


def test_get_endpoint_returns_matrix_when_exists(client, db_session, db_job, db_track):
    draft = _create_draft(
        db_session,
        db_job,
        db_track,
        review_feedback={"compliance_matrix": {"coverage_pct": 80.0}},
    )

    response = client.get(f"/drafts/{draft.id}/compliance-matrix")

    assert response.status_code == 200
    assert response.json()["coverage_pct"] == 80.0


def test_post_endpoint_generates_and_returns_matrix(client, db_session, db_job, db_track, monkeypatch):
    draft = _create_draft(db_session, db_job, db_track)
    expected = {
        "requirements": [],
        "strong_count": 0,
        "partial_count": 0,
        "missing_count": 0,
        "coverage_pct": 0.0,
    }
    monkeypatch.setattr(
        "job_agent.services.compliance_matrix.ComplianceMatrixService.generate",
        lambda self, draft_id: expected,
    )

    response = client.post(f"/drafts/{draft.id}/compliance-matrix")

    assert response.status_code == 200
    assert {"requirements", "coverage_pct"} <= response.json().keys()
