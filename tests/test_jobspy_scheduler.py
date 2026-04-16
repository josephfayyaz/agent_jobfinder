from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

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

    monkeypatch.setattr(worker.settings, "use_jobspy", False)
    monkeypatch.setattr(worker.settings, "gmail_auto_sync", False)
    monkeypatch.setattr(worker.settings, "jobspy_discover_interval_hours", 1)
    monkeypatch.setattr(worker.settings, "jobspy_discover_queries", ["Data Engineer"])
    monkeypatch.setattr(worker, "_last_enrichment", time.time())
    monkeypatch.setattr(worker, "_last_career_scan", time.time())
    monkeypatch.setattr(worker, "_last_jobspy_discover", 0.0)

    session = _mock_session()
    with patch("job_agent.worker.seed_reference_data"), patch(
        "job_agent.worker.CVWorkflowService"
    ), patch("job_agent.services.jobspy_service.JobSpyService.discover") as mock_discover:
        worker._run_one_iteration(session)

    mock_discover.assert_not_called()


def test_worker_skips_jobspy_when_interval_is_zero(monkeypatch):
    from job_agent import worker

    monkeypatch.setattr(worker.settings, "use_jobspy", True)
    monkeypatch.setattr(worker.settings, "gmail_auto_sync", False)
    monkeypatch.setattr(worker.settings, "jobspy_discover_interval_hours", 0)
    monkeypatch.setattr(worker.settings, "jobspy_discover_queries", ["Data Engineer"])
    monkeypatch.setattr(worker, "_last_enrichment", time.time())
    monkeypatch.setattr(worker, "_last_career_scan", time.time())
    monkeypatch.setattr(worker, "_last_jobspy_discover", 0.0)

    session = _mock_session()
    with patch("job_agent.worker.seed_reference_data"), patch(
        "job_agent.worker.CVWorkflowService"
    ), patch("job_agent.services.jobspy_service.JobSpyService.discover") as mock_discover:
        worker._run_one_iteration(session)

    mock_discover.assert_not_called()


def test_worker_calls_jobspy_when_interval_elapsed(monkeypatch):
    from job_agent import worker

    queries = ["Data Engineer", "Analytics Engineer", "MLOps Engineer"]
    monkeypatch.setattr(worker.settings, "use_jobspy", True)
    monkeypatch.setattr(worker.settings, "gmail_auto_sync", False)
    monkeypatch.setattr(worker.settings, "jobspy_discover_interval_hours", 1)
    monkeypatch.setattr(worker.settings, "jobspy_discover_queries", queries)
    monkeypatch.setattr(worker.settings, "jobspy_discover_location", "Italy")
    monkeypatch.setattr(worker.settings, "jobspy_default_limit", 50)
    monkeypatch.setattr(worker, "_last_enrichment", time.time())
    monkeypatch.setattr(worker, "_last_career_scan", time.time())
    monkeypatch.setattr(worker, "_last_jobspy_discover", time.time() - 7200)

    session = _mock_session()
    with patch("job_agent.worker.seed_reference_data"), patch(
        "job_agent.worker.CVWorkflowService"
    ), patch("job_agent.services.jobspy_service.JobSpyService.discover", return_value=3) as mock_discover:
        worker._run_one_iteration(session)

    assert mock_discover.call_count == len(queries)


def test_worker_skips_jobspy_when_interval_not_elapsed(monkeypatch):
    from job_agent import worker

    monkeypatch.setattr(worker.settings, "use_jobspy", True)
    monkeypatch.setattr(worker.settings, "gmail_auto_sync", False)
    monkeypatch.setattr(worker.settings, "jobspy_discover_interval_hours", 1)
    monkeypatch.setattr(worker.settings, "jobspy_discover_queries", ["Data Engineer"])
    monkeypatch.setattr(worker, "_last_enrichment", time.time())
    monkeypatch.setattr(worker, "_last_career_scan", time.time())
    monkeypatch.setattr(worker, "_last_jobspy_discover", time.time() - 60)

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
