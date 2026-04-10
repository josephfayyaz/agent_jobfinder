from __future__ import annotations

import sys
from types import SimpleNamespace

from job_agent.models import JobPost


class _FakeDataFrame:
    def __init__(self, rows: list[dict]):
        self._rows = rows
        self.empty = not rows

    def __len__(self) -> int:
        return len(self._rows)

    def iterrows(self):
        for index, row in enumerate(self._rows):
            yield index, row


def test_discover_skips_when_disabled(monkeypatch, db_session):
    """When USE_JOBSPY=false, discover returns 0 without calling jobspy."""
    from job_agent.config import get_settings
    from job_agent.services.jobspy_service import JobSpyService

    settings = get_settings()
    monkeypatch.setattr(settings, "use_jobspy", False)

    count = JobSpyService().discover("Data Engineer", session=db_session)
    assert count == 0


def test_seniority_query_suffix_junior():
    from job_agent.services.jobspy_service import _build_seniority_query_suffix

    suffix = _build_seniority_query_suffix("junior")
    assert "junior" in suffix.lower()


def test_seniority_query_suffix_any():
    from job_agent.services.jobspy_service import _build_seniority_query_suffix

    suffix = _build_seniority_query_suffix("any")
    assert suffix == ""


def test_discover_deduplicates_existing_url(monkeypatch, db_session):
    """If URL already exists in DB, no new JobPost is created."""
    from job_agent.config import get_settings
    from job_agent.services.jobspy_service import JobSpyService

    settings = get_settings()
    monkeypatch.setattr(settings, "use_jobspy", True)
    monkeypatch.setattr(settings, "jobspy_request_delay", 0.0)
    monkeypatch.setattr("job_agent.services.jobspy_service.time.sleep", lambda *_args, **_kwargs: None)

    existing_url = "https://linkedin.com/jobs/view/999"
    db_session.add(
        JobPost(
            title="DE",
            company="Co",
            source_url=existing_url,
            canonical_apply_url=existing_url,
            status="new",
            description="",
        )
    )
    db_session.commit()

    fake_jobspy = SimpleNamespace(
        scrape_jobs=lambda **_kwargs: _FakeDataFrame(
            [
                {
                    "title": "DE",
                    "company": "Co",
                    "job_url": existing_url,
                    "location": "Italy",
                    "description": "",
                }
            ]
        )
    )
    monkeypatch.setitem(sys.modules, "jobspy", fake_jobspy)

    count = JobSpyService().discover("Data Engineer", session=db_session)

    assert count == 0
    assert db_session.query(JobPost).filter_by(source_url=existing_url).count() == 1
