from __future__ import annotations

import json
import uuid
from unittest.mock import MagicMock


def test_fit_gaps_endpoint_returns_empty_without_candidate(client):
    resp = client.get(f"/jobs/{uuid.uuid4()}/fit-gaps")
    assert resp.status_code == 200
    data = resp.json()
    assert "rows" in data
    assert data["rows"] == []


def test_fit_gaps_clear_endpoint(client, db_session):
    from job_agent.models import JobPost

    job = JobPost(
        id=uuid.uuid4(),
        title="ML Engineer",
        company="TestCo",
        description="Python ML role",
        extracted_metadata={"fit_gaps": {"rows": [{"fit_level": "Strong"}], "summary": {}}},
    )
    db_session.add(job)
    db_session.commit()

    resp = client.post(f"/jobs/{job.id}/fit-gaps/clear")
    assert resp.status_code == 200
    assert resp.json()["cleared"] is True

    db_session.refresh(job)
    assert "fit_gaps" not in (job.extracted_metadata or {})


def test_fit_gap_service_caches_on_second_call(db_session):
    """Second call returns cached result without calling the LLM again."""
    from job_agent.models import Candidate, JobPost
    from job_agent.services.fit_gap import FitGapService

    candidate_id = str(uuid.uuid4())
    candidate = Candidate(id=candidate_id, full_name="Test User")
    job = JobPost(id=uuid.uuid4(), title="Data Engineer", company="Co", description="Python, dbt, Airflow")
    db_session.add_all([candidate, job])
    db_session.commit()

    mock_router = MagicMock()
    mock_router.generate.return_value = '[{"requirement":"Python","evidence":"Used Python","fit_level":"Strong"}]'

    svc = FitGapService(session=db_session, router=mock_router)
    r1 = svc.get_or_compute(job_id=job.id, candidate_id=candidate_id)
    r2 = svc.get_or_compute(job_id=job.id, candidate_id=candidate_id)

    assert mock_router.generate.call_count == 1
    assert r1 == r2
    assert len(r1["rows"]) == 1
    assert r1["rows"][0]["fit_level"] == "Strong"
    assert r1["rows"][0]["fit_emoji"] == "✅"
    assert r1["rows"][0]["best_next_move"] == "Include Now"
    assert r1["rows"][0]["draft_readiness"] == "Include Now"


def test_fit_gap_service_handles_llm_failure(db_session):
    from job_agent.llm import ProviderUnavailableError
    from job_agent.models import Candidate, JobPost
    from job_agent.services.fit_gap import FitGapService

    candidate_id = str(uuid.uuid4())
    candidate = Candidate(id=candidate_id, full_name="Test User")
    job = JobPost(id=uuid.uuid4(), title="SWE", company="Co", description="Java")
    db_session.add_all([candidate, job])
    db_session.commit()

    mock_router = MagicMock()
    mock_router.generate.side_effect = ProviderUnavailableError("LM Studio down")

    svc = FitGapService(session=db_session, router=mock_router)
    result = svc.get_or_compute(job_id=job.id, candidate_id=candidate_id)
    assert result["rows"] == []


def test_fit_gap_rows_sorted_missing_first(db_session):
    from job_agent.models import Candidate, JobPost
    from job_agent.services.fit_gap import FitGapService

    candidate_id = str(uuid.uuid4())
    db_session.add_all(
        [
            Candidate(id=candidate_id, full_name="Test"),
            JobPost(id=uuid.uuid4(), title="Analyst", company="Co", description="SQL Python R"),
        ]
    )
    db_session.commit()
    job = db_session.query(JobPost).filter_by(title="Analyst").one()

    mock_router = MagicMock()
    mock_router.generate.return_value = json.dumps(
        [
            {"requirement": "Python", "evidence": "Used Python 3 years", "fit_level": "Strong"},
            {"requirement": "R", "evidence": "Nothing yet", "fit_level": "Missing"},
            {"requirement": "SQL", "evidence": "Some SQL", "fit_level": "Close"},
        ]
    )

    svc = FitGapService(session=db_session, router=mock_router)
    result = svc.get_or_compute(job_id=job.id, candidate_id=candidate_id)
    fit_levels = [row["fit_level"] for row in result["rows"]]
    assert fit_levels[0] == "Missing"
    assert fit_levels[-1] == "Strong"


def test_fit_gaps_htmx_returns_partial_without_candidate(client):
    resp = client.get(
        f"/jobs/{uuid.uuid4()}/fit-gaps",
        headers={"HX-Request": "true"},
    )
    assert resp.status_code == 200
    assert "Role Readiness" not in resp.text
    assert "No readiness map yet" in resp.text
