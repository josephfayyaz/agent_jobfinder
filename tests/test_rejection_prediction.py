from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from job_agent.llm import ProviderUnavailableError
from job_agent.services.rejection_prediction import RejectionPredictionService


def test_predict_returns_risks_with_correct_shape(
    db_session,
    db_job,
    db_profile,
    db_track,
    monkeypatch,
):
    del db_profile
    monkeypatch.setattr("job_agent.services.workflows.settings.default_candidate_id", "")
    router = MagicMock()
    router.generate.return_value = {
        "risks": [
            {
                "type": "soft_blocker",
                "factor": "Keyword mismatch",
                "evidence": "JD asks for Kubernetes, draft does not mention it",
                "confidence": "medium",
                "mitigable": True,
                "suggestion": "Add validated Kubernetes evidence in bullets",
            }
        ],
        "hard_blocker_count": 0,
        "soft_blocker_count": 1,
        "overall_risk": "medium",
        "recommendation": "Apply with preparation",
    }

    result = RejectionPredictionService(db_session, router=router).predict(db_job.id)

    assert {"risks", "overall_risk", "recommendation"} <= result.keys()


def test_predict_stores_result_in_extracted_metadata(
    db_session,
    db_job,
    db_profile,
    db_track,
    monkeypatch,
):
    del db_profile
    monkeypatch.setattr("job_agent.services.workflows.settings.default_candidate_id", "")
    router = MagicMock()
    router.generate.return_value = {
        "risks": [],
        "hard_blocker_count": 0,
        "soft_blocker_count": 0,
        "overall_risk": "low",
        "recommendation": "Apply",
    }

    RejectionPredictionService(db_session, router=router).predict(db_job.id)
    db_session.refresh(db_job)

    assert "rejection_risks" in (db_job.extracted_metadata or {})


def test_predict_returns_empty_risks_on_provider_error(
    db_session,
    db_job,
    db_profile,
    db_track,
    monkeypatch,
):
    del db_profile
    monkeypatch.setattr("job_agent.services.workflows.settings.default_candidate_id", "")
    router = MagicMock()
    router.generate.side_effect = ProviderUnavailableError("offline")

    result = RejectionPredictionService(db_session, router=router).predict(db_job.id)

    assert result["error"] == "provider_unavailable"
    assert result["risks"] == []


def test_predict_raises_for_missing_job(db_session):
    with pytest.raises(ValueError, match="not found"):
        RejectionPredictionService(db_session).predict(uuid4())


def test_post_endpoint_returns_200_with_prediction(client, db_job, monkeypatch):
    monkeypatch.setattr(
        "job_agent.services.rejection_prediction.RejectionPredictionService.predict",
        lambda self, job_post_id: {
            "risks": [],
            "hard_blocker_count": 0,
            "soft_blocker_count": 0,
            "overall_risk": "low",
            "recommendation": "Apply",
        },
    )

    response = client.post(f"/jobs/{db_job.id}/rejection-risk")

    assert response.status_code == 200
    assert "overall_risk" in response.json()


def test_get_endpoint_returns_404_when_no_prediction(client, db_job):
    response = client.get(f"/jobs/{db_job.id}/rejection-risk")

    assert response.status_code == 404
    assert "No prediction generated" in response.json()["detail"]


def test_get_endpoint_returns_stored_prediction(client, db_session, db_job):
    db_job.extracted_metadata = {"rejection_risks": {"overall_risk": "low"}}
    db_session.commit()

    response = client.get(f"/jobs/{db_job.id}/rejection-risk")

    assert response.status_code == 200
    assert response.json()["overall_risk"] == "low"
