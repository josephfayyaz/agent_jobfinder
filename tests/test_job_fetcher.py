"""Tests for LinkedIn job description fetching and enrichment."""

from __future__ import annotations

import uuid
from unittest.mock import Mock

from bs4 import BeautifulSoup

from job_agent.models import JobPost, ResumeTrack
from job_agent.services.job_fetcher import JobFetcher, _extract_from_html, _extract_from_json_ld


def test_extract_from_json_ld_parses_description():
    soup = BeautifulSoup(
        """
        <html><body>
          <script type="application/ld+json">
            {"description": "<p>Build data pipelines with Python and SQL.</p>"}
          </script>
        </body></html>
        """,
        "lxml",
    )

    assert _extract_from_json_ld(soup) == "Build data pipelines with Python and SQL."


def test_extract_from_html_fallback():
    soup = BeautifulSoup(
        """
        <div class="show-more-less-html__markup">
          Lead ETL platform development for analytics teams.
        </div>
        """,
        "lxml",
    )

    assert _extract_from_html(soup) == "Lead ETL platform development for analytics teams."


def test_enrich_updates_description_and_scores(monkeypatch):
    track = ResumeTrack(
        id=uuid.uuid4(),
        slug="data-engineering-analytics",
        title="Data Engineer",
        role_family="data",
        baseline_summary="",
        target_keywords=["python", "sql", "etl"],
        emphasis={},
        active=True,
    )
    job = JobPost(
        title="Data Engineer",
        company="Acme",
        description="",
        source_url="https://www.linkedin.com/jobs/view/12345",
    )

    class _TracksQuery:
        def filter_by(self, **_: object):
            return self

        def all(self):
            return [track]

    class _Session:
        def __init__(self) -> None:
            self.flush = Mock()

        def query(self, model):
            assert model is ResumeTrack
            return _TracksQuery()

    session = _Session()
    fetcher = JobFetcher()
    upsert_scores = Mock()

    monkeypatch.setattr(
        "job_agent.services.job_fetcher.fetch_job_description",
        lambda url: "Python SQL ETL job description",
    )
    monkeypatch.setattr(fetcher, "_upsert_scores", upsert_scores)

    assert fetcher.enrich_job(job, session) is True
    assert job.description == "Python SQL ETL job description"
    session.flush.assert_called_once()
    upsert_scores.assert_called_once_with(job, [track], session)


def test_enrich_skips_job_without_url():
    job = JobPost(title="Data Engineer", company="Acme", description="", source_url="")

    assert JobFetcher().enrich_job(job, Mock()) is False
