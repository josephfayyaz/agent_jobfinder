# Stage 02 — Guided Key Setup + Validation

## Goal

Turn API key setup into a guided wizard instead of a blank password field.

## UX Pattern

For each provider, show a 4-step inline guide:

1. `Open provider console`
2. `Add credits or billing`
3. `Create API key`
4. `Paste key and test`

## UI Requirements

In onboarding and settings:

- provider-specific setup card
- short explanation of what billing is needed
- key input field
- `Test connection` button
- status badge
- `Save and continue` button

## OpenAI Guide Copy

- `Open OpenAI platform`
- `Add prepaid billing or active payment method`
- `Create a secret API key`
- `Paste it here to test`

## Claude Guide Copy

- `Open Claude Console`
- `Add API usage credits`
- `Create an API key`
- `Paste it here to test`

## Security Requirements

- key never stored in plaintext YAML
- key stored only through `job_agent/secrets.py`
- masked on all API responses
- frontend receives only configured/not-configured state

## Backend Requirements

Add or improve:

- test connection endpoint for OpenAI
- test connection endpoint for Anthropic
- standard response shape:
  - `ok`
  - `provider`
  - `error`
  - `model_access`

## Helpful Failure Messages

Avoid raw provider jargon when possible.

Translate to user-friendly language:

- `Billing not active`
- `Invalid key`
- `Credits exhausted`
- `Rate limited`
- `Provider unavailable`

## Files

- `job_agent/routers/system.py`
- `job_agent/llm.py`
- `job_agent/secrets.py`
- `frontend/templates/onboarding.html`
- `frontend/templates/settings.html`
- `frontend/static/onboarding.js`
- `frontend/static/settings.js`

## Acceptance Criteria

- user can complete setup without touching `.env`
- each provider can be tested before saving
- errors are readable and actionable
- key storage remains local-only
