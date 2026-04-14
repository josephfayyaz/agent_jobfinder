from __future__ import annotations

from threading import Lock
from unittest.mock import MagicMock, patch

from job_agent.models import CareerPageSource, JobPost


def test_scan_all_parallel_returns_same_count_as_sequential(db_session, db_track):
    """Parallel scan produces the same result as sequential scan."""
    from job_agent.services.career_scanner import CareerPageScanner

    db_session.add(
        CareerPageSource(
            company="TestCo",
            career_url="https://testco.example.com/jobs",
            active=True,
            country="Italy",
        )
    )
    db_session.commit()

    fake_html = """
    <html><body>
      <a href="/jobs/data-engineer">Data Engineer</a>
      <a href="/about">About Us</a>
    </body></html>
    """

    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.text = fake_html
    mock_response.status_code = 200

    with patch("job_agent.services.career_scanner.httpx.get", return_value=mock_response):
        count_parallel = CareerPageScanner().scan_all_parallel(db_session, max_workers=2)

    assert count_parallel == 1


def test_scan_parallel_deduplicates(db_session):
    """Parallel scan does not insert duplicate URLs."""
    from job_agent.services.career_scanner import CareerPageScanner

    existing_url = "https://testco.example.com/jobs/data-engineer"
    db_session.add(
        JobPost(
            title="Data Engineer",
            company="TestCo",
            source_url=existing_url,
            status="new",
            description="",
        )
    )
    db_session.add(
        CareerPageSource(
            company="TestCo",
            career_url="https://testco.example.com/jobs",
            active=True,
            country="Italy",
        )
    )
    db_session.commit()

    fake_html = f'<html><body><a href="{existing_url}">Data Engineer</a></body></html>'
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.text = fake_html
    mock_response.status_code = 200

    with patch("job_agent.services.career_scanner.httpx.get", return_value=mock_response):
        count = CareerPageScanner().scan_all_parallel(db_session, max_workers=2)

    assert count == 0


def test_enrich_parallel_writes_descriptions(db_session, monkeypatch):
    """Parallel enrichment writes descriptions to DB."""
    from job_agent.services.job_fetcher import JobFetcher

    job = JobPost(
        title="Data Engineer",
        company="TestCo",
        source_url="https://testco.example.com/jobs/de",
        status="new",
        description="",
    )
    db_session.add(job)
    db_session.commit()

    monkeypatch.setattr(
        "job_agent.services.job_fetcher._fetch_description_from_url",
        lambda _url: "Exciting data engineering role at TestCo.",
    )
    monkeypatch.setattr(
        "job_agent.services.company_resolver.find_company_url",
        lambda **_kwargs: None,
    )

    count = JobFetcher().enrich_pending_parallel(db_session, limit=5, max_workers=2)
    assert count == 1
    db_session.refresh(job)
    assert "TestCo" in job.description


def test_scan_parallel_uses_thread_local_sessions(db_session, monkeypatch):
    """Parallel scan must not reuse the caller session across source threads."""
    from job_agent.services.career_scanner import CareerPageScanner

    db_session.add(
        CareerPageSource(
            company="A",
            career_url="https://a.example.com/jobs",
            active=True,
            country="Italy",
        )
    )
    db_session.add(
        CareerPageSource(
            company="B",
            career_url="https://b.example.com/jobs",
            active=True,
            country="Italy",
        )
    )
    db_session.commit()

    session_ids: list[int] = []
    lock = Lock()
    main_session_id = id(db_session)

    def _fake_scan_one(self, source, session, tracks):
        del self, source, tracks
        with lock:
            session_ids.append(id(session))
        return 0

    monkeypatch.setattr("job_agent.services.career_scanner.CareerPageScanner._scan_one", _fake_scan_one)

    count = CareerPageScanner().scan_all_parallel(db_session, max_workers=2)

    assert count == 0
    assert len(session_ids) == 2
    assert all(session_id != main_session_id for session_id in session_ids)
    assert len(set(session_ids)) == 2


def test_scan_parallel_uses_scanner_max_workers_setting(db_session, monkeypatch):
    """When max_workers is omitted, scanner_max_workers setting should drive pool size."""
    from job_agent.config import settings
    from job_agent.services import career_scanner

    db_session.add(
        CareerPageSource(
            company="ConfigCo",
            career_url="https://configco.example.com/jobs",
            active=True,
            country="Italy",
        )
    )
    db_session.commit()

    monkeypatch.setattr(settings, "scanner_max_workers", 1)
    monkeypatch.setattr(
        "job_agent.services.career_scanner.CareerPageScanner._scan_one",
        lambda self, source, session, tracks: 0,
    )

    captured: dict[str, int] = {}
    real_executor = career_scanner.ThreadPoolExecutor

    def _wrapped_executor(*args, **kwargs):
        workers = kwargs.get("max_workers")
        if workers is None and args:
            workers = args[0]
        captured["max_workers"] = workers
        return real_executor(*args, **kwargs)

    monkeypatch.setattr(career_scanner, "ThreadPoolExecutor", _wrapped_executor)

    career_scanner.CareerPageScanner().scan_all_parallel(db_session)

    assert captured["max_workers"] == 1
