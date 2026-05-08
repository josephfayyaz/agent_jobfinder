# Settings Current Hardening

This pass hardens the legacy `GET /settings/current` endpoint while keeping the
legacy `/ui` flows and the Vue `/app` bridge unchanged.

Endpoint sanitized:

- `/settings/current`

Unsafe fields removed:

- `artifacts_dir`
- `fact_sheet_path`
- public API-key fields
- public password/secret fields

Safe replacement fields:

- `artifacts_available`
- `fact_sheet_configured`
- `openai_configured`
- `gemini_configured`
- `anthropic_configured`
- `gmail_oauth_configured`
- `gmail_legacy_configured`
- `gmail_configured`
- `secrets_exposed`
- `paths_exposed`

Compatibility notes:

- onboarding hydration now uses safe `*_configured` booleans instead of masked keys
- CLI settings display now uses safe provider booleans instead of secret-shaped fields
- `/settings/current` was later tightened again to remove public URL/model details
- `/ui/*` remains active
- the Vue `/app` bridge remains unchanged
