from __future__ import annotations

from job_agent.models import CareerPageSource


def test_ui_companies_returns_200(client):
    response = client.get("/ui/companies")
    assert response.status_code == 200
    assert "Watchlist" in response.text


def test_toggle_active_flips_flag(client, db_session):
    source = CareerPageSource(
        company="TestCo",
        career_url="https://testco.example.com/jobs",
        country="Italy",
        active=True,
    )
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)

    response = client.post(f"/career-pages/{source.id}/toggle-active")
    assert response.status_code == 204

    db_session.refresh(source)
    assert source.active is False

    client.post(f"/career-pages/{source.id}/toggle-active")
    db_session.refresh(source)
    assert source.active is True


def test_toggle_active_returns_404_for_unknown(client):
    response = client.post("/career-pages/999999/toggle-active")
    assert response.status_code == 404


def test_ui_companies_shows_sources(client, db_session):
    source = CareerPageSource(
        company="VelocityCorp",
        career_url="https://vc.example.com/jobs",
        country="Italy",
        ats_type="greenhouse",
        ats_slug="velocitycorp",
        active=True,
    )
    db_session.add(source)
    db_session.commit()

    response = client.get("/ui/companies")

    assert response.status_code == 200
    assert "VelocityCorp" in response.text
    assert "greenhouse" in response.text
