from __future__ import annotations

import re
from pathlib import Path

import pytest


ROOT = Path(__file__).parent.parent
APP = ROOT / "frontend/vue/src/App.vue"
WELCOME = ROOT / "frontend/vue/src/pages/WelcomePage.vue"
ROUTER = ROOT / "frontend/vue/src/router/index.js"
SIDEBAR = ROOT / "frontend/vue/src/components/AppSidebar.vue"
NAVIGATION = ROOT / "frontend/vue/src/constants/navigation.js"
BLANK_LAYOUT = ROOT / "frontend/vue/src/layouts/BlankLayout.vue"
APP_LAYOUT = ROOT / "frontend/vue/src/layouts/AppLayout.vue"
VUE_API = ROOT / "job_agent/routers/vue_api.py"
BUILD_PATH = ROOT / "frontend/static/dist/index.html"
VUE_HTML_MARKER = '<div id="app">'


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _route_block(source: str, route_path: str) -> str:
    match = re.search(
        rf"\{{\n\s+path: \"{re.escape(route_path)}\",(?P<body>.*?)\n\s+\}}",
        source,
        re.S,
    )
    assert match, f"Route block for {route_path} was not found."
    return match.group(0)


def test_app_slash_serves_vue_entry_or_build_missing(client) -> None:
    response = client.get("/app/")

    assert response.status_code in (200, 503), response.status_code
    if BUILD_PATH.is_file():
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        assert VUE_HTML_MARKER in response.text
    else:
        assert response.status_code == 503
        assert "build" in response.json().get("error", "").lower()


def test_welcome_page_renders_agent_jobfinder_entry_content() -> None:
    source = _read(WELCOME)

    assert 'data-testid="welcome-page"' in source
    assert "Agent Jobfinder" in source
    assert "Local-first career workspace" in source
    assert "targeted job applications" in source
    assert "Build better applications from facts you can trust." in source
    assert 'data-testid="welcome-start-button"' in source
    assert "Start setup" in source


def test_default_app_entry_uses_welcome_page_not_dashboard_redirect() -> None:
    source = _read(ROUTER)
    root_route = _route_block(source, "/")

    assert 'import WelcomePage from "../pages/WelcomePage.vue";' in source
    assert "name: \"welcome\"" in root_route
    assert "component: WelcomePage" in root_route
    assert 'meta: { layout: "blank" }' in root_route
    assert 'redirect: "/dashboard"' not in source


def test_app_uses_blank_layout_for_setup_routes_only() -> None:
    app = _read(APP)
    router = _read(ROUTER)
    blank_layout = _read(BLANK_LAYOUT)
    app_layout = _read(APP_LAYOUT)

    assert "useRoute" in app
    assert "BlankLayout" in app
    assert 'route.meta.layout === "blank"' in app
    assert "AppSidebar" not in blank_layout
    assert "navigationGroups" not in blank_layout
    assert "AppSidebar" in app_layout

    assert 'meta: { layout: "blank" }' in _route_block(router, "/")
    assert 'meta: { layout: "blank" }' in _route_block(router, "/onboarding")
    assert 'meta: { layout: "blank" }' not in _route_block(router, "/dashboard")


def test_about_route_is_legacy_redirect_not_separate_page() -> None:
    source = _read(ROUTER)

    assert "AboutPage" not in source
    assert re.search(r"path: \"/about\",\n\s+redirect: \"/\"", source)


def test_start_redirects_completed_users_to_dashboard() -> None:
    source = _read(WELCOME)

    assert "setupCompleteFromData(data)" in source
    assert 'router.push("/dashboard")' in source


def test_start_redirects_incomplete_users_to_onboarding() -> None:
    source = _read(WELCOME)

    assert 'router.push("/onboarding")' in source
    assert 'vueApiFetch("/setup/state")' in source


def test_sidebar_brand_routes_to_app_root() -> None:
    source = _read(SIDEBAR)

    assert 'data-testid="brand-home-link"' in source
    assert 'to="/"' in source
    assert "Agent Jobfinder" in source


@pytest.mark.parametrize("forbidden", ["/about", "/onboarding"])
def test_sidebar_navigation_omits_about_and_onboarding(forbidden: str) -> None:
    navigation = _read(NAVIGATION)
    sidebar = _read(SIDEBAR)

    assert f'to: "{forbidden}"' not in navigation
    assert f'to="{forbidden}"' not in sidebar


@pytest.mark.parametrize("forbidden", ["/about", "/onboarding"])
def test_vue_navigation_contract_omits_about_and_onboarding(forbidden: str) -> None:
    source = _read(VUE_API)

    assert f'"to": "{forbidden}"' not in source
