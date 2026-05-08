# 008 Convert Verified Facts Readonly

## Goal

Convert the Vue `/verified-facts` page from a placeholder into a real read-only Vue page.

Use the existing Vue API contract endpoints:

```text
GET /api/vue/verified-facts
GET /api/vue/verified-facts/schema
```

This task must be read-only.

Do not add, edit, delete, validate, generate, infer, or invent facts.

Do not change verified-fact validation logic.

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
AGENT_SPECS/completed/claude/006_convert_applications_drafts_readonly.md
AGENT_SPECS/completed/claude/007_convert_career_tools_readonly.md
```

Already converted to real Vue pages:

```text
/about
/help
/setup-required
/dashboard
/jobs
/companies
/applications
/drafts
/drafts/:id
/story-bank
/offer-compass
/analytics
/thesis
```

This task converts only:

```text
frontend/vue/src/pages/VerifiedFactsPage.vue
```

Do not convert any other page.

---

## Hard Constraints

Do not modify backend business logic.

Do not modify verified-fact validation rules.

Do not add fact creation.

Do not add fact editing.

Do not add fact deletion.

Do not add fact approval.

Do not add fact promotion to memory.

Do not infer facts from other fields.

Do not invent candidate facts.

Do not call LLMs.

Do not generate CV content.

Do not modify LLM routing.

Do not modify CV generation.

Do not modify human approval workflow.

Do not modify onboarding business rules.

Do not modify settings/provider/keyring logic.

Do not modify Gmail sync.

Do not modify background worker behavior.

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
frontend/vue/src/pages/VerifiedFactsPage.vue
```

You may add small shared Vue components if they reduce duplication:

```text
frontend/vue/src/components/EmptyState.vue
frontend/vue/src/components/ApiNotice.vue
frontend/vue/src/components/ReadonlyList.vue
frontend/vue/src/components/ReadonlyDetailCard.vue
frontend/vue/src/components/SchemaFieldCard.vue
```

If any of these components already exist from previous tasks, reuse them instead of duplicating.

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

- Do not modify backend files unless `/api/vue/verified-facts` or `/api/vue/verified-facts/schema` is broken.
- If an endpoint is broken, fix only the contract endpoint implementation in `job_agent/routers/vue_api.py`.
- Do not wire real write behavior.
- Do not expose secrets, local paths, generated CV content, or private candidate facts not already safely returned by the contract endpoint.

---

## API Usage

The converted page must use:

```js
vueApiFetch
```

from:

```text
frontend/vue/src/api/client.js
```

Use only these calls:

```text
vueApiFetch("/verified-facts")
vueApiFetch("/verified-facts/schema")
```

Do not call:

```text
/ui/*
raw /api/*
LLM endpoints
apply endpoints
draft endpoints
onboarding write endpoints
settings endpoints
workspace mutation endpoints
verified-facts mutation endpoints
```

Do not scrape HTML.

Do not import data from Jinja templates.

---

## Required Behavior

### `/verified-facts`

Convert `VerifiedFactsPage.vue` from placeholder to real Vue page.

It must:

1. Fetch data from `GET /api/vue/verified-facts`.
2. Fetch schema metadata from `GET /api/vue/verified-facts/schema`.
3. Show loading state while one or both requests are pending.
4. Show error state if one or both requests fail.
5. Handle placeholder API responses safely.
6. Render verified facts list if `data.items` exists and is non-empty.
7. Render empty state if no verified facts exist.
8. Show total count if available.
9. Render schema/field metadata if available.
10. Clearly show contract/placeholder status when API is not wired to real data.
11. Show a read-only safety notice explaining that facts cannot be edited from this migrated page yet.
12. Provide safe navigation links only.

Required visible sections:

```text
Verified Facts
Fact traceability status
Approved fact records
Fact schema
Read-only safety
Next actions
```

Allowed links:

```text
/onboarding
/settings
/apply
/drafts
```

Important:

- Do not create facts.
- Do not edit facts.
- Do not delete facts.
- Do not validate facts in Vue.
- Do not infer facts.
- Do not invent facts.
- Do not call LLMs.
- Do not mutate data.
- Do not promote facts to profile memory.

---

## Data Handling Rules

These endpoints may currently return placeholder data.

The page must safely handle:

```text
facts_response.data
facts_response.data.items
facts_response.data.total
facts_response.status
facts_response.message
schema_response.data
schema_response.data.fields
schema_response.data.required
schema_response.status
schema_response.message
missing fields
empty objects
network errors
backend offline
```

No page should crash if `/api/vue/verified-facts` returns:

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

No page should crash if `/api/vue/verified-facts/schema` returns:

```json
{
  "ok": true,
  "contract_version": 1,
  "status": "placeholder",
  "message": "This API contract is reserved for future Vue migration.",
  "data": {}
}
```

Use optional chaining and safe defaults.

Do not assume fact item schemas.

For unknown fact fields, render only safe generic fields:

```text
id
type
category
label
value
source
status
confidence
created_at
updated_at
```

For schema fields, render only safe generic fields:

```text
name
type
required
description
allowed_values
```

If fields are missing, use fallback labels:

```text
Untitled fact
Unknown category
Source unavailable
Status unavailable
```

Do not invent missing values.

Do not render secret-looking keys.

Do not render absolute local filesystem paths.

Do not render private candidate facts unless the API explicitly returns safe read-only data.

---

## Secret and Sensitive-Key Filtering

Before rendering arbitrary object fields, filter out keys that contain or resemble:

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
path
file_path
absolute_path
home
root
```

This is frontend defensive filtering only.

Do not change backend security logic.

If a field key matches a blocked pattern, do not render the key or value.

---

## Recommended Implementation Pattern

Use:

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
const factsPayload = ref(null);
const schemaPayload = ref(null);

onMounted(async () => {
  try {
    const [facts, schema] = await Promise.all([
      vueApiFetch("/verified-facts"),
      vueApiFetch("/verified-facts/schema")
    ]);

    factsPayload.value = facts;
    schemaPayload.value = schema;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Request failed";
  } finally {
    loading.value = false;
  }
});
```

Use computed values for:

```text
facts
total
schema_fields
is_placeholder
facts_message
schema_message
```

---

## Optional Shared Components

You may add or reuse these components if useful.

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

### `SchemaFieldCard.vue`

Props:

```text
field: object
```

Purpose:

Display one schema field safely.

Keep all shared components simple.

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

Read-only safety warnings should be clearly visible but not alarming:

```text
amber border/background for read-only notice
emerald border/background for safe contract status
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
http://localhost:5173/verified-facts
```

Expected `/verified-facts`:

```text
- page loads
- no console errors
- not the old placeholder card
- shows fact traceability status
- shows approved fact records section
- shows fact schema section
- shows read-only safety notice
- shows empty state if no verified facts exist
- shows placeholder/API message when relevant
- does not show secret-looking keys
- does not show absolute local filesystem paths
- does not provide create/edit/delete controls
```

Also verify these routes remain unchanged or still work:

```text
http://localhost:5173/about
http://localhost:5173/help
http://localhost:5173/setup-required
http://localhost:5173/dashboard
http://localhost:5173/jobs
http://localhost:5173/companies
http://localhost:5173/applications
http://localhost:5173/drafts
http://localhost:5173/drafts/123
http://localhost:5173/story-bank
http://localhost:5173/offer-compass
http://localhost:5173/analytics
http://localhost:5173/thesis
http://localhost:5173/apply
http://localhost:5173/onboarding
http://localhost:5173/settings
http://localhost:5173/workspace-reset
```

Expected:

```text
Previously converted pages remain real Vue pages.
/apply, /onboarding, /settings, /workspace-reset remain placeholders.
```

Verify legacy `/ui/*` routes still work if backend is running.

---

## Acceptance Criteria

This task is complete only if:

1. `VerifiedFactsPage.vue` is converted from placeholder to real Vue page.
2. The page uses `vueApiFetch("/verified-facts")`.
3. The page uses `vueApiFetch("/verified-facts/schema")`.
4. Loading state exists.
5. Error state exists.
6. Placeholder API responses are handled safely.
7. Empty list state is handled safely.
8. Verified facts list section exists.
9. Schema section exists.
10. Read-only safety notice exists.
11. No create/edit/delete controls are added.
12. No fact validation logic is changed.
13. No facts are inferred or invented.
14. No LLM calls are added.
15. No database mutation is added.
16. Existing Jinja templates are untouched.
17. Existing static JS files are untouched.
18. Existing `/ui/*` routes are unchanged.
19. Backend business logic is unchanged.
20. `npm run build:vue` passes.
21. `pytest tests/test_vue_api_contracts.py` passes.
22. Any full-test failures are reported and identified as pre-existing or caused by this task.

---

## Forbidden Outcomes

Do not:

- add facts
- edit facts
- delete facts
- validate facts in Vue
- infer facts
- invent candidate facts
- promote facts to profile memory
- migrate apply flow
- migrate onboarding
- migrate settings
- migrate workspace reset
- call apply endpoints
- call draft revise endpoint
- call draft polish endpoint
- call draft approve endpoint
- generate CV content
- call LLMs
- trigger Gmail sync
- trigger worker tasks
- trigger JobSpy
- trigger career page scans
- delete Jinja templates
- delete static JS
- call `/ui/*` from Vue
- scrape HTML
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

## Final Codex/Claude Response

Report:

1. files added
2. files modified
3. route/page converted
4. API endpoints used
5. commands run
6. `npm run build:vue` result
7. `pytest tests/test_vue_api_contracts.py` result
8. full `pytest` result
9. whether full-test failures are pre-existing or caused by this task
10. manual validation result
11. known issues

Do not continue to the next migration phase.
