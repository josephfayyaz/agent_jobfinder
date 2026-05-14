from __future__ import annotations

from job_agent.models import CareerPageSource, JobPost


class _Response:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code
        self.is_success = 200 <= status_code < 300


def test_scan_extracts_job_links(monkeypatch, db_session, db_track):
    """Scanner creates JobPost records for job-looking links."""
    from job_agent.services.career_scanner import CareerPageScanner, _looks_like_job_url

    assert _looks_like_job_url("https://example.com/jobs/data-engineer") is True
    assert _looks_like_job_url("https://example.com/about") is False

    source = CareerPageSource(company="Bending Spoons", career_url="https://example.com/careers")
    db_session.add(source)
    db_session.commit()

    monkeypatch.setattr(
        "job_agent.services.career_scanner.httpx.get",
        lambda *_args, **_kwargs: _Response(
            """
            <html>
              <body>
                <a href="/jobs/data-engineer">Data Engineer</a>
                <a href="/about">About</a>
              </body>
            </html>
            """
        ),
    )

    count = CareerPageScanner().scan_all(db_session)

    assert count == 1
    posts = db_session.query(JobPost).all()
    assert len(posts) == 1
    assert posts[0].title == "Data Engineer"
    assert posts[0].source_url == "https://example.com/jobs/data-engineer"


def test_scan_skips_duplicate_url(monkeypatch, db_session):
    """Scanner skips URLs already in the database."""
    from job_agent.services.career_scanner import CareerPageScanner

    existing_url = "https://bendingspoons.com/jobs/data-engineer"
    db_session.add(
        JobPost(
            title="Data Engineer",
            company="Bending Spoons",
            source_url=existing_url,
            canonical_apply_url=existing_url,
            status="new",
            description="",
        )
    )
    db_session.add(CareerPageSource(company="Bending Spoons", career_url="https://bendingspoons.com/jobs"))
    db_session.commit()

    monkeypatch.setattr(
        "job_agent.services.career_scanner.httpx.get",
        lambda *_args, **_kwargs: _Response(
            """
            <html>
              <body>
                <a href="https://bendingspoons.com/jobs/data-engineer">Data Engineer</a>
              </body>
            </html>
            """
        ),
    )

    count = CareerPageScanner().scan_all(db_session)

    assert count == 0
    assert db_session.query(JobPost).filter_by(source_url=existing_url).count() == 1


def test_seed_career_pages_does_not_insert_runtime_sources(db_session):
    """Career-page source catalogs must not silently become active runtime data."""
    from job_agent.seed import seed_career_pages

    seed_career_pages(db_session)
    seed_career_pages(db_session)

    count = db_session.query(CareerPageSource).count()
    assert count == 0
