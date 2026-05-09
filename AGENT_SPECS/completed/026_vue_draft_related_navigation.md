# 026 Vue Draft Related Navigation

## Goal

Improve navigation around Vue draft review pages.

Add safe, read-only related navigation from:

```text
/app/drafts/{draft_id}
```

to relevant nearby Vue pages when metadata exists:

```text
/app/jobs
/app/applications
/app/drafts
```

This task must not add new mutations.

Do not migrate revise, polish, clarify, HITL bullet rewrite, inferred additions, or preview-update flows in this task.

Do not call LLMs.

Do not remove legacy `/ui/drafts` or `/ui/drafts/{draft_id}`.

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
```

Current expected behavior before this task:

```text
/app/drafts works
/app/drafts/{draft_id} works
approve/reject/cover-letter actions work
draft detail shows linked job/company metadata when available
full pytest is green
```

Known safe draft metadata from Spec 025 may include:

```text
id
title
role
company
location
status
approved
created_at
updated_at
job
company_record
```

---

## Hard Constraints

Do not add new mutation behavior.

Do not change approve/reject/cover-letter behavior unless fixing a regression.

Do not call LLMs.

Do not generate cover letters automatically.

Do not approve drafts automatically.

Do not send emails.

Do not submit applications.

Do not mutate verified facts.

Do not remove `/ui/drafts`.

Do not remove `/ui/drafts/{draft_id}`.

Do not redirect legacy draft routes to Vue.

Do not remove Jinja templates.

Do not remove legacy static JavaScript.

Do not remove HTMX.

Do not remove Alpine.

Do not remove `/ui/*` routes.

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
job_agent/routers/vue_api.py
frontend/vue/src/pages/DraftsPage.vue
frontend/vue/src/pages/DraftDetailPage.vue
frontend/vue/src/router/index.js
frontend/vue/src/constants/navigation.js
tests/test_vue_draft_actions.py
tests/test_vue_draft_metadata.py
```

Search:

```bash
rg -n "job_id|application_id|applications|RouterLink|to=|/jobs|/applications|/drafts" frontend/vue/src/pages job_agent/routers/vue_api.py tests
rg -n "api/vue/jobs|api/vue/applications|api/vue/drafts|DraftDetailPage|DraftsPage" frontend/vue job_agent tests
```

Run baseline:

```bash
pytest tests/test_vue_draft_actions.py tests/test_vue_draft_metadata.py -v
pytest
```

If baseline is not green, stop and report.

---

## Files To Modify

Likely modify:

```text
frontend/vue/src/pages/DraftDetailPage.vue
frontend/vue/src/pages/DraftsPage.vue
tests/test_vue_draft_metadata.py
```

Possibly modify, only if needed to expose already-safe identifiers:

```text
job_agent/routers/vue_api.py
tests/test_vue_draft_actions.py
```

Do not modify:

```text
frontend/vue/src/router/index.js
vite.config.js
job_agent/main.py
frontend/templates/
frontend/static/draft_detail.js
frontend/static/apply.js
temp_mac_test/
```

unless investigation proves absolutely necessary.

Default expectation:

```text
This is mostly Vue navigation/display cleanup.
Backend changes are allowed only to add safe related IDs already present in models.
```

---

## Backend Contract Requirements

If not already present, add safe identifiers to:

```text
GET /api/vue/drafts/{draft_id}
GET /api/vue/drafts
```

Allowed safe fields:

```json
{
  "job_id": "...",
  "application_id": "...",
  "job": {
    "id": "...",
    "title": "...",
    "company": "...",
    "location": "...",
    "status": "..."
  },
  "application": {
    "id": "...",
    "status": "..."
  }
}
```

Only include fields that exist safely.

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

If no related application exists, omit it or return `null`.

Do not invent related IDs.

---

## Frontend Requirements: DraftDetailPage.vue

Add a clearly labeled related navigation section.

Required links:

```text
Back to drafts -> /drafts
View jobs -> /jobs
View applications -> /applications
```

When a related job ID exists and the app has a supported job detail route, link to it.

If the router does not currently support job detail routes, do not invent a route. Use `/jobs` with clear copy:

```text
View jobs
```

When a related application ID exists and the router has a supported application detail route, link to it.

If the router does not currently support application detail routes, use `/applications` with clear copy:

```text
View applications
```

Use `RouterLink`, not `window.location.href`.

Correct:

```vue
<RouterLink to="/drafts">Back to drafts</RouterLink>
<RouterLink to="/jobs">View jobs</RouterLink>
<RouterLink to="/applications">View applications</RouterLink>
```

Because Vue Router base is `/app`, these render as:

```text
/app/drafts
/app/jobs
/app/applications
```

Do not hardcode `/app`.

Do not link to `/ui/*` except the existing legacy fallback link.

---

## Frontend Requirements: DraftsPage.vue

Improve list-level navigation only if useful:

```text
Open draft detail
View jobs
View applications
```

Do not add new action buttons beyond approve/reject from Spec 024.

Do not add cover-letter generation to the list page.

---

## UX Copy Requirements

Use concise labels:

```text
Related workflow
Back to drafts
View jobs
View applications
Linked job
Application tracking
```

Do not use internal terms like:

```text
foreign key
job_id
application_id
database relation
contract payload
```

IDs may appear only in small technical metadata if the page already shows IDs.

---

## Tests Required

Update or add tests covering:

```text
DraftDetailPage.vue contains RouterLink to /drafts
DraftDetailPage.vue contains RouterLink to /jobs
DraftDetailPage.vue contains RouterLink to /applications
DraftDetailPage.vue does not hardcode /app/jobs or /app/applications
DraftDetailPage.vue does not use window.location.href for related navigation
GET /api/vue/drafts/{draft_id} still returns safe metadata
Existing approve/reject/cover-letter tests still pass
```

If backend IDs are added:

```text
GET /api/vue/drafts/{draft_id} includes job_id/application_id only when safely available
No secrets/paths/provider internals appear
```

Avoid brittle tests that depend on large real datasets.

Do not require live LLM providers.

---

## Validation Commands

Run:

```bash
npm run build:vue
npm run css:build
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
http://127.0.0.1:8000/app/drafts
http://127.0.0.1:8000/app/drafts/{existing_draft_id}
```

Test:

```text
1. Draft detail page loads.
2. Related workflow section appears.
3. Back to drafts navigates to /app/drafts.
4. View jobs navigates to /app/jobs.
5. View applications navigates to /app/applications.
6. Existing approve/reject/cover-letter controls still work.
7. No secrets, paths, provider URLs, or model names appear.
8. Legacy /ui/drafts still loads.
```

---

## Acceptance Criteria

This task is complete only if:

1. `/app/drafts/{draft_id}` has related navigation.
2. There is a Vue RouterLink back to `/drafts`.
3. There is a Vue RouterLink to `/jobs`.
4. There is a Vue RouterLink to `/applications`.
5. Links do not hardcode `/app`.
6. Links do not use `window.location.href`.
7. Existing approve/reject/cover-letter actions still work.
8. No new mutations are added.
9. No LLM calls are added.
10. No email sending is added.
11. No application submission is added.
12. No secrets/paths/provider internals are exposed.
13. `/ui/drafts` remains active.
14. `/ui/drafts/{draft_id}` remains active.
15. `npm run build:vue` passes.
16. Full `pytest` passes.
17. Vue Router base remains `/app`.
18. No legacy UI deletion happens.

---

## Forbidden Outcomes

Do not:

- add revise/polish/clarify/HITL rewrite
- add inferred additions flows
- add preview update flows
- auto-generate cover letters
- auto-approve drafts
- send emails
- submit applications
- expose raw career-page/private URLs unless already safely exposed by existing job contracts
- expose secrets
- expose local paths
- expose provider URLs or model names
- hardcode /app in RouterLinks
- use window.location.href for Vue navigation
- change Vue Router base
- change Vite base
- change /app bridge
- remove /ui/drafts
- remove /ui/drafts/{draft_id}
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
3. related navigation added
4. backend metadata changes, if any
5. commands run
6. `npm run build:vue` result
7. `npm run css:build` result
8. focused draft navigation/metadata/action test result
9. apply-flow regression test result
10. migration/security focused test result
11. full `pytest` result
12. manual validation result
13. known issues
14. recommended next step

Do not continue to revise/polish/HITL migration.
