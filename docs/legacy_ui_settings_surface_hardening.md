# Legacy UI Settings Surface Hardening

This pass hardens the server-rendered legacy settings surface at `/ui/settings`
without removing it or changing the `/app` Vue bridge.

## What changed

- Removed rendered artifact-folder and fact-sheet path values
- Removed rendered raw and masked provider/Gmail secret values
- Stopped prefilling secret inputs with saved values or secret-shaped placeholders
- Replaced the old display surface with safe status vocabulary:
  - `artifacts_available`
  - `fact_sheet_configured`
  - `*_configured`
  - `secrets_exposed: false`
  - `paths_exposed: false`

## Compatibility notes

- `/ui/settings` remains active and keeps the existing save/connect actions
- `/settings/current` remains the hardened JSON source for public settings status and no longer exposes public URL/model details
- `/api/vue/settings` remains active and unchanged as the Vue-safe contract
- `/app` Vue serving stays unchanged
