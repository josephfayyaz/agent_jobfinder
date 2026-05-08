# 006 Convert Applications Drafts Readonly

## Goal

Convert the next read-only Vue pages from placeholders into real Vue pages:

```text
/applications
/drafts
/drafts/:id
```

Use the existing Vue API contract endpoints:

```text
GET /api/vue/applications
GET /api/vue/drafts
GET /api/vue/drafts/{draft_id}
```

This task must be read-only.

Do not implement revise, polish, approve, apply flow, or CV generation yet.

Keep all legacy `/ui/*` routes active.

---

## Current State

Completed specs:

```text
AGENT_SPECS/completed/codex/001_vue_infrastructure.md
AGENT_SPECS/completed/codex/002_vue_layout_router.md
AGENT_SPECS/completed/codex/003_vue_api_contracts.md
AGENT_SPECS/completed/codex/004_convert_static_pages.md
AGENT_SPECS/completed/codex/005_convert_dashboard_jobs_companies.md
```

Already converted to real Vue pages:

```text
/about
/help
/setup-required
/dashboard
/jobs
/companies
```

This task converts only:

```text
frontend/vue/src/pages/ApplicationsPage.vue
frontend/vue/src/pages/DraftsPage.vue
frontend/vue/src/pages/DraftDetailPage.vue
```

Do not convert any other page.

---

## Hard Constraints

Do not modify backend business logic.

Do not modify LLM routing.

Do not call LLMs.

Do not generate CV content.

Do not revise CV drafts.

Do not polish CV drafts.

Do not approve CV drafts.

Do not submit applications.

Do not modify apply flow.

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
frontend/vue/src/pages/ApplicationsPage.vue
frontend/vue/src/pages/DraftsPage.vue
frontend/vue/src/pages/DraftDetailPage.vue
```

You may add small shared Vue components if they reduce duplication:

```text
frontend/vue/src/components/EmptyState.vue
frontend/vue/src/components/ApiNotice.vue
frontend/vue/src/components/ReadonlyList.vue
frontend/vue/src/components/ReadonlyDetailCard.vue
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
- Do not wire real business services unless they are already safe, read-only, and do not expose secrets, local paths, or generated CV content.

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
vueApiFetch("/applications")
vueApiFetch("/drafts")
vueApiFetch(`/drafts/${draftId}`)
```

Do not call:

```text
/ui/*
raw /api/*
LLM endpoints
apply endpoints
draft revise endpoints
draft polish endpoints
draft approve endpoints
settings endpoints
verified-facts endpoints
workspace mutation endpoints
```

Do not scrape HTML.

Do not import data from Jinja templates.

---

## Required Behavior

### `/applications`

Convert `ApplicationsPage.vue` from placeholder to real Vue page.

It must:

1. Fetch data from `GET /api/vue/applications`.
2. Show loading state.
3. Show error state.
4. Handle placeholder API response safely.
5. Render application list if `data.items` exists and is non-empty.
6. Render empty state if no applications exist.
7. Show total count if available.
8. Clearly show contract/placeholder status when API is not wired to real data.
9. Provide safe navigation links only.

Required visible sections:

```text
Applications
Application tracking status
Tracked applications
Next actions
```

Allowed links:

```text
/jobs
/drafts
/apply
```

Important:

- Links are allowed.
- Do not submit applications.
- Do not trigger automation.
- Do not mutate application data.

---

### `/drafts`

Convert `DraftsPage.vue` from placeholder to real Vue page.

It must:

1. Fetch data from `GET /api/vue/drafts`.
2. Show loading state.
3. Show error state.
4. Handle placeholder API response safely.
5. Render draft list if `data.items` exists and is non-empty.
6. Render empty state if no drafts exist.
7. Show total count if available.
8. Clearly show contract/placeholder status when API is not wired to real data.
9. Provide safe navigation links only.

Required visible sections:

```text
Drafts
Draft review status
Saved drafts
Next actions
```

Allowed links:

```text
/applications
/apply
/verified-facts
```

Important:

- Do not call revise/polish/approve endpoints.
- Do not generate draft content.
- Do not mutate draft data.
- If a draft item has an `id`, link to `/drafts/{id}`.

---

### `/drafts/:id`

Convert `DraftDetailPage.vue` from placeholder to real Vue page.

It must:

1. Read `id` from Vue route params.
2. Fetch data from `GET /api/vue/drafts/{draft_id}`.
3. Show loading state.
4. Show error state.
5. Handle placeholder API response safely.
6. Render safe draft metadata/detail if available.
7. Show the route draft ID visibly.
8. Clearly show contract/placeholder status when API is not wired to real data.
9. Show disabled/read-only action buttons for future revise/polish/approve actions.

Required visible sections:

```text
Draft Detail
Draft metadata
Read-only review
Future actions
```

Future action buttons must be disabled and must not call endpoints:

```text
Revise draft
Polish draft
Approve draft
```

Important:

- Do not call PATCH `/api/vue/drafts/{draft_id}`.
- Do not call POST `/api/vue/drafts/{draft_id}/revise`.
- Do not call POST `/api/vue/drafts/{draft_id}/polish`.
- Do not call POST `/api/vue/drafts/{draft_id}/approve`.
- Do not generate or modify CV text.
- Do not approve anything.

---

## Data Handling Rules

These endpoints may currently return placeholder data.

Pages must safely handle:

```text
response.data
response.data.items
response.data.total
response.data.id
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

No detail page should crash if backend returns:

```json
{
  "ok": true,
  "contract_version": 1,
  "status": "placeholder",
  "message": "This detail endpoint is ready for Vue migration but not wired to real data yet.",
  "data": {
    "id": "requested-id"
  }
}
```

Use optional chaining and safe defaults.

Do not assume item schemas.

For unknown item fields, render only safe generic fields:

Applications:

```text
id
title
role
company
status
location
source
created_at
updated_at
```

Drafts:

```text
id
title
role
company
status
created_at
updated_at
```

Draft Detail:

```text
id
title
role
company
status
created_at
updated_at
notes
summary
```

If fields are missing, use fallback labels:

```text
Untitled application
Untitled draft
Unknown company
Status unavailable
```

Do not invent missing values.

Do not render any field that looks like a secret.

Do not render absolute local filesystem paths.

---

## Recommended Implementation Pattern

Each page should use:

```js
import { computed, onMounted, ref } from "vue";
import { RouterLink, useRoute } from "vue-router";
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
    payload.value = await vueApiFetch("/drafts");
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Request failed";
  } finally {
    loading.value = false;
  }
});
```

For draft detail:

```js
const route = useRoute();
const draftId = computed(() => String(route.params.id || ""));

onMounted(async () => {
  try {
    payload.value = await vueApiFetch(`/drafts/${draftId.value}`);
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
detail
is_placeholder
message
```

---

## Optional Shared Components

You may add these components if useful.

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

### `ReadonlyList.vue`

Purpose:

Reusable list panel for generic read-only items.

Keep it simple.

### `ReadonlyDetailCard.vue`

Purpose:

Reusable metadata/detail card for generic read-only records.

Keep it simple.

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

Read-only/future action buttons should appear disabled:

```text
opacity-50
cursor-not-allowed
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
http://localhost:5173/applications
http://localhost:5173/drafts
http://localhost:5173/drafts/123
```

Expected `/applications`:

```text
- page loads
- no console errors
- not the old placeholder card
- shows application tracking status
- shows tracked applications section
- shows empty state if no applications exist
- shows placeholder/API message when relevant
```

Expected `/drafts`:

```text
- page loads
- no console errors
- not the old placeholder card
- shows draft review status
- shows saved drafts section
- shows empty state if no drafts exist
- shows placeholder/API message when relevant
```

Expected `/drafts/123`:

```text
- page loads
- no console errors
- not the old placeholder card
- shows draft ID 123
- shows read-only draft detail/metadata
- shows disabled future action buttons
- does not call revise/polish/approve endpoints
```

Also verify these routes remain unchanged or still work:

```text
http://localhost:5173/about
http://localhost:5173/help
http://localhost:5173/setup-required
http://localhost:5173/dashboard
http://localhost:5173/jobs
http://localhost:5173/companies
http://localhost:5173/apply
http://localhost:5173/onboarding
http://localhost:5173/settings
http://localhost:5173/verified-facts
```

Expected:

```text
/about, /help, /setup-required, /dashboard, /jobs, /companies remain real Vue pages
/apply, /onboarding, /settings, /verified-facts remain placeholders
```

Verify legacy `/ui/*` routes still work if backend is running.

---

## Acceptance Criteria

This task is complete only if:

1. `ApplicationsPage.vue` is converted from placeholder to real Vue page.
2. `DraftsPage.vue` is converted from placeholder to real Vue page.
3. `DraftDetailPage.vue` is converted from placeholder to real Vue page.
4. Applications uses `vueApiFetch("/applications")`.
5. Drafts uses `vueApiFetch("/drafts")`.
6. Draft detail uses `vueApiFetch("/drafts/{draft_id}")`.
7. Loading states exist.
8. Error states exist.
9. Placeholder API responses are handled safely.
10. Empty list states are handled safely.
11. Draft detail shows the route draft ID.
12. Draft detail shows disabled future action buttons for revise, polish, and approve.
13. No revise/polish/approve API calls are made.
14. No apply flow is migrated.
15. No CV generation is added.
16. No LLM calls are added.
17. No database mutation is added.
18. No complex pages are migrated.
19. Existing Jinja templates are untouched.
20. Existing static JS files are untouched.
21. Existing `/ui/*` routes are unchanged.
22. Backend business logic is unchanged.
23. `npm run build:vue` passes.
24. `pytest tests/test_vue_api_contracts.py` passes.
25. Any full-test failures are reported and identified as pre-existing or caused by this task.

---

## Forbidden Outcomes

Do not:

- migrate apply flow
- call apply endpoints
- call draft revise endpoint
- call draft polish endpoint
- call draft approve endpoint
- approve a draft
- generate CV content
- mutate draft data
- mutate application data
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
- trigger Gmail sync
- trigger worker tasks
- create applications
- create drafts
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
