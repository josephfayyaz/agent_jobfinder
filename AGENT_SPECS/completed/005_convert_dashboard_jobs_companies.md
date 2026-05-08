# 005 Convert Dashboard Jobs Companies

## Goal

Convert the next low-risk read-only Vue pages from placeholders into real Vue pages:

```text
/dashboard
/jobs
/companies
```

Use the existing Vue API contract endpoints:

```text
GET /api/vue/dashboard/summary
GET /api/vue/jobs
GET /api/vue/companies
```

This task must not touch apply flow, drafts, onboarding, settings, verified facts, CV generation, LLM logic, or workspace destructive actions.

Keep all legacy `/ui/*` routes active.

---

## Current State

Completed specs:

```text
AGENT_SPECS/completed/codex/001_vue_infrastructure.md
AGENT_SPECS/completed/codex/002_vue_layout_router.md
AGENT_SPECS/completed/codex/003_vue_api_contracts.md
AGENT_SPECS/completed/codex/004_convert_static_pages.md
```

Already converted to real Vue pages:

```text
/about
/help
/setup-required
```

This task converts only:

```text
frontend/vue/src/pages/DashboardPage.vue
frontend/vue/src/pages/JobsPage.vue
frontend/vue/src/pages/CompaniesPage.vue
```

Do not convert any other page.

---

## Hard Constraints

Do not modify backend business logic.

Do not modify LLM routing.

Do not call LLMs.

Do not generate CV content.

Do not modify CV generation.

Do not modify verified-fact validation.

Do not modify human approval workflow.

Do not modify Gmail sync.

Do not modify background worker behavior.

Do not modify onboarding business rules.

Do not modify settings/provider/keyring logic.

Do not modify workspace reset/delete/backup behavior.

Do not add FastAPI SPA catch-all route.

Do not change existing `/ui/*` routes.

Do not delete or rewrite legacy Jinja templates.

Do not delete or rewrite existing static JS.

Do not migrate these pages yet:

```text
Apply
Applications
Drafts
Draft Detail
Onboarding
Settings
Verified Facts
Story Bank
Offer Compass
Analytics
Thesis
Workspace Reset
```

Do not use Vuex.

Keep Pinia.

Do not use TypeScript.

Do not add Docker.

Do not switch package manager.

---

## Files To Modify

Modify only:

```text
frontend/vue/src/pages/DashboardPage.vue
frontend/vue/src/pages/JobsPage.vue
frontend/vue/src/pages/CompaniesPage.vue
```

You may add small shared Vue components if they reduce duplication:

```text
frontend/vue/src/components/EmptyState.vue
frontend/vue/src/components/MetricCard.vue
frontend/vue/src/components/ApiNotice.vue
```

You may modify these shared frontend files only if necessary:

```text
frontend/vue/src/api/client.js
frontend/vue/src/api/contracts.js
```

Do not modify:

```text
frontend/templates/
frontend/static/
start_apply/
config/
temp_mac_test/
```

Backend exception:

- Do not modify backend files unless one of the required `/api/vue/*` read-only contract endpoints is broken.
- If an endpoint is broken, fix only the contract endpoint implementation in `job_agent/routers/vue_api.py`.
- Do not wire real business services unless they are already safe, read-only, and do not expose secrets or local paths.

---

## API Usage

The converted pages must use:

```js
vueApiFetch
```

from:

```text
frontend/vue/src/api/client.js
```

Use only these calls:

```text
vueApiFetch("/dashboard/summary")
vueApiFetch("/jobs")
vueApiFetch("/companies")
```

Do not call:

```text
/ui/*
raw /api/*
LLM endpoints
apply endpoints
draft endpoints
settings endpoints
verified-facts endpoints
workspace mutation endpoints
```

Do not scrape HTML.

Do not import data from Jinja templates.

---

## Required Behavior

### `/dashboard`

Convert `DashboardPage.vue` from placeholder to real Vue page.

It must:

1. Fetch data from `GET /api/vue/dashboard/summary`.
2. Show loading state.
3. Show error state.
4. Handle placeholder API response safely.
5. Render a dashboard overview using available API data.
6. Provide fallback cards if API returns placeholder/empty data.
7. Link to `/jobs`, `/companies`, and `/apply`.
8. Clearly mark contract/placeholder status when API is not wired to real data.

Required visible sections:

```text
Dashboard
Overview
Next actions
Migration status
```

Recommended fallback metric cards:

```text
Jobs tracked: 0
Companies tracked: 0
Applications tracked: 0
Drafts pending: 0
```

No real fake business data.

Use zero/empty values if no real data is provided.

---

### `/jobs`

Convert `JobsPage.vue` from placeholder to real Vue page.

It must:

1. Fetch data from `GET /api/vue/jobs`.
2. Show loading state.
3. Show error state.
4. Handle placeholder API response safely.
5. Render job list if `data.items` exists and is non-empty.
6. Render empty state if no jobs exist.
7. Show total count if available.
8. Provide links/buttons for future actions without triggering unsupported endpoints.

Required visible sections:

```text
Jobs
Job discovery status
Saved jobs
Next actions
```

Allowed links:

```text
/companies
/apply
```

Do not call job discovery, scraping, Gmail sync, JobSpy, or career scan endpoints.

Do not create jobs.

Do not mutate data.

If API response is placeholder, show this clearly.

---

### `/companies`

Convert `CompaniesPage.vue` from placeholder to real Vue page.

It must:

1. Fetch data from `GET /api/vue/companies`.
2. Show loading state.
3. Show error state.
4. Handle placeholder API response safely.
5. Render company list if `data.items` exists and is non-empty.
6. Render empty state if no companies exist.
7. Show total count if available.
8. Provide links/buttons for future actions without triggering unsupported endpoints.

Required visible sections:

```text
Companies
Company research status
Tracked companies
Next actions
```

Allowed links:

```text
/jobs
/thesis
```

Do not call company scanning, ATS, scraping, or enrichment endpoints.

Do not create companies.

Do not mutate data.

If API response is placeholder, show this clearly.

---

## Data Handling Rules

These endpoints may currently return placeholder data.

Pages must safely handle:

```text
response.data
response.data.items
response.data.total
response.status
response.message
missing fields
empty objects
network errors
backend offline
```

No page should crash if backend returns:

```json
{
  "ok": true,
  "contract_version": 1,
  "status": "placeholder",
  "message": "This list endpoint is ready for Vue migration but not wired to real data yet.",
  "data": {
    "items": [],
    "total": 0
  }
}
```

Use optional chaining and safe defaults.

Do not assume item schemas.

For unknown item fields, render only safe generic fields:

```text
title
name
company
location
status
source
id
```

If an item lacks fields, render fallback labels like:

```text
Untitled job
Unnamed company
```

Do not invent missing values.

---

## Recommended Implementation Pattern

Each page should use:

```js
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { vueApiFetch } from "../api/client";
import AppPageHeader from "../components/AppPageHeader.vue";
```

State pattern:

```js
const loading = ref(true);
const error = ref("");
const payload = ref(null);

onMounted(async () => {
  try {
    payload.value = await vueApiFetch("/jobs");
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Request failed";
  } finally {
    loading.value = false;
  }
});
```

Use computed values for:

```text
items
total
isPlaceholder
message
```

---

## Optional Shared Components

You may add these components if useful.

### `MetricCard.vue`

Props:

```text
label: string
value: string | number
description: string optional
```

Purpose:

Simple dashboard metric card.

### `EmptyState.vue`

Props:

```text
title: string
message: string
```

Purpose:

Reusable empty-state panel.

### `ApiNotice.vue`

Props:

```text
status: string optional
message: string optional
error: string optional
```

Purpose:

Display placeholder/status/error notice.

Keep these components simple.

Do not introduce global state.

Do not install UI libraries.

---

## Styling Requirements

Use Tailwind only.

Match current Vue shell:

```text
slate background
white cards
rounded-2xl
border border-slate-200
shadow-sm
text-slate-950
text-slate-600
```

Do not add new CSS files.

Do not install icon libraries.

Do not add animation libraries.

---

## Tests Required

Do not force a new Vue test framework.

Run existing tests and builds.

At minimum:

```bash
npm run build:vue
npm run css:build
pytest tests/test_vue_api_contracts.py
pytest
```

Do not fix unrelated known failures:

```text
tests/test_frontend_null_guards.py
tests/test_temp_harness.py
```

unless this task directly caused them.

If build fails because of Vue code, fix it.

If API contract tests fail because of this task, fix them.

---

## Manual Validation

Run the backend using the project’s documented command.

Run Vue dev server:

```bash
npm run dev:vue
```

Open:

```text
http://localhost:5173/dashboard
http://localhost:5173/jobs
http://localhost:5173/companies
```

Expected `/dashboard`:

```text
- page loads
- no console errors
- not the old placeholder card
- shows overview/metric cards
- shows next action links
- handles placeholder API response safely
```

Expected `/jobs`:

```text
- page loads
- no console errors
- not the old placeholder card
- shows job discovery status
- shows saved jobs section
- shows empty state if no jobs exist
- shows placeholder/API message when relevant
```

Expected `/companies`:

```text
- page loads
- no console errors
- not the old placeholder card
- shows company research status
- shows tracked companies section
- shows empty state if no companies exist
- shows placeholder/API message when relevant
```

Also verify these routes remain unchanged or still work:

```text
http://localhost:5173/about
http://localhost:5173/help
http://localhost:5173/setup-required
http://localhost:5173/apply
http://localhost:5173/drafts
http://localhost:5173/onboarding
http://localhost:5173/settings
```

Expected:

```text
/about, /help, /setup-required remain real Vue pages
/apply, /drafts, /onboarding, /settings remain placeholders
```

Verify legacy `/ui/*` routes still work if backend is running.

---

## Acceptance Criteria

This task is complete only if:

1. `DashboardPage.vue` is converted from placeholder to real Vue page.
2. `JobsPage.vue` is converted from placeholder to real Vue page.
3. `CompaniesPage.vue` is converted from placeholder to real Vue page.
4. Dashboard uses `vueApiFetch("/dashboard/summary")`.
5. Jobs uses `vueApiFetch("/jobs")`.
6. Companies uses `vueApiFetch("/companies")`.
7. Loading states exist.
8. Error states exist.
9. Placeholder API responses are handled safely.
10. Empty list states are handled safely.
11. Dashboard shows overview cards and next action links.
12. Jobs shows saved jobs section and total count.
13. Companies shows tracked companies section and total count.
14. No complex pages are migrated.
15. Existing Jinja templates are untouched.
16. Existing static JS files are untouched.
17. Existing `/ui/*` routes are unchanged.
18. Backend business logic is unchanged.
19. No LLM calls are added.
20. No data mutation is added.
21. `npm run build:vue` passes.
22. `pytest tests/test_vue_api_contracts.py` passes.
23. Any full-test failures are reported and identified as pre-existing or caused by this task.

---

## Forbidden Outcomes

Do not:

- migrate apply flow
- migrate applications
- migrate drafts
- migrate draft detail
- migrate onboarding
- migrate settings
- migrate verified facts
- migrate story bank
- migrate offer compass
- migrate analytics
- migrate thesis
- migrate workspace reset
- delete Jinja templates
- delete static JS
- call `/ui/*` from Vue
- scrape HTML
- add backend generation behavior
- call LLMs
- trigger job discovery
- trigger Gmail sync
- trigger JobSpy
- trigger career page scans
- create jobs
- create companies
- mutate database data
- expose secrets
- expose local filesystem paths
- add router guards
- add SPA catch-all route
- use Vuex
- replace Pinia
- add TypeScript
- add Docker
- add a new frontend testing framework

---

## Final Codex Response

Report:

1. files added
2. files modified
3. routes/pages converted
4. API endpoints used
5. commands run
6. `npm run build:vue` result
7. `pytest tests/test_vue_api_contracts.py` result
8. full `pytest` result
9. whether full-test failures are pre-existing or caused by this task
10. manual validation result
11. known issues

Do not continue to the next migration phase.
