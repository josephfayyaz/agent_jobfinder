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


def test_worker_calls_gmail_sync_after_interval(monkeypatch):
    """Worker triggers GmailService.sync_jobs when interval has elapsed."""
    from job_agent import worker

    monkeypatch.setattr(worker.settings, "gmail_auto_sync", True)
    monkeypatch.setattr(worker.settings, "gmail_sync_interval_minutes", 0)
    monkeypatch.setattr(worker, "_last_gmail_sync", 0.0)

    session = _mock_session()
    mock_gmail = MagicMock()
    mock_gmail.sync_jobs.return_value = []

    with patch("job_agent.worker.seed_reference_data"):
        with patch("job_agent.worker.GmailService", return_value=mock_gmail):
            with patch("job_agent.worker.CVWorkflowService"):
                with patch("job_agent.worker.JobFetcher"):
                    worker._run_one_iteration(session)

    mock_gmail.sync_jobs.assert_called_once()


def test_worker_skips_gmail_when_disabled(monkeypatch):
    """Worker does NOT call GmailService when gmail_auto_sync=false."""
    from job_agent import worker

    monkeypatch.setattr(worker.settings, "gmail_auto_sync", False)
    session = _mock_session()
    mock_gmail = MagicMock()

    with patch("job_agent.worker.seed_reference_data"):
        with patch("job_agent.worker.GmailService", return_value=mock_gmail):
            with patch("job_agent.worker.CVWorkflowService"):
                with patch("job_agent.worker.JobFetcher"):
                    worker._run_one_iteration(session)

    mock_gmail.sync_jobs.assert_not_called()


def test_worker_calls_enrich_after_interval(monkeypatch):
    """Worker calls JobFetcher.enrich_pending after enrichment interval elapses."""
    from job_agent import worker

    monkeypatch.setattr(worker, "_last_enrichment", 0.0)
    session = _mock_session()
    mock_fetcher = MagicMock()

    with patch("job_agent.worker.seed_reference_data"):
        with patch("job_agent.worker.JobFetcher", return_value=mock_fetcher):
            with patch("job_agent.worker.GmailService"):
                with patch("job_agent.worker.CVWorkflowService"):
                    worker._run_one_iteration(session)

    mock_fetcher.enrich_pending.assert_called_once()
