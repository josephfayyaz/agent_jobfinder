# 004 Convert Static Pages

## Goal

Convert the simplest low-risk pages from Vue placeholders into real Vue pages:

```text
/about
/help
/setup-required
```

Use the existing Vue API contract endpoints:

```text
GET /api/vue/about
GET /api/vue/help
GET /api/vue/setup/state
```

Do not touch complex flows yet.

Keep all legacy `/ui/*` routes active.

---

## Current State

Completed specs:

```text
AGENT_SPECS/completed/codex/001_vue_infrastructure.md
AGENT_SPECS/completed/codex/002_vue_layout_router.md
AGENT_SPECS/completed/codex/003_vue_api_contracts.md
```

Current Vue pages are placeholders.

This task converts only:

```text
frontend/vue/src/pages/AboutPage.vue
frontend/vue/src/pages/HelpPage.vue
frontend/vue/src/pages/SetupRequiredPage.vue
```

Do not convert any other page.

---

## Hard Constraints

Do not modify backend business logic.

Do not modify LLM behavior.

Do not call LLMs.

Do not generate CV content.

Do not modify verified-fact validation.

Do not modify human approval workflow.

Do not modify Gmail sync.

Do not modify worker behavior.

Do not modify workspace reset/delete behavior.

Do not add FastAPI SPA catch-all route.

Do not change existing `/ui/*` routes.

Do not delete or rewrite legacy Jinja templates.

Do not delete or rewrite existing static JS.

Do not migrate these pages yet:

```text
Dashboard
Jobs
Companies
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

Modify only these Vue files unless tests require small additions:

```text
frontend/vue/src/pages/AboutPage.vue
frontend/vue/src/pages/HelpPage.vue
frontend/vue/src/pages/SetupRequiredPage.vue
```

You may modify these shared files only if needed for reusable non-business UI helpers:

```text
frontend/vue/src/api/contracts.js
frontend/vue/src/api/client.js
```

You may add one small reusable component if it avoids duplication:

```text
frontend/vue/src/components/ApiStatePanel.vue
```

Do not modify:

```text
frontend/templates/
frontend/static/
job_agent/
start_apply/
config/
temp_mac_test/
```

Exception:

- Do not modify backend files in this task unless an existing `/api/vue/about`, `/api/vue/help`, or `/api/vue/setup/state` endpoint is broken.
- If an endpoint is broken, fix only the contract endpoint implementation in `job_agent/routers/vue_api.py`.

---

## API Usage

The converted pages must use the existing frontend helper:

```js
vueApiFetch
```

from:

```text
frontend/vue/src/api/client.js
```

Use:

```text
vueApiFetch("/about")
vueApiFetch("/help")
vueApiFetch("/setup/state")
```

Do not call `/ui/*`.

Do not call raw `/api/*` routes.

Do not scrape HTML.

Do not import data from Jinja templates.

---

## Required Behavior

### `/about`

Convert `AboutPage.vue` from placeholder to real Vue page.

It must:

1. Fetch data from `GET /api/vue/about`.
2. Show loading state.
3. Show error state if request fails.
4. Show API-provided content if available.
5. Still render a useful fallback if the backend only returns placeholder data.
6. Mention that the app is local-first and privacy-first.
7. Not expose secrets or filesystem paths.

Required visible sections:

```text
About Local LLM Job Agent
Local-first workflow
Privacy and control
Vue migration status
```

The page must not depend on legacy Jinja.

---

### `/help`

Convert `HelpPage.vue` from placeholder to real Vue page.

It must:

1. Fetch data from `GET /api/vue/help`.
2. Show loading state.
3. Show error state if request fails.
4. Show API-provided content if available.
5. Still render a useful fallback if the backend only returns placeholder data.

Required visible sections:

```text
Help
Getting started
Job discovery
CV drafts
Verified facts
Troubleshooting
```

The page must not call any LLM or backend generation endpoint.

The page must not modify data.

---

### `/setup-required`

Convert `SetupRequiredPage.vue` from placeholder to real Vue page.

It must:

1. Fetch setup state from `GET /api/vue/setup/state`.
2. Show loading state.
3. Show error state if request fails.
4. Show whether setup is complete.
5. Show whether provider is configured.
6. Show whether setup is required.
7. Provide a Vue Router link to `/onboarding`.
8. Provide a Vue Router link to `/settings`.
9. Do not enforce routing guards yet.
10. Do not change onboarding business logic.

Required visible sections:

```text
Setup Required
Current setup state
Next actions
```

If setup is complete, show a clear message that setup appears complete and link to `/dashboard`.

If setup is incomplete, show links to `/onboarding` and `/settings`.

---

## Data Handling Rules

Because `/api/vue/about` and `/api/vue/help` may currently return placeholder data, pages must handle all of these safely:

```js
response.data
response.message
response.status
missing fields
empty objects
network errors
backend offline
```

Never assume a full real payload exists.

Use safe optional access.

No page should crash if the backend returns:

```json
{
  "ok": true,
  "contract_version": 1,
  "status": "placeholder",
  "message": "This API contract is reserved for future Vue migration.",
  "data": {}
}
```

---

## Recommended Implementation Pattern

Each converted page should use:

```js
import { onMounted, ref } from "vue";
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
    payload.value = await vueApiFetch("/about");
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Request failed";
  } finally {
    loading.value = false;
  }
});
```

For `/help`, use `/help`.

For `/setup-required`, use `/setup/state`.

---

## Optional Component

If useful, add:

```text
frontend/vue/src/components/ApiStatePanel.vue
```

Purpose:

Render loading/error/placeholder API status consistently.

Allowed props:

```text
loading: boolean
error: string
status: string optional
message: string optional
```

Do not make this component complex.

Do not add global state.

Do not add a UI library.

---

## Styling Requirements

Use Tailwind only.

Use existing style language from the Vue shell:

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

Add or update frontend-related tests only if the project already has a practical way to test Vue files.

Do not force a new test framework.

If no Vue test setup exists, do not add Vitest in this task.

Backend API tests from `003` should remain passing.

At minimum, run:

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

---

## Manual Validation

Run the backend using the project’s documented command.

Run Vue dev server:

```bash
npm run dev:vue
```

Open:

```text
http://localhost:5173/about
http://localhost:5173/help
http://localhost:5173/setup-required
```

Expected `/about`:

- page loads
- no console errors
- shows real Vue page, not placeholder card
- shows local-first/privacy-first app explanation
- handles placeholder API response safely

Expected `/help`:

- page loads
- no console errors
- shows help sections
- handles placeholder API response safely

Expected `/setup-required`:

- page loads
- no console errors
- shows setup state
- shows links to onboarding/settings
- if setup complete, shows dashboard link
- does not redirect automatically

Also verify:

```text
http://localhost:5173/dashboard
http://localhost:5173/jobs
http://localhost:5173/apply
```

Expected:

- these remain placeholder pages
- no other migration happened

Verify legacy routes still work if backend is running:

```text
http://localhost:8000/ui/about
http://localhost:8000/ui/help
```

If exact legacy route paths differ, verify the existing `/ui/*` frontend still works through the app navigation.

---

## Acceptance Criteria

This task is complete only if:

1. `AboutPage.vue` is converted from placeholder to real Vue page.
2. `HelpPage.vue` is converted from placeholder to real Vue page.
3. `SetupRequiredPage.vue` is converted from placeholder to real Vue page.
4. The pages use `vueApiFetch`.
5. The pages call only `/api/vue/about`, `/api/vue/help`, and `/api/vue/setup/state`.
6. Loading states exist.
7. Error states exist.
8. Placeholder API responses are handled safely.
9. `/setup-required` displays setup state fields.
10. `/setup-required` links to `/onboarding`, `/settings`, and conditionally `/dashboard`.
11. No complex pages are migrated.
12. Existing Jinja templates are untouched.
13. Existing static JS files are untouched.
14. Existing `/ui/*` routes are unchanged.
15. Backend business logic is unchanged.
16. `npm run build:vue` passes.
17. `pytest tests/test_vue_api_contracts.py` passes.
18. Any full-test failures are reported and identified as pre-existing or caused by this task.

---

## Forbidden Outcomes

Do not:

- migrate dashboard
- migrate jobs
- migrate companies
- migrate apply flow
- migrate drafts
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
