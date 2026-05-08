# 014 Vue Navigation Base Cleanup

## Goal

Clean up and verify Vue navigation after the SPA bridge moved the FastAPI-served Vue app under:

```text
/app
/app/*
```

The previous task updated the FastAPI SPA bridge, Vite base, and Vue Router base. This task verifies and fixes internal Vue navigation so all links, redirects, hard refreshes, and built assets work correctly under `/app`.

No backend business logic changes.

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
```

Current intended route strategy:

```text
FastAPI Vue entry:
- http://localhost:8000/app
- http://localhost:8000/app/dashboard
- http://localhost:8000/app/jobs
- http://localhost:8000/app/drafts/123

Vite dev entry:
- http://localhost:5173/app
- http://localhost:5173/app/dashboard

Backend legacy/API routes:
- /dashboard remains existing backend route
- /ui/* remains legacy Jinja
- /api/* remains backend API
- /api/vue/* remains Vue API contracts
- /static/* remains static files
```

Vue Router should use:

```js
createWebHistory("/app")
```

Vite production build should emit assets under:

```text
/static/dist/assets/
```

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

---

## Required Investigation Before Editing

Inspect:

```text
frontend/vue/src/router/index.js
frontend/vue/src/constants/navigation.js
frontend/vue/src/layouts/AppLayout.vue
frontend/vue/src/components/AppSidebar.vue
frontend/vue/src/components/AppTopbar.vue
frontend/vue/src/pages/*.vue
vite.config.js
job_agent/main.py
tests/test_vue_spa_serving.py
```

Search for hardcoded route strings:

```bash
rg 'to="/|href="/|router.push|createWebHistory|/dashboard|/jobs|/app' frontend/vue
rg 'createWebHistory|base:|/static/dist|/app' vite.config.js frontend/vue/src/router/index.js
```

Identify any links that accidentally point to full backend paths when they should be Vue-router paths.

---

## Files To Modify

Likely modify:

```text
frontend/vue/src/constants/navigation.js
frontend/vue/src/router/index.js
frontend/vue/src/components/AppSidebar.vue
frontend/vue/src/components/AppTopbar.vue
frontend/vue/src/pages/*.vue
tests/test_vue_spa_serving.py
```

Only modify files if needed.

Do not modify:

```text
frontend/templates/
frontend/static/*.js
job_agent/routers/
start_apply/
config/
temp_mac_test/
```

Backend exception:

- Do not modify `job_agent/main.py` unless the SPA bridge is clearly wrong after inspection.
- If modifying `job_agent/main.py`, only fix `/app` SPA serving behavior.
- Do not modify backend business logic.

---

## Main Cleanup Requirements

### 1. Router Base

Verify `frontend/vue/src/router/index.js` uses:

```js
createWebHistory("/app")
```

Do not use bare `createWebHistory()`.

Do not use hash routing.

Routes should remain client-side routes like:

```text
/dashboard
/jobs
/drafts/:id
```

Do not rename all Vue routes to `/app/dashboard`.

Expected:

```text
/app/dashboard -> route path /dashboard -> DashboardPage
/app/drafts/123 -> route path /drafts/:id -> DraftDetailPage
```

---

### 2. Root Redirect

The Vue route `/` should redirect to:

```text
/dashboard
```

not:

```text
/app/dashboard
```

Because the router base already handles `/app`.

Expected:

```js
{
  path: "/",
  redirect: "/dashboard"
}
```

---

### 3. RouterLinks

All internal Vue `RouterLink` targets must use route paths without `/app`.

Correct:

```vue
<RouterLink to="/dashboard">Dashboard</RouterLink>
<RouterLink to="/jobs">Jobs</RouterLink>
<RouterLink :to="`/drafts/${draft.id}`">Open</RouterLink>
```

Incorrect:

```vue
<RouterLink to="/app/dashboard">Dashboard</RouterLink>
<RouterLink href="/dashboard">Dashboard</RouterLink>
<a href="/dashboard">Dashboard</a>
```

The only acceptable normal anchor `<a>` tags are for external URLs or legacy `/ui/*` links that are explicitly marked as legacy.

---

### 4. Sidebar Navigation

Verify:

```text
frontend/vue/src/constants/navigation.js
frontend/vue/src/components/AppSidebar.vue
```

Navigation items should stay as Vue route paths:

```text
/dashboard
/jobs
...
```

They should not be changed to `/app/dashboard`.

`RouterLink` will render correct browser URLs because of router base.

---

### 5. Topbar / Entry Labels

Update any user-facing text if needed so it is clear that:

```text
Vue shell is served under /app
Legacy UI remains under /ui
```

Do not add noisy text everywhere.

A short label in topbar or about/help page is acceptable.

---

### 6. Direct Refresh Behavior

Ensure FastAPI supports direct refresh for:

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

`/app/unknown-route` may serve Vue index so Vue Router can show `NotFoundPage`.

Unknown non-`/app` routes should not be swallowed by Vue.

---

### 7. Vite Build Asset Paths

Verify after:

```bash
npm run build:vue
```

The built file:

```text
frontend/static/dist/index.html
```

references assets like:

```text
/static/dist/assets/...
```

and not:

```text
/assets/...
```

If already correct, do not change Vite config.

---

## Tests Required

Update or add tests in:

```text
tests/test_vue_spa_serving.py
```

Minimum tests:

```text
GET /app returns Vue HTML or safe 503 if build missing
GET /app/dashboard returns Vue HTML or safe 503
GET /app/jobs returns Vue HTML or safe 503
GET /app/drafts/123 returns Vue HTML or safe 503
GET /app/unknown-route returns Vue HTML or safe 503
GET /dashboard remains existing backend route and is not Vue HTML
GET /api/vue/health returns JSON, not Vue HTML
GET /static/nonexistent-file.js is not Vue HTML
GET /ui/about or another stable /ui route is not Vue HTML
built index.html references /static/dist/assets/ if build exists
built index.html does not reference bare /assets/ if build exists
```

If the project has no stable `/ui/about`, use a stable known `/ui/*` route from current routers.

Tests must not rely on absolute filesystem paths.

---

## Manual Validation

Run:

```bash
npm run build:vue
```

Start backend using the project’s documented command.

Open:

```text
http://localhost:8000/app
http://localhost:8000/app/dashboard
http://localhost:8000/app/jobs
http://localhost:8000/app/drafts/123
http://localhost:8000/app/unknown-route
http://localhost:8000/api/vue/health
http://localhost:8000/dashboard
```

Expected:

```text
/app* serves Vue
/app/unknown-route serves Vue NotFoundPage client-side
/api/vue/health returns JSON
/dashboard remains backend route and not Vue
/ui/* remains legacy Jinja
```

Run Vite dev server:

```bash
npm run dev:vue
```

Open:

```text
http://localhost:5173/app
http://localhost:5173/app/dashboard
http://localhost:5173/app/jobs
http://localhost:5173/app/drafts/123
```

Expected:

```text
Vite dev server works under /app
Sidebar links navigate under /app
Hard refresh under /app routes works in dev
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
pytest tests/test_vue_api_contracts.py tests/test_vue_spa_serving.py -v
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

## Acceptance Criteria

This task is complete only if:

1. Vue Router uses `/app` history base.
2. Internal Vue routes remain bare paths like `/dashboard`.
3. Internal RouterLinks do not hardcode `/app`.
4. Internal RouterLinks do not accidentally use legacy `/ui/*` unless intentionally linking to legacy fallback.
5. `/app/dashboard` serves Vue.
6. `/app/drafts/123` serves Vue.
7. `/app/unknown-route` serves Vue for client-side NotFoundPage.
8. `/dashboard` remains backend route and is not swallowed by Vue.
9. `/api/vue/health` returns JSON and is not swallowed by Vue.
10. `/static/*` is not swallowed by Vue.
11. Legacy `/ui/*` is not swallowed by Vue.
12. Built index references `/static/dist/assets/`.
13. Built index does not reference bare `/assets/`.
14. `npm run build:vue` passes.
15. Focused tests pass.
16. Existing unrelated full-test failures are reported as pre-existing.
17. No backend business logic is changed.
18. No Jinja templates are removed.
19. No legacy static JS is removed.

---

## Forbidden Outcomes

Do not:

- change Vue routes to `/app/dashboard` route definitions unless absolutely necessary
- hardcode `/app` into every RouterLink
- change existing backend `/dashboard` route
- redirect `/dashboard` to Vue
- redirect `/ui/*` to Vue
- redirect `/api/*` to Vue
- redirect `/api/vue/*` to Vue
- swallow `/static/*`
- remove Jinja templates
- remove legacy static JS
- remove HTMX
- remove Alpine
- call LLMs
- generate CV content
- mutate business data
- expose secrets
- expose local filesystem paths
- use Vuex
- replace Pinia
- add TypeScript
- add Docker

---

## Final Codex Response

Report:

1. files added
2. files modified
3. router base strategy
4. navigation/link cleanup result
5. build asset path result
6. commands run
7. `npm run build:vue` result
8. focused test result
9. full `pytest` result
10. whether full-test failures are pre-existing or caused by this task
11. manual validation result
12. known issues

Do not continue to legacy cleanup/removal.
