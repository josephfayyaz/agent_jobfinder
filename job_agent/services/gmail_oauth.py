"""Gmail OAuth helper for local OAuth consent, token exchange, and refresh."""

from __future__ import annotations

import json
import logging
from pathlib import Path
import secrets
import time
from urllib.parse import urlencode

import httpx

from job_agent.config import Settings, get_settings
from job_agent.runtime_paths import gmail_oauth_state_path, gmail_oauth_token_path

logger = logging.getLogger(__name__)

_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_PROFILE_URL = "https://gmail.googleapis.com/gmail/v1/users/me/profile"
_STATE_TTL_SECONDS = 900
_SCOPES = (
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
)


class GmailOAuthService:
    """Encapsulates OAuth state and Gmail token lifecycle for single-user runtime."""

    def __init__(self, app_settings: Settings | None = None) -> None:
        self.settings = app_settings or get_settings()

    def _token_path(self) -> Path:
        return gmail_oauth_token_path()

    def _state_path(self) -> Path:
        return gmail_oauth_state_path()

    def redirect_uri(self, base_url: str) -> str:
        return self._redirect_uri(base_url)

    def _redirect_uri(self, base_url: str) -> str:
        return f"{base_url.rstrip('/')}/gmail/oauth/callback"

    def _has_client_credentials(self) -> bool:
        return bool(
            str(getattr(self.settings, "gmail_oauth_client_id", "") or "").strip()
            and str(getattr(self.settings, "gmail_oauth_client_secret", "") or "").strip()
        )

    def load_token(self) -> dict[str, object]:
        path = self._token_path()
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Failed to read Gmail OAuth token file: %s", exc)
            return {}
        return data if isinstance(data, dict) else {}

    def save_token(self, payload: dict[str, object]) -> None:
        path = self._token_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _load_state(self) -> dict[str, object]:
        path = self._state_path()
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return data if isinstance(data, dict) else {}

    def _save_state(self, payload: dict[str, object]) -> None:
        path = self._state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _clear_state(self) -> None:
        path = self._state_path()
        if path.exists():
            path.unlink()

    def disconnect(self) -> None:
        token_path = self._token_path()
        if token_path.exists():
            token_path.unlink()
        self._clear_state()

    def status(self) -> dict[str, object]:
        token = self.load_token()
        now = int(time.time())
        expires_at = int(token.get("expires_at") or 0)
        connected = self.is_connected()
        return {
            "connected": connected,
            "has_client_credentials": self._has_client_credentials(),
            "email": str(token.get("email") or ""),
            "expires_at": expires_at,
            "expired": bool(expires_at and expires_at <= now),
            "has_refresh_token": bool(str(token.get("refresh_token") or "").strip()),
        }

    def is_connected(self) -> bool:
        token = self.load_token()
        access_token = str(token.get("access_token") or "").strip()
        refresh_token = str(token.get("refresh_token") or "").strip()
        expires_at = int(token.get("expires_at") or 0)
        now = int(time.time())
        return bool(refresh_token or (access_token and expires_at > now))

    def start(self, base_url: str) -> dict[str, str]:
        if not self._has_client_credentials():
            raise ValueError("Save Gmail OAuth Client ID and Client Secret first.")
        state = secrets.token_urlsafe(24)
        redirect_uri = self._redirect_uri(base_url)
        self._save_state({"state": state, "created_at": int(time.time()), "redirect_uri": redirect_uri})
        params = {
            "client_id": str(getattr(self.settings, "gmail_oauth_client_id", "") or "").strip(),
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(_SCOPES),
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
            "state": state,
        }
        return {"auth_url": f"{_AUTH_URL}?{urlencode(params)}", "state": state}

    def complete_callback(self, *, code: str, state: str, base_url: str) -> dict[str, object]:
        stored = self._load_state()
        expected_state = str(stored.get("state") or "")
        created_at = int(stored.get("created_at") or 0)
        if not expected_state or expected_state != state:
            raise ValueError("OAuth state mismatch. Start the Gmail connect flow again.")
        if created_at and int(time.time()) - created_at > _STATE_TTL_SECONDS:
            raise ValueError("OAuth session expired. Start the Gmail connect flow again.")

        redirect_uri = str(stored.get("redirect_uri") or self._redirect_uri(base_url))
        payload = {
            "client_id": str(getattr(self.settings, "gmail_oauth_client_id", "") or "").strip(),
            "client_secret": str(getattr(self.settings, "gmail_oauth_client_secret", "") or "").strip(),
            "code": code.strip(),
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
        response_data = self._exchange_token(payload)
        current = self.load_token()
        token = self._normalize_token_payload(response_data, fallback_refresh=str(current.get("refresh_token") or ""))
        access_token = str(token.get("access_token") or "")
        if access_token:
            email_address = self._fetch_account_email(access_token)
            if email_address:
                token["email"] = email_address

        self.save_token(token)
        self._clear_state()
        return token

    def _exchange_token(self, payload: dict[str, str]) -> dict[str, object]:
        try:
            response = httpx.post(_TOKEN_URL, data=payload, timeout=15)
        except Exception as exc:
            raise ValueError(f"Could not reach Google OAuth token endpoint: {exc}") from exc
        if not response.is_success:
            detail = response.text.strip()[:300] or f"HTTP {response.status_code}"
            raise ValueError(f"Gmail OAuth token exchange failed: {detail}")
        data = response.json()
        if not isinstance(data, dict) or not data.get("access_token"):
            raise ValueError("OAuth token exchange returned no access token.")
        return data

    def _normalize_token_payload(
        self,
        data: dict[str, object],
        *,
        fallback_refresh: str = "",
    ) -> dict[str, object]:
        expires_in = int(data.get("expires_in") or 3600)
        refresh_token = str(data.get("refresh_token") or fallback_refresh or "").strip()
        return {
            "access_token": str(data.get("access_token") or "").strip(),
            "refresh_token": refresh_token,
            "token_type": str(data.get("token_type") or "Bearer"),
            "scope": str(data.get("scope") or " ".join(_SCOPES)),
            "expires_at": int(time.time()) + max(0, expires_in - 30),
            "updated_at": int(time.time()),
        }

    def _fetch_account_email(self, access_token: str) -> str:
        try:
            response = httpx.get(
                _PROFILE_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            if response.is_success:
                payload = response.json()
                if isinstance(payload, dict):
                    return str(payload.get("emailAddress") or "").strip()
        except Exception as exc:
            logger.debug("Failed to fetch Gmail profile email: %s", exc)
        return ""

    def _refresh_access_token(self, token: dict[str, object]) -> dict[str, object]:
        refresh_token = str(token.get("refresh_token") or "").strip()
        if not refresh_token:
            raise ValueError("No refresh token available.")
        payload = {
            "client_id": str(getattr(self.settings, "gmail_oauth_client_id", "") or "").strip(),
            "client_secret": str(getattr(self.settings, "gmail_oauth_client_secret", "") or "").strip(),
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        refreshed = self._exchange_token(payload)
        merged = self._normalize_token_payload(refreshed, fallback_refresh=refresh_token)
        if token.get("email"):
            merged["email"] = token["email"]
        return merged

    def get_access_token(self) -> str:
        token = self.load_token()
        if not token:
            return ""
        access_token = str(token.get("access_token") or "").strip()
        expires_at = int(token.get("expires_at") or 0)
        if access_token and expires_at > int(time.time()) + 30:
            return access_token

        if not self._has_client_credentials():
            logger.warning("Gmail OAuth token exists but OAuth client credentials are missing.")
            return access_token if expires_at > int(time.time()) else ""

        try:
            refreshed = self._refresh_access_token(token)
        except ValueError as exc:
            logger.warning("Could not refresh Gmail access token: %s", exc)
            return access_token if expires_at > int(time.time()) else ""

        self.save_token(refreshed)
        return str(refreshed.get("access_token") or "").strip()
