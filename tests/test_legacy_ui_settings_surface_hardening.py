from __future__ import annotations

_VUE_HTML_MARKER = '<div id="app">'
_UNSAFE_HTML_SNIPPETS = (
    "artifacts_dir",
    "fact_sheet_path",
    "openai_api_key",
    "gemini_api_key",
    "anthropic_api_key",
    "gmail_oauth_client_secret",
    "/Users/",
    "/home/",
    "/var/",
    "/tmp/",
    "~/",
    "file://",
    "sk-",
    "GOCSPX-",
    "***",
)


def _assert_safe_settings_html(body: str) -> None:
    for snippet in _UNSAFE_HTML_SNIPPETS:
        assert snippet not in body, f"unsafe settings HTML snippet rendered: {snippet}"


def test_ui_settings_returns_hardened_html(client) -> None:
    response = client.get("/ui/settings")

    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    body = response.text
    _assert_safe_settings_html(body)
    assert "Generated Files Storage" in body
    assert "Fact Sheet Source" in body
    assert "No Secret Values Rendered" in body
    assert "No Local Paths Rendered" in body


def test_settings_current_remains_hardened(client) -> None:
    payload = client.get("/settings/current").json()

    assert "artifacts_dir" not in payload
    assert "fact_sheet_path" not in payload
    assert payload["secrets_exposed"] is False
    assert payload["paths_exposed"] is False


def test_vue_settings_contract_remains_hardened(client) -> None:
    response = client.get("/api/vue/settings")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    payload = response.json()
    assert payload["ok"] is True
    serialized = str(payload).lower()
    assert "api_key" not in serialized
    assert "artifacts_dir" not in serialized


def test_app_settings_still_serves_vue_html_or_safe_503(client) -> None:
    response = client.get("/app/settings")

    assert response.status_code in (200, 503)
    if response.status_code == 200:
        assert "text/html" in response.headers.get("content-type", "")
        assert _VUE_HTML_MARKER in response.text
    else:
        assert response.headers["content-type"].startswith("application/json")
