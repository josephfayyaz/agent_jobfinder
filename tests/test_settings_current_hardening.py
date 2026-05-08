from __future__ import annotations

from collections.abc import Iterator

_VUE_HTML_MARKER = '<div id="app">'
_ALLOWED_UNSAFE_KEYS = {"secrets_exposed", "paths_exposed"}
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
    "absolute_path",
    "file_path",
    "artifacts_dir",
)
_UNSAFE_VALUE_PREFIXES = (
    "/Users/",
    "/home/",
    "/var/",
    "/tmp/",
    "/Library/",
    "~/",
    "file:",
    "sk-",
    "****",
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
        if (
            key_name not in _ALLOWED_UNSAFE_KEYS
            and not key_name.endswith("_configured")
            and any(part in key_name for part in _UNSAFE_KEY_PARTS)
        ):
            hits.append(f"unsafe key at {path}")
        if isinstance(node, str):
            lowered = node.lower()
            if any(lowered.startswith(prefix.lower()) for prefix in _UNSAFE_VALUE_PREFIXES):
                hits.append(f"unsafe value at {path}: {node}")
    return hits


def test_settings_current_returns_safe_json(client) -> None:
    response = client.get("/settings/current")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    payload = response.json()
    assert "artifacts_dir" not in payload
    assert "fact_sheet_path" not in payload
    assert payload["secrets_exposed"] is False
    assert payload["paths_exposed"] is False
    assert payload["artifacts_available"] in (True, False)
    assert payload["openai_configured"] in (True, False)
    assert payload["gemini_configured"] in (True, False)
    assert payload["anthropic_configured"] in (True, False)
    assert _unsafe_entries(payload) == []


def test_settings_current_reports_gmail_flags_without_secret_fields(client) -> None:
    payload = client.get("/settings/current").json()

    assert "gmail_oauth_client_secret" not in payload
    assert "gmail_app_password" not in payload
    assert payload["gmail_oauth_configured"] in (True, False)
    assert payload["gmail_legacy_configured"] in (True, False)
    assert payload["gmail_configured"] in (True, False)


def test_vue_settings_contract_remains_safe(client) -> None:
    response = client.get("/api/vue/settings")

    assert response.status_code == 200
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


def test_ui_about_stays_legacy_html(client) -> None:
    response = client.get("/ui/about")

    assert response.status_code != 404
    assert _VUE_HTML_MARKER not in response.text
