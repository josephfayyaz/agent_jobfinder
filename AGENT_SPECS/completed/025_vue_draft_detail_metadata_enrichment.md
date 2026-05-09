# 025 Vue Draft Detail Metadata Enrichment

## Goal

Enrich the Vue draft detail API and page so `/app/drafts/{draft_id}` shows safe linked job/company metadata instead of generic fallback values like:

```text
Unknown company
Untitled draft
Status unavailable
```

This task is read-only metadata enrichment.

Do not add new draft mutations.

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
```

Known issue from task 024:

```text
The Vue draft detail contract currently does not hydrate linked job/company info, so the page can still show Unknown company even when the draft belongs to a real job.
```

Current expected behavior before this task:

```text
/app/drafts works
/app/drafts/{draft_id} works
approve/reject/cover-letter actions work
full pytest is green
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
job_agent/routers/
job_agent/services/
frontend/vue/src/pages/DraftsPage.vue
frontend/vue/src/pages/DraftDetailPage.vue
tests/test_vue_draft_actions.py
tests/test_vue_api_contracts.py
```

Search:

```bash
rg -n "ResumeDraft|draft_id|job_id|company|company_name|job_title|location|source|status|application" job_agent frontend/vue tests
rg -n "api/vue/drafts|DraftDetailPage|Unknown company|Untitled draft|jobCompany|jobTitle" frontend/vue job_agent tests
```

Run baseline:

```bash
pytest tests/test_vue_draft_actions.py tests/test_vue_api_contracts.py -v
pytest
```

If baseline is not green, stop and report.

---

## Files To Modify

Likely modify:

```text
job_agent/routers/vue_api.py
frontend/vue/src/pages/DraftsPage.vue
frontend/vue/src/pages/DraftDetailPage.vue
tests/test_vue_draft_actions.py
```

Optional:

```text
tests/test_vue_draft_metadata.py
```

Only add a new test file if cleaner than extending `tests/test_vue_draft_actions.py`.

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
This is mostly /api/vue/drafts read-shape enrichment and small Vue display cleanup.
```

---

## Backend Contract Requirements

Enrich safe read responses for:

```text
GET /api/vue/drafts
GET /api/vue/drafts/{draft_id}
```

Focus especially on:

```text
GET /api/vue/drafts/{draft_id}
```

Keep the existing envelope:

```json
{
  "ok": true,
  "contract_version": 1,
  "data": {}
}
```

Do not break existing keys used by the Vue page.

Add safe metadata where available.

Recommended `data` fields for detail endpoint:

```json
{
  "id": "...",
  "title": "...",
  "role": "...",
  "company": "...",
  "location": "...",
  "status": "...",
  "approved": false,
  "created_at": "...",
  "updated_at": "...",
  "job": {
    "id": "...",
    "title": "...",
    "company": "...",
    "location": "...",
    "source": "...",
    "status": "..."
  },
  "company_record": {
    "id": "...",
    "name": "...",
    "career_page_url_available": true
  }
}
```

Use the actual project model names/relationships after inspection.

If some fields are unavailable, omit them or return `null`.

Do not invent values.

Do not expose:

```text
absolute paths
secrets
provider config
raw prompt text
private model names
keyring/env values
internal file paths
```

For URLs:

```text
Do not expose raw career-page URLs if previous hardening policy treats URLs as sensitive.
Use career_page_url_available: true/false if needed.
```

If ordinary public job source URLs are already exposed safely in job list endpoints, keep consistent with existing project policy. Do not add new sensitive URLs.

---

## Frontend Requirements: DraftDetailPage.vue

Update `/app/drafts/{draft_id}` display so it prefers enriched metadata.

Required display improvements:

```text
- Show role/job title when available.
- Show company name when available.
- Show location when available.
- Show draft status/approval state.
- Show linked job metadata section if available.
```

Fallback behavior:

```text
- Continue to handle missing fields safely.
- Use Unknown company only when no company value exists.
- Use Untitled draft only when no title/role/job title exists.
```

Do not break existing:

```text
Approve Draft
Reject Draft
Generate Cover Letter
Cover letter display
Legacy fallback link
```

---

## Frontend Requirements: DraftsPage.vue

If the list endpoint can be enriched safely, update list cards/table to use:

```text
job title / role
company name
status / approval state
location if available
```

If the list endpoint is not enriched, leave list behavior unchanged and document why.

Do not add new mutations beyond existing approve/reject list actions from task 024.

---

## Tests Required

Update or add tests covering:

```text
GET /api/vue/drafts/{draft_id} includes safe linked job/company metadata when relationships exist
GET /api/vue/drafts/{draft_id} does not expose secrets/paths/provider config
GET /api/vue/drafts/{draft_id} still returns safe placeholder/fallback for missing relationships
GET /api/vue/drafts includes safe metadata if list enrichment is implemented
DraftDetailPage.vue prefers job/company metadata over Unknown company fallback
Existing approve/reject/cover-letter tests still pass
```

If fixtures exist for creating linked job + draft, use them.

If not, create minimal test setup using the project’s existing DB/session test utilities.

Avoid brittle tests that depend on large real datasets.

Do not require live LLM providers.

---

## Validation Commands

Run:

```bash
npm run build:vue
npm run css:build
pytest tests/test_vue_draft_actions.py -v
pytest tests/test_vue_apply_flow.py -v
pytest tests/test_vue_api_contracts.py tests/test_vue_spa_serving.py tests/test_legacy_surface_hardening.py tests/test_settings_current_hardening.py tests/test_legacy_ui_settings_surface_hardening.py tests/test_settings_public_contract_tightening.py tests/test_settings_copy_consistency.py -v
pytest
```

If you add `tests/test_vue_draft_metadata.py`, run it explicitly:

```bash
pytest tests/test_vue_draft_metadata.py -v
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
2. Linked job title/role appears if draft has a linked job.
3. Company name appears if available.
4. Location appears if available.
5. Approval/status display still works.
6. Approve/reject/cover-letter buttons still exist.
7. No secrets, paths, provider URLs, or model names appear.
8. Legacy /ui/drafts still loads.
```

Also verify:

```text
http://127.0.0.1:8000/api/vue/drafts/{existing_draft_id}
```

Expected:

```text
Safe JSON envelope with enriched metadata.
```

---

## Acceptance Criteria

This task is complete only if:

1. `/api/vue/drafts/{draft_id}` returns safe linked job/company metadata when available.
2. `/app/drafts/{draft_id}` displays job/company metadata instead of unnecessary Unknown company fallback.
3. Missing metadata is handled safely.
4. Existing approve/reject/cover-letter actions still work.
5. No new mutation behavior is added.
6. No LLM calls are added.
7. No email sending is added.
8. No application submission is added.
9. No secrets/paths/provider internals are exposed.
10. `/ui/drafts` remains active.
11. `/ui/drafts/{draft_id}` remains active.
12. `npm run build:vue` passes.
13. Full `pytest` passes.
14. Vue Router base remains `/app`.
15. No legacy UI deletion happens.

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
3. metadata fields added to Vue draft contracts
4. frontend display changes made
5. commands run
6. `npm run build:vue` result
7. `npm run css:build` result
8. focused draft metadata/action test result
9. apply-flow regression test result
10. migration/security focused test result
11. full `pytest` result
12. manual validation result
13. known issues
14. recommended next step

Do not continue to revise/polish/HITL migration.
