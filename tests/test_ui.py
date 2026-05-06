from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_ui_returns_html(client):
    response = client.get("/ui")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Dashboard" in response.text


def test_onboarding_alias_redirects_to_ui_page(client):
    response = client.get("/onboarding/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/ui/onboarding"


def test_static_frontend_assets_are_served(client):
    response = client.get("/static/tailwind.css")
    assert response.status_code == 200
    assert ".hidden" in response.text


def test_jobs_ui_returns_html(client):
    response = client.get("/ui/jobs")
    assert response.status_code == 200
    assert "Jobs" in response.text


def test_jobs_ui_serializes_discovery_prerequisites_for_client_guard(client):
    response = client.get("/ui/jobs")
    assert response.status_code == 200
    assert '"discoveryEnabled"' in response.text
    assert '"searchFocus"' in response.text


def test_drafts_ui_returns_html(client):
    response = client.get("/ui/drafts")
    assert response.status_code == 200
    assert "CV Drafts" in response.text


def test_thesis_ui_returns_html(client):
    response = client.get("/ui/thesis")
    assert response.status_code == 200
    assert "Thesis" in response.text


def test_applications_ui_returns_html(client):
    response = client.get("/ui/applications")
    assert response.status_code == 200
    assert "Applications" in response.text


def test_settings_ui_returns_html(client):
    response = client.get("/ui/settings")
    assert response.status_code == 200
    assert "seniority" in response.text.lower()


def test_help_ui_reflects_current_setup_model(client):
    response = client.get("/ui/help")
    assert response.status_code == 200
    body = response.text
    assert "one active AI provider" in body
    assert "up to four target roles" in body


def test_about_ui_includes_local_first_copy_and_github_links(client):
    response = client.get("/ui/about")
    assert response.status_code == 200
    body = response.text
    assert "About Job Agent" in body
    assert "local-first career workspace" in body
    assert "github.com/josephfayyaz/agent_jobfinder" in body


def test_jobs_ui_reloads_destructive_actions_only_on_success(client):
    response = client.get("/ui/jobs")
    assert response.status_code == 200
    body = response.text
    assert 'hx-on::after-request="if(event.detail.successful) window.location.reload()"' in body


def test_companies_ui_reloads_destructive_actions_only_on_success(client):
    response = client.get("/ui/companies")
    assert response.status_code == 200
    body = (REPO_ROOT / "frontend/templates/companies.html").read_text()
    assert body.count('hx-on::after-request="if(event.detail.successful) window.location.reload()"') >= 2


def test_drafts_ui_reloads_mutations_only_on_success(client):
    response = client.get("/ui/drafts")
    assert response.status_code == 200
    body = (REPO_ROOT / "frontend/templates/drafts.html").read_text()
    assert 'hx-on::after-request="if(event.detail.successful) window.location.reload()"' in body


def test_applications_ui_reloads_stage_advance_only_on_success(client):
    response = client.get("/ui/applications")
    assert response.status_code == 200
    body = (REPO_ROOT / "frontend/templates/applications.html").read_text()
    assert 'hx-on::after-request="if(event.detail.successful) window.location.reload()"' in body
