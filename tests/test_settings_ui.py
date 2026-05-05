from __future__ import annotations


def test_ui_settings_returns_200(client):
    response = client.get("/ui/settings")
    assert response.status_code == 200
    assert "LLM Provider" in response.text
    assert "Job Discovery" in response.text


def test_lm_studio_models_endpoint_offline(client, monkeypatch):
    import httpx

    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: (_ for _ in ()).throw(Exception("down")))
    response = client.get("/lm-studio/models")
    assert response.status_code == 200
    assert response.json()["online"] is False
    assert response.json()["models"] == []


def test_settings_reload_endpoint(client):
    response = client.post("/settings/reload")
    assert response.status_code == 200
    assert response.json()["status"] == "reloaded"


def test_settings_save_and_page_reflects_new_value(client, tmp_path, monkeypatch):
    from job_agent import config as cfg
    from job_agent import user_config

    temp_path = tmp_path / "us.yml"
    monkeypatch.setattr(user_config, "USER_SETTINGS_PATH", temp_path)

    original = cfg.settings.target_job_seniority
    try:
        save_response = client.post("/settings/save", json={"target_job_seniority": "senior"})
        assert save_response.status_code == 200

        response = client.get("/ui/settings")
        assert response.status_code == 200
        assert "senior" in response.text
    finally:
        object.__setattr__(cfg.settings, "target_job_seniority", original)


def test_settings_page_includes_provider_visibility_hooks(client):
    response = client.get("/ui/settings")
    assert response.status_code == 200
    body = response.text
    assert 'data-provider-panel="lm_studio"' in body
    assert 'data-provider-panel="openai"' in body
    assert 'data-provider-panel="gemini"' in body
    assert 'data-provider-action="lm_studio"' in body
    assert 'data-provider-action="ollama"' in body
    assert "OpenAI Fast Model" not in body
    assert "OpenAI Writer Model" not in body
    assert "Claude Writer Model" not in body
