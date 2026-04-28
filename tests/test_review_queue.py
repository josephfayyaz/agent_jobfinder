from __future__ import annotations

from datetime import datetime, timezone
import uuid

from job_agent.models import Application, JobPost
from job_agent.services.job_signals import JobSignalService


def _job(*, company: str, title: str, queue_state: str = "new", status: str = "new") -> JobPost:
    now = datetime.now(timezone.utc)
    return JobPost(
        id=uuid.uuid4(),
        company=company,
        title=title,
        description="This role needs Python, SQL, pipelines, and analytics ownership across production workflows.",
        source_name="manual",
        source_url=f"https://example.com/{company.lower()}",
        canonical_apply_url=f"https://example.com/{company.lower()}",
        created_at=now,
        last_seen_at=now,
        queue_state=queue_state,
        status=status,
    )


def test_jobs_ui_filters_by_review_lane(client, db_session):
    jobs = [
        _job(company="ReviewCo", title="Data Engineer", queue_state="new"),
        _job(company="ShortlistCo", title="ML Engineer", queue_state="shortlisted", status="reviewed"),
        _job(company="SavedCo", title="Architect", queue_state="saved", status="reviewed"),
    ]
    db_session.add_all(jobs)
    db_session.commit()

    response = client.get("/ui/jobs?lane=review&show_all=true&min_score=0")

    assert response.status_code == 200
    assert "ReviewCo" in response.text
    assert "ShortlistCo" not in response.text
    assert "SavedCo" not in response.text
    assert "New for you" in response.text


def test_ui_queue_state_endpoint_updates_job(client, db_session):
    job = _job(company="QueueCo", title="Backend Engineer")
    db_session.add(job)
    db_session.commit()

    response = client.post(f"/ui/jobs/{job.id}/queue-state?state=shortlisted")

    assert response.status_code == 204
    db_session.refresh(job)
    assert job.queue_state == "shortlisted"
    assert job.status == "reviewed"


def test_queue_cv_blocks_dead_apply_link(client, db_session, db_track, monkeypatch):
    job = _job(company="DeadLinkCo", title="Software Developer")
    db_session.add(job)
    db_session.commit()

    monkeypatch.setattr(
        JobSignalService,
        "refresh_apply_link_check",
        lambda self, _job, force=False: {"status": "unavailable", "label": "Link unavailable"},
    )

    response = client.post(f"/ui/jobs/{job.id}/queue-cv?resume_track_slug={db_track.slug}")

    assert response.status_code == 409
    assert response.headers["X-Toast-Error"]


def test_applied_lane_uses_application_presence(client, db_session):
    job = _job(company="AppliedCo", title="Accountant", queue_state="new")
    db_session.add(job)
    db_session.commit()

    application = Application(job_post_id=job.id, status="applied")
    db_session.add(application)
    db_session.commit()

    response = client.get("/ui/jobs?lane=applied&show_all=true&min_score=0")

    assert response.status_code == 200
    assert "AppliedCo" in response.text


def test_job_signal_service_marks_fresh_jobs_as_recently_imported(db_session):
    job = _job(company="SignalCo", title="Material Engineer")
    db_session.add(job)
    db_session.commit()

    payload = JobSignalService(db_session).evaluate_many([job])[job.id]

    assert payload["freshness"]["label"] == "Fresh"
    assert payload["confidence"]["label"] in {"Recently imported", "Needs verification"}
    assert payload["suspicion"]["label"] in {"Looks credible", "Needs verification"}


def test_ui_discover_jobs_returns_actionable_message_when_disabled(client, monkeypatch):
    from job_agent.config import settings

    monkeypatch.setattr(settings, "use_jobspy", False)
    response = client.post("/ui/jobs/discover")

    assert response.status_code == 409
    assert "X-Toast-Error" in response.headers
