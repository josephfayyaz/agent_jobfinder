# 016 Legacy Surface Hardening

## Goal

Audit and sanitize remaining non-Vue backend surfaces that may expose unsafe implementation details, especially legacy JSON endpoints such as:

```text
/dashboard
```

This task must harden legacy/backend responses without changing Vue behavior and without removing the legacy `/ui/*` frontend.

Primary known issue from the final Vue audit:

```text
Legacy backend /dashboard JSON still exposes pdflatex_path.
```

Fix that class of leak.

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
```

Current route strategy:

```text
Vue SPA:
- /app
- /app/*

Legacy UI:
- /ui/*

Backend APIs:
- /api/*
- /api/vue/*

Existing backend JSON dashboard:
- /dashboard
```

Known full-suite failures before this task:

```text
tests/test_frontend_null_guards.py::test_intake_js_has_null_guard_on_full_name
tests/test_frontend_null_guards.py::test_intake_js_has_null_guard_on_email
tests/test_temp_harness.py::test_temp_harness_bootstrap_does_not_hardcode_repo_root
```

Do not fix these in this task unless this task directly affects them.

---

## Purpose

This task is not part of Vue page migration.

It is a security/surface-hardening pass for old backend JSON surfaces that remain active alongside Vue.

The goal is to prevent legacy endpoints from exposing:

```text
absolute local filesystem paths
secret-looking fields
environment or keyring details
implementation-only tool paths
```

while preserving route existence and functional compatibility as much as possible.

---

## Hard Constraints

Do not remove Jinja templates.

Do not remove legacy static JavaScript.

Do not remove HTMX.

Do not remove Alpine.

Do not remove `/ui/*` routes.

Do not remove `/api/*` routes.

Do not remove `/api/vue/*` routes.

Do not remove `/static/*` behavior.

Do not redirect `/dashboard` to Vue.

Do not change the Vue `/app` serving strategy.

Do not call LLMs.

Do not generate CV content.

Do not mutate business data.

Do not reset/delete workspace data.

Do not create backups.

Do not expose secrets.

Do not expose absolute local filesystem paths.

Do not add Docker.

Do not use Vuex.

Keep Pinia.

Do not use TypeScript.

---

## Required Investigation Before Editing

Inspect route definitions and response payloads for legacy/backend endpoints.

At minimum inspect:

```text
job_agent/main.py
job_agent/routers/
job_agent/services/
tests/
docs/vue_migration_final_audit.md
```

Search for path/secret exposure:

```bash
rg -n "pdflatex_path|latex|path|file_path|absolute_path|/Users/|~/|HOME|keyring|api_key|token|secret|password|credential|private_key|access_key|refresh_token" job_agent tests docs
```

Find route handlers for:

```text
/dashboard
/api/*
/ui/*
```

Use:

```bash
rg -n '@.*\.get\("/dashboard"|@.*\.get\(.*dashboard|dashboard' job_agent
rg -n 'APIRouter|include_router|FastAPI|@.*\.get|@.*\.post|@.*\.patch|@.*\.delete' job_agent
```

Do not assume the route location.

---

## Files To Modify

Likely modify one or more backend files containing legacy route logic, for example:

```text
job_agent/main.py
job_agent/routers/*.py
job_agent/services/*.py
```

Add tests:

```text
tests/test_legacy_surface_hardening.py
```

Optional documentation update:

```text
docs/legacy_surface_hardening.md
```

Do not modify:

```text
frontend/templates/
frontend/static/*.js
frontend/vue/src/pages/
frontend/vue/src/router/index.js
vite.config.js
start_apply/
config/
temp_mac_test/
```

Exception:

- If an existing test needs a small update to reflect sanitized safe output, update only the relevant test.

---

## Sanitization Rules

Legacy/backend JSON responses must not expose fields whose keys contain or resemble:

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
pdflatex_path
```

Do not return absolute local path values, including values starting with:

```text
/
/Users/
~/ 
file:
```

Do not return masked secrets either, for example:

```text
sk-****
****abcd
openai-api-key
anthropic-key
lmstudio-token
```

If a field is useful but unsafe as a raw value, replace it with a safe boolean/status field.

Examples:

Bad:

```json
{
  "pdflatex_path": "/Library/TeX/texbin/pdflatex"
}
```

Good:

```json
{
  "pdflatex_available": true
}
```

Bad:

```json
{
  "workspace_path": "/Users/name/Library/Application Support/agent_jobfinder"
}
```

Good:

```json
{
  "workspace_available": true
}
```

---

## Required Fixes

### 1. Harden `/dashboard`

Inspect the existing `/dashboard` response.

It must continue to exist and must not be redirected to Vue.

It must not expose:

```text
pdflatex_path
absolute paths
secret-looking keys
environment/keyring details
```

If the current response includes `pdflatex_path`, replace it with:

```text
pdflatex_available
```

or remove it entirely if it is not required by clients/tests.

Prefer:

```json
{
  "pdflatex_available": true
}
```

over returning a path.

Do not expose where the binary lives.

### 2. Harden Related Legacy JSON Surfaces

Audit other backend JSON endpoints that are easy to check and likely active.

Focus on response payloads from route handlers, not internal implementation variables.

If you find unsafe public JSON fields, sanitize them using the same strategy:

```text
raw path/secret -> boolean/status/count
```

Do not perform large rewrites.

Do not change database schemas.

Do not change internal service APIs unless necessary to prevent public leakage.

### 3. Preserve Compatibility

Avoid breaking clients unnecessarily.

If a field must be removed or renamed for safety, add a safer replacement field.

Example:

```text
remove pdflatex_path
add pdflatex_available
```

Do not include deprecated unsafe fields.

---

## Tests Required

Add:

```text
tests/test_legacy_surface_hardening.py
```

Use existing FastAPI TestClient/app fixture conventions.

Minimum tests:

```text
GET /dashboard returns non-HTML JSON or expected backend response
GET /dashboard does not contain pdflatex_path
GET /dashboard does not contain absolute local filesystem paths
GET /dashboard does not contain secret-looking keys
GET /dashboard includes safe status field if LaTeX availability is still reported, e.g. pdflatex_available
/api/vue/dashboard/summary still does not expose pdflatex_path
/api/vue/health still returns JSON envelope
/app/dashboard still serves Vue HTML or safe 503
/ui/about or another stable /ui route still returns legacy HTML and is not swallowed
```

Also add a reusable test helper in the test file to recursively scan JSON for unsafe keys/values.

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
pdflatex_path
```

Unsafe value patterns:

```text
/Users/
file:
```

Be careful with `/`:

- Do not fail every URL or route path just because it contains `/`.
- Only fail obvious absolute local filesystem paths such as `/Users/`, `/home/`, `/var/`, `/tmp/`, `/Library/`, `~/`, or `file:`.

---

## Documentation Required

Add:

```text
docs/legacy_surface_hardening.md
```

Keep it concise.

Include:

```text
- purpose of hardening pass
- sanitized endpoint(s)
- unsafe fields removed
- safe replacement fields
- statement that /ui remains active
- statement that /app Vue bridge remains unchanged
```

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
pytest tests/test_vue_api_contracts.py tests/test_vue_spa_serving.py tests/test_legacy_surface_hardening.py -v
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
http://localhost:8000/dashboard
http://localhost:8000/api/vue/dashboard/summary
http://localhost:8000/api/vue/health
http://localhost:8000/app/dashboard
http://localhost:8000/ui/about
```

Expected:

```text
/dashboard returns backend JSON and does not expose pdflatex_path or absolute paths
/api/vue/dashboard/summary returns safe Vue contract JSON
/api/vue/health returns JSON
/app/dashboard serves Vue
/ui/about remains legacy HTML
```

---

## Acceptance Criteria

This task is complete only if:

1. `/dashboard` still exists.
2. `/dashboard` is not redirected to Vue.
3. `/dashboard` no longer exposes `pdflatex_path`.
4. `/dashboard` no longer exposes absolute local filesystem paths.
5. `/dashboard` no longer exposes secret-looking keys.
6. `/dashboard` includes a safe status replacement if LaTeX availability is still reported.
7. `/api/vue/dashboard/summary` remains safe.
8. `/app/dashboard` still serves Vue.
9. `/ui/*` remains legacy.
10. `/api/vue/*` remains JSON.
11. Tests for legacy surface hardening are added.
12. Focused tests pass.
13. `npm run build:vue` passes.
14. Full pytest has no new failures beyond known pre-existing failures.
15. No Jinja templates are removed.
16. No legacy static JS is removed.
17. No Vue routing strategy is changed.
18. No backend business logic beyond response sanitization is changed.

---

## Forbidden Outcomes

Do not:

- remove /dashboard
- redirect /dashboard to Vue
- remove /ui routes
- remove Jinja templates
- remove legacy static JS
- change /app SPA bridge strategy
- change Vue Router base
- expose pdflatex_path
- expose absolute paths
- expose secrets
- expose masked secrets
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
3. endpoints audited
4. unsafe fields found
5. sanitization changes made
6. commands run
7. `npm run build:vue` result
8. focused test result
9. full `pytest` result
10. whether full-test failures are pre-existing or caused by this task
11. manual validation result
12. known issues
13. recommended next step

Do not continue to legacy cleanup/removal.
