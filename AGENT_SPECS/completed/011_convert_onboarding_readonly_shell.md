# 011 Convert Onboarding Readonly Shell

## Goal

Convert the Vue `/onboarding` page from a placeholder into a real read-only Vue shell.

Use the existing Vue API contract endpoints:

```text
GET /api/vue/onboarding/state
GET /api/vue/onboarding/steps
GET /api/vue/setup/state
```

This task must be read-only.

Do not save provider settings.
Do not save profile data.
Do not write verified facts.
Do not advance onboarding state.
Do not change setup gating.
Do not call LLMs.
Do not generate or infer profile/fact content.

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
AGENT_SPECS/completed/claude/010_convert_workspace_reset_readonly_preview.md
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
/workspace-reset
```

This task converts only:

```text
frontend/vue/src/pages/OnboardingPage.vue
```

Do not convert any other page.

---

## Hard Constraints

Do not modify backend business logic.

Do not modify onboarding business rules.

Do not modify setup gating logic.

Do not add onboarding writes.

Do not save provider selection.

Do not save profile data.

Do not save Q&A answers.

Do not save verified facts.

Do not upload files.

Do not parse PDFs/DOCX.

Do not promote anything to profile memory.

Do not call LLMs.

Do not generate candidate profile content.

Do not infer facts.

Do not invent facts.

Do not modify settings/provider/keyring logic.

Do not expose secrets.

Do not expose masked secrets.

Do not expose local filesystem paths.

Do not modify LLM routing.

Do not generate CV content.

Do not modify CV generation.

Do not modify verified-fact validation.

Do not modify human approval workflow.

Do not modify Gmail sync.

Do not modify background worker behavior.

Do not modify workspace reset/delete/backup behavior.

Do not add FastAPI SPA catch-all route.

Do not change existing `/ui/*` routes.

Do not delete or rewrite legacy Jinja templates.

Do not delete or rewrite existing static JS.

Do not migrate this page yet:

```text
Apply
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
frontend/vue/src/pages/OnboardingPage.vue
```

You may add small shared Vue components if they reduce duplication:

```text
frontend/vue/src/components/EmptyState.vue
frontend/vue/src/components/ApiNotice.vue
frontend/vue/src/components/ReadonlyDetailCard.vue
frontend/vue/src/components/OnboardingStepCard.vue
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

- Do not modify backend files unless `/api/vue/onboarding/state`, `/api/vue/onboarding/steps`, or `/api/vue/setup/state` is broken or unsafe.
- If an endpoint is broken or unsafe, fix only the curated contract endpoint implementation in `job_agent/routers/vue_api.py`.
- Do not wire write/update behavior.
- Do not expose secrets, local paths, uploaded file paths, or private candidate facts not already safely returned by the contract endpoint.

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
vueApiFetch("/onboarding/state")
vueApiFetch("/onboarding/steps")
vueApiFetch("/setup/state")
```

Do not call:

```text
/ui/*
raw /api/*
onboarding write/update endpoints
provider save endpoints
profile save endpoints
fact write endpoints
file upload endpoints
settings write/update endpoints
LLM endpoints
apply endpoints
draft endpoints
workspace mutation endpoints
```

Do not scrape HTML.

Do not import data from Jinja templates.

---

## Required Behavior

### `/onboarding`

Convert `OnboardingPage.vue` from placeholder to real Vue page.

It must:

1. Fetch onboarding state from `GET /api/vue/onboarding/state`.
2. Fetch onboarding steps from `GET /api/vue/onboarding/steps`.
3. Fetch setup state from `GET /api/vue/setup/state`.
4. Show loading state while requests are pending.
5. Show error state if one or more requests fail.
6. Handle placeholder API responses safely.
7. Render onboarding progress/state if available.
8. Render onboarding step list if `data.steps` or `data.items` exists and is non-empty.
9. Render fallback 7-step onboarding list if no steps are returned.
10. Render setup readiness fields from setup state.
11. Clearly show contract/placeholder status when API is not wired to real data.
12. Show a read-only safety notice explaining that this Vue page does not save setup/profile/facts yet.
13. Provide safe navigation links only.

Required visible sections:

```text
Onboarding
Setup readiness
Onboarding steps
Read-only safety
Next actions
```

Allowed links:

```text
/setup-required
/settings
/verified-facts
/dashboard
```

Important:

- Do not add working form fields.
- Do not add save buttons.
- Do not add provider selection controls.
- Do not add file upload controls.
- Do not add answer submission controls.
- Do not mutate data.
- Do not change setup gating.
- Do not redirect automatically.
- Display only safe read-only information.

---

## Fallback Step List

If `/api/vue/onboarding/steps` returns no usable steps, render this fallback list:

```text
1. Provider
2. Profile
3. Fact Sheet
4. Q&A
5. Review
6. Search
7. Done
```

These are display-only.

Do not let users mark steps complete.

Do not write progress.

---

## Data Handling Rules

These endpoints may currently return placeholder data.

The page must safely handle:

```text
onboarding_state_response.data
onboarding_state_response.data.steps
onboarding_state_response.data.current_step
onboarding_state_response.data.completed_steps
onboarding_state_response.data.progress
onboarding_state_response.status
onboarding_state_response.message

onboarding_steps_response.data
onboarding_steps_response.data.steps
onboarding_steps_response.data.items
onboarding_steps_response.status
onboarding_steps_response.message

setup_state_response.data
setup_state_response.data.loaded
setup_state_response.data.setup_complete
setup_state_response.data.provider_configured
setup_state_response.data.requires_setup
setup_state_response.status
setup_state_response.message

missing fields
empty objects
network errors
backend offline
```

No page should crash if endpoints return:

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

Do not assume step item schemas.

For unknown step fields, render only safe generic fields:

```text
id
key
name
label
title
description
status
complete
completed
order
```

If fields are missing, use fallback labels:

```text
Untitled step
Status unavailable
```

Do not invent missing values beyond the explicit fallback step list.

Do not render secret-looking keys.

Do not render absolute local filesystem paths.

Do not render private candidate facts unless the API explicitly returns safe read-only data.

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
upload
uploaded_file
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
const onboardingStatePayload = ref(null);
const onboardingStepsPayload = ref(null);
const setupStatePayload = ref(null);

onMounted(async () => {
  try {
    const [onboardingState, onboardingSteps, setupState] = await Promise.all([
      vueApiFetch("/onboarding/state"),
      vueApiFetch("/onboarding/steps"),
      vueApiFetch("/setup/state")
    ]);

    onboardingStatePayload.value = onboardingState;
    onboardingStepsPayload.value = onboardingSteps;
    setupStatePayload.value = setupState;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Request failed";
  } finally {
    loading.value = false;
  }
});
```

Use computed values for:

```text
setup_state
onboarding_state
steps
current_step
completed_count
progress_label
is_placeholder
status_messages
safe_step_fields
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

Read-only safety warnings should be clearly visible:

```text
amber border/background for read-only warning
emerald border/background for safe setup/status indicators
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
http://localhost:5173/onboarding
```

Expected `/onboarding`:

```text
- page loads
- no console errors
- not the old placeholder card
- shows setup readiness section
- shows onboarding steps section
- shows fallback 7-step list if API returns no steps
- shows read-only safety notice
- shows placeholder/API message when relevant
- does not show secret-looking keys
- does not show absolute local filesystem paths
- does not show provider save controls
- does not show file upload controls
- does not show answer submission controls
- does not redirect automatically
- does not mutate setup/onboarding state
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
http://localhost:5173/workspace-reset
http://localhost:5173/apply
```

Expected:

```text
Previously converted pages remain real Vue pages.
/apply remains placeholder.
```

Verify legacy `/ui/*` routes still work if backend is running.

---

## Acceptance Criteria

This task is complete only if:

1. `OnboardingPage.vue` is converted from placeholder to real Vue page.
2. The page uses `vueApiFetch("/onboarding/state")`.
3. The page uses `vueApiFetch("/onboarding/steps")`.
4. The page uses `vueApiFetch("/setup/state")`.
5. Loading state exists.
6. Error state exists.
7. Placeholder API responses are handled safely.
8. Setup readiness section exists.
9. Onboarding steps section exists.
10. Fallback 7-step list exists when API returns no steps.
11. Read-only safety notice exists.
12. No provider save controls are added.
13. No profile/fact write controls are added.
14. No file upload controls are added.
15. No answer submission controls are added.
16. No setup/onboarding state mutation is added.
17. No setup gating logic is changed.
18. No automatic redirect is added.
19. No secrets or masked secrets are rendered.
20. No absolute local filesystem paths are rendered.
21. No backend onboarding/settings/business logic is changed.
22. No LLM calls are added.
23. No database mutation is added.
24. Existing Jinja templates are untouched.
25. Existing static JS files are untouched.
26. Existing `/ui/*` routes are unchanged.
27. `npm run build:vue` passes.
28. `pytest tests/test_vue_api_contracts.py` passes.
29. Any full-test failures are reported and identified as pre-existing or caused by this task.

---

## Forbidden Outcomes

Do not:

- save provider config
- save profile data
- save Q&A answers
- save verified facts
- upload files
- parse PDFs/DOCX
- promote facts to memory
- infer candidate facts
- invent candidate facts
- change setup gating
- redirect automatically based on setup state
- add provider selection controls
- add file upload controls
- add answer submission controls
- expose secrets
- expose masked secrets
- expose absolute filesystem paths
- mutate settings
- call LLMs
- migrate apply flow
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
