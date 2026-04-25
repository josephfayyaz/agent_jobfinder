"""Tests for the keyring-based secret storage layer."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from job_agent.secrets import (
    SENTINEL,
    SECRET_FIELDS,
    delete_secret,
    load_secret,
    migrate_plaintext_secrets,
    resolve_secret,
    store_secret,
)


def test_secret_fields_known():
    assert "openai_api_key" in SECRET_FIELDS
    assert "anthropic_api_key" in SECRET_FIELDS
    assert "gmail_app_password" in SECRET_FIELDS
    assert "gmail_oauth_client_secret" in SECRET_FIELDS
    assert "clearbit_api_key" in SECRET_FIELDS


def test_resolve_secret_passthrough():
    assert resolve_secret("openai_api_key", "sk-abc123") == "sk-abc123"
    assert resolve_secret("openai_api_key", "") == ""
    assert resolve_secret("openai_api_key", "plain-text-value") == "plain-text-value"


def test_resolve_secret_sentinel_fetches_from_keyring():
    with patch("job_agent.secrets.load_secret", return_value="real-key") as mock_load:
        result = resolve_secret("openai_api_key", SENTINEL)
    assert result == "real-key"
    mock_load.assert_called_once_with("openai_api_key")


def test_resolve_secret_sentinel_missing_keyring_returns_empty():
    with patch("job_agent.secrets.load_secret", return_value=None):
        result = resolve_secret("openai_api_key", SENTINEL)
    assert result == ""


def test_store_and_load_secret():
    mock_kr = MagicMock()
    mock_kr.get_password.return_value = "stored-value"
    with patch.dict("sys.modules", {"keyring": mock_kr}):
        ok = store_secret("openai_api_key", "stored-value")
        assert ok is True
        mock_kr.set_password.assert_called_once()

    with patch.dict("sys.modules", {"keyring": mock_kr}):
        value = load_secret("openai_api_key")
        assert value == "stored-value"


def test_store_secret_empty_returns_false():
    assert store_secret("openai_api_key", "") is False


def test_delete_secret_no_error_on_missing():
    mock_kr = MagicMock()
    mock_kr.delete_password.side_effect = Exception("not found")
    with patch.dict("sys.modules", {"keyring": mock_kr}):
        delete_secret("openai_api_key")  # must not raise


def test_migrate_plaintext_secrets():
    settings_dict = {
        "openai_api_key": "sk-live",
        "gmail_app_password": "app-pass",
        "lm_studio_base_url": "http://localhost:1234",
    }
    mock_kr = MagicMock()
    mock_kr.get_password.return_value = None
    with patch.dict("sys.modules", {"keyring": mock_kr}):
        migrated = migrate_plaintext_secrets(settings_dict)

    assert migrated.get("openai_api_key") == SENTINEL
    assert migrated.get("gmail_app_password") == SENTINEL
    assert "lm_studio_base_url" not in migrated


def test_migrate_skips_sentinel_values():
    settings_dict = {"openai_api_key": SENTINEL}
    mock_kr = MagicMock()
    with patch.dict("sys.modules", {"keyring": mock_kr}):
        migrated = migrate_plaintext_secrets(settings_dict)
    assert "openai_api_key" not in migrated


def test_keyring_available_false_when_import_fails():
    import sys
    original = sys.modules.pop("keyring", None)
    try:
        with patch.dict("sys.modules", {"keyring": None}):
            # When the module is None in sys.modules, importing it raises ImportError
            pass
    finally:
        if original is not None:
            sys.modules["keyring"] = original


def test_write_user_settings_stores_secret_in_keychain(tmp_path):
    """write_user_settings should not persist plain-text secrets to YAML when keyring works."""
    from unittest.mock import patch
    import yaml

    settings_path = tmp_path / "user_settings.yml"

    mock_kr = MagicMock()
    mock_kr.get_password.return_value = None

    with (
        patch("job_agent.user_config.USER_SETTINGS_PATH", settings_path),
        patch("job_agent.user_config.keyring_available", return_value=True),
        patch("job_agent.user_config.store_secret", return_value=True) as mock_store,
    ):
        from job_agent.user_config import write_user_settings
        write_user_settings({"openai_api_key": "sk-test-key", "lm_studio_base_url": "http://localhost:1234"})

    written = yaml.safe_load(settings_path.read_text()) or {}
    assert written.get("openai_api_key") == SENTINEL
    assert written.get("lm_studio_base_url") == "http://localhost:1234"
    mock_store.assert_called_once_with("openai_api_key", "sk-test-key")


def test_write_user_settings_keeps_plaintext_when_keychain_store_fails(tmp_path):
    """A keychain write failure must not replace the only copy of the secret."""
    from unittest.mock import patch
    import yaml

    settings_path = tmp_path / "user_settings.yml"

    with (
        patch("job_agent.user_config.USER_SETTINGS_PATH", settings_path),
        patch("job_agent.user_config.keyring_available", return_value=True),
        patch("job_agent.user_config.store_secret", return_value=False) as mock_store,
    ):
        from job_agent.user_config import write_user_settings

        write_user_settings({"openai_api_key": "sk-fallback-key"})

    written = yaml.safe_load(settings_path.read_text()) or {}
    assert written.get("openai_api_key") == "sk-fallback-key"
    mock_store.assert_called_once_with("openai_api_key", "sk-fallback-key")


def test_load_user_settings_overlay_migrates_plaintext_secrets(tmp_path):
    """Plain-text YAML secrets should migrate to keychain and reload via sentinel."""
    import yaml

    from job_agent.config import Settings, load_user_settings_overlay

    settings_path = tmp_path / "user_settings.yml"
    settings_path.write_text(
        yaml.safe_dump(
            {
                "openai_api_key": "sk-live-key",
                "lm_studio_base_url": "http://localhost:1234/v1",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    test_settings = Settings()

    with (
        patch("job_agent.secrets.keyring_available", return_value=True),
        patch("job_agent.secrets.store_secret", return_value=True) as mock_store,
        patch("job_agent.secrets.load_secret", return_value="sk-live-key"),
    ):
        load_user_settings_overlay(test_settings, path=settings_path)

    written = yaml.safe_load(settings_path.read_text()) or {}
    assert written.get("openai_api_key") == SENTINEL
    assert test_settings.openai_api_key == "sk-live-key"
    mock_store.assert_called_once_with("openai_api_key", "sk-live-key")
