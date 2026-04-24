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


def test_settings_save_rejects_more_than_5_roles(client):
    response = client.post(
        "/settings/save",
        json={"jobspy_discover_queries": ["A", "B", "C", "D", "E", "F"]},
    )

    assert response.status_code == 422
    assert "5" in response.json()["detail"]
