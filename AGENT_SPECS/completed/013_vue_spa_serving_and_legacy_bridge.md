# 013 Vue SPA Serving and Legacy Bridge

## Goal

Serve the built Vue app from FastAPI safely while keeping the legacy Jinja `/ui/*` frontend active.

This task must add a controlled SPA serving bridge for Vue routes only.

Do not remove Jinja templates.
Do not remove legacy static JavaScript.
Do not remove HTMX or Alpine.
Do not break existing `/ui/*`, `/api/*`, `/api/vue/*`, or `/static/*` routes.

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
```

The Vue app now has real Vue pages/shells for all current Vue routes.

Current Vue build output is expected under:

```text
frontend/static/dist/
```

Existing legacy Jinja frontend remains under:

```text
frontend/templates/
frontend/static/
```

---

## Purpose

After this task, FastAPI should be able to serve the built Vue app for Vue frontend routes in production/local mode.

Legacy `/ui/*` routes must remain available during the migration.

This task is a bridge, not cleanup.

---

## Hard Constraints

Do not remove Jinja templates.

Do not remove legacy static JS.

Do not remove HTMX.

Do not remove Alpine.

Do not remove existing `/ui/*` routes.

Do not remove existing `/api/*` routes.

Do not remove `/api/vue/*` routes.

Do not change backend business logic.

Do not modify LLM routing.

Do not call LLMs.

Do not generate CV content.

Do not modify CV generation.

Do not modify verified-fact validation.

Do not modify human approval workflow.

Do not modify onboarding business rules.

Do not modify settings/provider/keyring logic.

Do not modify Gmail sync.

Do not modify background worker behavior.

Do not modify workspace reset/delete/backup behavior.

Do not expose secrets.

Do not expose local filesystem paths.

Do not add Docker.

Do not use Vuex.

Keep Pinia.

Do not use TypeScript.

---

## Required Investigation Before Editing

Inspect:

```text
job_agent/main.py
job_agent/routers/
frontend/static/
frontend/static/dist/
vite.config.js
package.json
tests/
```

Find:

```text
FastAPI app object
existing StaticFiles mounts
existing /static mount
existing /ui router registration
existing /api router registration
existing route order
current test client pattern
```

Use the project’s existing style.

Do not assume route order; verify it.

---

## Files To Modify

Likely modify:

```text
job_agent/main.py
```

Add tests:

```text
tests/test_vue_spa_serving.py
```

Optional docs update:

```text
docs/vue_spa_serving.md
```

Do not modify Vue page files unless absolutely necessary.

Do not modify legacy templates/static JS.

Do not modify `job_agent/routers/vue_api.py` unless needed for route-order tests.

---

## Route Serving Strategy

Add a controlled SPA fallback that serves the built Vue `index.html` for known Vue routes only.

Do not add an unrestricted catch-all that can swallow APIs or legacy routes.

### Required Vue Routes

The SPA bridge must serve Vue index for these paths:

```text
/
 /dashboard
 /jobs
 /companies
 /apply
 /applications
 /drafts
 /drafts/{anything}
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
```

Use route definitions that are safe and explicit.

Acceptable approach:

```py
VUE_ROUTES = {
    "/",
    "/dashboard",
    "/jobs",
    "/companies",
    "/apply",
    "/applications",
    "/drafts",
    "/onboarding",
    "/settings",
    "/setup-required",
    "/verified-facts",
    "/story-bank",
    "/offer-compass",
    "/analytics",
    "/thesis",
    "/workspace-reset",
    "/help",
    "/about",
    "/vue-smoke",
}

@app.get("/{full_path:path}", include_in_schema=False)
async def serve_vue_spa(full_path: str):
    normalized = "/" + full_path.strip("/")
    if normalized == "/":
        ...
    if normalized in VUE_ROUTES or normalized.startswith("/drafts/"):
        ...
    raise HTTPException(status_code=404)
```

But this catch-all must be registered after:

```text
/static mount
/api routers
/api/vue router
/ui routes
auth routes
other backend routes
```

If the project already has a 404 handler, follow the existing style.

---

## Build File Behavior

Serve:

```text
frontend/static/dist/index.html
```

If it exists.

If it does not exist, return a clear JSON or text 503/404 message that says the Vue build is missing and `npm run build:vue` must be run.

Do not crash the backend with an unhandled exception.

Preferred behavior:

```text
HTTP 503
message: Vue build not found. Run npm run build:vue.
```

Do not expose absolute file paths in the response.

---

## Static Assets

Vite built assets are under:

```text
frontend/static/dist/assets/
```

Ensure FastAPI can serve these files.

If `/static` is already mounted to `frontend/static`, this may already work:

```text
/static/dist/assets/...
```

Do not add duplicate conflicting static mounts.

If a new mount is needed, use a non-conflicting path and explain why.

Preferred:

```text
Use existing /static mount if available.
```

---

## Legacy Bridge Requirements

The following must continue to work:

```text
/api/vue/health
/api/vue/navigation
/api/vue/settings
/api/vue/workspace/status
/ui/* existing routes
/static/* existing assets
```

Do not redirect `/ui/*` to Vue.

Do not redirect `/api/*` to Vue.

Do not redirect `/api/vue/*` to Vue.

Do not redirect `/static/*` to Vue.

---

## Tests Required

Add:

```text
tests/test_vue_spa_serving.py
```

Use the existing FastAPI TestClient/app fixture pattern.

Minimum tests:

```text
GET / returns 200 or 503 if build missing, but does not hit /ui
GET /dashboard returns Vue index or 503 build-missing message
GET /about returns Vue index or 503 build-missing message
GET /drafts/123 returns Vue index or 503 build-missing message
GET /not-a-vue-route returns 404
GET /api/vue/health still returns JSON API envelope, not Vue HTML
GET /api/vue/settings still returns JSON API envelope, not Vue HTML
GET /static/nonexistent-file.js does not return Vue index
Existing /ui route still returns legacy HTML if a stable known /ui route exists
```

Important:

- Tests must work whether `frontend/static/dist/index.html` exists or not.
- If build exists, assert response contains Vue index shell or HTML.
- If build missing, assert 503 and a safe build-missing message.
- Do not require absolute paths in assertions.
- Do not break existing tests.

---

## Optional Documentation

Add:

```text
docs/vue_spa_serving.md
```

Keep it short.

Include:

```text
Purpose of SPA bridge
Vue build command: npm run build:vue
Vue build output: frontend/static/dist/
Legacy /ui/* remains active
/api/* and /api/vue/* are not swallowed by SPA fallback
Known Vue routes served by FastAPI
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
pytest tests/test_vue_api_contracts.py tests/test_vue_spa_serving.py
```

Run full tests:

```bash
pytest
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

Then check:

```text
http://localhost:8000/
http://localhost:8000/dashboard
http://localhost:8000/about
http://localhost:8000/drafts/123
http://localhost:8000/api/vue/health
http://localhost:8000/api/vue/settings
```

Expected:

```text
/ and Vue routes serve the built Vue app
/api/vue/* returns JSON
/ui/* legacy app still works
/static/* still works
```

Also check Vite dev mode still works separately:

```bash
npm run dev:vue
```

Open:

```text
http://localhost:5173/dashboard
```

Expected:

```text
Vite dev server still works
```

---

## Acceptance Criteria

This task is complete only if:

1. FastAPI serves Vue build for `/`.
2. FastAPI serves Vue build for `/dashboard`.
3. FastAPI serves Vue build for `/about`.
4. FastAPI serves Vue build for `/drafts/123`.
5. Unknown non-Vue routes return 404, not Vue index.
6. `/api/vue/*` routes still return JSON.
7. `/api/*` routes are not swallowed by Vue fallback.
8. `/ui/*` legacy routes remain active.
9. `/static/*` assets are not swallowed by Vue fallback.
10. Missing Vue build is handled gracefully with safe 503/404 message.
11. Tests for SPA serving are added.
12. `npm run build:vue` passes.
13. Focused tests pass.
14. Existing unrelated full-test failures are reported as pre-existing.
15. No backend business logic is changed.
16. No Jinja templates are removed.
17. No legacy static JS is removed.

---

## Forbidden Outcomes

Do not:

- add an unrestricted catch-all that swallows API routes
- redirect /ui routes to Vue
- redirect /api routes to Vue
- redirect /api/vue routes to Vue
- redirect /static routes to Vue
- remove Jinja templates
- remove legacy static JS
- remove HTMX
- remove Alpine
- change LLM routing
- call LLMs
- generate CV content
- mutate business data
- expose absolute filesystem paths
- expose secrets
- add Docker
- use Vuex
- replace Pinia
- add TypeScript

---

## Final Codex/Claude Response

Report:

1. files added
2. files modified
3. route serving strategy implemented
4. commands run
5. `npm run build:vue` result
6. focused test result
7. full `pytest` result
8. whether full-test failures are pre-existing or caused by this task
9. manual validation result
10. known issues

Do not continue to cleanup/removal of legacy frontend.
