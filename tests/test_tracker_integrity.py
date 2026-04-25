from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid

from job_agent.models import Application, CareerPageSource, JobPost, ResumeDraft


def test_system_integrity_empty_workspace_is_healthy(client):
    response = client.get("/system/integrity")

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["issue_count"] == 0


def test_system_integrity_repairs_job_status_drift(client, db_session):
    job = JobPost(
        id=uuid.uuid4(),
        company="DriftCo",
        title="Architect",
        description="Architecture role with stakeholder management and delivery leadership.",
        source_name="manual",
        source_url="https://example.com/architect",
        canonical_apply_url="https://example.com/architect",
        status="new",
        queue_state="new",
        created_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    db_session.add(job)
    db_session.commit()

    application = Application(job_post_id=job.id, status="applied")
    db_session.add(application)
    db_session.commit()

    before = client.get("/system/integrity").json()
    assert any(issue["code"] == "job_status_drift" for issue in before["issues"])

    repair = client.post("/system/integrity/repair")
    assert repair.status_code == 200

    db_session.refresh(job)
    assert job.status == "applied"
    assert job.queue_state == "shortlisted"


def test_system_integrity_detects_missing_draft_artifacts(client, db_session, db_job, db_track):
    draft = ResumeDraft(
        id=uuid.uuid4(),
        job_post_id=db_job.id,
        resume_track_id=db_track.id,
        provider="test",
        status="drafted",
        score=80,
        content={},
        review_feedback={},
        tex_path="/tmp/does-not-exist-job-agent.tex",
    )
    db_session.add(draft)
    db_session.commit()

    response = client.get("/system/integrity")

    assert response.status_code == 200
    issues = response.json()["issues"]
    assert any(issue["code"] == "missing_draft_artifacts" for issue in issues)


def test_system_integrity_detects_stale_sources(client, db_session):
    source = CareerPageSource(
        company="OldScanner",
        career_url="https://example.com/jobs",
        active=True,
        last_checked_at=datetime.now(timezone.utc) - timedelta(days=20),
    )
    db_session.add(source)
    db_session.commit()

    response = client.get("/system/integrity")

    assert response.status_code == 200
    issues = response.json()["issues"]
    assert any(issue["code"] == "stale_sources" for issue in issues)
