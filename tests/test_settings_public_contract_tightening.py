from __future__ import annotations

from collections.abc import Iterator

_VUE_HTML_MARKER = '<div id="app">'
_ALLOWED_UNSAFE_KEYS = {
    "ok",
    "providers",
    "provider_status",
    "name",
    "label",
    "configured",
    "available",
    "enabled",
    "local",
    "default_candidate_id",
    "settings_file_available",
    "artifacts_available",
    "fact_sheet_configured",
    "openai_configured",
    "gemini_configured",
    "anthropic_configured",
    "lm_studio_configured",
    "ollama_configured",
    "openai_available",
    "gemini_available",
    "anthropic_available",
    "lm_studio_available",
    "ollama_available",
    "local_providers_available",
    "remote_providers_configured",
    "gmail_oauth_configured",
    "gmail_legacy_configured",
    "gmail_configured",
    "secrets_exposed",
    "paths_exposed",
    "target_job_seniority",
    "match_min_score",
    "discovery_min_fit_score",
    "discovery_max_visible_jobs",
    "cv_pass_score",
    "cv_revise_score",
    "bullet_clarify_word_limit",
    "use_jobspy",
    "jobspy_detail_enrichment_enabled",
    "jobspy_detail_enrichment_limit",
    "jobspy_discover_location",
    "job_search_countries",
    "job_search_languages",
    "jobspy_discover_queries",
    "gmail_label_filter",
    "gmail_auto_sync",
}
_UNSAFE_KEY_PARTS = (
    "api_key",
    "token",
    "secret",
    "password",
    "credential",
    "private_key",
    "access_key",
    "refresh_token",
    "keyring",
    "path",
    "file_path",
    "absolute_path",
    "artifacts_dir",
    "fact_sheet_path",
    "url",
    "base_url",
    "endpoint",
    "host",
    "port",
    "model",
    "model_name",
)
_UNSAFE_VALUE_SNIPPETS = (
    "/Users/",
    "/home/",
    "/var/",
    "/tmp/",
    "~/",
    "file:",
    "http://localhost",
    "http://127.0.0.1",
    "localhost:",
    "127.0.0.1:",
    "sk-",
    "****",
    "gpt-",
    "claude-",
    "gemini-",
    "qwen",
    "llama",
)


def _walk_json(node: object, path: str = "$") -> Iterator[tuple[str, object]]:
    yield path, node
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _walk_json(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk_json(value, f"{path}[{index}]")


def _unsafe_entries(payload: object) -> list[str]:
    hits: list[str] = []
    for path, node in _walk_json(payload):
        key_name = path.rsplit(".", 1)[-1].lower()
        if key_name not in _ALLOWED_UNSAFE_KEYS and any(part in key_name for part in _UNSAFE_KEY_PARTS):
            hits.append(f"unsafe key at {path}")
        if isinstance(node, str):
            lowered = node.lower()
            if path.endswith(".name") or path.endswith(".label"):
                continue
            if any(snippet.lower() in lowered for snippet in _UNSAFE_VALUE_SNIPPETS):
                hits.append(f"unsafe value at {path}: {node}")
    return hits


def test_settings_current_contract_is_small_and_safe(client) -> None:
    response = client.get("/settings/current")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    payload = response.json()
    assert payload["ok"] is True
    assert payload["secrets_exposed"] is False
    assert payload["paths_exposed"] is False
    assert payload["artifacts_available"] in (True, False)
    assert payload["fact_sheet_configured"] in (True, False)
    assert payload["gmail_configured"] in (True, False)
    assert payload["openai_configured"] in (True, False)
    assert payload["lm_studio_configured"] in (True, False)
    assert payload["local_providers_available"] in (True, False)
    assert payload["remote_providers_configured"] in (True, False)
    assert isinstance(payload["providers"], list)
    assert isinstance(payload["provider_status"], dict)
    assert _unsafe_entries(payload) == []


def test_settings_current_omits_provider_urls_and_models(client) -> None:
    payload = client.get("/settings/current").json()
    serialized = str(payload).lower()

    assert "lm_studio_base_url" not in payload
    assert "ollama_base_url" not in payload
    assert "gmail_oauth_client_id" not in payload
    assert "openai_review_model" not in payload
    assert "anthropic_model" not in payload
    assert "lm_studio_small_model" not in payload
    assert "ollama_writer_model" not in payload
    assert "http://localhost" not in serialized
    assert "gpt-" not in serialized
    assert "qwen" not in serialized


def test_ui_settings_remains_safe_legacy_html(client) -> None:
    response = client.get("/ui/settings")

    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    body = response.text
    assert "artifacts_dir" not in body
    assert "lm_studio_base_url" not in body
    assert "ollama_base_url" not in body
    assert "gmail_oauth_client_secret" not in body


def test_vue_settings_contract_and_app_settings_remain_available(client) -> None:
    vue_response = client.get("/api/vue/settings")
    app_response = client.get("/app/settings")

    assert vue_response.status_code == 200
    assert vue_response.headers["content-type"].startswith("application/json")
    assert app_response.status_code in (200, 503)
    if app_response.status_code == 200:
        assert "text/html" in app_response.headers.get("content-type", "")
        assert _VUE_HTML_MARKER in app_response.text
    else:
        assert app_response.headers["content-type"].startswith("application/json")
