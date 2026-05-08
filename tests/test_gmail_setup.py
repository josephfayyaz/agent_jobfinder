from __future__ import annotations

import json
from pathlib import Path


def test_gmail_status_unconfigured(client):
    response = client.get("/gmail/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["configured"] is False
    assert payload["oauth_connected"] is False
    assert payload["mode"] == "none"


def test_gmail_oauth_start_requires_credentials(client):
    response = client.post("/gmail/oauth/start")
    assert response.status_code == 422
    assert "Client ID" in response.json()["detail"]


def test_gmail_oauth_start_returns_auth_url(client, monkeypatch, tmp_path: Path):
    import job_agent.config as cfg
    import job_agent.services.gmail_oauth as gmail_oauth

    original_client_id = cfg.settings.gmail_oauth_client_id
    original_client_secret = cfg.settings.gmail_oauth_client_secret
    monkeypatch.setattr(gmail_oauth, "gmail_oauth_state_path", lambda: tmp_path / "oauth_state.json")
    try:
        object.__setattr__(cfg.settings, "gmail_oauth_client_id", "client-id")
        object.__setattr__(cfg.settings, "gmail_oauth_client_secret", "client-secret")
        response = client.post("/gmail/oauth/start")
        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert "accounts.google.com" in payload["auth_url"]
        assert "state=" in payload["auth_url"]
    finally:
        object.__setattr__(cfg.settings, "gmail_oauth_client_id", original_client_id)
        object.__setattr__(cfg.settings, "gmail_oauth_client_secret", original_client_secret)


def test_gmail_oauth_callback_stores_token(client, monkeypatch, tmp_path: Path):
    import job_agent.config as cfg
    import job_agent.services.gmail_oauth as gmail_oauth

    state_path = tmp_path / "oauth_state.json"
    token_path = tmp_path / "oauth_token.json"
    monkeypatch.setattr(gmail_oauth, "gmail_oauth_state_path", lambda: state_path)
    monkeypatch.setattr(gmail_oauth, "gmail_oauth_token_path", lambda: token_path)

    original_client_id = cfg.settings.gmail_oauth_client_id
    original_client_secret = cfg.settings.gmail_oauth_client_secret

    class _Resp:
        def __init__(self, payload: dict[str, object], status_code: int = 200):
            self._payload = payload
            self.status_code = status_code
            self.is_success = status_code < 400
            self.text = json.dumps(payload)
            self.content = self.text.encode("utf-8")

        def json(self):
            return self._payload

    def _fake_post(url, data=None, timeout=None):
        assert "oauth2.googleapis.com/token" in url
        assert data["grant_type"] == "authorization_code"
        return _Resp(
            {
                "access_token": "ya29.test-token",
                "refresh_token": "refresh-token",
                "expires_in": 3600,
                "token_type": "Bearer",
            }
        )

    def _fake_get(url, headers=None, timeout=None):
        assert "gmail.googleapis.com/gmail/v1/users/me/profile" in url
        return _Resp({"emailAddress": "user@example.com"})

    monkeypatch.setattr(gmail_oauth.httpx, "post", _fake_post)
    monkeypatch.setattr(gmail_oauth.httpx, "get", _fake_get)

    try:
        object.__setattr__(cfg.settings, "gmail_oauth_client_id", "client-id")
        object.__setattr__(cfg.settings, "gmail_oauth_client_secret", "client-secret")
        start = client.post("/gmail/oauth/start")
        assert start.status_code == 200
        state = start.json()["state"]

        callback = client.get(f"/gmail/oauth/callback?code=abc123&state={state}", follow_redirects=False)
        assert callback.status_code == 302
        assert token_path.exists()
        data = json.loads(token_path.read_text(encoding="utf-8"))
        assert data["access_token"] == "ya29.test-token"
        assert data["refresh_token"] == "refresh-token"
        assert data["email"] == "user@example.com"
    finally:
        object.__setattr__(cfg.settings, "gmail_oauth_client_id", original_client_id)
        object.__setattr__(cfg.settings, "gmail_oauth_client_secret", original_client_secret)


def test_gmail_oauth_disconnect_clears_token(client, monkeypatch, tmp_path: Path):
    import job_agent.services.gmail_oauth as gmail_oauth

    state_path = tmp_path / "oauth_state.json"
    token_path = tmp_path / "oauth_token.json"
    token_path.write_text(json.dumps({"access_token": "x"}), encoding="utf-8")
    state_path.write_text(json.dumps({"state": "x"}), encoding="utf-8")

    monkeypatch.setattr(gmail_oauth, "gmail_oauth_state_path", lambda: state_path)
    monkeypatch.setattr(gmail_oauth, "gmail_oauth_token_path", lambda: token_path)

    response = client.post("/gmail/oauth/disconnect")
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert not token_path.exists()
    assert not state_path.exists()


def test_ui_settings_shows_gmail_oauth_section(client):
    response = client.get("/ui/settings")
    assert response.status_code == 200
    assert "Gmail Integration" in response.text
    assert "Google Client ID" in response.text
    assert "Connect Gmail" in response.text
    assert "http://testserver/gmail/oauth/callback" in response.text


def test_settings_current_reports_safe_gmail_oauth_flag(client):
    import job_agent.config as cfg

    original_client_id = cfg.settings.gmail_oauth_client_id
    original_secret = cfg.settings.gmail_oauth_client_secret
    try:
        object.__setattr__(cfg.settings, "gmail_oauth_client_id", "")
        object.__setattr__(cfg.settings, "gmail_oauth_client_secret", "secret-value")
        response = client.get("/settings/current")
        assert response.status_code == 200
        payload = response.json()
        assert "gmail_oauth_client_secret" not in payload
        assert payload["gmail_oauth_configured"] is False
        assert payload["secrets_exposed"] is False
    finally:
        object.__setattr__(cfg.settings, "gmail_oauth_client_id", original_client_id)
        object.__setattr__(cfg.settings, "gmail_oauth_client_secret", original_secret)
