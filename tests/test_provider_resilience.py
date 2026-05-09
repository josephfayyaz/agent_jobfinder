from __future__ import annotations

import pytest
from bs4 import BeautifulSoup
from types import SimpleNamespace
from unittest.mock import MagicMock


def test_normalize_provider_mode_maps_local_to_lm_studio():
    from job_agent.providers import normalize_provider_mode

    assert normalize_provider_mode("local") == "lm_studio"
    assert normalize_provider_mode("LM_STUDIO") == "lm_studio"
    assert normalize_provider_mode("ollama") == "ollama"
    assert normalize_provider_mode("gemini") == "gemini"


def test_normalize_provider_mode_prefers_ready_local_provider_for_legacy_mixed(monkeypatch):
    from job_agent.providers import normalize_provider_mode

    monkeypatch.setattr(
        "job_agent.providers.provider_readiness_snapshot",
        lambda: {
            "openai_ready": False,
            "gemini_ready": False,
            "anthropic_ready": False,
            "lm_studio_ready": True,
            "ollama_ready": False,
        },
    )

    assert normalize_provider_mode("mixed") == "lm_studio"


def test_normalize_provider_mode_falls_back_to_default_when_legacy_mixed_has_no_ready_provider(monkeypatch):
    from job_agent.providers import normalize_provider_mode

    monkeypatch.setattr(
        "job_agent.providers.provider_readiness_snapshot",
        lambda: {
            "openai_ready": False,
            "gemini_ready": False,
            "anthropic_ready": False,
            "lm_studio_ready": False,
            "ollama_ready": False,
        },
    )

    assert normalize_provider_mode("mixed", default="ollama") == "ollama"


def test_provider_capabilities_returns_gemini_contract():
    from job_agent.providers import provider_capabilities

    payload = provider_capabilities("gemini")

    assert payload["label"] == "Google Gemini"
    assert payload["supports_native_json"] is True
    assert payload["workflow_prompt_char_limits"]["intake"] > 0


def test_provider_prompt_char_limit_uses_registry():
    from job_agent.providers import provider_prompt_char_limit

    assert provider_prompt_char_limit("intake", "gemini") == 14000
    assert provider_prompt_char_limit("cv_writer", "lm_studio") == 14000


def test_provider_unavailable_error_carries_taxonomy_fields():
    from job_agent.llm import ProviderUnavailableError

    exc = ProviderUnavailableError(
        "Gemini auth failed",
        provider="gemini",
        category="auth",
        retryable=True,
    )
    assert exc.provider == "gemini"
    assert exc.category == "auth"
    assert exc.retryable is True


def test_generate_with_retry_allows_one_extra_attempt_for_retryable_provider_errors():
    from job_agent.llm import LLMRouter, ProviderUnavailableError

    router = LLMRouter()
    attempts = {"count": 0}

    def fake_generate(**_kwargs):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise ProviderUnavailableError(
                "Gemini temporary outage",
                provider="gemini",
                category="service_unavailable",
                retryable=True,
            )
        return {"ok": True}

    router.generate = fake_generate  # type: ignore[method-assign]

    result = router.generate_with_retry(
        role="small",
        system_prompt="system",
        user_prompt="user",
    )

    assert result == {"ok": True}
    assert attempts["count"] == 3


def test_generate_local_delegates_to_local_provider_adapter(monkeypatch):
    from job_agent.llm import LLMRouter

    expected = {"adapter": "local", "ok": True}
    monkeypatch.setattr("job_agent.llm.generate_local_gateway_json", lambda **_kwargs: expected)

    result = LLMRouter()._generate_local(
        role="small",
        system_prompt="system",
        user_prompt="user",
        temperature=0.2,
    )

    assert result == expected


def test_generate_ollama_delegates_to_local_provider_adapter(monkeypatch):
    from job_agent.llm import LLMRouter

    expected = {"adapter": "ollama", "ok": True}
    monkeypatch.setattr("job_agent.llm.generate_ollama_json", lambda **_kwargs: expected)

    result = LLMRouter()._generate_ollama(
        role="small",
        system_prompt="system",
        user_prompt="user",
        temperature=0.2,
    )

    assert result == expected


def test_generate_with_openai_delegates_to_openai_adapter(monkeypatch):
    from job_agent.llm import LLMRouter

    expected = {"adapter": "openai", "ok": True}
    monkeypatch.setattr("job_agent.llm.generate_openai_json", lambda **_kwargs: expected)

    router = LLMRouter()
    router._openai_client = object()

    result = router.generate_with_openai(
        model="gpt-4o-mini",
        system_prompt="system",
        user_prompt="user",
    )

    assert result == expected


def test_generate_with_claude_delegates_to_claude_adapter(monkeypatch):
    from job_agent.llm import LLMRouter

    expected = {"adapter": "claude", "ok": True}
    monkeypatch.setattr("job_agent.llm.generate_claude_json", lambda **_kwargs: expected)

    router = LLMRouter()
    router._anthropic_client = object()

    result = router.generate_with_claude(
        system_prompt="system",
        user_prompt="user",
    )

    assert result == expected


def test_generate_with_gemini_delegates_to_gemini_adapter(monkeypatch):
    import job_agent.config as cfg
    from job_agent.llm import LLMRouter

    tracked = {
        "gemini_api_key": cfg.settings.gemini_api_key,
        "gemini_model": cfg.settings.gemini_model,
    }
    expected = {"adapter": "gemini", "ok": True}
    try:
        object.__setattr__(cfg.settings, "gemini_api_key", "AIza-test")
        object.__setattr__(cfg.settings, "gemini_model", "gemini-2.5-flash")
        monkeypatch.setattr("job_agent.llm.generate_gemini_json", lambda **_kwargs: expected)

        result = LLMRouter().generate_with_gemini(
            system_prompt="system",
            user_prompt="user",
        )

        assert result == expected
    finally:
        for key, value in tracked.items():
            object.__setattr__(cfg.settings, key, value)


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
        ("gemini", {"gemini_api_key": "AIza-test"}, "gemini_ready"),
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
    ],
)
def test_health_ai_status_reports_ready_for_each_provider_mode(client, mode, updates, expected_ready):
    import job_agent.config as cfg

    tracked = {
        "llm_provider_mode": cfg.settings.llm_provider_mode,
        "openai_api_key": cfg.settings.openai_api_key,
        "gemini_api_key": cfg.settings.gemini_api_key,
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
        object.__setattr__(cfg.settings, "gemini_api_key", "")
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


def test_settings_save_accepts_gemini_mode(client, tmp_path, monkeypatch):
    from job_agent import config as cfg
    from job_agent import user_config

    temp_path = tmp_path / "user_settings.yml"
    monkeypatch.setattr(user_config, "USER_SETTINGS_PATH", temp_path)
    monkeypatch.setattr(cfg, "_USER_SETTINGS_PATH", temp_path)

    response = client.post(
        "/settings/save",
        json={
            "llm_provider_mode": "gemini",
            "gemini_api_key": "AIza-test",
        },
    )
    assert response.status_code == 200
    saved = temp_path.read_text(encoding="utf-8")
    assert "llm_provider_mode: gemini" in saved


def test_settings_save_accepts_lm_studio_mode(client, tmp_path, monkeypatch):
    from job_agent import config as cfg
    from job_agent import user_config

    temp_path = tmp_path / "user_settings.yml"
    monkeypatch.setattr(user_config, "USER_SETTINGS_PATH", temp_path)
    monkeypatch.setattr(cfg, "_USER_SETTINGS_PATH", temp_path)

    response = client.post(
        "/settings/save",
        json={
            "llm_provider_mode": "lm_studio",
            "lm_studio_base_url": "http://localhost:1234/v1",
            "lm_studio_small_model": "qwen-small",
            "lm_studio_writer_model": "qwen-writer",
            "lm_studio_mid_model": "qwen-mid",
        },
    )
    assert response.status_code == 200
    saved = temp_path.read_text(encoding="utf-8")
    assert "llm_provider_mode: lm_studio" in saved
    assert "lm_studio_base_url: http://localhost:1234/v1" in saved
    assert "lm_studio_small_model: qwen-small" in saved
    assert "lm_studio_writer_model: qwen-writer" in saved
    assert "lm_studio_mid_model: qwen-mid" in saved


def test_settings_save_clears_previous_provider_configuration_when_switching_modes(client, tmp_path, monkeypatch):
    from job_agent import config as cfg
    from job_agent import user_config

    temp_path = tmp_path / "user_settings.yml"
    temp_path.write_text(
        "llm_provider_mode: openai\n"
        "openai_api_key: sk-old\n"
        "lm_studio_base_url: http://localhost:1234/v1\n"
        "lm_studio_small_model: qwen-small\n"
        "lm_studio_writer_model: qwen-writer\n",
        encoding="utf-8",
    )
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
    assert response.status_code == 200, response.text
    saved = temp_path.read_text(encoding="utf-8")
    assert "llm_provider_mode: ollama" in saved
    assert "ollama_fast_model: llama3" in saved
    assert "openai_api_key: ''" in saved or "openai_api_key: \"\"" in saved
    assert "lm_studio_base_url: ''" in saved or "lm_studio_base_url: \"\"" in saved
    assert "lm_studio_small_model: ''" in saved or "lm_studio_small_model: \"\"" in saved


def test_settings_save_rejects_mixed_mode(client):
    response = client.post("/settings/save", json={"llm_provider_mode": "mixed"})
    assert response.status_code == 422
    assert "must be openai, gemini, anthropic, lm_studio, or ollama" in response.text


def test_validate_provider_rejects_mixed_mode(client):
    response = client.post("/providers/validate", json={"provider_mode": "mixed"})
    assert response.status_code == 422
    assert "must be openai, gemini, anthropic, lm_studio, or ollama" in response.text


def test_validate_provider_returns_lm_studio_models(client, monkeypatch):
    monkeypatch.setattr(
        "job_agent.routers.system._lm_studio_models_data",
        lambda _base_url=None: {
            "models": ["qwen-small", "qwen-writer"],
            "online": True,
            "target_url": "http://localhost:1234/v1",
            "error": "",
        },
    )
    response = client.post(
        "/providers/validate",
        json={"provider_mode": "lm_studio", "lm_studio_base_url": "http://localhost:1234/v1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["models"] == ["qwen-small", "qwen-writer"]


def test_validate_provider_reports_lm_studio_target_url_when_offline(client, monkeypatch):
    monkeypatch.setattr(
        "job_agent.routers.system._lm_studio_models_data",
        lambda _base_url=None: {
            "models": [],
            "online": False,
            "target_url": "http://localhost:1234/v1",
            "error": "Connection refused",
        },
    )
    response = client.post(
        "/providers/validate",
        json={"provider_mode": "lm_studio", "lm_studio_base_url": "http://localhost:1234/v1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert "http://localhost:1234/v1/models" in data["detail"]
    assert "Connection refused" in data["detail"]


def test_validate_provider_accepts_gemini(client, monkeypatch):
    import httpx

    class Response:
        status_code = 200
        is_success = True

        def json(self):
            return {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}

    def fake_post(*args, **kwargs):
        assert kwargs.get("params", {}).get("key") == "AIza-test"
        return Response()

    monkeypatch.setattr(httpx, "post", fake_post)
    response = client.post(
        "/providers/validate",
        json={"provider_mode": "gemini", "gemini_api_key": "AIza-test"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["provider_mode"] == "gemini"


def test_validate_provider_surfaces_gemini_request_errors(client, monkeypatch):
    import httpx

    class Response:
        status_code = 400
        is_success = False
        text = '{"error":{"code":400,"message":"Developer instruction error","status":"INVALID_ARGUMENT"}}'

    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: Response())
    response = client.post(
        "/providers/validate",
        json={"provider_mode": "gemini", "gemini_api_key": "AIza-test"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is False
    assert "Developer instruction error" in payload["detail"]


def test_workflow_review_uses_router_generate_for_active_provider(monkeypatch):
    import job_agent.config as cfg
    from job_agent.services.workflows import CVWorkflowService, WorkflowContext

    tracked = {
        "llm_provider_mode": cfg.settings.llm_provider_mode,
        "use_openai_review": cfg.settings.use_openai_review,
        "use_claude_final_review": cfg.settings.use_claude_final_review,
    }
    try:
        object.__setattr__(cfg.settings, "llm_provider_mode", "lm_studio")
        object.__setattr__(cfg.settings, "use_openai_review", True)
        object.__setattr__(cfg.settings, "use_claude_final_review", True)

        router = MagicMock()
        router.generate.return_value = {
            "score": 82,
            "decision": "pass",
            "gaps": [],
            "must_fix": [],
            "keyword_coverage": [],
            "revised_summary": "",
        }
        router.generate_with_openai.side_effect = AssertionError("generate_with_openai should not be used")
        router.generate_with_claude.side_effect = AssertionError("generate_with_claude should not be used")

        service = CVWorkflowService(session=MagicMock(), router=router)
        context = WorkflowContext(
            profile=SimpleNamespace(
                full_name="Test User",
                email="test@example.com",
                phone="",
                location="Milan",
                linkedin_url="",
                github_url="",
                public_brand_summary="",
                experiences=[],
                projects=[],
                education=[],
                certifications=[],
                achievements=[],
                global_skills=["Python"],
                additional_notes={},
            ),
            track=SimpleNamespace(
                slug="data-engineer",
                title="Data Engineer",
                role_family="data",
                baseline_summary="",
                target_keywords=["Python"],
                emphasis={},
                linkedin_strategy="",
                github_strategy="",
            ),
            job=SimpleNamespace(
                company="Acme",
                title="Data Engineer",
                location="Milan, Italy",
                role_track_hint="",
                description="Looking for Python experience",
                extracted_metadata={},
            ),
        )

        review = service._review_draft(
            context=context,
            draft_content={
                "professional_summary": "Data engineer focused on Python and SQL.",
                "selected_experiences": [],
                "selected_projects": [],
                "selected_skills": ["Python", "SQL"],
            },
            force_cloud_review=True,
            presentation_mode="junior",
        )

        assert review["score"] == 82
        router.generate.assert_called_once()
    finally:
        for key, value in tracked.items():
            object.__setattr__(cfg.settings, key, value)


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
