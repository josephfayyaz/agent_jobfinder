# 012 Convert Apply Readonly Shell

## Goal

Convert the Vue `/apply` page from a placeholder into a real read-only Vue shell.

This task must not implement scoring, questions, draft generation, LLM calls, or CV generation.

The page should only display the apply-flow structure as disabled/read-only future steps:

```text
Paste JD → Score → Questions → Draft
```

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
AGENT_SPECS/completed/claude/011_convert_onboarding_readonly_shell.md
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
/onboarding
```

This task converts only:

```text
frontend/vue/src/pages/ApplyPage.vue
```

Do not convert any other page.

---

## Hard Constraints

Do not modify backend business logic.

Do not call LLMs.

Do not generate CV content.

Do not score jobs.

Do not generate clarifying questions.

Do not generate drafts.

Do not create workflow tasks.

Do not enqueue worker jobs.

Do not mutate database state.

Do not save pasted job descriptions.

Do not call apply score endpoint.

Do not call apply questions endpoint.

Do not call apply draft endpoint.

Do not call draft endpoints.

Do not modify verified-fact validation.

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

Do not use Vuex.

Keep Pinia.

Do not use TypeScript.

Do not add Docker.

Do not switch package manager.

---

## Files To Modify

Modify only:

```text
frontend/vue/src/pages/ApplyPage.vue
```

You may add small shared Vue components if they reduce duplication:

```text
frontend/vue/src/components/ApiNotice.vue
frontend/vue/src/components/ReadonlyDetailCard.vue
frontend/vue/src/components/ApplyStepCard.vue
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
job_agent/
start_apply/
config/
temp_mac_test/
```

Backend exception:

- Do not modify backend files in this task.
- Do not wire apply endpoints.
- Do not alter `/api/vue/apply/*` contract behavior.

---

## API Usage

This task should not call apply/generative APIs.

Allowed API calls:

```text
none required
```

Optional safe API calls allowed only if useful for status display:

```text
GET /api/vue/setup/state
GET /api/vue/session
```

If used, call through:

```js
vueApiFetch
```

Do not call:

```text
POST /api/vue/apply/score
POST /api/vue/apply/questions
POST /api/vue/apply/draft
/ui/*
raw /api/*
LLM endpoints
draft endpoints
settings write/update endpoints
verified-facts mutation endpoints
workspace mutation endpoints
```

Do not scrape HTML.

Do not import data from Jinja templates.

---

## Required Behavior

### `/apply`

Convert `ApplyPage.vue` from placeholder to real Vue shell.

It must:

1. Render a full Vue page, not the old placeholder wrapper.
2. Show the apply workflow structure.
3. Show the four future steps:
   - Paste JD
   - Score
   - Questions
   - Draft
4. Show that every step is currently read-only/disabled in the Vue migration.
5. Show a read-only safety notice explaining that generation is still disabled in this Vue shell.
6. Provide safe navigation links only.
7. Not call any generative/mutating endpoint.
8. Not save any pasted text.
9. Not include active submit/generate buttons.

Required visible sections:

```text
Apply
Apply flow preview
Read-only safety
Future steps
Next actions
```

Allowed links:

```text
/jobs
/verified-facts
/drafts
/applications
/settings
```

Important:

- A disabled textarea may be shown as a preview only.
- Disabled future buttons may be shown for clarity.
- Disabled buttons must not have click handlers.
- Do not add active forms.
- Do not save user input.
- Do not call APIs on button clicks.
- Do not generate anything.

---

## Apply Flow Step Details

Render these four step cards:

### Step 1: Paste JD

Description:

```text
Future step for pasting a job description. Disabled until safe Vue apply migration is implemented.
```

Status:

```text
Disabled
```

### Step 2: Score

Description:

```text
Future step for matching the job against verified profile facts. Disabled; no scoring endpoint is called.
```

Status:

```text
Disabled
```

### Step 3: Questions

Description:

```text
Future step for clarifying missing information. Disabled; no question generation endpoint is called.
```

Status:

```text
Disabled
```

### Step 4: Draft

Description:

```text
Future step for creating a reviewable CV draft. Disabled; no CV generation endpoint is called.
```

Status:

```text
Disabled
```

Do not mark any step complete.

Do not infer readiness from backend state.

---

## Data Handling Rules

Because this is a read-only shell, no business data is required.

The page may show static explanatory content.

If optional setup/session calls are used, safely handle:

```text
response.data
response.status
response.message
missing fields
empty objects
network errors
backend offline
```

Use optional chaining and safe defaults.

Do not render secret-looking keys.

Do not render absolute local filesystem paths.

Do not render private candidate facts.

---

## Secret and Path Filtering

If rendering any object fields from optional API calls, filter out keys that contain or resemble:

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

---

## Recommended Implementation Pattern

Use:

```js
import { RouterLink } from "vue-router";
import AppPageHeader from "../components/AppPageHeader.vue";
```

Optional local constant:

```js
const steps = [
  {
    title: "Paste JD",
    status: "Disabled",
    description:
      "Future step for pasting a job description. Disabled until safe Vue apply migration is implemented."
  },
  {
    title: "Score",
    status: "Disabled",
    description:
      "Future step for matching the job against verified profile facts. Disabled; no scoring endpoint is called."
  },
  {
    title: "Questions",
    status: "Disabled",
    description:
      "Future step for clarifying missing information. Disabled; no question generation endpoint is called."
  },
  {
    title: "Draft",
    status: "Disabled",
    description:
      "Future step for creating a reviewable CV draft. Disabled; no CV generation endpoint is called."
  }
];
```

Do not add click handlers for disabled future actions.

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
emerald border/background for safe/no-generation confirmation
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

Run Vue dev server:

```bash
npm run dev:vue
```

Open:

```text
http://localhost:5173/apply
```

Expected `/apply`:

```text
- page loads
- no console errors
- not the old placeholder card
- shows apply flow preview
- shows Paste JD → Score → Questions → Draft
- shows read-only safety notice
- shows disabled future controls only
- does not submit anything
- does not call apply score/questions/draft endpoints
- does not call LLMs
- does not generate CV content
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
http://localhost:5173/onboarding
```

Expected:

```text
Previously converted pages remain real Vue pages.
```

Verify legacy `/ui/*` routes still work if backend is running.

---

## Acceptance Criteria

This task is complete only if:

1. `ApplyPage.vue` is converted from placeholder to real Vue shell.
2. Page shows apply flow preview.
3. Page shows Paste JD step.
4. Page shows Score step.
5. Page shows Questions step.
6. Page shows Draft step.
7. All steps are disabled/read-only.
8. Read-only safety notice exists.
9. No active submit/generate buttons are added.
10. No apply score/questions/draft endpoints are called.
11. No LLM calls are added.
12. No CV generation is added.
13. No user input is saved.
14. No database mutation is added.
15. Existing Jinja templates are untouched.
16. Existing static JS files are untouched.
17. Existing `/ui/*` routes are unchanged.
18. Backend business logic is unchanged.
19. `npm run build:vue` passes.
20. `pytest tests/test_vue_api_contracts.py` passes.
21. Any full-test failures are reported and identified as pre-existing or caused by this task.

---

## Forbidden Outcomes

Do not:

- call POST /api/vue/apply/score
- call POST /api/vue/apply/questions
- call POST /api/vue/apply/draft
- call LLMs
- generate CV content
- score jobs
- generate questions
- generate drafts
- save pasted job descriptions
- create workflow tasks
- enqueue worker jobs
- mutate database data
- add active forms
- add active generate buttons
- add active submit buttons
- call draft revise endpoint
- call draft polish endpoint
- call draft approve endpoint
- save verified facts
- infer facts
- invent candidate facts
- change setup gating
- expose secrets
- expose masked secrets
- expose absolute filesystem paths
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
4. API endpoints used, or state that none were used
5. commands run
6. `npm run build:vue` result
7. `pytest tests/test_vue_api_contracts.py` result
8. full `pytest` result
9. whether full-test failures are pre-existing or caused by this task
10. manual validation result
11. known issues

Do not continue to the next migration phase.
