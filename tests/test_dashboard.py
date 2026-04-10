from __future__ import annotations

from datetime import datetime, timezone

from job_agent.models import JobPost


def test_dashboard_returns_expected_keys(client):
    """GET /dashboard returns all expected top-level keys."""
    response = client.get("/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "jobs" in data
    assert "cv" in data
    assert "thesis" in data
    assert "applications" in data
    assert "config" in data
    assert "system" in data


def test_dashboard_config_has_seniority(client):
    """Dashboard config section includes target_seniority."""
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert response.json()["config"]["target_seniority"] == "junior"


def test_dashboard_jobs_new_24h_counts_correctly(client, db_session):
    """new_24h count increments when a new job is added."""
    db_session.add(
        JobPost(
            title="New Job",
            company="Test",
            status="new",
            description="",
            created_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert response.json()["jobs"]["new_24h"] >= 1
