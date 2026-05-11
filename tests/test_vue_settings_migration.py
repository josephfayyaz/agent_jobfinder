from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_vue_settings_phase_one_routes_exist_and_legacy_settings_redirects() -> None:
    router = _read("frontend/vue/src/router/index.js")

    assert 'path: "/settings"' in router
    assert 'redirect: "/settings/ai-provider"' in router
    assert 'path: "/settings/ai-provider"' in router
    assert 'path: "/settings/workspace"' in router
    assert 'name: "settings-ai-provider"' in router
    assert 'name: "settings-workspace"' in router
    assert "AiProviderSettingsPage" in router
    assert "WorkspaceSettingsPage" in router


def test_ai_provider_page_is_component_based_without_legacy_globals() -> None:
    page = _read("frontend/vue/src/pages/settings/AiProviderSettingsPage.vue")
    source = "\n".join(
        _read(path)
        for path in (
            "frontend/vue/src/pages/settings/AiProviderSettingsPage.vue",
            "frontend/vue/src/components/settings/ProviderModeSelector.vue",
            "frontend/vue/src/components/settings/ProviderCredentialsForm.vue",
            "frontend/vue/src/components/settings/LocalProviderPanel.vue",
            "frontend/vue/src/composables/settings/useProviderSettings.js",
        )
    )

    for component in (
        "ProviderModeSelector",
        "ProviderCredentialsForm",
        "LocalProviderPanel",
        "ProviderValidationStatus",
    ):
        assert component in page
    assert "window.SettingsApp" not in source
    assert "ProviderController" not in source
    assert "document.getElementById" not in source
    assert "document.querySelector" not in source


def test_ai_provider_page_references_required_endpoints() -> None:
    provider_api = _read("frontend/vue/src/api/providerApi.js")
    settings_api = _read("frontend/vue/src/api/settingsApi.js")
    composable = _read("frontend/vue/src/composables/settings/useProviderSettings.js")

    assert 'vueApiFetch("/settings")' in settings_api
    assert 'apiFetch("/providers/validate"' in provider_api
    assert 'apiFetch("/settings/save"' in provider_api
    assert "/lm-studio/models" in provider_api
    assert "/ollama/models" in provider_api
    assert "validateProvider(buildValidationPayload" in composable
    assert "saveSettings(payload)" in composable


def test_provider_payload_behavior_matches_legacy_controller() -> None:
    helpers = _read("frontend/vue/src/composables/settings/providerHelpers.js")

    assert 'use_openai_review: mode === "openai"' in helpers
    assert 'use_claude_final_review: mode === "anthropic"' in helpers
    assert "if (openaiKey)" in helpers
    assert "if (geminiKey)" in helpers
    assert "if (anthropicKey)" in helpers
    assert "payload.lm_studio_small_model = selectedModel" in helpers
    assert "payload.lm_studio_writer_model = selectedModel" in helpers
    assert "payload.lm_studio_mid_model = selectedModel" in helpers
    assert "payload.ollama_fast_model = selectedModel" in helpers
    assert "payload.ollama_writer_model = selectedModel" in helpers
    assert "/embed/i" in helpers
    assert "LM Studio responded, but no usable chat models were found." in helpers
    assert "Ollama responded, but no usable chat models were found." in helpers


def test_vue_settings_provider_contract_exposes_flags_without_secret_fields(client) -> None:
    response = client.get("/api/vue/settings")

    assert response.status_code == 200
    payload = response.json()
    provider = payload["data"]["provider"]
    assert provider["llm_provider_mode"] in {"openai", "gemini", "anthropic", "lm_studio", "ollama"}
    for field in (
        "openai_configured",
        "gemini_configured",
        "anthropic_configured",
        "lm_studio_configured",
        "ollama_configured",
    ):
        assert isinstance(provider[field], bool)

    serialized = str(payload).lower()
    assert "api_key" not in serialized
    assert "secret" not in serialized
    assert "password" not in serialized


def test_workspace_settings_page_references_required_endpoints() -> None:
    settings_api = _read("frontend/vue/src/api/settingsApi.js")
    page = _read("frontend/vue/src/pages/settings/WorkspaceSettingsPage.vue")
    search_form = _read("frontend/vue/src/components/settings/SearchPreferencesForm.vue")

    for endpoint in (
        "/search/preferences/recommendations",
        "/settings/save",
        "/gmail/oauth/start",
        "/gmail/oauth/disconnect",
        "/settings/reload",
        "/workspace/",
    ):
        assert endpoint in settings_api

    for component in (
        "SearchPreferencesForm",
        "LanguageRowsEditor",
        "GmailIntegrationPanel",
        "CvSettingsForm",
        "WorkspaceMaintenancePanel",
    ):
        assert component in page or component in search_form


def test_workspace_settings_logic_stays_out_of_legacy_globals_and_dom_queries() -> None:
    source = "\n".join(
        _read(path)
        for path in (
            "frontend/vue/src/pages/settings/WorkspaceSettingsPage.vue",
            "frontend/vue/src/components/settings/SearchPreferencesForm.vue",
            "frontend/vue/src/components/settings/GmailIntegrationPanel.vue",
            "frontend/vue/src/components/settings/CvSettingsForm.vue",
            "frontend/vue/src/components/settings/WorkspaceMaintenancePanel.vue",
            "frontend/vue/src/composables/settings/useWorkspaceSettings.js",
        )
    )

    assert "window.SettingsApp" not in source
    assert "document.getElementById" not in source
    assert "document.querySelector" not in source


def test_workspace_search_language_and_maintenance_behaviors_are_migrated() -> None:
    helpers = _read("frontend/vue/src/composables/settings/workspaceHelpers.js")
    composable = _read("frontend/vue/src/composables/settings/useWorkspaceSettings.js")

    assert "roleCount = computed" in composable
    assert "roleCount.value > 4" in composable
    assert "return countries[0] || \"Italy\"" in helpers
    assert "job_search_countries: [country]" in helpers
    assert "English" in helpers
    assert "professional" in helpers
    assert "toLowerCase() === name.toLowerCase()" in helpers
    assert "addLanguageRow" in composable
    assert "removeLanguageRow" in composable
    assert "Enter the confirmation phrase first." in helpers
    assert "Type exactly:" in helpers
    assert "runWorkspaceAction(action, phrase)" in composable
    assert "/ui/workspace-reset?mode=reset" in composable
    assert "&open=1" in composable
    assert "/ui/workspace-reset?mode=delete" in composable


def test_vue_settings_workspace_contract_contains_workspace_sections(client) -> None:
    response = client.get("/api/vue/settings")

    assert response.status_code == 200
    data = response.json()["data"]
    for key in (
        "search",
        "language_options",
        "language_level_options",
        "gmail",
        "cv",
        "discovery",
        "share_url",
        "active_candidate_id",
        "maintenance",
    ):
        assert key in data
    assert isinstance(data["search"]["jobspy_discover_queries"], list)
    assert isinstance(data["gmail"]["gmail_connected"], bool)
    assert isinstance(data["cv"]["cv_pass_score"], int)
    assert isinstance(data["discovery"]["match_min_score"], int)
