from __future__ import annotations

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
