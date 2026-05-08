# 009 Convert Settings Readonly

## Goal

Convert the Vue `/settings` page from a placeholder into a real read-only Vue page.

Use the existing Vue API contract endpoint:

```text
GET /api/vue/settings
```

This task must be read-only.

Do not change provider settings.
Do not change keyring behavior.
Do not expose secrets.
Do not add API key editing.
Do not add model/provider switching.
Do not change backend settings logic.

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
AGENT_SPECS/completed/claude/008_convert_verified_facts_readonly.md
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
/verified-facts
```

This task converts only:

```text
frontend/vue/src/pages/SettingsPage.vue
```

Do not convert any other page.

---

## Hard Constraints

Do not modify backend business logic.

Do not modify settings/provider/keyring logic.

Do not add settings writes.

Do not add provider update actions.

Do not add API key editing.

Do not add model switching.

Do not expose secrets.

Do not expose masked secret values.

Do not expose local filesystem paths.

Do not modify LLM routing.

Do not call LLMs.

Do not generate CV content.

Do not modify CV generation.

Do not modify verified-fact validation.

Do not modify human approval workflow.

Do not modify onboarding business rules.

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
frontend/vue/src/pages/SettingsPage.vue
```

You may add small shared Vue components if they reduce duplication:

```text
frontend/vue/src/components/EmptyState.vue
frontend/vue/src/components/ApiNotice.vue
frontend/vue/src/components/ReadonlyDetailCard.vue
frontend/vue/src/components/SettingsStatusCard.vue
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

- Do not modify backend files unless `/api/vue/settings` is broken or exposes unsafe fields.
- If the endpoint is broken or unsafe, fix only the curated contract endpoint implementation in `job_agent/routers/vue_api.py`.
- Do not expose secrets.
- Do not expose masked secret values.
- Do not wire write/update behavior.

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

Use only this call:

```text
vueApiFetch("/settings")
```

Do not call:

```text
/ui/*
raw /api/*
settings write/update endpoints
provider update endpoints
keyring endpoints
LLM endpoints
apply endpoints
draft endpoints
workspace mutation endpoints
```

Do not scrape HTML.

Do not import data from Jinja templates.

---

## Required Behavior

### `/settings`

Convert `SettingsPage.vue` from placeholder to real Vue page.

It must:

1. Fetch data from `GET /api/vue/settings`.
2. Show loading state.
3. Show error state.
4. Handle placeholder API response safely.
5. Render provider/setup status if available.
6. Render empty/read-only state if no provider details exist.
7. Clearly show contract/placeholder status when API is not wired to real data.
8. Show a read-only safety notice explaining settings cannot be edited from this migrated page yet.
9. Show that secrets are not exposed.
10. Provide safe navigation links only.

Required visible sections:

```text
Settings
Provider status
Local inference
Security and secrets
Read-only safety
Next actions
```

Allowed links:

```text
/onboarding
/setup-required
/about
/help
```

Important:

- Do not create settings forms.
- Do not add API key input fields.
- Do not add provider selection controls.
- Do not add model switching controls.
- Do not add save buttons.
- Do not expose secrets.
- Do not expose masked secret values.
- Do not call LLMs.
- Do not mutate data.

---

## Data Handling Rules

`GET /api/vue/settings` may currently return placeholder data.

The page must safely handle:

```text
response.data
response.data.providers
response.data.provider
response.data.local_inference
response.data.secrets_exposed
response.data.setup
response.status
response.message
missing fields
empty objects
network errors
backend offline
```

No page should crash if `/api/vue/settings` returns:

```json
{
  "ok": true,
  "contract_version": 1,
  "status": "placeholder",
  "message": "This settings endpoint is curated to avoid exposing secrets.",
  "data": {
    "providers": [],
    "secrets_exposed": false
  }
}
```

Use optional chaining and safe defaults.

Do not assume provider item schemas.

For provider/status items, render only safe generic fields:

```text
name
label
provider
type
enabled
configured
available
status
local
description
```

If fields are missing, use fallback labels:

```text
Unnamed provider
Status unavailable
Configuration hidden
```

Do not invent missing values.

Do not render secret-looking keys.

Do not render absolute local filesystem paths.

Do not render environment variable values.

Do not render keyring values.

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
keyring
env
environment
path
file_path
absolute_path
home
root
```

This is frontend defensive filtering only.

Do not change backend security logic unless `/api/vue/settings` is clearly unsafe.

If a field key matches a blocked pattern, do not render the key or value.

Also block values that appear to be absolute local filesystem paths, for example values starting with:

```text
/
/Users/
~/ 
file:
```

Do not render masked secrets either.

Examples of values that must not be rendered:

```text
sk-****
****abcd
lmstudio-token
anthropic-key
openai-api-key
```

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
const payload = ref(null);

onMounted(async () => {
  try {
    payload.value = await vueApiFetch("/settings");
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Request failed";
  } finally {
    loading.value = false;
  }
});
```

Use computed values for:

```text
providers
secrets_exposed
is_placeholder
message
safe_status_fields
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

### `SettingsStatusCard.vue`

Props:

```text
title: string
value: string
description: string optional
```

Purpose:

Display safe read-only settings status.

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

Read-only/security warnings should be clearly visible but not alarming:

```text
amber border/background for read-only notice
emerald border/background for safe contract/security status
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
http://localhost:5173/settings
```

Expected `/settings`:

```text
- page loads
- no console errors
- not the old placeholder card
- shows provider status section
- shows local inference section
- shows security/secrets section
- shows read-only safety notice
- shows placeholder/API message when relevant
- does not show secret-looking keys
- does not show masked secret values
- does not show absolute local filesystem paths
- does not show API key inputs
- does not show provider save/update controls
- does not call write endpoints
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
http://localhost:5173/verified-facts
http://localhost:5173/apply
http://localhost:5173/onboarding
http://localhost:5173/workspace-reset
```

Expected:

```text
Previously converted pages remain real Vue pages.
/apply, /onboarding, /workspace-reset remain placeholders.
```

Verify legacy `/ui/*` routes still work if backend is running.

---

## Acceptance Criteria

This task is complete only if:

1. `SettingsPage.vue` is converted from placeholder to real Vue page.
2. The page uses `vueApiFetch("/settings")`.
3. Loading state exists.
4. Error state exists.
5. Placeholder API responses are handled safely.
6. Provider status section exists.
7. Local inference section exists.
8. Security and secrets section exists.
9. Read-only safety notice exists.
10. No settings forms are added.
11. No API key inputs are added.
12. No provider save/update controls are added.
13. No secrets or masked secrets are rendered.
14. No absolute local filesystem paths are rendered.
15. No settings/keyring/backend business logic is changed.
16. No LLM calls are added.
17. No database mutation is added.
18. Existing Jinja templates are untouched.
19. Existing static JS files are untouched.
20. Existing `/ui/*` routes are unchanged.
21. Backend business logic is unchanged.
22. `npm run build:vue` passes.
23. `pytest tests/test_vue_api_contracts.py` passes.
24. Any full-test failures are reported and identified as pre-existing or caused by this task.

---

## Forbidden Outcomes

Do not:

- add API key inputs
- edit API keys
- show API keys
- show masked API keys
- show tokens
- show secrets
- show keyring values
- show environment variable values
- show absolute filesystem paths
- add provider switching
- add model switching
- add save/update buttons
- mutate settings
- call settings write endpoints
- call LLMs
- migrate apply flow
- migrate onboarding
- migrate workspace reset
- call apply endpoints
- call draft revise endpoint
- call draft polish endpoint
- call draft approve endpoint
- generate CV content
- trigger Gmail sync
- trigger worker tasks
- trigger JobSpy
- trigger career page scans
- delete Jinja templates
- delete static JS
- call `/ui/*` from Vue
- scrape HTML
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
4. API endpoint used
5. commands run
6. `npm run build:vue` result
7. `pytest tests/test_vue_api_contracts.py` result
8. full `pytest` result
9. whether full-test failures are pre-existing or caused by this task
10. manual validation result
11. known issues

Do not continue to the next migration phase.
