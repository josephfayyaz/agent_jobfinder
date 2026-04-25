# Phase P2a — Gmail OAuth Setup

## Scope delivered

- Added Gmail OAuth credentials to settings:
  - `gmail_oauth_client_id`
  - `gmail_oauth_client_secret` (keyring-backed secret)
- Implemented OAuth helper service:
  - [gmail_oauth.py](/Users/youseffayyaz/Local_LLM/job_agent/services/gmail_oauth.py)
  - Handles auth URL generation, callback token exchange, token refresh, status, and disconnect.
- Added OAuth token/state runtime paths:
  - [runtime_paths.py](/Users/youseffayyaz/Local_LLM/job_agent/runtime_paths.py)
- Added OAuth endpoints:
  - `POST /gmail/oauth/start`
  - `GET /gmail/oauth/callback`
  - `POST /gmail/oauth/disconnect`
  - `GET /gmail/status` now reflects OAuth state and legacy fallback mode.
- Updated Gmail ingestion service:
  - OAuth-first Gmail API sync path
  - IMAP app-password compatibility fallback retained for transition.
- Updated Settings UI from app-password flow to OAuth flow:
  - OAuth setup instructions
  - client id/secret fields
  - connect/disconnect actions.

## Files changed (main)

- [config.py](/Users/youseffayyaz/Local_LLM/job_agent/config.py)
- [user_config.py](/Users/youseffayyaz/Local_LLM/job_agent/user_config.py)
- [secrets.py](/Users/youseffayyaz/Local_LLM/job_agent/secrets.py)
- [system.py](/Users/youseffayyaz/Local_LLM/job_agent/routers/system.py)
- [gmail.py](/Users/youseffayyaz/Local_LLM/job_agent/services/gmail.py)
- [gmail_oauth.py](/Users/youseffayyaz/Local_LLM/job_agent/services/gmail_oauth.py)
- [settings.html](/Users/youseffayyaz/Local_LLM/frontend/templates/settings.html)
- [settings.js](/Users/youseffayyaz/Local_LLM/frontend/static/settings.js)
- [.env.example](/Users/youseffayyaz/Local_LLM/.env.example)
- [user_settings.example.yml](/Users/youseffayyaz/Local_LLM/config/user_settings.example.yml)

## Validation

- Targeted tests:
  - `tests/test_gmail_setup.py`
  - `tests/test_gmail.py`
- Full suite:
  - `pytest --tb=short -q` → pass
- Lint:
  - `ruff check` → pass

## Notes

- Legacy IMAP app-password support remains intentionally for one transition phase.
- OAuth state is persisted in runtime app-data, not repo-local files.
