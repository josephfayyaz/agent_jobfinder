# 027 Vue Context Detail Routes

## Goal

Add low-risk, read-only Vue detail/context routes for:

```text
/app/jobs/:id
/app/applications/:id
/app/companies/:id
```

Use existing Vue API contract endpoints where available:

```text
GET /api/vue/jobs/{job_id}
GET /api/vue/applications/{application_id}
GET /api/vue/companies/{company_id}
```

Then improve related navigation between draft, job, application, and company contexts where safe.

This is a read-only task.

Do not add mutations.

Do not add queue-state changes.

Do not add discovery actions.

Do not call LLMs.

Do not remove legacy `/ui/*`.

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
AGENT_SPECS/completed/codex/014_vue_navigation_base_cleanup.md
AGENT_SPECS/completed/codex/015_vue_migration_final_audit.md
AGENT_SPECS/completed/codex/016_legacy_surface_hardening.md
AGENT_SPECS/completed/codex/017_settings_current_hardening.md
AGENT_SPECS/completed/codex/018_legacy_ui_settings_surface_hardening.md
AGENT_SPECS/completed/codex/019_settings_public_json_contract_tightening.md
AGENT_SPECS/completed/claude/020_onboarding_settings_copy_consistency.md
AGENT_SPECS/completed/claude/021_fix_pre_existing_test_failures.md
AGENT_SPECS/completed/codex/022_apply_flow_vue_migration.md
AGENT_SPECS/completed/codex/023_vue_apply_setup_required_ux.md
AGENT_SPECS/completed/codex/024_vue_draft_actions_migration.md
AGENT_SPECS/completed/codex/025_vue_draft_detail_metadata_enrichment.md
AGENT_SPECS/completed/codex/026_vue_draft_related_navigation.md
```

Current expected behavior before this task:

```text
/app/jobs exists as list page
/app/applications exists as list page
/app/companies exists as list page
/app/drafts/{id} has related navigation to list routes
No job/application/company detail Vue routes exist yet
full pytest is green
```

---

## Scope

This spec contains two small read-only tasks.

### Task A: Jobs + Applications detail routes

Add:

```text
/app/jobs/:id
/app/applications/:id
```

Use:

```text
GET /api/vue/jobs/{job_id}
GET /api/vue/applications/{application_id}
```

### Task B: Companies detail route + cross-links

Add:

```text
/app/companies/:id
```

Use:

```text
GET /api/vue/companies/{company_id}
```

Improve safe related navigation:

```text
Draft detail -> job detail if job id exists
Draft detail -> application detail if application id exists
Job detail -> companies list/detail if safe company id exists
Application detail -> job detail if job id exists
Application detail -> drafts list/detail if draft id exists
Company detail -> jobs list
```

Only add direct detail links where IDs are already safely available.

Do not invent IDs.

Do not widen backend payloads unless necessary and safe.

---

## Hard Constraints

Do not add mutation behavior.

Do not add queue-state changes.

Do not add job discovery actions.

Do not add enrich actions.

Do not add apply generation.

Do not add draft generation.

Do not approve drafts.

Do not reject drafts.

Do not generate cover letters.

Do not call LLMs.

Do not send emails.

Do not submit applications.

Do not mutate verified facts.

Do not remove `/ui/jobs`.

Do not remove `/ui/applications` if present.

Do not remove `/ui/companies`.

Do not remove `/ui/drafts`.

Do not remove any `/ui/*` routes.

Do not remove Jinja templates.

Do not remove legacy static JavaScript.

Do not remove HTMX.

Do not remove Alpine.

Do not remove `/api/*` routes.

Do not remove `/api/vue/*` routes.

Do not change Vue Router base.

Do not change Vite base.

Do not change `/app` SPA bridge strategy.

Do not expose secrets.

Do not expose local filesystem paths.

Do not expose provider URLs, model names, client IDs, keyring values, or environment values.

Do not use Vuex.

Keep Pinia.

Do not add TypeScript.

Do not add Docker.

---

## Required Investigation Before Editing

Inspect:

```text
frontend/vue/src/router/index.js
frontend/vue/src/pages/JobsPage.vue
frontend/vue/src/pages/ApplicationsPage.vue
frontend/vue/src/pages/CompaniesPage.vue
frontend/vue/src/pages/DraftDetailPage.vue
job_agent/routers/vue_api.py
tests/test_vue_api_contracts.py
tests/test_vue_draft_metadata.py
tests/test_vue_spa_serving.py
```

Search:

```bash
rg -n "jobs/:|applications/:|companies/:|JobDetail|ApplicationDetail|CompanyDetail|jobs/\{job_id\}|applications/\{application_id\}|companies/\{company_id\}" frontend/vue job_agent tests
rg -n "job_id|application_id|company_id|RouterLink|/jobs|/applications|/companies" frontend/vue/src/pages job_agent/routers/vue_api.py tests
```

Run baseline:

```bash
pytest tests/test_vue_api_contracts.py tests/test_vue_spa_serving.py tests/test_vue_draft_metadata.py -v
pytest
```

If baseline is not green, stop and report.

---

## Files To Modify

Likely add:

```text
frontend/vue/src/pages/JobDetailPage.vue
frontend/vue/src/pages/ApplicationDetailPage.vue
frontend/vue/src/pages/CompanyDetailPage.vue
tests/test_vue_context_detail_routes.py
```

Likely modify:

```text
frontend/vue/src/router/index.js
frontend/vue/src/pages/JobsPage.vue
frontend/vue/src/pages/ApplicationsPage.vue
frontend/vue/src/pages/CompaniesPage.vue
frontend/vue/src/pages/DraftDetailPage.vue
tests/test_vue_spa_serving.py
tests/test_vue_api_contracts.py
```

Possibly modify only if safe IDs are missing:

```text
job_agent/routers/vue_api.py
```

Do not modify:

```text
vite.config.js
job_agent/main.py
frontend/templates/
frontend/static/
temp_mac_test/
```

unless investigation proves absolutely necessary.

Default expectation:

```text
This is mostly Vue routing/pages + tests.
Backend changes should be limited to safe read-shape enrichment if needed.
```

---

## Router Requirements

Add these routes to `frontend/vue/src/router/index.js`:

```text
/jobs/:id
/applications/:id
/companies/:id
```

Names are optional, but route paths must remain bare Vue paths, not `/app/...`.

Correct:

```js
{
  path: "/jobs/:id",
  component: JobDetailPage
}
```

Incorrect:

```js
{
  path: "/app/jobs/:id",
  component: JobDetailPage
}
```

Because router base is already:

```js
createWebHistory("/app")
```

---

## SPA Bridge Requirements

FastAPI SPA bridge must serve direct refresh for:

```text
/app/jobs/123
/app/applications/123
/app/companies/123
```

If the current `/app/*` bridge already serves all `/app` paths, no backend change is needed.

Add or update tests in `tests/test_vue_spa_serving.py` to verify:

```text
GET /app/jobs/example-id returns Vue HTML or safe build-missing response
GET /app/applications/example-id returns Vue HTML or safe build-missing response
GET /app/companies/example-id returns Vue HTML or safe build-missing response
```

Do not change `/dashboard`.

Do not let `/api/*`, `/api/vue/*`, `/ui/*`, or `/static/*` be swallowed.

---

## API Contract Requirements

Verify these endpoints exist and are safe:

```text
GET /api/vue/jobs/{job_id}
GET /api/vue/applications/{application_id}
GET /api/vue/companies/{company_id}
```

If an endpoint already exists and is safe, do not rewrite it.

If a response lacks safe related IDs needed for navigation, add only minimal safe fields.

Allowed safe fields:

```text
id
title
role
company
company_id
job_id
application_id
location
status
source
created_at
updated_at
approved
score
```

Do not expose:

```text
absolute paths
secrets
provider config
raw prompt text
private model names
keyring/env values
internal file paths
private URLs unless already exposed safely elsewhere
```

For URLs:

```text
Do not add new raw URLs unless existing Vue APIs already expose the same class safely.
Prefer *_url_available booleans.
```

All responses must use the existing Vue API envelope:

```json
{
  "ok": true,
  "contract_version": 1,
  "data": {}
}
```

Unknown IDs must return safe contract error envelope.

---

## Page Requirements

### JobDetailPage.vue

Create a read-only job detail page.

Use:

```text
vueApiFetch(`/jobs/${route.params.id}`)
```

Required sections:

```text
Job detail
Company/context
Status
Related workflow
```

Display safe fields if available:

```text
title / role
company
location
status
source
score
created_at / updated_at
```

Links:

```text
Back to jobs -> /jobs
View applications -> /applications
View drafts -> /drafts
View company -> /companies/:id only if company_id exists
```

If `company_id` does not exist, link to `/companies`.

No mutation buttons.

No queue-state controls.

No enrich/discover controls.

---

### ApplicationDetailPage.vue

Create a read-only application detail page.

Use:

```text
vueApiFetch(`/applications/${route.params.id}`)
```

Required sections:

```text
Application detail
Linked job
Status
Related workflow
```

Display safe fields if available:

```text
status
company
role/title
location
created_at / updated_at
job metadata
draft metadata if available
```

Links:

```text
Back to applications -> /applications
View jobs -> /jobs
View drafts -> /drafts
View linked job -> /jobs/:id only if job_id exists
View linked draft -> /drafts/:id only if draft_id exists
```

No mutation buttons.

No status update controls.

---

### CompanyDetailPage.vue

Create a read-only company detail page.

Use:

```text
vueApiFetch(`/companies/${route.params.id}`)
```

Required sections:

```text
Company detail
Career source status
Related workflow
```

Display safe fields if available:

```text
name
status
active/enabled
job_count
last_seen/updated_at
career_page_url_available
```

Links:

```text
Back to companies -> /companies
View jobs -> /jobs
View applications -> /applications
```

No mutation buttons.

No toggle active controls.

No discovery controls.

---

## List Page Link Requirements

Update list pages to link to new detail routes:

```text
JobsPage.vue -> /jobs/{id}
ApplicationsPage.vue -> /applications/{id}
CompaniesPage.vue -> /companies/{id}
```

Use `RouterLink`.

Do not hardcode `/app`.

Do not use `window.location.href`.

If ID is missing, do not render a broken detail link.

---

## Draft Detail Cross-Link Requirements

Update `DraftDetailPage.vue` related workflow:

```text
If draft.job.id exists, link to /jobs/{job.id}
If draft.application.id exists, link to /applications/{application.id}
Otherwise keep list links:
- /jobs
- /applications
```

Use `RouterLink`.

Do not invent IDs.

Do not hardcode `/app`.

---

## Tests Required

Add:

```text
tests/test_vue_context_detail_routes.py
```

Minimum tests:

```text
router/index.js contains /jobs/:id
router/index.js contains /applications/:id
router/index.js contains /companies/:id
JobDetailPage.vue exists and uses vueApiFetch(`/jobs/${...}`)
ApplicationDetailPage.vue exists and uses vueApiFetch(`/applications/${...}`)
CompanyDetailPage.vue exists and uses vueApiFetch(`/companies/${...}`)
JobsPage.vue links to /jobs/{id} with RouterLink or equivalent safe route path
ApplicationsPage.vue links to /applications/{id}
CompaniesPage.vue links to /companies/{id}
DraftDetailPage.vue links to /jobs/{id} when safe job id exists or contains logic for it
No detail page uses window.location.href for Vue navigation
No detail page hardcodes /app/
```

Backend/API tests:

```text
GET /api/vue/jobs/not-a-real-id returns safe contract error
GET /api/vue/applications/not-a-real-id returns safe contract error
GET /api/vue/companies/not-a-real-id returns safe contract error
Responses expose no secrets/paths/provider internals
```

SPA serving tests:

```text
GET /app/jobs/example-id serves Vue HTML or safe 503
GET /app/applications/example-id serves Vue HTML or safe 503
GET /app/companies/example-id serves Vue HTML or safe 503
```

Avoid brittle tests that require real datasets.

Do not require live LLM providers.

---

## Validation Commands

Run:

```bash
npm run build:vue
npm run css:build
pytest tests/test_vue_context_detail_routes.py -v
pytest tests/test_vue_draft_actions.py -v
pytest tests/test_vue_draft_metadata.py -v
pytest tests/test_vue_apply_flow.py -v
pytest tests/test_vue_api_contracts.py tests/test_vue_spa_serving.py tests/test_legacy_surface_hardening.py tests/test_settings_current_hardening.py tests/test_legacy_ui_settings_surface_hardening.py tests/test_settings_public_contract_tightening.py tests/test_settings_copy_consistency.py -v
pytest
```

Expected:

```text
full pytest passes
```

---

## Manual Validation

Start backend:

```bash
uvicorn job_agent.main:app --host 127.0.0.1 --port 8000 --reload
```

Open:

```text
http://127.0.0.1:8000/app/jobs
http://127.0.0.1:8000/app/applications
http://127.0.0.1:8000/app/companies
```

If you have existing IDs, open:

```text
http://127.0.0.1:8000/app/jobs/{job_id}
http://127.0.0.1:8000/app/applications/{application_id}
http://127.0.0.1:8000/app/companies/{company_id}
```

Test:

```text
1. List pages load.
2. Detail links appear only when IDs exist.
3. Detail pages load.
4. Related workflow links navigate under /app.
5. No mutation buttons appear.
6. No secrets, paths, provider URLs, or model names appear.
7. Legacy /ui/* routes still load.
```

---

## Acceptance Criteria

This task is complete only if:

1. `/app/jobs/:id` route exists.
2. `/app/applications/:id` route exists.
3. `/app/companies/:id` route exists.
4. Direct refresh works for all three detail route patterns.
5. JobDetailPage fetches `/api/vue/jobs/{id}`.
6. ApplicationDetailPage fetches `/api/vue/applications/{id}`.
7. CompanyDetailPage fetches `/api/vue/companies/{id}`.
8. List pages link to detail pages when IDs exist.
9. Draft detail links directly to job/application detail when IDs exist.
10. No mutation controls are added.
11. No LLM calls are added.
12. No email sending is added.
13. No application submission is added.
14. No secrets/paths/provider internals are exposed.
15. `/ui/*` remains active.
16. `npm run build:vue` passes.
17. Full `pytest` passes.
18. Vue Router base remains `/app`.
19. No legacy UI deletion happens.

---

## Forbidden Outcomes

Do not:

- add queue-state mutation
- add discovery mutation
- add enrich mutation
- add apply generation
- add draft mutation
- auto-generate anything
- send emails
- submit applications
- expose raw URLs/private URLs unless already safely exposed elsewhere
- expose secrets
- expose local paths
- expose provider URLs or model names
- hardcode /app in RouterLinks
- use window.location.href for Vue navigation
- change Vue Router base
- change Vite base
- change /app bridge
- remove /ui routes
- remove Jinja templates
- remove legacy static JS
- use Vuex
- add TypeScript
- add Docker
- start /ui deprecation
- start /ui deletion

---

## Final Codex Response

Report:

1. files added
2. files modified
3. routes added
4. pages added
5. API/backend changes, if any
6. related navigation changes
7. commands run
8. `npm run build:vue` result
9. `npm run css:build` result
10. focused context-route test result
11. draft/apply regression test result
12. migration/security focused test result
13. full `pytest` result
14. manual validation result
15. known issues
16. recommended next step

Do not continue to mutations.
