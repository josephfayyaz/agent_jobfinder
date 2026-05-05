"""OS keychain integration for API key storage.

Secrets are stored in the platform keychain (macOS Keychain, Windows Credential
Manager, GNOME Keyring) under the service name "LocalJobAgent".

When a user saves a key through the settings UI the YAML settings file stores the
sentinel string ``__keyring__`` instead of the plain-text value.  At runtime
``config.py`` reads the real value from the keychain via ``resolve_secret()``.

If the keyring package is unavailable the helpers fall back gracefully to plain-text
storage with a logged warning — the app still works, keys are just less protected.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

SERVICE_NAME = "LocalJobAgent"
SENTINEL = "__keyring__"

SECRET_FIELDS: frozenset[str] = frozenset(
    {
        "openai_api_key",
        "gemini_api_key",
        "anthropic_api_key",
        "gmail_app_password",
        "gmail_oauth_client_secret",
        "clearbit_api_key",
    }
)


def keyring_available() -> bool:
    try:
        import keyring  # noqa: F401
        return True
    except ImportError:
        return False


def store_secret(field: str, value: str) -> bool:
    """Store *value* in the OS keychain under *field*.  Returns True on success."""
    if not value:
        return False
    try:
        import keyring
        keyring.set_password(SERVICE_NAME, field, value)
        return True
    except Exception as exc:
        logger.warning("keyring store failed for %s: %s", field, exc)
        return False


def load_secret(field: str) -> str | None:
    """Return the stored secret for *field*, or None if unavailable."""
    try:
        import keyring
        return keyring.get_password(SERVICE_NAME, field) or None
    except Exception as exc:
        logger.warning("keyring load failed for %s: %s", field, exc)
        return None


def delete_secret(field: str) -> None:
    """Remove the stored secret for *field* (best-effort, silently ignored on error)."""
    try:
        import keyring
        keyring.delete_password(SERVICE_NAME, field)
    except Exception:
        pass


def resolve_secret(field: str, raw_value: str) -> str:
    """Return the real value for *field*.

    If *raw_value* is the sentinel string ``__keyring__`` the real value is
    fetched from the OS keychain.  Otherwise *raw_value* is returned as-is.
    """
    if raw_value != SENTINEL:
        return raw_value
    value = load_secret(field)
    if value is None:
        logger.warning(
            "Secret '%s' has sentinel in YAML but no value in keychain. "
            "Re-enter the key in Settings to fix this.",
            field,
        )
        return ""
    return value


def migrate_plaintext_secrets(settings_dict: dict) -> dict[str, str]:
    """Move any plain-text secrets in *settings_dict* to the keychain.

    Returns a mapping of ``{field: SENTINEL}`` for values that were migrated.
    Caller should persist these replacements to the YAML settings file.
    """
    if not keyring_available():
        return {}
    migrated: dict[str, str] = {}
    for field in SECRET_FIELDS:
        value = settings_dict.get(field, "")
        if value and value != SENTINEL:
            if store_secret(field, value):
                migrated[field] = SENTINEL
                logger.info("Migrated '%s' from plain-text to keychain.", field)
    return migrated
