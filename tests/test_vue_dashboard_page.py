from __future__ import annotations

import re
from pathlib import Path


DASHBOARD = Path("frontend/vue/src/pages/DashboardPage.vue")
ROUTER = Path("frontend/vue/src/router/index.js")


def _source() -> str:
    return DASHBOARD.read_text(encoding="utf-8")


def test_dashboard_page_uses_summary_endpoint_and_cockpit_sections() -> None:
    source = _source()

    assert 'vueApiFetch("/dashboard/summary")' in source
    assert "Next Best Action" in source
    assert "Job Discovery" in source
    assert "Draft &amp; Application Workflow" in source
    assert "System Health" in source
    assert "Search Configuration" in source
    assert "Setup / Reliability Checklist" in source
    assert "Data source status" in source


def test_dashboard_placeholder_and_empty_payload_guards_are_preserved() -> None:
    source = _source()

    assert (
        "Dashboard is currently showing scaffolded backend data. Treat counts as structural "
        "placeholders until the summary endpoint is connected to real records."
    ) in source
    assert 'responseStatus.value === "placeholder"' in source
    assert "const responseData = computed(() => objectValue(payload.value?.data));" in source
    assert "const sections = computed(() => objectValue(responseData.value.sections));" in source
    assert "const cards = computed(() => (Array.isArray(responseData.value.cards)" in source


def test_dashboard_metric_fallbacks_and_shortcut_routes_are_present() -> None:
    source = _source()

    assert "const fallbackMetrics = [" in source
    for key in (
        "jobs_tracked",
        "companies_tracked",
        "applications_tracked",
        "drafts_pending",
    ):
        assert key in source
    assert "cards.value.length ? cards.value : fallbackMetrics" in source
    assert "metricRouteByKey" in source
    assert "focus-visible:ring-2 focus-visible:ring-indigo-500" in source


def test_dashboard_next_best_action_branches_cover_key_states() -> None:
    source = _source()

    assert "systemSummary.value.lmStudioOnline === false" in source
    assert "Fix or select workflow AI" in source
    assert "approvalBlockers.value > 0" in source
    assert "Review pending CV approvals" in source
    assert "jobsSummary.value.highMatch > 0" in source
    assert "Review high-match jobs" in source
    assert "jobsSummary.value.needsEnrichment > 0" in source
    assert "Enrich jobs before drafting" in source
    assert "noKnownJobActivity.value" in source
    assert "Start job intake" in source


def test_dashboard_system_health_badge_labels_are_explicit() -> None:
    source = _source()

    assert 'badge: "Blocking"' in source
    assert 'value: "Offline"' in source
    assert 'badge: "Limited"' in source
    assert 'value: "Missing"' in source
    assert 'badge: "Ready"' in source
    assert 'badge: "Unknown"' in source


def test_dashboard_route_links_are_existing_vue_router_paths() -> None:
    source = _source()
    router_source = ROUTER.read_text(encoding="utf-8")

    route_block = re.search(r"const ROUTES = Object\.freeze\(\{(?P<body>.*?)\n\}\);", source, re.S)
    assert route_block, "Dashboard route constants were not found."
    dashboard_routes = set(re.findall(r': "([^"]+)"', route_block.group("body")))
    router_paths = set(re.findall(r'path: "([^"]+)"', router_source))

    assert dashboard_routes
    assert dashboard_routes <= router_paths
    assert '"/app/' not in source
