# Legacy Surface Hardening

This pass hardens legacy backend JSON surfaces that remain active alongside the
Vue `/app` bridge.

Sanitized endpoints:

- `/dashboard`
- `/health`
- follow-on pass: `/settings/current`
- follow-on pass: `/ui/settings`

Unsafe fields removed:

- `system.pdflatex_path` from `/dashboard`
- `pdflatex.path` from `/health`

Safe replacement fields:

- `system.pdflatex_available`
- `pdflatex.available`
- `artifacts_available`
- provider `*_configured` flags
- `secrets_exposed`
- `paths_exposed`

Guardrails preserved:

- `/dashboard` remains a backend JSON route
- `/ui/*` legacy pages remain active
- `/api/vue/*` contract routes remain active
- `/app` SPA serving strategy remains unchanged
- no absolute local filesystem paths are exposed by the hardened responses
