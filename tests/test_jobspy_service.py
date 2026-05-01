"""Tests for the JobSpy selective second-pass detail enrichment (Phase E2)."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from job_agent.models import JobPost
from job_agent.services.jobspy_service import JobSpyService


# ── Helpers ──────────────────────────────────────────────────────────────

class FakeDataFrame:
    """Minimal DataFrame stand-in for tests that don't need pandas."""

    def __init__(self, rows: list[dict]):
        self._rows = rows

    @property
    def empty(self) -> bool:
        return not self._rows

    def __len__(self) -> int:
        return len(self._rows)

    def iterrows(self):
        for index, row in enumerate(self._rows):
            yield index, row


def _make_job(
    session,
    *,
    title: str = "Data Engineer",
    company: str = "Acme",
    location: str = "Milan, Italy",
    description: str = "short",
    source_name: str = "jobspy_linkedin",
    source_url: str | None = None,
    enrichment_status: str = "pending",
) -> JobPost:
    job = JobPost(
        id=uuid4(),
        title=title,
        company=company,
        location=location,
        description=description,
        source_name=source_name,
        source_url=source_url or f"https://linkedin.com/jobs/{uuid4().hex[:8]}",
        canonical_apply_url=source_url or f"https://linkedin.com/jobs/{uuid4().hex[:8]}",
        queue_state="new",
        status="new",
        enrichment_status=enrichment_status,
        created_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    session.add(job)
    session.flush()
    return job


# ── Test: second pass is skipped when disabled ───────────────────────────

def test_detail_enrichment_skipped_when_disabled(db_session, monkeypatch):
    """When JOBSPY_DETAIL_ENRICHMENT_ENABLED=false, the second pass returns zeros."""
    monkeypatch.setattr(
        "job_agent.services.jobspy_service.settings.jobspy_detail_enrichment_enabled",
        False,
        raising=False,
    )
    job = _make_job(db_session, description="short description")
    result = JobSpyService().detail_enrich_survivors(
        saved_job_ids=[str(job.id)],
        session=db_session,
        selected_country="Italy",
        seniority="junior",
    )
    assert result["detail_enrichment_attempted"] == 0
    assert result["detail_enrichment_improved"] == 0
    assert result["detail_enrichment_skipped"] == 0
    assert result["detail_enrichment_failed"] == 0


# ── Test: second pass is capped ──────────────────────────────────────────

def test_detail_enrichment_is_capped(db_session, monkeypatch):
    """The second-pass should not enrich more jobs than the configured limit."""
    monkeypatch.setattr(
        "job_agent.services.jobspy_service.settings.jobspy_detail_enrichment_enabled",
        True,
        raising=False,
    )
    monkeypatch.setattr(
        "job_agent.services.jobspy_service.settings.jobspy_detail_enrichment_limit",
        2,
        raising=False,
    )
    monkeypatch.setattr(
        "job_agent.services.jobspy_service.settings.jobspy_request_delay",
        0.0,
        raising=False,
    )

    # Create 5 weak-JD jobs
    jobs = [
        _make_job(db_session, title=f"Role {i}", description="tiny")
        for i in range(5)
    ]
    db_session.commit()

    rich_desc = "This is a comprehensive data engineering role. " * 20

    def _fake_scrape_jobs(**kwargs):
        return FakeDataFrame([{
            "job_url": "https://linkedin.com/jobs/enriched",
            "title": "Role 0",
            "description": rich_desc,
        }])

    monkeypatch.setitem(sys.modules, "jobspy", SimpleNamespace(scrape_jobs=_fake_scrape_jobs))
    monkeypatch.setattr(
        "job_agent.services.jobspy_service.importlib.metadata.packages_distributions",
        lambda: {"jobspy": ["python-jobspy"]},
    )

    result = JobSpyService().detail_enrich_survivors(
        saved_job_ids=[str(j.id) for j in jobs],
        session=db_session,
        selected_country="Italy",
        seniority="junior",
    )

    # At most 2 should be attempted (cap = 2)
    assert result["detail_enrichment_attempted"] <= 2


# ── Test: strong ATS jobs are not redundantly re-enriched ────────────────

def test_strong_ats_jobs_are_skipped(db_session, monkeypatch):
    """Jobs that already have a ready-for-scoring description should be skipped."""
    monkeypatch.setattr(
        "job_agent.services.jobspy_service.settings.jobspy_detail_enrichment_enabled",
        True,
        raising=False,
    )
    monkeypatch.setattr(
        "job_agent.services.jobspy_service.settings.jobspy_detail_enrichment_limit",
        10,
        raising=False,
    )

    # Create an ATS-origin job with a strong description
    strong_desc = (
        "Requirements: Python, SQL, ETL pipelines. "
        "Qualifications: 2+ years of experience. "
        "Responsibilities: design data infrastructure. "
    ) * 10
    job = _make_job(
        db_session,
        description=strong_desc,
        source_name="ats_greenhouse",
    )
    db_session.commit()

    result = JobSpyService().detail_enrich_survivors(
        saved_job_ids=[str(job.id)],
        session=db_session,
        selected_country="Italy",
        seniority="junior",
    )

    # Strong ATS description → skipped, not attempted
    assert result["detail_enrichment_skipped"] >= 1
    assert result["detail_enrichment_attempted"] == 0


# ── Test: richer description replaces thin LinkedIn snippet ──────────────

def test_richer_description_replaces_thin_snippet(db_session, monkeypatch):
    """When the second pass finds a richer description, it replaces the thin one."""
    monkeypatch.setattr(
        "job_agent.services.jobspy_service.settings.jobspy_detail_enrichment_enabled",
        True,
        raising=False,
    )
    monkeypatch.setattr(
        "job_agent.services.jobspy_service.settings.jobspy_detail_enrichment_limit",
        5,
        raising=False,
    )
    monkeypatch.setattr(
        "job_agent.services.jobspy_service.settings.jobspy_request_delay",
        0.0,
        raising=False,
    )

    original_url = "https://linkedin.com/jobs/thin-jd"
    job = _make_job(
        db_session,
        title="Data Engineer",
        description="Short LinkedIn snippet.",
        source_url=original_url,
    )
    db_session.commit()

    rich_desc = (
        "We are looking for a Data Engineer to join our team. "
        "Requirements: Python, SQL, dbt, Airflow. "
        "Qualifications: Bachelor's degree in CS or related field. "
        "Responsibilities: build and maintain data pipelines. "
    ) * 8

    def _fake_scrape_jobs(**kwargs):
        assert kwargs.get("linkedin_fetch_description") is True
        return FakeDataFrame([{
            "job_url": original_url,
            "title": "Data Engineer",
            "description": rich_desc,
        }])

    monkeypatch.setitem(sys.modules, "jobspy", SimpleNamespace(scrape_jobs=_fake_scrape_jobs))
    monkeypatch.setattr(
        "job_agent.services.jobspy_service.importlib.metadata.packages_distributions",
        lambda: {"jobspy": ["python-jobspy"]},
    )

    result = JobSpyService().detail_enrich_survivors(
        saved_job_ids=[str(job.id)],
        session=db_session,
        selected_country="Italy",
        seniority="junior",
    )

    assert result["detail_enrichment_improved"] == 1
    assert result["detail_enrichment_attempted"] == 1

    db_session.refresh(job)
    assert len(job.description) > 120
    assert "Requirements" in job.description

    # Provenance stamps
    metadata = dict(job.extracted_metadata or {})
    assert metadata.get("jobspy_detail_enriched") is True
    assert "jobspy_detail_enriched_at" in metadata
    assert metadata.get("direct_job_url") == original_url


# ── Test: discovery progress records the detail-enrichment stage ─────────

def test_discovery_progress_records_detail_enrichment_stage(db_session, monkeypatch):
    """The discovery pipeline should record detail_enrichment stage progress."""
    from job_agent.models import Candidate, WorkflowTask
    from job_agent.services.workflows import CVWorkflowService

    candidate = Candidate(full_name="Test User", email="test@example.test", active=True)
    db_session.add(candidate)
    db_session.commit()

    monkeypatch.setattr("job_agent.services.workflows.settings.use_jobspy", True, raising=False)
    monkeypatch.setattr("job_agent.services.workflows.settings.default_candidate_id", candidate.id, raising=False)
    monkeypatch.setattr("job_agent.services.workflows.settings.discovery_min_fit_score", 70, raising=False)
    monkeypatch.setattr("job_agent.services.workflows.settings.discovery_max_visible_jobs", 80, raising=False)

    # Track what stages are persisted
    persisted_stages: list[str] = []
    original_persist = CVWorkflowService._persist_discovery_progress

    def _tracking_persist(self, task, payload, *, stage, message, counts):
        persisted_stages.append(stage)
        original_persist(self, task, payload, stage=stage, message=message, counts=counts)

    monkeypatch.setattr(
        "job_agent.services.workflows.CVWorkflowService._persist_discovery_progress",
        _tracking_persist,
    )

    job = _make_job(db_session, description="thin snippet")
    db_session.commit()

    def _discover_for_roles(self, **_kwargs):
        return {
            "roles_queried": 1,
            "raw_hits": 1,
            "duplicates": 0,
            "rejected_by_country": 0,
            "rejected_by_role": 0,
            "rejected_by_seniority": 0,
            "queued_for_scoring": 1,
            "saved_jobs": 1,
            "saved_job_ids": [str(job.id)],
        }

    def _detail_enrich_survivors(self, **_kwargs):
        return {
            "detail_enrichment_attempted": 1,
            "detail_enrichment_improved": 1,
            "detail_enrichment_skipped": 0,
            "detail_enrichment_failed": 0,
        }

    def _enrich_job(self, job, session):
        return True

    def _score_and_persist(self, job_id, *, candidate_id, force=False, commit=True):
        resolved = db_session.get(JobPost, type(job.id)(str(job_id)))
        if resolved is not None:
            metadata = dict(resolved.extracted_metadata or {})
            metadata["candidate_fit"] = {
                str(candidate_id): {
                    "fit_score": 75,
                    "score_source": "provider",
                    "threshold_eligible": True,
                }
            }
            resolved.extracted_metadata = metadata
            db_session.flush()
        return {}

    monkeypatch.setattr("job_agent.services.workflows.JobSpyService.discover_for_roles", _discover_for_roles)
    monkeypatch.setattr("job_agent.services.workflows.JobSpyService.detail_enrich_survivors", _detail_enrich_survivors)
    monkeypatch.setattr("job_agent.services.workflows.JobFetcher.enrich_job", _enrich_job)
    monkeypatch.setattr("job_agent.services.workflows.JobFitScoringService.score_and_persist", _score_and_persist)

    task = WorkflowTask(
        id=uuid4(),
        kind="job_discovery",
        status="pending",
        payload={
            "candidate_id": candidate.id,
            "provider_mode": "lm_studio",
            "country": "Italy",
            "roles": ["Data Engineer"],
            "seniority": "junior",
            "location": "Italy",
            "sources": ["linkedin"],
            "limit": 10,
        },
        result={},
    )
    db_session.add(task)
    db_session.commit()

    result = CVWorkflowService(db_session).run_job_discovery(task)

    # Verify detail_enrichment stage was persisted
    assert "detail_enrichment" in persisted_stages
    # Verify counts were merged
    assert result["counts"]["detail_enrichment_improved"] == 1
    assert result["counts"]["detail_enrichment_attempted"] == 1


# ── Test: non-JobSpy sources are skipped ─────────────────────────────────

def test_non_jobspy_source_skipped(db_session, monkeypatch):
    """Only JobSpy/LinkedIn-origin jobs should be enriched, not ATS or manual."""
    monkeypatch.setattr(
        "job_agent.services.jobspy_service.settings.jobspy_detail_enrichment_enabled",
        True,
        raising=False,
    )
    monkeypatch.setattr(
        "job_agent.services.jobspy_service.settings.jobspy_detail_enrichment_limit",
        10,
        raising=False,
    )

    manual_job = _make_job(
        db_session,
        source_name="manual",
        description="short manual description",
    )
    db_session.commit()

    result = JobSpyService().detail_enrich_survivors(
        saved_job_ids=[str(manual_job.id)],
        session=db_session,
        selected_country="Italy",
        seniority="junior",
    )

    assert result["detail_enrichment_skipped"] == 1
    assert result["detail_enrichment_attempted"] == 0
