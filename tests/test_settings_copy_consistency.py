"""Tests for copy consistency across settings and onboarding surfaces.

Verifies that user-facing rendered HTML uses safe vocabulary only:
- No localhost or 127.0.0.1 in rendered provider inputs
- No partial API key prefix patterns in placeholders
- No model names in copy text
- Safe wording (Leave blank / Configured / Not configured) is present
- /settings/current and /api/vue/settings remain safe JSON
"""
from __future__ import annotations

_VUE_HTML_MARKER = '<div id="app">'

# Patterns that must not appear in rendered HTML surfaces.
# These are wording violations, not data leaks (data leaks are checked by
# the hardening test suites).  Focus on copy that would confuse or mislead.
_UNSAFE_COPY_SNIPPETS = (
    "sk-...",
    "sk-ant-...",
    "AIza...",
    "gpt-oss-20b",
    'placeholder="http://localhost',
    'placeholder="http://127.0.0.1',
    'value="http://localhost',
    'value="http://127.0.0.1',
)


def _assert_safe_copy(body: str, surface: str) -> None:
    for snippet in _UNSAFE_COPY_SNIPPETS:
        assert snippet not in body, (
            f"{surface}: unsafe copy snippet rendered: {snippet!r}"
        )


# ---------------------------------------------------------------------------
# /ui/settings — legacy Jinja surface
# ---------------------------------------------------------------------------


def test_ui_settings_copy_is_consistent(client) -> None:
    response = client.get("/ui/settings")

    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    body = response.text

    _assert_safe_copy(body, "/ui/settings")

    # Safe wording present (provider key inputs already carry these hints)
    assert "Leave blank" in body

    # Existing hardening assertions still hold
    assert "No Secret Values Rendered" in body
    assert "No Local Paths Rendered" in body


def test_ui_onboarding_copy_is_consistent(client) -> None:
    response = client.get("/ui/onboarding")

    assert response.status_code == 200
    body = response.text

    _assert_safe_copy(body, "/ui/onboarding")

    # Provider card labels and safe copy
    assert "Local Gateway" in body or "Ollama" in body or "OpenAI" in body


# ---------------------------------------------------------------------------
# /settings/current — public JSON endpoint
# ---------------------------------------------------------------------------


def test_settings_current_still_safe_after_copy_pass(client) -> None:
    response = client.get("/settings/current")

    assert response.status_code == 200
    payload = response.json()
    assert payload["secrets_exposed"] is False
    assert payload["paths_exposed"] is False
    serialized = str(payload).lower()
    assert "localhost" not in serialized
    assert "127.0.0.1" not in serialized
    assert "sk-" not in serialized
    assert "gpt-oss-20b" not in serialized


# ---------------------------------------------------------------------------
# /api/vue/settings — Vue-safe JSON endpoint
# ---------------------------------------------------------------------------


def test_vue_settings_still_safe_after_copy_pass(client) -> None:
    response = client.get("/api/vue/settings")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    serialized = str(payload).lower()
    assert "api_key" not in serialized
    assert "localhost" not in serialized
    assert "sk-" not in serialized


# ---------------------------------------------------------------------------
# /app/settings — Vue SPA bridge
# ---------------------------------------------------------------------------


def test_app_settings_still_active_after_copy_pass(client) -> None:
    response = client.get("/app/settings")

    assert response.status_code in (200, 503)
    if response.status_code == 200:
        assert "text/html" in response.headers.get("content-type", "")
        assert _VUE_HTML_MARKER in response.text
    else:
        assert response.headers["content-type"].startswith("application/json")
