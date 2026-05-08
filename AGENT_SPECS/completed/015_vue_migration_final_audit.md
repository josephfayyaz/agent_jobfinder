# 015 Vue Migration Final Audit

## Goal

Audit the completed Vue migration before any legacy cleanup/removal.

This task must verify that:

```text
- all Vue routes work under /app
- legacy /ui routes still work
- /api/* and /api/vue/* are not swallowed by Vue
- /static/* is not swallowed by Vue
- no unsafe endpoints are called from Vue pages
- no old PlaceholderPage wrappers remain on migrated pages
- build and tests pass except known pre-existing failures
- final migration status is documented
```

This is an audit and verification task.

Do not remove Jinja.
Do not remove HTMX.
Do not remove Alpine.
Do not remove legacy static JS.
Do not perform cleanup/removal yet.

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
```

Current route strategy:

```text
Vue app:
- /app
- /app/*

Legacy UI:
- /ui/*

APIs:
- /api/*
- /api/vue/*

Static:
- /static/*
```

Known pre-existing full-suite failures:

```text
tests/test_frontend_null_guards.py::test_intake_js_has_null_guard_on_full_name
tests/test_frontend_null_guards.py::test_intake_js_has_null_guard_on_email
tests/test_temp_harness.py::test_temp_harness_bootstrap_does_not_hardcode_repo_root
```

Do not fix these in this task unless this task directly worsens them.

---

## Hard Constraints

Do not modify backend business logic.

Do not remove Jinja templates.

Do not remove legacy static JavaScript.

Do not remove HTMX.

Do not remove Alpine.

Do not remove existing `/ui/*` routes.

Do not remove existing `/api/*` routes.

Do not remove existing `/api/vue/*` routes.

Do not remove existing `/static/*` behavior.

Do not rename or change the existing backend `/dashboard` route.

Do not call LLMs.

Do not generate CV content.

Do not mutate business data.

Do not expose secrets.

Do not expose local filesystem paths.

Do not add Docker.

Do not use Vuex.

Keep Pinia.

Do not use TypeScript.

Do not implement new product behavior.

---

## Files To Inspect

Inspect at minimum:

```text
frontend/vue/
frontend/vue/src/router/index.js
frontend/vue/src/constants/navigation.js
frontend/vue/src/components/
frontend/vue/src/pages/
frontend/vue/src/api/client.js
vite.config.js
job_agent/main.py
job_agent/routers/vue_api.py
tests/test_vue_api_contracts.py
tests/test_vue_spa_serving.py
package.json
tailwind.config.js
```

Also inspect legacy directories for existence only:

```text
frontend/templates/
frontend/static/
```

Do not rewrite legacy files.

---

## Files To Add Or Modify

Add:

```text
docs/vue_migration_final_audit.md
```

Optionally add:

```text
tests/test_vue_migration_audit.py
```

Only add the test file if useful and consistent with the existing test style.

Allowed modifications:

```text
tests/test_vue_spa_serving.py
tests/test_vue_api_contracts.py
docs/vue_migration_final_audit.md
```

Only modify Vue source files if the audit finds a real migration bug.

Do not modify backend business logic.

Do not modify legacy Jinja/static JS.

---

## Audit Checklist

### 1. Route Inventory

Verify Vue Router has routes for:

```text
/
 /dashboard
 /jobs
 /companies
 /apply
 /applications
 /drafts
 /drafts/:id
 /onboarding
 /settings
 /setup-required
 /verified-facts
 /story-bank
 /offer-compass
 /analytics
 /thesis
 /workspace-reset
 /help
 /about
 /vue-smoke
 /:pathMatch(.*)*
```

Verify FastAPI serves Vue under:

```text
/app
/app/*
```

Verify direct refresh works for:

```text
/app
/app/dashboard
/app/jobs
/app/companies
/app/apply
/app/applications
/app/drafts
/app/drafts/123
/app/onboarding
/app/settings
/app/setup-required
/app/verified-facts
/app/story-bank
/app/offer-compass
/app/analytics
/app/thesis
/app/workspace-reset
/app/help
/app/about
/app/vue-smoke
/app/unknown-route
```

---

### 2. Legacy Route Protection

Verify these are not swallowed by the SPA bridge:

```text
/api/vue/health
/api/vue/navigation
/api/vue/settings
/api/vue/workspace/status
/api/*
/ui/*
/static/*
/dashboard
```

Important:

```text
/dashboard must remain the existing backend route, not Vue.
```

---

### 3. Build Asset Audit

After:

```bash
npm run build:vue
```

Verify:

```text
frontend/static/dist/index.html exists
frontend/static/dist/index.html references /static/dist/assets/
frontend/static/dist/index.html does not reference bare /assets/
frontend/static/dist/assets/ exists
```

Do not commit build output if it is gitignored.

---

### 4. Placeholder Audit

Search:

```bash
rg "PlaceholderPage" frontend/vue/src/pages
```

Expected:

```text
No migrated route page should still import or render PlaceholderPage.
```

If `PlaceholderPage.vue` remains in components but is unused, leave it for cleanup/removal in a later cleanup spec.

Do not remove it in this audit.

---

### 5. Unsafe API Call Audit

Search Vue source for disallowed endpoint calls:

```bash
rg "/api/vue/apply|/apply/score|/apply/questions|/apply/draft|/revise|/polish|/approve|workspace/backup|workspace/reset|settings" frontend/vue/src
```

Manually classify results.

Allowed:

```text
GET /api/vue/settings through vueApiFetch("/settings") in read-only settings page
GET /api/vue/workspace/status
POST /api/vue/workspace/reset-preview
static text mentioning disabled revise/polish/approve actions
static text mentioning future apply actions
```

Forbidden:

```text
POST /api/vue/apply/score
POST /api/vue/apply/questions
POST /api/vue/apply/draft
PATCH /api/vue/drafts/{id}
POST /api/vue/drafts/{id}/revise
POST /api/vue/drafts/{id}/polish
POST /api/vue/drafts/{id}/approve
POST /api/vue/workspace/backup
real reset/delete endpoint calls
settings write/update endpoint calls
```

No forbidden calls may exist.

---

### 6. Secret/Path Exposure Audit

Search for likely unsafe render keys or strings:

```bash
rg "api_key|token|secret|password|credential|private_key|access_key|refresh_token|keyring|absolute_path|file_path|/Users/|~/" frontend/vue/src
```

Manually classify results.

Allowed:

```text
blocked key pattern lists
security notices
test text
```

Forbidden:

```text
rendering secret values
rendering masked secret values
rendering absolute local filesystem paths
rendering environment variable values
```

---

### 7. Package/Dependency Audit

Verify:

```text
vue exists
vue-router exists
pinia exists
vite exists
@vitejs/plugin-vue exists
vuex is not used
```

Run:

```bash
npm ls vue vue-router pinia vite @vitejs/plugin-vue
npm ls vuex
```

Expected:

```text
vuex should be absent or unused.
```

If `vuex` remains installed accidentally, remove it only if safe:

```bash
npm uninstall vuex
```

Then rerun build/tests.

---

### 8. Documentation Audit

Create:

```text
docs/vue_migration_final_audit.md
```

It must include:

```text
- migration summary
- final route strategy
- list of converted Vue pages
- API contract layer summary
- safety boundaries still enforced
- how to run Vue via FastAPI
- how to run Vue via Vite dev server
- known pre-existing test failures
- next recommended step
```

Keep it concise and specific.

---

## Tests Required

Run:

```bash
npm run build:vue
npm run css:build
pytest tests/test_vue_api_contracts.py tests/test_vue_spa_serving.py -v
pytest
```

If adding `tests/test_vue_migration_audit.py`, include it in focused tests:

```bash
pytest tests/test_vue_api_contracts.py tests/test_vue_spa_serving.py tests/test_vue_migration_audit.py -v
```

Do not fix unrelated known failures:

```text
tests/test_frontend_null_guards.py
tests/test_temp_harness.py
```

unless this task directly caused them.

---

## Manual Validation

Start backend using the project’s documented command.

Open:

```text
http://localhost:8000/app
http://localhost:8000/app/dashboard
http://localhost:8000/app/jobs
http://localhost:8000/app/apply
http://localhost:8000/app/drafts/123
http://localhost:8000/app/onboarding
http://localhost:8000/app/settings
http://localhost:8000/app/verified-facts
http://localhost:8000/app/workspace-reset
http://localhost:8000/app/unknown-route
http://localhost:8000/api/vue/health
http://localhost:8000/dashboard
http://localhost:8000/ui/about
```

Expected:

```text
/app* serves Vue
/app/unknown-route shows Vue NotFoundPage client-side
/api/vue/health returns JSON
/dashboard remains backend route and not Vue
/ui/about remains legacy route and not Vue
```

Run Vite dev server:

```bash
npm run dev:vue
```

Open:

```text
http://localhost:5173/app
http://localhost:5173/app/dashboard
http://localhost:5173/app/apply
```

Expected:

```text
Vite dev server works under /app
Sidebar links navigate under /app
Hard refresh under /app routes works in dev
```

---

## Acceptance Criteria

This task is complete only if:

1. Final audit document exists at `docs/vue_migration_final_audit.md`.
2. All Vue routes are reachable under `/app`.
3. `/app/unknown-route` is handled by Vue client-side NotFoundPage.
4. `/dashboard` remains backend route and is not swallowed by Vue.
5. `/api/vue/*` returns JSON and is not swallowed by Vue.
6. `/ui/*` remains legacy and is not swallowed by Vue.
7. `/static/*` remains static and is not swallowed by Vue.
8. Built Vue assets use `/static/dist/assets/`.
9. Built Vue assets do not use bare `/assets/`.
10. No migrated Vue page still renders `PlaceholderPage`.
11. No forbidden mutating/generative endpoint calls exist in Vue source.
12. No secrets or local filesystem paths are rendered.
13. Pinia is used.
14. Vuex is not used.
15. `npm run build:vue` passes.
16. Focused tests pass.
17. Full pytest has no new failures beyond the known pre-existing failures.
18. No backend business logic is changed.
19. No legacy Jinja/HTMX/Alpine/static JS cleanup is performed.

---

## Forbidden Outcomes

Do not:

- remove Jinja templates
- remove legacy static JS
- remove HTMX
- remove Alpine
- delete PlaceholderPage component
- delete old templates
- delete old static JS
- change backend /dashboard route
- redirect /dashboard to Vue
- redirect /ui/* to Vue
- redirect /api/* to Vue
- redirect /api/vue/* to Vue
- swallow /static/*
- call apply score/questions/draft endpoints
- call draft revise/polish/approve endpoints
- call workspace backup/reset/delete endpoints
- call settings write/update endpoints
- call LLMs
- generate CV content
- mutate business data
- expose secrets
- expose absolute local paths
- use Vuex
- add TypeScript
- add Docker
- do cleanup/removal of legacy frontend

---

## Final Codex/Claude Response

Report:

1. files added
2. files modified
3. route audit result
4. legacy route protection result
5. build asset audit result
6. placeholder audit result
7. unsafe API call audit result
8. secret/path exposure audit result
9. dependency audit result
10. commands run
11. `npm run build:vue` result
12. focused test result
13. full `pytest` result
14. whether full-test failures are pre-existing or caused by this task
15. manual validation result
16. known issues
17. recommended next step

Do not continue to legacy cleanup/removal.
