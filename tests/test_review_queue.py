from __future__ import annotations

from datetime import datetime, timezone
import uuid

from job_agent.models import Application, Candidate, JobPost, WorkflowTask
from job_agent.services.job_signals import JobSignalService


def _job(*, company: str, title: str, queue_state: str = "new", status: str = "new") -> JobPost:
    now = datetime.now(timezone.utc)
    return JobPost(
        id=uuid.uuid4(),
        company=company,
        title=title,
        description=(
            "We are hiring for a strong analytics role. "
            "Responsibilities: lead production workflows, build Python and SQL pipelines, and improve reporting quality. "
            "Requirements: hands-on analytics ownership, data pipeline experience, and stakeholder collaboration. "
            "Qualifications: proven delivery in production environments. "
        ) * 2,
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

    assert response.status_code == 200
    assert f'id="job-group-{job.id}"' in response.text
    db_session.refresh(job)
    assert job.queue_state == "shortlisted"
    assert job.status == "reviewed"


def test_ui_queue_state_removes_row_when_job_leaves_current_lane(client, db_session):
    job = _job(company="QueueCo", title="Backend Engineer")
    db_session.add(job)
    db_session.commit()

    response = client.post(
        f"/ui/jobs/{job.id}/queue-state?state=shortlisted",
        headers={"HX-Current-URL": "http://testserver/ui/jobs?lane=review"},
    )

    assert response.status_code == 200
    assert f'id="job-group-{job.id}"' not in response.text
    assert 'id="jobs-queue-controls" hx-swap-oob="outerHTML"' in response.text
    assert 'id="jobs-queue-table" hx-swap-oob="outerHTML"' in response.text


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


def test_job_signal_service_uses_posted_date_for_stale_freshness(db_session):
    job = _job(company="StaleCo", title="Planner")
    job.posted_date = "2026-03-01T10:00:00Z"
    db_session.add(job)
    db_session.commit()

    payload = JobSignalService(db_session).evaluate_many([job])[job.id]

    assert payload["freshness"]["label"] == "Stale listing"
    assert payload["freshness"]["title"].startswith("Posted about ")


def test_ui_discover_jobs_returns_actionable_message_when_disabled(client, monkeypatch):
    from job_agent.config import settings

    monkeypatch.setattr(settings, "use_jobspy", False)
    response = client.post("/ui/jobs/discover")

    assert response.status_code == 409
    assert "X-Toast-Error" in response.headers


def test_awaiting_enrichment_lane_surfaces_unscored_jobs(client, db_session, monkeypatch):
    import job_agent.config as cfg

    candidate = Candidate(
        id=str(uuid.uuid4()),
        full_name="Awaiting User",
        spoken_languages=[{"name": "English", "level": "C1"}],
    )
    db_session.add(candidate)
    db_session.commit()
    monkeypatch.setattr(cfg.settings, "default_candidate_id", candidate.id, raising=False)

    job = _job(company="ThinJDCo", title="Operations Analyst")
    job.extracted_metadata = {
        "candidate_fit": {
            candidate.id: {
                "fit_score": 31,
                "score_source": "awaiting_enrichment",
                "provider_mode": "lm_studio",
                "language_assessment": {"label": "unknown", "reason": "Pending stronger JD."},
                "seniority_assessment": {"label": "unknown", "reason": "Pending stronger JD."},
                "short_reason": "Job description is too weak for provider scoring; awaiting stronger enrichment.",
                "threshold_eligible": False,
                "awaiting_enrichment": True,
            }
        }
    }
    db_session.add(job)
    db_session.commit()

    response = client.get("/ui/jobs?lane=awaiting")

    assert response.status_code == 200
    assert "ThinJDCo" in response.text
    assert "Awaiting enrichment" in response.text


def test_jobs_ui_shows_discovery_awaiting_summary_counts(client, db_session, monkeypatch):
    monkeypatch.setattr("job_agent.routers.jobs._redirect_if_setup_required", lambda _request, _db: None)
    task = WorkflowTask(
        kind="job_discovery",
        status="completed",
        result={
            "stage": "completed_awaiting_enrichment",
            "message": "Discovery completed. 2 jobs need stronger descriptions before they can clear the fit threshold. Check the Awaiting enrichment lane.",
            "counts": {
                "roles_queried": 2,
                "raw_hits": 12,
                "ats_sources_scanned": 3,
                "ats_raw_hits": 4,
                "duplicates": 1,
                "rejected_by_country": 1,
                "rejected_by_role": 2,
                "rejected_by_seniority": 1,
                "scored_jobs": 5,
                "awaiting_enrichment_count": 2,
                "provider_scored_count": 2,
                "fallback_scored_count": 1,
                "ready_for_threshold_count": 3,
                "saved_jobs": 5,
                "visible_after_threshold": 1,
                "visible_in_default_view": 1,
            },
        },
    )
    db_session.add(task)
    db_session.commit()

    response = client.get("/ui/jobs")

    assert response.status_code == 200
    assert "Completed with jobs awaiting enrichment" in response.text
    assert "Awaiting enrichment: 2" in response.text
    assert "Provider scored: 2" in response.text
    assert "Ready for threshold: 3" in response.text
