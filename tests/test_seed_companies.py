from __future__ import annotations


def test_seed_italy_companies_inserts_rows(db_session):
    from job_agent.seed_companies import seed_italy_companies

    count = seed_italy_companies(db_session)

    assert count == 54


def test_seed_italy_companies_idempotent(db_session):
    from job_agent.seed_companies import seed_italy_companies

    seed_italy_companies(db_session)
    count = seed_italy_companies(db_session)

    assert count == 0


def test_reference_data_does_not_seed_career_page_sources(db_session):
    from job_agent.models import CareerPageSource
    from job_agent.seed import seed_reference_data

    seed_reference_data(db_session)

    assert db_session.query(CareerPageSource).count() == 0


def test_settings_save_rejects_more_than_4_roles(client):
    response = client.post(
        "/settings/save",
        json={"jobspy_discover_queries": ["A", "B", "C", "D", "E"]},
    )

    assert response.status_code == 422
    assert "4" in response.json()["detail"]
