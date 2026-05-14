from __future__ import annotations

import sys
import time
from types import ModuleType
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4
from uuid import UUID

from job_agent.config import Settings


def _mock_session():
    session = MagicMock()
    query = session.query.return_value
    query.filter.return_value = query
    query.order_by.return_value = query
    query.first.return_value = None
    return session


def test_worker_skips_jobspy_when_disabled(monkeypatch):
    from job_agent import worker

    monkeypatch.setattr(worker, "reload_settings_from_sources", lambda _settings: None)
    monkeypatch.setattr(worker.settings, "use_jobspy", False)
    monkeypatch.setattr(worker.settings, "gmail_auto_sync", False)
    monkeypatch.setattr(worker.settings, "jobspy_discover_queries", ["Data Engineer"])
    monkeypatch.setattr(worker, "_last_enrichment", time.time())

    session = _mock_session()
    with patch("job_agent.worker.seed_reference_data"), patch(
        "job_agent.worker.CVWorkflowService"
    ), patch("job_agent.services.jobspy_service.JobSpyService.discover") as mock_discover:
        worker._run_one_iteration(session)

    mock_discover.assert_not_called()


def test_worker_skips_jobspy_when_interval_is_zero(monkeypatch):
    from job_agent import worker

    monkeypatch.setattr(worker, "reload_settings_from_sources", lambda _settings: None)
    monkeypatch.setattr(worker.settings, "use_jobspy", True)
    monkeypatch.setattr(worker.settings, "gmail_auto_sync", False)
    monkeypatch.setattr(worker.settings, "jobspy_discover_queries", ["Data Engineer"])
    monkeypatch.setattr(worker, "_last_enrichment", time.time())

    session = _mock_session()
    with patch("job_agent.worker.seed_reference_data"), patch(
        "job_agent.worker.CVWorkflowService"
    ), patch("job_agent.services.jobspy_service.JobSpyService.discover") as mock_discover:
        worker._run_one_iteration(session)

    mock_discover.assert_not_called()


def test_worker_does_not_auto_run_jobspy_when_interval_elapsed(monkeypatch):
    from job_agent import worker

    monkeypatch.setattr(worker, "reload_settings_from_sources", lambda _settings: None)
    queries = ["Data Engineer", "Analytics Engineer", "MLOps Engineer"]
    monkeypatch.setattr(worker.settings, "use_jobspy", True)
    monkeypatch.setattr(worker.settings, "gmail_auto_sync", False)
    monkeypatch.setattr(worker.settings, "jobspy_discover_queries", queries)
    monkeypatch.setattr(worker.settings, "jobspy_discover_location", "Italy")
    monkeypatch.setattr(worker.settings, "jobspy_default_limit", 50)
    monkeypatch.setattr(worker, "_last_enrichment", time.time())

    session = _mock_session()
    with patch("job_agent.worker.seed_reference_data"), patch(
        "job_agent.worker.CVWorkflowService"
    ), patch("job_agent.services.jobspy_service.JobSpyService.discover", return_value=3) as mock_discover:
        worker._run_one_iteration(session)

    mock_discover.assert_not_called()


def test_worker_skips_jobspy_when_interval_not_elapsed(monkeypatch):
    from job_agent import worker

    monkeypatch.setattr(worker, "reload_settings_from_sources", lambda _settings: None)
    monkeypatch.setattr(worker.settings, "use_jobspy", True)
    monkeypatch.setattr(worker.settings, "gmail_auto_sync", False)
    monkeypatch.setattr(worker.settings, "jobspy_discover_queries", ["Data Engineer"])
    monkeypatch.setattr(worker, "_last_enrichment", time.time())

    session = _mock_session()
    with patch("job_agent.worker.seed_reference_data"), patch(
        "job_agent.worker.CVWorkflowService"
    ), patch("job_agent.services.jobspy_service.JobSpyService.discover") as mock_discover:
        worker._run_one_iteration(session)

    mock_discover.assert_not_called()


def test_parse_queries_validator_parses_json_string():
    parsed = Settings(JOBSPY_DISCOVER_QUERIES='["A","B"]').jobspy_discover_queries
    assert parsed == ["A", "B"]


def test_parse_queries_validator_parses_csv_string():
    parsed = Settings(JOBSPY_DISCOVER_QUERIES="A, B, C").jobspy_discover_queries
    assert parsed == ["A", "B", "C"]


def test_jobspy_package_guard_rejects_unrelated_distribution(monkeypatch):
    from job_agent.services.jobspy_service import JobSpyService

    module = ModuleType("jobspy")
    module.scrape_jobs = lambda **_kwargs: []
    monkeypatch.setitem(sys.modules, "jobspy", module)
    monkeypatch.setattr(
        "job_agent.services.jobspy_service.importlib.metadata.packages_distributions",
        lambda: {"jobspy": ["jobspy"]},
    )

    with patch.dict(sys.modules, {"jobspy": module}, clear=False):
        try:
            JobSpyService._resolve_scrape_jobs()
            assert False, "Expected ImportError for unrelated jobspy distribution"
        except ImportError as exc:
            assert "python-jobspy" in str(exc)


def test_worker_processes_pending_job_discovery_task(db_session, monkeypatch):
    from job_agent import worker
    from job_agent.models import WorkflowTask

    monkeypatch.setattr(worker, "reload_settings_from_sources", lambda _settings: None)
    task = WorkflowTask(
        id=uuid4(),
        kind="job_discovery",
        status="pending",
        payload={
            "candidate_id": None,
            "provider_mode": "lm_studio",
            "country": "Italy",
            "roles": ["Data Engineer", "Analytics Engineer"],
            "seniority": "junior",
            "location": "Italy",
            "sources": ["linkedin"],
            "limit": 10,
        },
        result={},
    )
    db_session.add(task)
    db_session.commit()

    monkeypatch.setattr(worker.settings, "use_jobspy", True)
    monkeypatch.setattr(worker.settings, "gmail_auto_sync", False)
    monkeypatch.setattr(worker, "_last_enrichment", time.time())
    monkeypatch.setattr(worker, "seed_reference_data", lambda _session: None)

    monkeypatch.setattr(
        "job_agent.services.jobspy_service.JobSpyService.discover_for_roles",
        lambda self, **_kwargs: {
            "roles_queried": 2,
            "raw_hits": 12,
            "duplicates": 3,
            "rejected_by_country": 1,
            "rejected_by_role": 1,
            "rejected_by_seniority": 2,
            "queued_for_scoring": 5,
            "saved_jobs": 5,
        },
    )

    worker._run_one_iteration(db_session)
    db_session.refresh(task)
    assert task.status == "completed"
    assert task.result["counts"]["saved_jobs"] == 5
    assert task.result["counts"]["roles_queried"] == 2


def test_worker_reloads_settings_before_processing_job_discovery_task(db_session, monkeypatch):
    from job_agent import worker
    from job_agent.models import WorkflowTask

    task = WorkflowTask(
        id=uuid4(),
        kind="job_discovery",
        status="pending",
        payload={
            "candidate_id": None,
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

    monkeypatch.setattr(worker.settings, "use_jobspy", False, raising=False)
    monkeypatch.setattr(worker.settings, "gmail_auto_sync", False, raising=False)
    monkeypatch.setattr(worker, "_last_enrichment", time.time())
    monkeypatch.setattr(worker, "seed_reference_data", lambda _session: None)

    def _reload(current_settings):
        setattr(current_settings, "use_jobspy", True)

    monkeypatch.setattr(worker, "reload_settings_from_sources", _reload)
    monkeypatch.setattr(
        "job_agent.services.jobspy_service.JobSpyService.discover_for_roles",
        lambda self, **_kwargs: {
            "roles_queried": 1,
            "raw_hits": 6,
            "duplicates": 1,
            "rejected_by_country": 1,
            "rejected_by_role": 1,
            "rejected_by_seniority": 0,
            "queued_for_scoring": 3,
            "saved_jobs": 3,
        },
    )

    worker._run_one_iteration(db_session)
    db_session.refresh(task)
    assert task.status == "completed"
    assert task.result["counts"]["saved_jobs"] == 3


def test_worker_marks_job_discovery_task_failed_when_jobspy_missing(db_session, monkeypatch):
    from job_agent import worker
    from job_agent.models import WorkflowTask
    from job_agent.services.jobspy_service import JobSpyDiscoveryError

    monkeypatch.setattr(worker, "reload_settings_from_sources", lambda _settings: None)
    task = WorkflowTask(
        id=uuid4(),
        kind="job_discovery",
        status="pending",
        payload={
            "candidate_id": None,
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

    monkeypatch.setattr(worker.settings, "use_jobspy", True)
    monkeypatch.setattr(worker.settings, "gmail_auto_sync", False)
    monkeypatch.setattr(worker, "_last_enrichment", time.time())
    monkeypatch.setattr(worker, "seed_reference_data", lambda _session: None)

    def _raise_missing(self, **_kwargs):
        raise JobSpyDiscoveryError("JobSpy package is not installed in the ML environment. Reinstall dependencies and retry.")

    monkeypatch.setattr("job_agent.services.jobspy_service.JobSpyService.discover_for_roles", _raise_missing)

    worker._run_one_iteration(db_session)
    db_session.refresh(task)
    assert task.status == "failed"
    assert "not installed" in task.error_message.lower()
    assert task.result["stage"] == "failed"


def test_worker_marks_job_discovery_task_failed_for_unexpected_runtime_error(db_session, monkeypatch):
    from job_agent import worker
    from job_agent.models import WorkflowTask

    monkeypatch.setattr(worker, "reload_settings_from_sources", lambda _settings: None)
    task = WorkflowTask(
        id=uuid4(),
        kind="job_discovery",
        status="pending",
        payload={
            "candidate_id": None,
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

    monkeypatch.setattr(worker.settings, "use_jobspy", True)
    monkeypatch.setattr(worker.settings, "gmail_auto_sync", False)
    monkeypatch.setattr(worker, "_last_enrichment", time.time())
    monkeypatch.setattr(worker, "seed_reference_data", lambda _session: None)

    def _raise_runtime(self, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("job_agent.services.jobspy_service.JobSpyService.discover_for_roles", _raise_runtime)

    worker._run_one_iteration(db_session)
    db_session.refresh(task)
    assert task.status == "failed"
    assert task.error_message == "boom"
    assert task.result["stage"] == "failed"
    assert task.result["message"] == "boom"


def test_job_discovery_enriches_saved_jobs_before_scoring(db_session, monkeypatch):
    from job_agent.models import Candidate, JobPost, WorkflowTask
    from job_agent.services.workflows import CVWorkflowService

    candidate = Candidate(full_name="Ari Leone", email="ari@example.test", active=True)
    db_session.add(candidate)
    db_session.commit()

    monkeypatch.setattr("job_agent.services.workflows.settings.use_jobspy", True, raising=False)
    monkeypatch.setattr("job_agent.services.workflows.settings.default_candidate_id", candidate.id, raising=False)
    monkeypatch.setattr("job_agent.services.workflows.settings.discovery_min_fit_score", 70, raising=False)
    monkeypatch.setattr("job_agent.services.workflows.settings.discovery_max_visible_jobs", 80, raising=False)

    captured: list[str] = []

    def _discover_for_roles(self, **_kwargs):
        job = JobPost(
            title="Junior Data Engineer",
            company="Acme",
            source_name="jobspy_linkedin",
            source_url="https://example.com/jobs/1",
            canonical_apply_url="https://example.com/jobs/1",
            location="Milan, Italy",
            country="Italy",
            description="",
            queue_state="new",
            status="new",
        )
        db_session.add(job)
        db_session.commit()
        captured.append(f"discover:{job.id}")
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

    def _enrich_job(self, job, session):
        captured.append(f"enrich:{job.id}")
        job.description = "Python SQL ETL pipelines in a data engineering team." * 10
        session.flush()
        return True

    def _score_and_persist(self, job, *, candidate_id, force=False, commit=True):
        normalized = str(job)
        captured.append(f"score:{normalized}")
        resolved = db_session.get(JobPost, UUID(normalized))
        assert resolved is not None
        assert len((resolved.description or "").strip()) >= 120
        metadata = dict(resolved.extracted_metadata or {})
        metadata["candidate_fit"] = {
            str(candidate_id): {
                "fit_score": 88,
                "score_source": "provider",
                "provider_mode": "lm_studio",
                "matched_evidence": ["Python", "SQL", "ETL"],
                "top_gaps": [],
                "language_assessment": {"label": "good", "reason": "English fit is acceptable."},
                "seniority_assessment": {"label": "aligned", "reason": "Junior scope."},
                "short_reason": "Strong junior data fit.",
            }
        }
        resolved.extracted_metadata = metadata
        if commit:
            db_session.commit()
        else:
            db_session.flush()
        return metadata["candidate_fit"][str(candidate_id)]

    monkeypatch.setattr("job_agent.services.workflows.JobSpyService.discover_for_roles", _discover_for_roles)
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

    assert result["stage"] == "completed"
    assert result["counts"]["saved_jobs"] == 1
    assert result["counts"]["visible_after_threshold"] == 1
    assert captured[1].startswith("enrich:")
    assert captured[2].startswith("score:")


def test_job_discovery_merges_ats_results_into_same_run(db_session, monkeypatch):
    from job_agent.models import Candidate, JobPost, WorkflowTask
    from job_agent.services.workflows import CVWorkflowService

    candidate = Candidate(full_name="Ari Leone", email="ari@example.test", active=True)
    db_session.add(candidate)
    db_session.commit()

    monkeypatch.setattr("job_agent.services.workflows.settings.use_jobspy", True, raising=False)
    monkeypatch.setattr("job_agent.services.workflows.settings.default_candidate_id", candidate.id, raising=False)
    monkeypatch.setattr("job_agent.services.workflows.settings.discovery_min_fit_score", 70, raising=False)
    monkeypatch.setattr("job_agent.services.workflows.settings.discovery_max_visible_jobs", 80, raising=False)

    def _discover_for_roles(self, **_kwargs):
        return {
            "roles_queried": 1,
            "raw_hits": 1,
            "duplicates": 0,
            "rejected_by_country": 0,
            "rejected_by_role": 0,
            "rejected_by_seniority": 0,
            "queued_for_scoring": 0,
            "saved_jobs": 0,
            "saved_job_ids": [],
        }

    def _discover_active_sources(self, **_kwargs):
        job = JobPost(
            title="Junior Data Engineer",
            company="ATS Co",
            source_name="ats_greenhouse",
            source_url="https://ats.example/jobs/1",
            canonical_apply_url="https://ats.example/jobs/1",
            location="Milan, Italy",
            country="Italy",
            description="Python SQL ETL pipelines in a data team." * 8,
            queue_state="new",
            status="new",
        )
        db_session.add(job)
        db_session.commit()
        return {
            "raw_hits": 1,
            "ats_sources_scanned": 1,
            "ats_raw_hits": 1,
            "duplicates": 0,
            "rejected_by_country": 0,
            "rejected_by_role": 0,
            "rejected_by_seniority": 0,
            "queued_for_scoring": 1,
            "saved_jobs": 1,
            "saved_job_ids": [str(job.id)],
        }

    def _enrich_job(self, job, session):
        return True

    def _score_and_persist(self, job, *, candidate_id, force=False, commit=True):
        resolved = db_session.get(JobPost, UUID(str(job)))
        metadata = dict(resolved.extracted_metadata or {})
        metadata["candidate_fit"] = {
            str(candidate_id): {
                "fit_score": 86,
                "score_source": "provider",
                "provider_mode": "lm_studio",
                "matched_evidence": ["Python", "SQL"],
                "top_gaps": [],
                "language_assessment": {"label": "good", "reason": "English fit is acceptable."},
                "seniority_assessment": {"label": "aligned", "reason": "Junior scope."},
                "short_reason": "Strong ATS data fit.",
            }
        }
        resolved.extracted_metadata = metadata
        if commit:
            db_session.commit()
        else:
            db_session.flush()
        return metadata["candidate_fit"][str(candidate_id)]

    monkeypatch.setattr("job_agent.services.workflows.JobSpyService.discover_for_roles", _discover_for_roles)
    monkeypatch.setattr("job_agent.services.workflows.AtsDiscoveryService.discover_active_sources", _discover_active_sources)
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
            "include_ats": True,
            "include_direct_company_sources": True,
            "career_source_ids": [1],
            "source_policy": "selected_companies",
            "limit": 10,
        },
        result={},
    )
    db_session.add(task)
    db_session.commit()

    result = CVWorkflowService(db_session).run_job_discovery(task)

    assert result["stage"] == "completed"
    assert result["counts"]["saved_jobs"] == 1
    assert result["counts"]["ats_sources_scanned"] == 1
    assert result["counts"]["ats_raw_hits"] == 1
    assert result["counts"]["visible_after_threshold"] == 1


def test_job_discovery_default_payload_does_not_call_ats(db_session, monkeypatch):
    from job_agent.models import Candidate, WorkflowTask
    from job_agent.services.workflows import CVWorkflowService

    monkeypatch.setattr("job_agent.services.workflows.settings.use_jobspy", True, raising=False)

    candidate = Candidate(id=str(uuid4()), full_name="No ATS User")
    db_session.add(candidate)
    db_session.commit()

    def _discover_for_roles(self, **_kwargs):
        return {
            "roles_queried": 1,
            "raw_hits": 0,
            "duplicates": 0,
            "rejected_by_country": 0,
            "rejected_by_role": 0,
            "rejected_by_seniority": 0,
            "queued_for_scoring": 0,
            "saved_jobs": 0,
            "saved_job_ids": [],
        }

    def _discover_active_sources(self, **_kwargs):
        raise AssertionError("ATS discovery should require explicit company source selection")

    monkeypatch.setattr("job_agent.services.workflows.JobSpyService.discover_for_roles", _discover_for_roles)
    monkeypatch.setattr("job_agent.services.workflows.AtsDiscoveryService.discover_active_sources", _discover_active_sources)

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

    assert result["stage"] == "completed_zero_results"
    assert result["counts"]["ats_sources_scanned"] == 0


def test_worker_prioritizes_pending_tasks_over_scheduled_jobspy(monkeypatch):
    from job_agent import worker

    monkeypatch.setattr(worker, "reload_settings_from_sources", lambda _settings: None)
    monkeypatch.setattr(worker.settings, "use_jobspy", True, raising=False)
    monkeypatch.setattr(worker.settings, "gmail_auto_sync", False, raising=False)
    monkeypatch.setattr(worker.settings, "jobspy_discover_queries", ["Data Engineer"], raising=False)
    monkeypatch.setattr(worker, "_last_enrichment", time.time())

    session = _mock_session()
    pending = SimpleNamespace(id=uuid4(), kind="job_discovery", status="pending")
    session.query.return_value.filter.return_value.order_by.return_value.first.return_value = pending

    mock_service = MagicMock()
    mock_service.process_next_task.return_value = pending
    with patch("job_agent.worker.seed_reference_data"), patch(
        "job_agent.worker.CVWorkflowService", return_value=mock_service
    ), patch("job_agent.services.jobspy_service.JobSpyService.discover") as mock_discover:
        worker._run_one_iteration(session)

    mock_service.process_next_task.assert_called_once()
    mock_discover.assert_not_called()


def test_discover_for_roles_dedupes_across_multiple_role_queries(db_session, monkeypatch):
    from job_agent.models import JobPost
    from job_agent.services.jobspy_service import JobSpyService

    class FakeDataFrame:
        def __init__(self, rows):
            self._rows = rows

        @property
        def empty(self):
            return not self._rows

        def __len__(self):
            return len(self._rows)

        def iterrows(self):
            for index, row in enumerate(self._rows):
                yield index, row

    rows_by_role = {
        "Data Engineer junior OR \"entry level\" OR graduate OR \"new grad\"": FakeDataFrame(
            [
                {
                    "job_url": "https://example.com/jobs/1",
                    "title": "Data Engineer",
                    "company": "Acme",
                    "location": "Milan, Italy",
                    "description": "Python and SQL role",
                },
                {
                    "job_url": "https://example.com/jobs/2",
                    "title": "Data Engineer",
                    "company": "Beta",
                    "location": "Rome, Italy",
                    "description": "ETL and dbt role",
                },
            ]
        ),
        "Analytics Engineer junior OR \"entry level\" OR graduate OR \"new grad\"": FakeDataFrame(
            [
                {
                    "job_url": "https://example.com/jobs/1",
                    "title": "Data Engineer",
                    "company": "Acme",
                    "location": "Milan, Italy",
                    "description": "Duplicate across roles",
                },
                {
                    "job_url": "https://example.com/jobs/3",
                    "title": "Analytics Engineer",
                    "company": "Gamma",
                    "location": "Turin, Italy",
                    "description": "Analytics stack role",
                },
            ]
        ),
    }

    def _fake_scrape_jobs(site_name, search_term, location, results_wanted, country_indeed=None):  # noqa: ARG001
        return rows_by_role.get(search_term, FakeDataFrame([]))

    monkeypatch.setitem(sys.modules, "jobspy", SimpleNamespace(scrape_jobs=_fake_scrape_jobs))
    monkeypatch.setattr("job_agent.services.jobspy_service.settings.use_jobspy", True, raising=False)
    monkeypatch.setattr("job_agent.services.jobspy_service.settings.jobspy_request_delay", 0.0, raising=False)
    monkeypatch.setattr("job_agent.services.jobspy_service.score_tracks_for_job", lambda _job, _tracks: [])

    counts = JobSpyService().discover_for_roles(
        roles=["Data Engineer", "Analytics Engineer"],
        location="Italy",
        selected_country="Italy",
        seniority="junior",
        session=db_session,
        limit=25,
        sources=["linkedin"],
    )

    assert counts["roles_queried"] == 2
    assert counts["raw_hits"] == 4
    assert counts["duplicates"] == 1
    assert counts["saved_jobs"] == 3
    assert db_session.query(JobPost).count() == 3


def test_discover_for_roles_rejects_generic_engineer_title_without_role_match(db_session, monkeypatch):
    from job_agent.services.jobspy_service import JobSpyService

    class FakeDataFrame:
        def __init__(self, rows):
            self._rows = rows

        @property
        def empty(self):
            return not self._rows

        def __len__(self):
            return len(self._rows)

        def iterrows(self):
            for index, row in enumerate(self._rows):
                yield index, row

    def _fake_scrape_jobs(site_name, search_term, location, results_wanted, country_indeed=None):  # noqa: ARG001
        return FakeDataFrame(
            [
                {
                    "job_url": "https://example.com/jobs/software-grad",
                    "title": "Graduate software engineer",
                    "company": "Evernote",
                    "location": "Milan, Italy",
                    "description": "Build backend systems with Python and English communication.",
                }
            ]
        )

    monkeypatch.setitem(sys.modules, "jobspy", SimpleNamespace(scrape_jobs=_fake_scrape_jobs))
    monkeypatch.setattr("job_agent.services.jobspy_service.settings.use_jobspy", True, raising=False)
    monkeypatch.setattr("job_agent.services.jobspy_service.settings.jobspy_request_delay", 0.0, raising=False)
    monkeypatch.setattr("job_agent.services.jobspy_service.score_tracks_for_job", lambda _job, _tracks: [])

    counts = JobSpyService().discover_for_roles(
        roles=["Junior Data Engineer", "BI Engineer"],
        location="Italy",
        selected_country="Italy",
        seniority="junior",
        session=db_session,
        limit=10,
        sources=["linkedin"],
    )

    assert counts["saved_jobs"] == 0
    assert counts["rejected_by_role"] == 1
