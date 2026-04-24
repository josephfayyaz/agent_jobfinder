from __future__ import annotations

from datetime import datetime, timedelta, timezone


def test_velocity_endpoint_no_logs(client):
    resp = client.get("/career-pages/999/velocity")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_surging"] is False
    assert data["recent_scans"] == []


def test_velocity_bulk_returns_surging_sources(db_session, client):
    from job_agent.models import CareerPageScanLog, CareerPageSource

    source = CareerPageSource(company="TestCo", career_url="https://test.co", active=True)
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)

    for hours_ago in range(2):
        db_session.add(
            CareerPageScanLog(
                source_id=source.id,
                scanned_at=datetime.now(timezone.utc) - timedelta(hours=hours_ago),
                jobs_found=5,
                new_jobs=2,
            )
        )
    db_session.commit()

    resp = client.get("/career-pages/velocity/bulk")
    assert resp.status_code == 200
    assert source.id in resp.json()["surging"]


def test_velocity_not_surging_with_single_scan(db_session, client):
    from job_agent.models import CareerPageScanLog, CareerPageSource

    source = CareerPageSource(company="SingleScan", career_url="https://single.co", active=True)
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)

    db_session.add(
        CareerPageScanLog(
            source_id=source.id,
            scanned_at=datetime.now(timezone.utc),
            jobs_found=3,
            new_jobs=1,
        )
    )
    db_session.commit()

    resp = client.get("/career-pages/velocity/bulk")
    assert resp.status_code == 200
    assert source.id not in resp.json()["surging"]


def test_velocity_ignores_old_scans(db_session, client):
    from job_agent.models import CareerPageScanLog, CareerPageSource

    source = CareerPageSource(company="OldCo", career_url="https://old.co", active=True)
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)

    for days_ago in (10, 11):
        db_session.add(
            CareerPageScanLog(
                source_id=source.id,
                scanned_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
                jobs_found=4,
                new_jobs=2,
            )
        )
    db_session.commit()

    resp = client.get("/career-pages/velocity/bulk")
    assert resp.status_code == 200
    assert source.id not in resp.json()["surging"]
