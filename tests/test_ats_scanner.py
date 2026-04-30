from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx

from job_agent.models import CareerPageScanLog, CareerPageSource, JobPost
from job_agent.services.ats_discovery import AtsDiscoveryService
from job_agent.services.ats_scanner import AtsApiScanner
from job_agent.services.career_scanner import CareerPageScanner


class _JsonResponse:
    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.is_success = 200 <= status_code < 300
        self.text = ""

    def raise_for_status(self):
        if not self.is_success:
            raise httpx.HTTPStatusError("error", request=httpx.Request("GET", "https://example.com"), response=None)

    def json(self):
        return self._payload


class _HtmlResponse:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code
        self.is_success = 200 <= status_code < 300


def _create_source(
    db_session,
    *,
    company: str = "Acme",
    ats_type: str | None = None,
    ats_slug: str | None = None,
) -> CareerPageSource:
    source = CareerPageSource(
        company=company,
        career_url=f"https://{company.lower()}.example.com/careers",
        country="Italy",
        ats_type=ats_type,
        ats_slug=ats_slug,
    )
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)
    return source


def test_ats_scanner_greenhouse_parses_response(monkeypatch):
    payload = {
        "jobs": [
            {
                "id": 1,
                "title": "ML Engineer",
                "absolute_url": "https://x/jobs/1",
                "location": {"name": "Milan"},
                "content": "Python and ML pipelines.",
            },
            {"id": 2, "title": "Data Engineer", "absolute_url": "https://x/jobs/2", "location": {"name": "Turin"}},
        ]
    }
    monkeypatch.setattr("job_agent.services.ats_scanner.httpx.get", lambda *_a, **_k: _JsonResponse(payload))

    jobs = AtsApiScanner().fetch_jobs("greenhouse", "acme")

    assert len(jobs) == 2
    assert jobs[0]["title"] == "ML Engineer"
    assert jobs[0]["url"] == "https://x/jobs/1"
    assert jobs[0]["location"] == "Milan"
    assert jobs[0]["description"] == "Python and ML pipelines."


def test_ats_scanner_lever_parses_response(monkeypatch):
    payload = [
        {
            "id": "1",
            "text": "MLOps Engineer",
            "hostedUrl": "https://x/lever/1",
            "categories": {"location": "Rome"},
            "descriptionPlain": "Operate ML systems.",
        }
    ]
    monkeypatch.setattr("job_agent.services.ats_scanner.httpx.get", lambda *_a, **_k: _JsonResponse(payload))

    jobs = AtsApiScanner().fetch_jobs("lever", "acme")

    assert jobs[0]["title"] == "MLOps Engineer"
    assert jobs[0]["url"] == "https://x/lever/1"
    assert jobs[0]["location"] == "Rome"
    assert jobs[0]["description"] == "Operate ML systems."


def test_ats_scanner_ashby_parses_response(monkeypatch):
    payload = {
        "jobPostings": [
            {
                "id": "1",
                "title": "Platform Engineer",
                "jobPostingUrl": "https://x/ashby/1",
                "locationName": "Remote",
                "descriptionHtml": "<p>Build platform services.</p>",
            }
        ]
    }
    monkeypatch.setattr("job_agent.services.ats_scanner.httpx.get", lambda *_a, **_k: _JsonResponse(payload))

    jobs = AtsApiScanner().fetch_jobs("ashby", "acme")

    assert jobs[0]["title"] == "Platform Engineer"
    assert jobs[0]["url"] == "https://x/ashby/1"
    assert jobs[0]["location"] == "Remote"
    assert jobs[0]["description"] == "<p>Build platform services.</p>"


def test_ats_discovery_service_filters_and_saves_matching_jobs(monkeypatch, db_session, db_track):
    _create_source(db_session, company="GreenCo", ats_type="greenhouse", ats_slug="greenco")
    monkeypatch.setattr(
        "job_agent.services.ats_discovery.AtsApiScanner.fetch_jobs",
        lambda *_a, **_k: [
            {
                "title": "Junior Data Engineer",
                "url": "https://greenco.example/jobs/1",
                "location": "Milan, Italy",
                "description": "Python SQL ETL pipelines for analytics teams.",
            },
            {
                "title": "Senior Accountant",
                "url": "https://greenco.example/jobs/2",
                "location": "Milan, Italy",
                "description": "Accounting and treasury management.",
            },
        ],
    )

    result = AtsDiscoveryService(db_session).discover_active_sources(
        roles=["Data Engineer"],
        selected_country="Italy",
        seniority="junior",
    )

    assert result["ats_sources_scanned"] == 1
    assert result["ats_raw_hits"] == 2
    assert result["saved_jobs"] == 1
    post = db_session.query(JobPost).filter_by(company="GreenCo").one()
    assert post.title == "Junior Data Engineer"
    assert post.source_name == "ats_greenhouse"


def test_ats_discovery_service_skips_broken_source_and_continues(monkeypatch, db_session, db_track):
    _create_source(db_session, company="BrokenCo", ats_type="greenhouse", ats_slug="broken")
    _create_source(db_session, company="HealthyCo", ats_type="lever", ats_slug="healthy")

    def _fake_fetch(_self, ats_type: str, ats_slug: str):
        if ats_slug == "broken":
            raise httpx.HTTPStatusError(
                "missing",
                request=httpx.Request("GET", "https://example.com/broken"),
                response=httpx.Response(404, request=httpx.Request("GET", "https://example.com/broken")),
            )
        return [
            {
                "title": "Junior Financial Analyst",
                "url": "https://healthy.example/jobs/1",
                "location": "Milan, Italy",
                "description": "Excel forecasting and finance reporting support.",
            }
        ]

    monkeypatch.setattr("job_agent.services.ats_discovery.AtsApiScanner.fetch_jobs", _fake_fetch)

    result = AtsDiscoveryService(db_session).discover_active_sources(
        roles=["Financial Analyst"],
        selected_country="Italy",
        seniority="junior",
    )

    assert result["ats_sources_scanned"] == 2
    assert result["ats_raw_hits"] == 1
    assert result["saved_jobs"] == 1
    assert db_session.query(JobPost).filter_by(company="HealthyCo").count() == 1


def test_scan_one_ats_creates_job_posts(monkeypatch, db_session, db_track):
    source = _create_source(db_session, ats_type="greenhouse", ats_slug="acme")
    monkeypatch.setattr(
        "job_agent.services.career_scanner.AtsApiScanner.fetch_jobs",
        lambda *_a, **_k: [
            {"title": "ML Engineer", "url": "https://acme/jobs/1", "location": "Milan"},
            {"title": "Data Engineer", "url": "https://acme/jobs/2", "location": "Turin"},
        ],
    )

    count = CareerPageScanner()._scan_one_ats(source, db_session, [db_track])

    assert count == 2
    assert db_session.query(JobPost).filter_by(company="Acme").count() == 2


def test_scan_one_ats_deduplicates_existing_urls(monkeypatch, db_session, db_track):
    source = _create_source(db_session, ats_type="greenhouse", ats_slug="acme")
    db_session.add(
        JobPost(
            id=uuid4(),
            source_name="career_page",
            source_url="https://acme/jobs/1",
            canonical_apply_url="https://acme/jobs/1",
            company="Acme",
            title="Existing",
            location="Milan",
            country="Italy",
            description="",
            status="new",
        )
    )
    db_session.commit()
    monkeypatch.setattr(
        "job_agent.services.career_scanner.AtsApiScanner.fetch_jobs",
        lambda *_a, **_k: [
            {"title": "Existing", "url": "https://acme/jobs/1", "location": "Milan"},
            {"title": "New Role", "url": "https://acme/jobs/2", "location": "Rome"},
        ],
    )

    count = CareerPageScanner()._scan_one_ats(source, db_session, [db_track])

    assert count == 1
    assert db_session.query(JobPost).filter(JobPost.company == "Acme").count() == 2


def test_scan_one_falls_back_to_html_on_ats_failure(monkeypatch, db_session, db_track):
    source = _create_source(db_session, ats_type="greenhouse", ats_slug="acme")
    monkeypatch.setattr(
        "job_agent.services.career_scanner.AtsApiScanner.fetch_jobs",
        lambda *_a, **_k: (_ for _ in ()).throw(httpx.HTTPError("ATS down")),
    )
    monkeypatch.setattr(
        "job_agent.services.career_scanner.httpx.get",
        lambda *_a, **_k: _HtmlResponse('<html><body><a href="/jobs/ml">ML Engineer</a></body></html>'),
    )

    count = CareerPageScanner()._scan_one(source, db_session, [db_track])

    assert count == 1


def test_check_velocity_spikes_returns_spikes_above_threshold(monkeypatch, db_session):
    from job_agent.config import settings

    monkeypatch.setattr(settings, "velocity_spike_threshold", 3)
    source = _create_source(db_session, company="SpikeCo")
    db_session.add(CareerPageScanLog(source_id=source.id, jobs_found=8, new_jobs=5))
    db_session.commit()

    spikes = CareerPageScanner().check_velocity_spikes(db_session)

    assert len(spikes) == 1
    assert spikes[0]["company"] == "SpikeCo"
    assert spikes[0]["new_jobs"] == 5


def test_velocity_spike_threshold_filters_below_threshold(monkeypatch, db_session):
    from job_agent.config import settings

    monkeypatch.setattr(settings, "velocity_spike_threshold", 3)
    source = _create_source(db_session, company="CalmCo")
    db_session.add(CareerPageScanLog(source_id=source.id, jobs_found=4, new_jobs=2))
    db_session.commit()

    spikes = CareerPageScanner().check_velocity_spikes(db_session)

    assert spikes == []


def test_velocity_spike_old_log_excluded(monkeypatch, db_session):
    """Logs older than 2 hours must NOT trigger a spike alert."""
    from job_agent.config import settings

    monkeypatch.setattr(settings, "velocity_spike_threshold", 3)
    source = _create_source(db_session, company="OldCo")
    old_time = datetime.now(timezone.utc) - timedelta(hours=3)
    log = CareerPageScanLog(source_id=source.id, jobs_found=10, new_jobs=8)
    db_session.add(log)
    db_session.commit()
    log.scanned_at = old_time
    db_session.commit()

    spikes = CareerPageScanner().check_velocity_spikes(db_session)

    assert spikes == []


def test_velocity_spike_recent_log_included(monkeypatch, db_session):
    """Logs within the last 2 hours above threshold MUST be returned."""
    from job_agent.config import settings

    monkeypatch.setattr(settings, "velocity_spike_threshold", 3)
    source = _create_source(db_session, company="RecentCo")
    db_session.add(CareerPageScanLog(source_id=source.id, jobs_found=6, new_jobs=5))
    db_session.commit()

    spikes = CareerPageScanner().check_velocity_spikes(db_session)

    assert len(spikes) == 1
    assert spikes[0]["company"] == "RecentCo"


def test_create_career_page_with_ats_type(client, db_session):
    response = client.post(
        "/career-pages",
        params={
            "company": "GreenhouseCo",
            "career_url": "https://greenhouseco.example.com/careers",
            "country": "Italy",
            "ats_type": "greenhouse",
            "ats_slug": "greenhouseco",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    source = db_session.get(CareerPageSource, payload["id"])
    assert source is not None
    assert source.ats_type == "greenhouse"
    assert source.ats_slug == "greenhouseco"


def test_create_career_page_rejects_invalid_ats_type(client):
    response = client.post(
        "/career-pages",
        params={
            "company": "BadCo",
            "career_url": "https://badco.example.com/careers",
            "ats_type": "invalid",
        },
    )

    assert response.status_code == 400
    assert "Invalid ats_type" in response.json()["detail"]


def test_posting_velocity_endpoint_returns_grouped_data(client, db_session):
    source = _create_source(db_session, company="VelocityCo", ats_type="lever", ats_slug="velocityco")
    now = datetime.now(timezone.utc)
    db_session.add(CareerPageScanLog(source_id=source.id, scanned_at=now, jobs_found=5, new_jobs=2))
    db_session.add(CareerPageScanLog(source_id=source.id, scanned_at=now, jobs_found=3, new_jobs=1))
    db_session.commit()

    response = client.get("/analytics/posting-velocity", params={"days": 7})

    assert response.status_code == 200
    data = response.json()
    assert data["days"] == 7
    assert data["companies"][0]["company"] == "VelocityCo"
    assert data["companies"][0]["new_jobs"] == 3
