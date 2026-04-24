from __future__ import annotations


def test_setup_status_reports_incomplete_without_candidate(client):
    resp = client.get("/setup/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["complete"] is False
    assert "Create your candidate profile" in data["missing_steps"]


def test_setup_gate_redirects_core_ui_in_non_test_env(client):
    import job_agent.config as cfg

    object.__setattr__(cfg.settings, "app_env", "development")
    resp = client.get("/ui/jobs", follow_redirects=False)
    assert resp.status_code == 303
    assert "/ui/setup-required" in resp.headers["location"]


def test_create_candidate_accepts_fast_onboarding_payload(client, tmp_path, monkeypatch):
    import job_agent.config as cfg
    from job_agent import user_config

    monkeypatch.setattr(user_config, "USER_SETTINGS_PATH", tmp_path / "user_settings.yml")
    resp = client.post(
        "/candidates",
        json={
            "first_name": "Test",
            "last_name": "Candidate",
            "email": "test@example.com",
            "active": "false",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["full_name"] == "Test Candidate"
    assert data["email"] == "test@example.com"
    assert data["active"] is False
    assert cfg.settings.default_candidate_id == data["id"]
