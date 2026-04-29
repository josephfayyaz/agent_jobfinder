from __future__ import annotations

from datetime import datetime, timezone
import uuid

import yaml


def test_search_preferences_endpoint_prefills_from_candidate_profile(client, db_session):
    from job_agent.models import Candidate, JobSource, MatchProfile

    candidate = Candidate(
        id=str(uuid.uuid4()),
        full_name="Test User",
        skills_json={
            "programming_languages": ["Python", "SQL"],
            "frameworks_and_platforms": [],
            "cloud_and_infra": [],
            "data_and_analytics": ["dbt", "Airflow"],
            "business_tools": [],
            "methods": [],
        },
        spoken_languages=[
            {"name": "English", "level": "C1"},
            {"name": "Italian", "level": "B1"},
        ],
    )
    profile = MatchProfile(
        id=str(uuid.uuid4()),
        candidate_id=candidate.id,
        target_roles=["Data Engineer", "Analytics Engineer"],
        location_preferences={"preferred_countries": ["Italy", "Germany"]},
    )
    db_session.add_all(
        [
            candidate,
            profile,
            JobSource(
                id=uuid.uuid4(),
                slug="eures",
                name="EURES",
                target_regions=["Italy", "EU"],
                role_families=["data", "analytics"],
                active=True,
                priority=10,
            ),
        ]
    )
    db_session.commit()

    response = client.get(f"/search/preferences/recommendations?candidate_id={candidate.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["countries"] == ["Italy", "Germany"]
    assert data["suggested_roles"] == ["Data Engineer", "Analytics Engineer", "ETL Developer", "BI Engineer"]
    assert any(item["name"] == "English" for item in data["selected_languages"])
    assert not any(item["name"] == "Italian" for item in data["selected_languages"])


def test_search_preferences_endpoint_suggests_contextual_roles_for_non_data_profile(client, db_session):
    from job_agent.models import Candidate, MatchProfile

    candidate = Candidate(
        id=str(uuid.uuid4()),
        full_name="Designer User",
        skills_json={
            "programming_languages": [],
            "frameworks_and_platforms": ["Figma"],
            "cloud_and_infra": [],
            "data_and_analytics": [],
            "business_tools": [],
            "methods": ["User research"],
        },
        spoken_languages=[{"name": "English", "level": "C1"}],
    )
    profile = MatchProfile(
        id=str(uuid.uuid4()),
        candidate_id=candidate.id,
        target_roles=["Product Designer"],
        location_preferences={"preferred_countries": ["Italy", "France"]},
    )
    db_session.add_all([candidate, profile])
    db_session.commit()

    response = client.get(f"/search/preferences/recommendations?candidate_id={candidate.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["suggested_roles"] == ["Product Designer", "UX Designer", "UI/UX Designer", "Interaction Designer"]


def test_settings_save_normalizes_search_preferences(client, tmp_path, monkeypatch):
    from job_agent import user_config

    monkeypatch.setattr(user_config, "USER_SETTINGS_PATH", tmp_path / "user_settings.yml")

    response = client.post(
        "/settings/save",
        json={
            "job_search_countries": ["Italy", "Germany"],
            "job_search_languages": [{"name": "English", "level": "C1"}],
            "jobspy_discover_queries": ["Data Engineer", "ML Engineer"],
        },
    )

    assert response.status_code == 200, response.text
    payload = yaml.safe_load((tmp_path / "user_settings.yml").read_text(encoding="utf-8"))
    assert payload["job_search_countries"] == ["Italy", "Germany"]
    assert payload["jobspy_discover_location"] == "Italy"
    assert payload["job_search_languages"][0]["name"] == "English"
    assert payload["job_search_languages"][0]["level"] == "fluent"


def test_jobs_endpoint_filters_by_selected_job_language(client, db_session, monkeypatch):
    import job_agent.config as cfg
    from job_agent.models import JobPost

    monkeypatch.setattr(
        cfg.settings,
        "job_search_languages",
        [{"name": "English", "level": "professional"}],
        raising=False,
    )

    english_job = JobPost(
        id=uuid.uuid4(),
        company="Acme",
        title="Data Engineer",
        description=(
            "We are looking for a data engineer. You will build Python pipelines and work with SQL. "
            "Requirements include experience with warehousing and analytics."
        ),
        source_name="manual",
        source_url="https://example.com/en",
        canonical_apply_url="https://example.com/en",
        created_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    italian_job = JobPost(
        id=uuid.uuid4(),
        company="Beta",
        title="Data Engineer",
        description=(
            "Siamo alla ricerca di un data engineer. Il candidato lavorera con dati e pipeline. "
            "Requisiti richiesti: esperienza con Python e SQL."
        ),
        source_name="manual",
        source_url="https://example.com/it",
        canonical_apply_url="https://example.com/it",
        created_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    db_session.add_all([english_job, italian_job])
    db_session.commit()

    response = client.get("/jobs?min_score=0")

    assert response.status_code == 200
    payload = response.json()
    companies = {item["company"] for item in payload}
    assert "Acme" in companies
    assert "Beta" not in companies

    response_all = client.get("/jobs?show_all=true")
    companies_all = {item["company"] for item in response_all.json()}
    assert {"Acme", "Beta"} <= companies_all


def test_detect_job_languages_handles_italian_text():
    from job_agent.search_preferences import detect_job_languages

    detected = detect_job_languages(
        "Siamo alla ricerca di un ingegnere dei dati. Requisiti richiesti: esperienza con Python e SQL."
    )

    assert detected
    assert detected[0]["name"] == "Italian"
