# 017 Settings Current Hardening

## Goal

Compatibility-aware hardening of the legacy backend endpoint:

```text
GET /settings/current
```

This endpoint currently exposes a legacy-sensitive response shape, including:

```text
artifacts_dir
masked secret-like fields
```

The goal is to remove unsafe public exposure while preserving existing onboarding/settings flows and tests as much as possible.

Do not break the Vue `/app` SPA bridge.

Do not change the Vue `/api/vue/settings` contract unless needed to keep it safe.

---

## Current State

Completed specs:

```text
AGENT_SPECS/completed/codex/001_vue_infrastructure.md
AGENT_SPECS/completed/codex/002_vue_layout_router.md
AGENT_SPECS/completed/codex/003_vue_api_contracts.md
AGENT_SPECS/completed/codex/004_convert_static_pages.md
AGENT_SPECS/completed/codex/005_convert_dashboard_jobs_companies.md
AGENT_SPECS/completed/claude/006_convert_applications_drafts_readonly.md
AGENT_SPECS/completed/claude/007_convert_career_tools_readonly.md
AGENT_SPECS/completed/claude/008_convert_verified_facts_readonly.md
AGENT_SPECS/completed/claude/009_convert_settings_readonly.md
AGENT_SPECS/completed/claude/010_convert_workspace_reset_readonly_preview.md
AGENT_SPECS/completed/claude/011_convert_onboarding_readonly_shell.md
AGENT_SPECS/completed/claude/012_convert_apply_readonly_shell.md
AGENT_SPECS/completed/claude/013_vue_spa_serving_and_legacy_bridge.md
AGENT_SPECS/completed/codex/014_vue_navigation_base_cleanup.md
AGENT_SPECS/completed/codex/015_vue_migration_final_audit.md
AGENT_SPECS/completed/codex/016_legacy_surface_hardening.md
```

Known from task 016:

```text
/dashboard was sanitized.
/health was sanitized.
/settings/current still exposes artifacts_dir and masked secret-like fields.
```

Known full-suite failures before this task:

```text
tests/test_frontend_null_guards.py::test_intake_js_has_null_guard_on_full_name
tests/test_frontend_null_guards.py::test_intake_js_has_null_guard_on_email
tests/test_temp_harness.py::test_temp_harness_bootstrap_does_not_hardcode_repo_root
```

Do not fix those in this task unless this task directly affects them.

---

## Purpose

Harden `/settings/current` without breaking legitimate legacy consumers.

Unsafe public response fields must be replaced with safe booleans/status fields.

Examples:

Bad:

```json
{
  "artifacts_dir": "/Users/name/Library/Application Support/agent_jobfinder/artifacts"
}
```

Good:

```json
{
  "artifacts_available": true
}
```

Bad:

```json
{
  "openai_api_key": "sk-****abcd",
  "anthropic_api_key": "****xyz"
}
```

Good:

```json
{
  "openai_configured": true,
  "anthropic_configured": true
}
```

Do not expose raw secrets.

Do not expose masked secrets.

Do not expose local filesystem paths.

---

## Hard Constraints

Do not remove `/settings/current`.

Do not redirect `/settings/current` to Vue.

Do not break legacy onboarding/settings flows.

Do not remove Jinja templates.

Do not remove legacy static JavaScript.

Do not remove HTMX.

Do not remove Alpine.

Do not remove `/ui/*` routes.

Do not remove `/api/*` routes.

Do not remove `/api/vue/*` routes.

Do not change the Vue `/app` SPA serving strategy.

Do not change Vue Router base.

Do not call LLMs.

Do not generate CV content.

Do not mutate business data except normal read-only status computation.

Do not reset/delete workspace data.

Do not create backups.

Do not expose secrets.

Do not expose masked secrets.

Do not expose absolute local filesystem paths.

Do not add Docker.

Do not use Vuex.

Keep Pinia.

Do not use TypeScript.

---

## Required Investigation Before Editing

Inspect route and consumer usage.

Run/search:

```bash
rg -n 'settings/current|current settings|artifacts_dir|api_key|token|secret|password|credential|keyring|masked|configured' .
rg -n '@.*\.get\("/settings/current"|settings/current|settings' job_agent tests frontend
rg -n 'fetch\(|apiFetch|vueApiFetch|settings/current' frontend
```

Inspect likely files:

```text
job_agent/routers/
job_agent/services/
job_agent/config/
tests/
frontend/templates/
frontend/static/
frontend/vue/
docs/legacy_surface_hardening.md
docs/vue_migration_final_audit.md
```

Identify:

```text
- route handler for GET /settings/current
- response schema/shape
- tests that assert current response fields
- frontend/static or template consumers that expect old fields
```

Do not assume location.

---

## Files To Modify

Likely modify one or more backend files containing settings route logic, for example:

```text
job_agent/routers/settings.py
job_agent/routers/system.py
job_agent/services/settings*.py
job_agent/main.py
```

Add tests:

```text
tests/test_settings_current_hardening.py
```

Optional documentation update:

```text
docs/settings_current_hardening.md
```

Modify existing tests only if they explicitly assert unsafe fields.

Do not modify:

```text
frontend/vue/src/router/index.js
vite.config.js
frontend/templates/
frontend/static/*.js
temp_mac_test/
```

Exception:

- If a legacy frontend static JS file genuinely relies on unsafe response fields, update it to use safe replacement fields only.
- Keep that change minimal and document it.

---

## Sanitization Rules

`GET /settings/current` must not expose keys containing or resembling:

```text
api_key
token
secret
password
credential
private_key
access_key
refresh_token
auth
keyring
env
environment
path
file_path
absolute_path
home
root
directory
dir
artifacts_dir
```

`GET /settings/current` must not expose values that look like:

```text
absolute local filesystem paths
masked API keys
raw API keys
environment variable values
keyring values
```

Unsafe value examples:

```text
/Users/name/...
/home/name/...
/var/...
/tmp/...
~/...
file:///...
sk-****
****abcd
lmstudio-token
openai-api-key
anthropic-key
```

Do not return masked secrets either.

Replace unsafe fields with safe booleans/status values.

---

## Required Response Shape Strategy

Preserve compatibility where safe.

Preferred response fields may include:

```json
{
  "ok": true,
  "providers": [
    {
      "name": "lm_studio",
      "configured": true,
      "available": true,
      "local": true
    }
  ],
  "artifacts_available": true,
  "secrets_exposed": false,
  "paths_exposed": false
}
```

Actual response shape should follow the existing project style.

Do not force a new global envelope if the legacy endpoint does not use one, unless existing patterns support it.

But these safety fields should be present if useful:

```text
secrets_exposed: false
paths_exposed: false
```

If artifact/workspace status is useful, expose:

```text
artifacts_available: boolean
```

not:

```text
artifacts_dir
```

For provider credentials, expose:

```text
configured: boolean
```

not:

```text
api_key
masked_api_key
token
masked_token
```

---

## Compatibility Requirements

Do not break legitimate legacy consumers.

If old frontend code expects a field like `artifacts_dir`, update the consumer to use `artifacts_available` or another safe replacement.

If old tests expect masked keys, update them to assert safe boolean/status fields.

If old docs mention `artifacts_dir` as a public response field, update docs.

Do not keep deprecated unsafe fields for backward compatibility.

Security wins over unsafe compatibility.

---

## Tests Required

Add:

```text
tests/test_settings_current_hardening.py
```

Use existing FastAPI TestClient/app fixture conventions.

Minimum tests:

```text
GET /settings/current returns 200
GET /settings/current returns JSON
GET /settings/current does not contain artifacts_dir
GET /settings/current does not contain keys matching api_key/token/secret/password/credential/keyring/path-like unsafe names
GET /settings/current does not contain absolute local filesystem path values
GET /settings/current does not contain masked secret-looking values
GET /settings/current includes secrets_exposed=false or equivalent safe signal
GET /settings/current includes paths_exposed=false or equivalent safe signal
GET /settings/current includes safe provider configured booleans if provider status is returned
GET /api/vue/settings remains safe
GET /app/settings still serves Vue
GET /ui/about or stable /ui route remains legacy HTML
```

Add a recursive helper to scan JSON keys and values.

Unsafe key patterns:

```text
api_key
token
secret
password
credential
private_key
access_key
refresh_token
keyring
absolute_path
file_path
artifacts_dir
```

Unsafe value patterns:

```text
/Users/
/home/
/var/
/tmp/
~/ 
file:
sk-
****
```

Be careful:

- Do not fail normal URLs solely because they contain `/`.
- Do not fail route paths like `/app/settings` unless they are clearly filesystem paths.
- Do not fail the safe key `secrets_exposed` if used. Treat it as allowed.
- Do not fail the safe key `paths_exposed` if used. Treat it as allowed.
- Do not fail safe boolean fields ending with `_configured`.

---

## Existing Test Updates

Search existing tests for now-unsafe fields:

```bash
rg -n 'artifacts_dir|api_key|masked|token|secret|settings/current' tests
```

If tests assert unsafe public response fields, update them to assert safe replacements.

Do not remove meaningful test coverage.

---

## Documentation Required

Add:

```text
docs/settings_current_hardening.md
```

Keep it concise.

Include:

```text
- purpose of hardening pass
- endpoint sanitized: /settings/current
- unsafe fields removed
- safe replacement fields
- compatibility notes
- statement that /ui remains active
- statement that /app Vue bridge remains unchanged
```

Optionally update:

```text
docs/legacy_surface_hardening.md
```

to mention that `/settings/current` was handled in this follow-on pass.

---

## Validation Commands

Run:

```bash
npm run build:vue
```

Run:

```bash
npm run css:build
```

Run focused tests:

```bash
pytest tests/test_vue_api_contracts.py tests/test_vue_spa_serving.py tests/test_legacy_surface_hardening.py tests/test_settings_current_hardening.py -v
```

Run full tests:

```bash
pytest
```

Do not fix unrelated known failures unless this task directly caused them.

---

## Manual Validation

Start backend using the project’s documented command.

Check:

```text
http://localhost:8000/settings/current
http://localhost:8000/api/vue/settings
http://localhost:8000/app/settings
http://localhost:8000/ui/about
```

Expected:

```text
/settings/current returns JSON
/settings/current does not expose artifacts_dir
/settings/current does not expose masked or raw secrets
/settings/current does not expose absolute local filesystem paths
/api/vue/settings remains safe
/app/settings serves Vue
/ui/about remains legacy HTML
```

---

## Acceptance Criteria

This task is complete only if:

1. `/settings/current` still exists.
2. `/settings/current` returns JSON.
3. `/settings/current` does not expose `artifacts_dir`.
4. `/settings/current` does not expose raw secrets.
5. `/settings/current` does not expose masked secrets.
6. `/settings/current` does not expose absolute local filesystem paths.
7. `/settings/current` exposes safe booleans/status fields instead.
8. `/api/vue/settings` remains safe.
9. `/app/settings` still serves Vue.
10. `/ui/*` remains legacy.
11. Tests for settings-current hardening are added.
12. Focused tests pass.
13. `npm run build:vue` passes.
14. Full pytest has no new failures beyond known pre-existing failures.
15. No Jinja templates are removed.
16. No legacy static JS is removed unless a minimal safe-field consumer update is necessary.
17. No Vue routing strategy is changed.
18. No backend business logic beyond response sanitization is changed.

---

## Forbidden Outcomes

Do not:

- remove /settings/current
- redirect /settings/current to Vue
- expose artifacts_dir
- expose masked API keys
- expose raw API keys
- expose tokens
- expose secrets
- expose keyring values
- expose environment variable values
- expose absolute paths
- break /app/settings
- break /ui routes
- remove Jinja templates
- remove legacy static JS
- change /app SPA bridge strategy
- change Vue Router base
- call LLMs
- generate CV content
- mutate business data
- reset workspace
- delete workspace data
- create backups
- add Docker
- use Vuex
- add TypeScript

---

## Final Codex/Claude Response

Report:

1. files added
2. files modified
3. endpoint audited
4. unsafe fields found
5. sanitization changes made
6. compatibility updates made
7. commands run
8. `npm run build:vue` result
9. focused test result
10. full `pytest` result
11. whether full-test failures are pre-existing or caused by this task
12. manual validation result
13. known issues
14. recommended next step

Do not continue to legacy cleanup/removal.
