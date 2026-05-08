# 010 Convert Workspace Reset Readonly Preview

## Goal

Convert the Vue `/workspace-reset` page from a placeholder into a real read-only preview Vue page.

Use the existing Vue API contract endpoints:

```text
GET /api/vue/workspace/status
POST /api/vue/workspace/reset-preview
```

This task must be safe and non-destructive.

Do not reset workspace data.
Do not delete workspace data.
Do not create backup files.
Do not expose absolute local filesystem paths.
Do not add destructive controls.

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
AGENT_SPECS/completed/claude/009_convert_settings_readonly.md
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
/settings
```

This task converts only:

```text
frontend/vue/src/pages/WorkspaceResetPage.vue
```

Do not convert any other page.

---

## Hard Constraints

Do not modify backend business logic.

Do not reset workspace state.

Do not delete workspace files.

Do not create backup files.

Do not call backup creation code.

Do not expose absolute local filesystem paths.

Do not expose local app-data home paths.

Do not expose secret-like values.

Do not add real reset buttons.

Do not add real delete buttons.

Do not add real backup buttons.

Do not call destructive endpoints.

Do not modify settings/provider/keyring logic.

Do not modify LLM routing.

Do not call LLMs.

Do not generate CV content.

Do not modify verified-fact validation.

Do not modify human approval workflow.

Do not modify onboarding business rules.

Do not modify Gmail sync.

Do not modify background worker behavior.

Do not add FastAPI SPA catch-all route.

Do not change existing `/ui/*` routes.

Do not delete or rewrite legacy Jinja templates.

Do not delete or rewrite existing static JS.

Do not migrate these pages yet:

```text
Apply
Onboarding
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
frontend/vue/src/pages/WorkspaceResetPage.vue
```

You may add small shared Vue components if they reduce duplication:

```text
frontend/vue/src/components/EmptyState.vue
frontend/vue/src/components/ApiNotice.vue
frontend/vue/src/components/ReadonlyDetailCard.vue
frontend/vue/src/components/WorkspaceStatusCard.vue
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

- Do not modify backend files unless `/api/vue/workspace/status` or `/api/vue/workspace/reset-preview` is broken or unsafe.
- If an endpoint is broken or unsafe, fix only the curated contract endpoint implementation in `job_agent/routers/vue_api.py`.
- Do not wire real reset/delete/backup behavior.
- Do not expose local paths.

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
vueApiFetch("/workspace/status")
vueApiFetch("/workspace/reset-preview", {
  method: "POST",
  body: JSON.stringify({
    include_generated_files: false,
    include_cached_results: false
  })
})
```

Do not call:

```text
/ui/*
raw /api/*
workspace reset/delete endpoints
workspace backup endpoint
settings endpoints
LLM endpoints
apply endpoints
draft endpoints
```

Do not scrape HTML.

Do not import data from Jinja templates.

---

## Required Behavior

### `/workspace-reset`

Convert `WorkspaceResetPage.vue` from placeholder to real Vue page.

It must:

1. Fetch workspace status from `GET /api/vue/workspace/status`.
2. Fetch read-only reset preview from `POST /api/vue/workspace/reset-preview`.
3. Show loading state while one or both requests are pending.
4. Show error state if one or both requests fail.
5. Handle placeholder API responses safely.
6. Render safe workspace status fields if available.
7. Render reset preview result if available.
8. Clearly show that no destructive action was performed.
9. Clearly show contract/placeholder status when API is not wired to real data.
10. Show a read-only safety notice explaining that reset/delete/backup actions are not available from this migrated page yet.
11. Provide safe navigation links only.

Required visible sections:

```text
Workspace Reset
Workspace status
Reset preview
Read-only safety
Next actions
```

Allowed links:

```text
/settings
/help
/about
/dashboard
```

Important:

- Do not add real reset controls.
- Do not add real delete controls.
- Do not add real backup controls.
- Do not call `/api/vue/workspace/backup`.
- Do not call any legacy reset/delete route.
- Do not mutate data.
- Do not expose paths.

---

## Data Handling Rules

These endpoints may currently return placeholder data.

The page must safely handle:

```text
status_response.data
status_response.data.available
status_response.data.paths_exposed
status_response.status
status_response.message
preview_response.data
preview_response.data.destructive_action_performed
preview_response.data.would_affect
preview_response.status
preview_response.message
missing fields
empty objects
network errors
backend offline
```

No page should crash if `/api/vue/workspace/status` returns:

```json
{
  "ok": true,
  "contract_version": 1,
  "status": "placeholder",
  "message": "This workspace status endpoint avoids exposing local filesystem paths.",
  "data": {
    "available": true,
    "paths_exposed": false
  }
}
```

No page should crash if `/api/vue/workspace/reset-preview` returns:

```json
{
  "ok": true,
  "contract_version": 1,
  "status": "placeholder",
  "message": "This reset preview is read-only and does not delete or reset anything.",
  "data": {
    "destructive_action_performed": false,
    "would_affect": []
  }
}
```

Use optional chaining and safe defaults.

For workspace status fields, render only safe generic fields:

```text
available
paths_exposed
backup_available
reset_available
delete_available
generated_count
cache_count
results_count
status
```

For reset preview fields, render only safe generic fields:

```text
destructive_action_performed
would_affect
include_generated_files
include_cached_results
status
```

If fields are missing, use fallback labels:

```text
Status unavailable
No affected items reported
Preview unavailable
```

Do not invent missing values.

Do not render secret-looking keys.

Do not render absolute local filesystem paths.

---

## Secret and Path Filtering

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
directory
dir
```

This is frontend defensive filtering only.

If a field key matches a blocked pattern, do not render the key or value.

Also block string values that appear to be absolute local filesystem paths, for example values starting with:

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
/Users/name/project
~/Library/Application Support/...
file:///...
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
const statusPayload = ref(null);
const previewPayload = ref(null);

onMounted(async () => {
  try {
    const [status, preview] = await Promise.all([
      vueApiFetch("/workspace/status"),
      vueApiFetch("/workspace/reset-preview", {
        method: "POST",
        body: JSON.stringify({
          include_generated_files: false,
          include_cached_results: false
        })
      })
    ]);

    statusPayload.value = status;
    previewPayload.value = preview;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Request failed";
  } finally {
    loading.value = false;
  }
});
```

Use computed values for:

```text
workspace_status
reset_preview
destructive_action_performed
would_affect
is_placeholder
status_message
preview_message
safe_status_fields
safe_preview_fields
```

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

Read-only/destructive safety warnings should be clearly visible:

```text
amber border/background for read-only warning
emerald border/background for safe preview confirmation
red must not be used unless showing an error state
```

Disabled future controls, if shown, must be clearly disabled:

```text
opacity-50
cursor-not-allowed
disabled
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
http://localhost:5173/workspace-reset
```

Expected `/workspace-reset`:

```text
- page loads
- no console errors
- not the old placeholder card
- shows workspace status section
- shows reset preview section
- shows read-only safety notice
- shows that destructive_action_performed is false
- shows placeholder/API message when relevant
- does not show secret-looking keys
- does not show absolute local filesystem paths
- does not show active reset/delete/backup controls
- does not call backup endpoint
- does not call destructive endpoints
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
http://localhost:5173/settings
http://localhost:5173/apply
http://localhost:5173/onboarding
```

Expected:

```text
Previously converted pages remain real Vue pages.
/apply and /onboarding remain placeholders.
```

Verify legacy `/ui/*` routes still work if backend is running.

---

## Acceptance Criteria

This task is complete only if:

1. `WorkspaceResetPage.vue` is converted from placeholder to real Vue page.
2. The page uses `vueApiFetch("/workspace/status")`.
3. The page uses `vueApiFetch("/workspace/reset-preview", { method: "POST", ... })`.
4. Loading state exists.
5. Error state exists.
6. Placeholder API responses are handled safely.
7. Workspace status section exists.
8. Reset preview section exists.
9. Read-only safety notice exists.
10. Page shows that no destructive action was performed.
11. No active reset button is added.
12. No active delete button is added.
13. No active backup button is added.
14. `/api/vue/workspace/backup` is not called.
15. No destructive endpoint is called.
16. No secrets or masked secrets are rendered.
17. No absolute local filesystem paths are rendered.
18. No backend workspace reset/delete/backup logic is changed.
19. No LLM calls are added.
20. No database/file mutation is added.
21. Existing Jinja templates are untouched.
22. Existing static JS files are untouched.
23. Existing `/ui/*` routes are unchanged.
24. Backend business logic is unchanged.
25. `npm run build:vue` passes.
26. `pytest tests/test_vue_api_contracts.py` passes.
27. Any full-test failures are reported and identified as pre-existing or caused by this task.

---

## Forbidden Outcomes

Do not:

- reset workspace data
- delete workspace data
- create backup files
- call backup endpoint
- call destructive endpoints
- show active reset button
- show active delete button
- show active backup button
- expose secrets
- expose masked secrets
- expose absolute filesystem paths
- mutate settings
- call LLMs
- migrate apply flow
- migrate onboarding
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
4. API endpoints used
5. commands run
6. `npm run build:vue` result
7. `pytest tests/test_vue_api_contracts.py` result
8. full `pytest` result
9. whether full-test failures are pre-existing or caused by this task
10. manual validation result
11. known issues

Do not continue to the next migration phase.
