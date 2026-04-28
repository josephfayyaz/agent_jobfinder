from __future__ import annotations

import pytest
from bs4 import BeautifulSoup


def test_normalize_provider_mode_maps_local_to_lm_studio():
    from job_agent.providers import normalize_provider_mode

    assert normalize_provider_mode("local") == "lm_studio"
    assert normalize_provider_mode("LM_STUDIO") == "lm_studio"
    assert normalize_provider_mode("ollama") == "ollama"


def test_health_ai_status_reports_ollama_ready(client):
    import job_agent.config as cfg

    original_mode = cfg.settings.llm_provider_mode
    original_base = getattr(cfg.settings, "ollama_base_url", "")
    original_fast = getattr(cfg.settings, "ollama_fast_model", "")
    original_writer = getattr(cfg.settings, "ollama_writer_model", "")
    try:
        object.__setattr__(cfg.settings, "llm_provider_mode", "ollama")
        object.__setattr__(cfg.settings, "ollama_base_url", "http://localhost:11434")
        object.__setattr__(cfg.settings, "ollama_fast_model", "llama3")
        object.__setattr__(cfg.settings, "ollama_writer_model", "llama3")
        response = client.get("/health/ai-status")
        assert response.status_code == 200
        data = response.json()
        assert data["configured"] is True
        assert data["provider_mode"] == "ollama"
        assert data["ollama_ready"] is True
    finally:
        object.__setattr__(cfg.settings, "llm_provider_mode", original_mode)
        object.__setattr__(cfg.settings, "ollama_base_url", original_base)
        object.__setattr__(cfg.settings, "ollama_fast_model", original_fast)
        object.__setattr__(cfg.settings, "ollama_writer_model", original_writer)


def test_health_ai_status_distinguishes_configured_from_selected_mode_ready(client):
    import job_agent.config as cfg

    original_mode = cfg.settings.llm_provider_mode
    original_key = cfg.settings.openai_api_key
    original_base = cfg.settings.lm_studio_base_url
    original_small = cfg.settings.lm_studio_small_model
    original_writer = cfg.settings.lm_studio_writer_model
    try:
        object.__setattr__(cfg.settings, "llm_provider_mode", "lm_studio")
        object.__setattr__(cfg.settings, "openai_api_key", "sk-test")
        object.__setattr__(cfg.settings, "lm_studio_base_url", "")
        object.__setattr__(cfg.settings, "lm_studio_small_model", "")
        object.__setattr__(cfg.settings, "lm_studio_writer_model", "")

        response = client.get("/health/ai-status")
        assert response.status_code == 200
        data = response.json()
        assert data["configured"] is True
        assert data["ready"] is False
        assert data["provider_mode"] == "lm_studio"
        assert data["openai_ready"] is True
        assert data["lm_studio_ready"] is False
    finally:
        object.__setattr__(cfg.settings, "llm_provider_mode", original_mode)
        object.__setattr__(cfg.settings, "openai_api_key", original_key)
        object.__setattr__(cfg.settings, "lm_studio_base_url", original_base)
        object.__setattr__(cfg.settings, "lm_studio_small_model", original_small)
        object.__setattr__(cfg.settings, "lm_studio_writer_model", original_writer)


@pytest.mark.parametrize(
    ("mode", "updates", "expected_ready"),
    [
        ("openai", {"openai_api_key": "sk-test"}, "openai_ready"),
        ("anthropic", {"anthropic_api_key": "sk-ant-test"}, "anthropic_ready"),
        (
            "lm_studio",
            {
                "lm_studio_base_url": "http://localhost:1234/v1",
                "lm_studio_small_model": "fast-model",
                "lm_studio_writer_model": "writer-model",
            },
            "lm_studio_ready",
        ),
        (
            "ollama",
            {
                "ollama_base_url": "http://localhost:11434",
                "ollama_fast_model": "llama3",
                "ollama_writer_model": "llama3",
            },
            "ollama_ready",
        ),
        ("mixed", {"openai_api_key": "sk-test"}, "openai_ready"),
    ],
)
def test_health_ai_status_reports_ready_for_each_provider_mode(client, mode, updates, expected_ready):
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

        response = client.get("/health/ai-status")
        assert response.status_code == 200
        data = response.json()
        assert data["provider_mode"] == mode
        assert data["configured"] is True
        assert data["ready"] is True
        assert data[expected_ready] is True
    finally:
        for key, value in tracked.items():
            object.__setattr__(cfg.settings, key, value)


def test_settings_save_accepts_ollama_mode(client, tmp_path, monkeypatch):
    from job_agent import config as cfg
    from job_agent import user_config

    temp_path = tmp_path / "user_settings.yml"
    monkeypatch.setattr(user_config, "USER_SETTINGS_PATH", temp_path)
    monkeypatch.setattr(cfg, "_USER_SETTINGS_PATH", temp_path)

    response = client.post(
        "/settings/save",
        json={
            "llm_provider_mode": "ollama",
            "ollama_base_url": "http://localhost:11434",
            "ollama_fast_model": "llama3",
            "ollama_writer_model": "llama3",
        },
    )
    assert response.status_code == 200
    saved = temp_path.read_text(encoding="utf-8")
    assert "llm_provider_mode: ollama" in saved
    assert "ollama_fast_model: llama3" in saved


def test_validate_provider_returns_lm_studio_models(client, monkeypatch):
    monkeypatch.setattr(
        "job_agent.routers.system._lm_studio_models_data",
        lambda _base_url=None: {"models": ["qwen-small", "qwen-writer"], "online": True},
    )
    response = client.post(
        "/providers/validate",
        json={"provider_mode": "lm_studio", "lm_studio_base_url": "http://localhost:1234/v1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["models"] == ["qwen-small", "qwen-writer"]


def test_validate_provider_reports_unreachable_lm_studio(client, monkeypatch):
    monkeypatch.setattr(
        "job_agent.routers.system._lm_studio_models_data",
        lambda _base_url=None: {"models": [], "online": False},
    )
    response = client.post(
        "/providers/validate",
        json={"provider_mode": "lm_studio", "lm_studio_base_url": "http://127.0.0.1:9999"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert "not reachable" in data["detail"].lower()


def test_validate_provider_normalizes_lm_studio_url_without_v1(client, monkeypatch):
    captured: dict[str, str | None] = {}

    def fake_models(base_url=None):
        captured["base_url"] = base_url
        return {"models": ["qwen-small", "qwen-writer"], "online": True}

    monkeypatch.setattr("job_agent.routers.system._lm_studio_models_data", fake_models)
    response = client.post(
        "/providers/validate",
        json={"provider_mode": "lm_studio", "lm_studio_base_url": "http://localhost:1234"},
    )
    assert response.status_code == 200
    assert captured["base_url"] == "http://localhost:1234/v1"


def test_settings_save_normalizes_lm_studio_url(client, tmp_path, monkeypatch):
    from job_agent import config as cfg
    from job_agent import user_config

    temp_path = tmp_path / "user_settings.yml"
    monkeypatch.setattr(user_config, "USER_SETTINGS_PATH", temp_path)
    monkeypatch.setattr(cfg, "_USER_SETTINGS_PATH", temp_path)

    response = client.post(
        "/settings/save",
        json={
            "llm_provider_mode": "lm_studio",
            "lm_studio_base_url": "http://localhost:1234",
            "lm_studio_small_model": "qwen-small",
            "lm_studio_writer_model": "qwen-writer",
        },
    )
    assert response.status_code == 200
    saved = temp_path.read_text(encoding="utf-8")
    assert "lm_studio_base_url: http://localhost:1234/v1" in saved


def test_extract_posted_date_from_json_ld():
    from job_agent.services.job_fetcher import _extract_posted_date_from_json_ld

    html = """
    <html><head>
      <script type="application/ld+json">
        {"@type":"JobPosting","datePosted":"2026-04-24T10:00:00Z"}
      </script>
    </head><body></body></html>
    """
    soup = BeautifulSoup(html, "lxml")
    assert _extract_posted_date_from_json_ld(soup) == "2026-04-24T10:00:00Z"


def test_extract_json_repairs_missing_closing_brace():
    from job_agent.llm import LLMRouter

    router = LLMRouter()
    broken = '{"questions":["One?"],"partial_fact_sheet":{"missing_information":{"x":"y"}}'
    parsed = router._extract_json(broken)
    assert parsed["questions"] == ["One?"]
    assert parsed["partial_fact_sheet"]["missing_information"]["x"] == "y"
