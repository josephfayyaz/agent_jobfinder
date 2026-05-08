# Settings Public JSON Contract Tightening

This pass tightens the public JSON contract for `/settings/current` so it
exposes only safe status and workflow fields.

## What changed

- Removed local provider URLs, base URLs, and client IDs
- Removed provider and runtime model identifiers
- Removed path-bearing and secret-bearing public fields
- Added a smaller safe status shape with:
  - `providers`
  - `provider_status`
  - `*_configured`
  - `*_available`
  - `artifacts_available`
  - `fact_sheet_configured`
  - `gmail_configured`
  - `secrets_exposed: false`
  - `paths_exposed: false`

## Compatibility notes

- `/ui/settings` remains active and safe
- onboarding hydration keeps using `/settings/current`, but now only reads safe status/search fields
- the CLI reads safe provider status instead of local URL/model details
- `/app` Vue serving remains unchanged
