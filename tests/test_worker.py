"""Tests for one-iteration worker behavior."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def _mock_session():
    session = MagicMock()
    query = session.query.return_value
    query.filter.return_value = query
    query.order_by.return_value = query
    query.first.return_value = None
    return session


def test_worker_does_not_run_gmail_sync_from_idle_loop(monkeypatch):
    """Idle worker iterations must not create job posts from Gmail."""
    from job_agent import worker

    monkeypatch.setattr(worker, "reload_settings_from_sources", lambda _settings: None)
    monkeypatch.setattr(worker.settings, "gmail_auto_sync", True)
    monkeypatch.setattr(worker.settings, "gmail_sync_interval_minutes", 0)

    session = _mock_session()

    with patch("job_agent.worker.seed_reference_data"):
        with patch("job_agent.services.gmail.GmailService.sync_jobs") as mock_sync:
            with patch("job_agent.worker.CVWorkflowService"):
                with patch("job_agent.worker.JobFetcher"):
                    worker._run_one_iteration(session)

    mock_sync.assert_not_called()


def test_worker_skips_gmail_when_disabled(monkeypatch):
    """Worker does NOT call GmailService when gmail_auto_sync=false."""
    from job_agent import worker

    monkeypatch.setattr(worker, "reload_settings_from_sources", lambda _settings: None)
    monkeypatch.setattr(worker.settings, "gmail_auto_sync", False)
    session = _mock_session()
    mock_gmail = MagicMock()

    with patch("job_agent.worker.seed_reference_data"):
        with patch("job_agent.services.gmail.GmailService.sync_jobs") as mock_sync:
            with patch("job_agent.worker.CVWorkflowService"):
                with patch("job_agent.worker.JobFetcher"):
                    worker._run_one_iteration(session)

    mock_gmail.sync_jobs.assert_not_called()
    mock_sync.assert_not_called()


def test_worker_calls_enrich_after_interval(monkeypatch):
    """Worker calls JobFetcher.enrich_pending_parallel after enrichment interval elapses."""
    from job_agent import worker

    monkeypatch.setattr(worker, "reload_settings_from_sources", lambda _settings: None)
    monkeypatch.setattr(worker, "_last_enrichment", 0.0)
    session = _mock_session()
    mock_fetcher = MagicMock()

    with patch("job_agent.worker.seed_reference_data"):
        with patch("job_agent.worker.JobFetcher", return_value=mock_fetcher):
            with patch("job_agent.worker.CVWorkflowService"):
                worker._run_one_iteration(session)

    mock_fetcher.enrich_pending_parallel.assert_called_once()


def test_worker_does_not_scan_career_pages_from_idle_loop(monkeypatch):
    """Career-page jobs are only imported by explicit user actions."""
    from job_agent import worker

    monkeypatch.setattr(worker, "reload_settings_from_sources", lambda _settings: None)
    session = _mock_session()

    with patch("job_agent.worker.seed_reference_data"):
        with patch("job_agent.worker.JobFetcher"):
            with patch("job_agent.worker.CVWorkflowService"):
                with patch("job_agent.services.career_scanner.CareerPageScanner.scan_all_parallel") as mock_parallel:
                    worker._run_one_iteration(session)

    mock_parallel.assert_not_called()


def test_worker_does_not_run_scheduled_jobspy_from_idle_loop(monkeypatch):
    """JobSpy discovery is queued by user action, not by worker idle intervals."""
    from job_agent import worker

    monkeypatch.setattr(worker, "reload_settings_from_sources", lambda _settings: None)
    monkeypatch.setattr(worker.settings, "use_jobspy", True)
    monkeypatch.setattr(worker.settings, "jobspy_discover_queries", ["Data Engineer"])
    session = _mock_session()

    with patch("job_agent.worker.seed_reference_data"):
        with patch("job_agent.worker.JobFetcher"):
            with patch("job_agent.worker.CVWorkflowService"):
                with patch("job_agent.services.jobspy_service.JobSpyService.discover") as mock_discover:
                    worker._run_one_iteration(session)

    mock_discover.assert_not_called()
