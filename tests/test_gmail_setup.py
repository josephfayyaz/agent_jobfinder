from __future__ import annotations


def test_gmail_status_unconfigured(client):
    import job_agent.config as cfg

    original_email = cfg.settings.gmail_email
    original_password = cfg.settings.gmail_app_password
    try:
        object.__setattr__(cfg.settings, "gmail_email", "")
        object.__setattr__(cfg.settings, "gmail_app_password", "")
        response = client.get("/gmail/status")
        assert response.status_code == 200
        assert response.json()["configured"] is False
    finally:
        object.__setattr__(cfg.settings, "gmail_email", original_email)
        object.__setattr__(cfg.settings, "gmail_app_password", original_password)


def test_gmail_test_connection_bad_credentials(client, monkeypatch):
    import imaplib

    class _FakeIMAP:
        def __init__(self, *_args, **_kwargs):
            pass

        def login(self, *_args, **_kwargs):
            raise imaplib.IMAP4.error("bad credentials")

        def logout(self):
            return None

    monkeypatch.setattr(imaplib, "IMAP4_SSL", _FakeIMAP)
    response = client.post("/gmail/test-connection?email=test@gmail.com&app_password=badpass")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert "bad credentials" in data["error"]


def test_ui_settings_shows_gmail_section(client):
    response = client.get("/ui/settings")
    assert response.status_code == 200
    assert "Gmail Integration" in response.text
    assert "App Password" in response.text


def test_settings_current_masks_gmail_password(client):
    import job_agent.config as cfg

    original_password = cfg.settings.gmail_app_password
    try:
        object.__setattr__(cfg.settings, "gmail_app_password", "secret-pass")
        response = client.get("/settings/current")
        assert response.status_code == 200
        assert response.json()["gmail_app_password"] == "***"
    finally:
        object.__setattr__(cfg.settings, "gmail_app_password", original_password)
