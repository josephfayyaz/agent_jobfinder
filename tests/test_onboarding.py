from __future__ import annotations

import pytest
import yaml


def test_onboarding_status_endpoint_unconfigured(client, tmp_path, monkeypatch):
    import job_agent.routers.setup_state as setup_state

    monkeypatch.setattr(
        setup_state,
        "_USER_SETTINGS_FILE",
        tmp_path / "config" / "user_settings.yml",
    )
    response = client.get("/onboarding/status")
    assert response.status_code == 200
    data = response.json()
    assert "configured" in data
    assert data["configured"] is False


def test_prerequisites_check_fails_gracefully(monkeypatch):
    """LM Studio offline should warn but not block onboarding."""
    import job_agent.onboard as onboard

    monkeypatch.setattr(onboard, "_fetch_lm_studio_models", lambda _url: (False, []))
    monkeypatch.setattr(onboard, "_is_port_free", lambda _port: True)

    ok, models = onboard._run_prerequisites_check("http://localhost:1234/v1")

    assert ok is True
    assert models == []


def test_write_default_candidate_id_replaces_existing_value(tmp_path):
    from job_agent.onboard import _write_default_candidate_id

    env_path = tmp_path / ".env"
    env_path.write_text("APP_ENV=development\nDEFAULT_CANDIDATE_ID=old-id\n", encoding="utf-8")

    _write_default_candidate_id("new-id", env_path=env_path)

    content = env_path.read_text(encoding="utf-8")
    assert "DEFAULT_CANDIDATE_ID=new-id" in content
    assert "DEFAULT_CANDIDATE_ID=old-id" not in content


def test_run_onboarding_overwrites_provider_settings(tmp_path, monkeypatch):
    import job_agent.onboard as onboard
    import job_agent.user_config as user_config

    settings_path = tmp_path / "config" / "user_settings.yml"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        "anthropic_api_key: sk-ant-old\n"
        "use_claude_final_review: true\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(user_config, "USER_SETTINGS_PATH", settings_path)
    monkeypatch.setattr(onboard, "USER_SETTINGS_PATH", settings_path)
    monkeypatch.setattr(onboard, "load_user_settings_overlay", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(onboard, "_run_prerequisites_check", lambda _url: (True, ["small-model", "writer-model"]))
    monkeypatch.setattr(onboard, "_fetch_lm_studio_models", lambda _url: (True, ["small-model", "writer-model"]))
    monkeypatch.setattr(onboard, "_server_is_running", lambda: False)

    def prompt_select(message, choices, *, default, non_interactive=False):
        if "Which AI provider" in message:
            return "Local LLM (LM Studio)"
        if "Small/review model" in message:
            return "small-model"
        if "Writer model" in message:
            return "writer-model"
        if "Mid/extraction model" in message:
            return "small-model"
        if "Target job seniority" in message:
            return "junior"
        return default

    def prompt_text(message, *, default="", non_interactive=False):
        if "Primary location" in message:
            return "Italy"
        if "Job titles to search" in message:
            return "AI Engineer, Data Engineer"
        if "Path to your fact sheet" in message:
            return ""
        return default

    def prompt_confirm(message, *, default=True, non_interactive=False):
        if "Re-run setup?" in message:
            return True
        if "Enable automatic JobSpy discovery?" in message:
            return False
        if "Save these settings?" in message:
            return True
        return default

    monkeypatch.setattr(onboard, "_prompt_select", prompt_select)
    monkeypatch.setattr(onboard, "_prompt_text", prompt_text)
    monkeypatch.setattr(onboard, "_prompt_confirm", prompt_confirm)
    monkeypatch.setattr(onboard, "_prompt_int_range", lambda *args, **kwargs: 75)

    onboard.run_onboarding(non_interactive=False)

    data = yaml.safe_load(settings_path.read_text(encoding="utf-8"))
    assert data["anthropic_api_key"] == ""
    assert data["use_claude_final_review"] is False
    assert data["lm_studio_small_model"] == "small-model"
    assert data["lm_studio_writer_model"] == "writer-model"


@pytest.mark.parametrize(
    ("mode", "updates"),
    [
        ("openai", {"openai_api_key": "sk-test"}),
        ("anthropic", {"anthropic_api_key": "sk-ant-test"}),
        (
            "lm_studio",
            {
                "lm_studio_base_url": "http://localhost:1234/v1",
                "lm_studio_small_model": "fast-model",
                "lm_studio_writer_model": "writer-model",
            },
        ),
        (
            "ollama",
            {
                "ollama_base_url": "http://localhost:11434",
                "ollama_fast_model": "llama3",
                "ollama_writer_model": "llama3",
            },
        ),
    ],
)
def test_setup_status_reports_provider_ready_for_supported_modes(client, mode, updates):
    import job_agent.config as cfg

    tracked = {
        "llm_provider_mode": cfg.settings.llm_provider_mode,
        "openai_api_key": cfg.settings.openai_api_key,
        "anthropic_api_key": cfg.settings.anthropic_api_key,
        "lm_studio_base_url": cfg.settings.lm_studio_base_url,
        "lm_studio_small_model": cfg.settings.lm_studio_small_model,
        "lm_studio_writer_model": cfg.settings.lm_studio_writer_model,
        "ollama_base_url": getattr(cfg.settings, "ollama_base_url", ""),
        "ollama_fast_model": getattr(cfg.settings, "ollama_fast_model", ""),
        "ollama_writer_model": getattr(cfg.settings, "ollama_writer_model", ""),
    }
    try:
        object.__setattr__(cfg.settings, "llm_provider_mode", mode)
        object.__setattr__(cfg.settings, "openai_api_key", "")
        object.__setattr__(cfg.settings, "anthropic_api_key", "")
        object.__setattr__(cfg.settings, "lm_studio_base_url", "")
        object.__setattr__(cfg.settings, "lm_studio_small_model", "")
        object.__setattr__(cfg.settings, "lm_studio_writer_model", "")
        object.__setattr__(cfg.settings, "ollama_base_url", "")
        object.__setattr__(cfg.settings, "ollama_fast_model", "")
        object.__setattr__(cfg.settings, "ollama_writer_model", "")
        for key, value in updates.items():
            object.__setattr__(cfg.settings, key, value)

        response = client.get("/setup/status")
        assert response.status_code == 200
        data = response.json()
        assert data["provider"]["mode"] == mode
        assert data["provider"]["ready"] is True
    finally:
        for key, value in tracked.items():
            object.__setattr__(cfg.settings, key, value)


def test_onboarding_page_shows_job_language_proficiency_controls(client):
    response = client.get("/ui/onboarding")
    assert response.status_code == 200
    body = response.text
    assert "Job description languages" in body
    assert "set your proficiency" in body
    assert body.count(">Back<") >= 3


def test_onboarding_style_language_payload_persists_proficiency_levels(client, tmp_path, monkeypatch):
    from job_agent import user_config

    monkeypatch.setattr(user_config, "USER_SETTINGS_PATH", tmp_path / "user_settings.yml")
    response = client.post(
        "/settings/save",
        json={
            "job_search_countries": ["Italy"],
            "jobspy_discover_queries": ["Data Engineer"],
            "target_job_seniority": "junior",
            "job_search_languages": [
                {"name": "English", "level": "C1"},
                {"name": "Italian", "level": "B1"},
            ],
        },
    )
    assert response.status_code == 200, response.text
    data = yaml.safe_load((tmp_path / "user_settings.yml").read_text(encoding="utf-8"))
    assert data["job_search_languages"] == [
        {"name": "English", "level": "fluent"},
        {"name": "Italian", "level": "working"},
    ]
