from __future__ import annotations


def test_dashboard_ui_returns_html(client):
    response = client.get("/ui")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Dashboard" in response.text


def test_jobs_ui_returns_html(client):
    response = client.get("/ui/jobs")
    assert response.status_code == 200
    assert "Jobs" in response.text


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
