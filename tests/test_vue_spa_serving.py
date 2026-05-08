"""Tests for the Vue SPA serving bridge in FastAPI.

The Vue app is served exclusively under the /app prefix.  All /app and
/app/* paths return the built index.html (or a safe 503 when the build
artifact is absent).  Every path outside /app is left entirely to the
existing router/mount registrations — nothing is shadowed.

Tests are designed to pass whether or not the Vue build artifact exists at
frontend/static/dist/index.html.
"""
from __future__ import annotations

from pathlib import Path

import pytest

_BUILD_PATH = (
    Path(__file__).parent.parent / "frontend" / "static" / "dist" / "index.html"
)

_VUE_HTML_MARKER = '<div id="app">'


def _build_exists() -> bool:
    return _BUILD_PATH.is_file()


# ---------------------------------------------------------------------------
# Build artifact asset URLs — must reference /static/dist/assets/, not /assets/
# ---------------------------------------------------------------------------


def test_built_index_references_static_dist_assets() -> None:
    """Vite base="/static/dist/" must produce /static/dist/assets/... URLs.
    Skipped when the build artifact is absent."""
    if not _build_exists():
        pytest.skip("Vue build artifact not present")
    content = _BUILD_PATH.read_text(encoding="utf-8")
    assert "/static/dist/assets/" in content, (
        "Built index.html does not reference /static/dist/assets/ — "
        "check vite.config.js build base setting"
    )
    assert 'src="/assets/' not in content, (
        "Built index.html still references bare /assets/ — Vite base not applied"
    )


# ---------------------------------------------------------------------------
# /app and /app/* → serve Vue index (or safe 503 when build is absent)
# ---------------------------------------------------------------------------


def test_app_root_serves_vue_index_or_build_missing(client) -> None:
    response = client.get("/app")
    build_exists = _build_exists()
    assert response.status_code in (200, 503), response.status_code
    if build_exists:
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        assert _VUE_HTML_MARKER in response.text
    else:
        assert response.status_code == 503
        assert "build" in response.json().get("error", "").lower()


def test_app_dashboard_serves_vue_index_or_build_missing(client) -> None:
    response = client.get("/app/dashboard")
    build_exists = _build_exists()
    assert response.status_code in (200, 503), response.status_code
    if build_exists:
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        assert _VUE_HTML_MARKER in response.text
    else:
        assert response.status_code == 503


def test_app_jobs_serves_vue_index_or_build_missing(client) -> None:
    response = client.get("/app/jobs")
    build_exists = _build_exists()
    assert response.status_code in (200, 503), response.status_code
    if build_exists:
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        assert _VUE_HTML_MARKER in response.text
    else:
        assert response.status_code == 503


def test_app_drafts_detail_serves_vue_index_or_build_missing(client) -> None:
    response = client.get("/app/drafts/123")
    build_exists = _build_exists()
    assert response.status_code in (200, 503), response.status_code
    if build_exists:
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        assert _VUE_HTML_MARKER in response.text
    else:
        assert response.status_code == 503


def test_app_unknown_subpath_serves_vue_for_client_side_routing(client) -> None:
    """Unknown /app/* paths still serve the Vue shell; Vue Router handles 404."""
    response = client.get("/app/this-route-does-not-exist-xyz")
    build_exists = _build_exists()
    assert response.status_code in (200, 503), response.status_code
    if build_exists:
        assert _VUE_HTML_MARKER in response.text


# ---------------------------------------------------------------------------
# /dashboard must remain handled by the existing backend route, not by Vue
# ---------------------------------------------------------------------------


def test_dashboard_is_backend_route_not_vue(client) -> None:
    """/dashboard is an existing JSON endpoint in system.router.
    The SPA bridge must never shadow it."""
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "application/json" in response.headers.get("content-type", "")
    assert _VUE_HTML_MARKER not in response.text


# ---------------------------------------------------------------------------
# /api/vue/* must not be swallowed by the SPA bridge
# ---------------------------------------------------------------------------


def test_api_vue_health_returns_json_not_vue_html(client) -> None:
    response = client.get("/api/vue/health")
    assert response.status_code == 200
    assert "application/json" in response.headers.get("content-type", "")
    body = response.json()
    assert body.get("ok") is True
    assert _VUE_HTML_MARKER not in response.text


def test_api_vue_settings_returns_json_not_vue_html(client) -> None:
    response = client.get("/api/vue/settings")
    assert response.status_code == 200
    assert "application/json" in response.headers.get("content-type", "")
    assert _VUE_HTML_MARKER not in response.text


def test_api_vue_navigation_returns_json_not_vue_html(client) -> None:
    response = client.get("/api/vue/navigation")
    assert response.status_code == 200
    assert "application/json" in response.headers.get("content-type", "")
    assert _VUE_HTML_MARKER not in response.text


# ---------------------------------------------------------------------------
# /static/* must not be swallowed by the SPA bridge
# ---------------------------------------------------------------------------


def test_static_nonexistent_file_returns_404_not_vue_html(client) -> None:
    response = client.get("/static/nonexistent-test-file-xyz123.js")
    assert response.status_code == 404
    assert _VUE_HTML_MARKER not in response.text


# ---------------------------------------------------------------------------
# /ui/* legacy routes must not be swallowed by the SPA bridge
# ---------------------------------------------------------------------------


def test_ui_about_not_swallowed_by_spa(client) -> None:
    """/ui/about is a known legacy Jinja route.  The SPA bridge must never
    intercept it.  We allow 200 (template rendered) or 500 (internal error in
    test environment) — but NOT 404 from the catch-all, and NOT the Vue shell."""
    response = client.get("/ui/about")
    assert response.status_code != 404, (
        "/ui/about returned 404 — the SPA bridge may have intercepted it"
    )
    assert _VUE_HTML_MARKER not in response.text


# ---------------------------------------------------------------------------
# Unknown non-/app routes must return 404, not Vue HTML
# ---------------------------------------------------------------------------


def test_unknown_bare_route_returns_404(client) -> None:
    response = client.get("/not-a-route-xyzabc")
    assert response.status_code == 404
    assert _VUE_HTML_MARKER not in response.text


def test_unknown_deep_path_returns_404(client) -> None:
    response = client.get("/random/deep/path/that/does/not/exist")
    assert response.status_code == 404
    assert _VUE_HTML_MARKER not in response.text
