from __future__ import annotations

import yaml


def test_yaml_overlay_overrides_defaults(tmp_path):
    """Values in user_settings.yml override defaults."""
    yml = tmp_path / "user_settings.yml"
    yml.write_text("target_job_seniority: senior\nmatch_min_score: 90\n", encoding="utf-8")

    from job_agent.config import Settings, load_user_settings_overlay

    settings_obj = Settings()
    load_user_settings_overlay(settings_obj, path=yml)
    assert settings_obj.target_job_seniority == "senior"
    assert settings_obj.match_min_score == 90


def test_yaml_overlay_loads_jobspy_detail_enrichment_fields(tmp_path):
    yml = tmp_path / "user_settings.yml"
    yml.write_text(
        "jobspy_detail_enrichment_enabled: true\njobspy_detail_enrichment_limit: 8\n",
        encoding="utf-8",
    )

    from job_agent.config import Settings, load_user_settings_overlay

    settings_obj = Settings()
    load_user_settings_overlay(settings_obj, path=yml)
    assert settings_obj.jobspy_detail_enrichment_enabled is True
    assert settings_obj.jobspy_detail_enrichment_limit == 8


def test_yaml_missing_does_not_crash(tmp_path):
    from job_agent.config import Settings, load_user_settings_overlay

    settings_obj = Settings()
    original = settings_obj.target_job_seniority
    load_user_settings_overlay(settings_obj, path=tmp_path / "nonexistent.yml")
    assert settings_obj.target_job_seniority == original


def test_settings_save_endpoint_writes_yaml(client, tmp_path, monkeypatch):
    from job_agent import config as cfg
    from job_agent import user_config

    temp_path = tmp_path / "us.yml"
    monkeypatch.setattr(user_config, "USER_SETTINGS_PATH", temp_path)
    monkeypatch.setattr(cfg, "_USER_SETTINGS_PATH", temp_path)

    original_seniority = cfg.settings.target_job_seniority
    try:
        response = client.post("/settings/save", json={"target_job_seniority": "mid"})
        assert response.status_code == 200
        data = yaml.safe_load(temp_path.read_text(encoding="utf-8"))
        assert data["target_job_seniority"] == "mid"
    finally:
        object.__setattr__(cfg.settings, "target_job_seniority", original_seniority)


def test_settings_save_accepts_jobspy_detail_enrichment_fields(client, tmp_path, monkeypatch):
    from job_agent import user_config

    temp_path = tmp_path / "us.yml"
    monkeypatch.setattr(user_config, "USER_SETTINGS_PATH", temp_path)

    response = client.post(
        "/settings/save",
        json={
            "jobspy_detail_enrichment_enabled": True,
            "jobspy_detail_enrichment_limit": 7,
        },
    )
    assert response.status_code == 200
    data = yaml.safe_load(temp_path.read_text(encoding="utf-8"))
    assert data["jobspy_detail_enrichment_enabled"] is True
    assert data["jobspy_detail_enrichment_limit"] == 7


def test_settings_save_rejects_unknown_field(client):
    response = client.post("/settings/save", json={"database_url": "hack"})
    assert response.status_code == 400


def test_settings_current_masks_api_keys(client):
    import job_agent.config as cfg

    original_key = cfg.settings.openai_api_key
    try:
        object.__setattr__(cfg.settings, "openai_api_key", "sk-real-key")
        response = client.get("/settings/current")
        assert response.status_code == 200
        assert response.json()["openai_api_key"] == "***"
    finally:
        object.__setattr__(cfg.settings, "openai_api_key", original_key)


def test_settings_reload_endpoint(client):
    response = client.post("/settings/reload")
    assert response.status_code == 200
    assert response.json()["status"] == "reloaded"


def test_settings_save_blank_api_key_does_not_overwrite(client, tmp_path, monkeypatch):
    from job_agent import config as cfg
    from job_agent.secrets import SENTINEL
    from job_agent import user_config

    temp_path = tmp_path / "us.yml"
    temp_path.write_text('openai_api_key: "sk-existing"\n', encoding="utf-8")
    monkeypatch.setattr(user_config, "USER_SETTINGS_PATH", temp_path)

    original = cfg.settings.openai_api_key
    try:
        object.__setattr__(cfg.settings, "openai_api_key", "sk-existing")
        response = client.post("/settings/save", json={"openai_api_key": ""})
        assert response.status_code == 200
        data = yaml.safe_load(temp_path.read_text(encoding="utf-8"))
        assert data["openai_api_key"] in {"sk-existing", SENTINEL}
    finally:
        object.__setattr__(cfg.settings, "openai_api_key", original)
