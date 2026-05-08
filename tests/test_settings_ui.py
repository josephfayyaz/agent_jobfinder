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
    assert 'data-provider-panel="gemini" hidden' in body
    assert 'data-provider-panel="anthropic" hidden' in body
    assert "OpenAI Fast Model" not in body
    assert "OpenAI Writer Model" not in body
    assert "Claude Writer Model" not in body


def test_settings_page_save_button_uses_real_provider_fields_only(client):
    response = client.get("/ui/settings")
    assert response.status_code == 200
    body = response.text
    assert "onclick=\"saveSection('provider-form', ['lm_studio_base_url','lm_studio_small_model','lm_studio_writer_model','lm_studio_mid_model','ollama_base_url','ollama_fast_model','ollama_writer_model','openai_api_key','gemini_api_key','anthropic_api_key'])\"" in body
    assert "lm_studio_local_model" not in body.split("onclick=\"saveSection('provider-form',", 1)[1].split("])", 1)[0]
    assert "ollama_local_model" not in body.split("onclick=\"saveSection('provider-form',", 1)[1].split("])", 1)[0]


def test_settings_page_reflects_active_provider_and_stored_key_message(client):
    from job_agent.config import settings as runtime_settings

    tracked = {
        "llm_provider_mode": runtime_settings.llm_provider_mode,
        "gemini_api_key": runtime_settings.gemini_api_key,
    }
    try:
        object.__setattr__(runtime_settings, "llm_provider_mode", "gemini")
        object.__setattr__(runtime_settings, "gemini_api_key", "AIza-test")

        response = client.get("/ui/settings")
        assert response.status_code == 200
        body = response.text
        assert 'input type="radio" name="provider_mode" value="gemini" class="peer sr-only" checked' in body
        assert "Active provider: Google Gemini" in body
        assert "A Gemini key is already stored on this machine. Leave this blank to keep it." in body
        assert 'data-provider-panel="openai" hidden' in body
        assert 'data-provider-panel="gemini"' in body
        assert 'data-provider-panel="gemini" hidden' not in body
    finally:
        for key, value in tracked.items():
            object.__setattr__(runtime_settings, key, value)
