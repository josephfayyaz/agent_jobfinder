# 024 Vue Draft Actions Migration

## Goal

Enable the first set of real draft actions in the Vue app:

```text
/app/drafts
/app/drafts/{draft_id}
```

This task must migrate only the safe, review-oriented draft actions:

```text
Approve draft
Reject draft
Generate/display cover letter
```

Do not migrate HITL bullet rewrite, clarify, revise, polish, inferred additions, or preview-update flows in this task.

Keep legacy `/ui/drafts` and `/ui/drafts/{draft_id}` active as rollback.

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
```

Current expected behavior before this task:

```text
/app/apply is active
/app/apply can navigate to /app/drafts/{draft_id} after draft generation
/app/drafts and /app/drafts/{draft_id} are read-only review pages
/api/vue/drafts endpoints are partially present
full pytest is green
```

---

## Backend Reality To Verify

Before editing, inspect the actual existing backend routes and service logic.

Expected legacy/bare endpoints may include:

```text
POST /drafts/{draft_id}/approve
POST /drafts/{draft_id}/cover-letter
POST /ui/drafts/{draft_id}/approve
POST /ui/drafts/{draft_id}/reject
```

Expected existing Vue contract endpoint:

```text
POST /api/vue/drafts/{draft_id}/approve   currently 501
```

Likely missing Vue endpoints:

```text
POST /api/vue/drafts/{draft_id}/reject
POST /api/vue/drafts/{draft_id}/cover-letter
```

Do not assume exact route names or payloads. Inspect the real handlers first.

---

## Hard Constraints

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

Do not auto-approve drafts.

Do not approve without explicit confirmation.

Do not reject without explicit confirmation.

Do not send emails.

Do not submit applications.

Do not mutate verified facts.

Do not migrate revise/polish/clarify/HITL rewrite in this task.

Do not call LLMs except for the existing cover-letter generation path, and only after explicit user click.

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
frontend/vue/src/pages/DraftsPage.vue
frontend/vue/src/pages/DraftDetailPage.vue
frontend/vue/src/api/client.js
frontend/vue/src/router/index.js
job_agent/routers/vue_api.py
job_agent/routers/
job_agent/services/
frontend/static/draft_detail.js
tests/
```

Search:

```bash
rg -n "drafts/.*/approve|cover-letter|reject|clarify|polish|revise|inferred|preview/update|approved|ResumeDraft|draft_id" job_agent frontend tests
rg -n "api/vue/drafts|DraftsPage|DraftDetailPage|vueApiFetch|router.push|window.location" frontend/vue job_agent tests
```

Run baseline tests before editing:

```bash
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
frontend/vue/src/api/contracts.js
```

Only if the project already uses this pattern.

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

Default preference:

```text
Do not touch legacy draft_detail.js.
Do not touch /ui/drafts.
Add or upgrade Vue-safe wrappers under /api/vue.
```

---

## API Contract Requirements

All `/api/vue/drafts/*` responses must use the existing Vue API envelope style.

Success shape:

```json
{
  "ok": true,
  "contract_version": 1,
  "data": {}
}
```

Error shape:

```json
{
  "ok": false,
  "contract_version": 1,
  "error": {
    "code": "not_found",
    "message": "..."
  }
}
```

Use the helper style already present in `job_agent/routers/vue_api.py`.

Do not add global exception handlers.

Do not return raw legacy response shapes directly if they do not match the Vue envelope.

---

## Endpoint 1: POST /api/vue/drafts/{draft_id}/approve

Upgrade the existing 501 stub.

Behavior:

```text
Approve the draft using the same business behavior as the existing draft approve flow.
Return the updated draft status or a compact safe draft object.
```

Validation:

```text
Unknown draft_id returns safe 404 contract error.
Invalid draft_id returns safe 404 or 422 contract error.
```

Response data should include:

```json
{
  "draft_id": "...",
  "approved": true,
  "status": "approved"
}
```

or equivalent existing status fields.

Safety:

```text
Must only run after explicit user confirmation.
Do not submit application.
Do not send email.
Do not create cover letter automatically.
```

---

## Endpoint 2: POST /api/vue/drafts/{draft_id}/reject

Add this endpoint if missing.

Behavior:

```text
Reject/unapprove the draft using the same business behavior as existing legacy reject flow.
If the backend stores approved as boolean, set approved to false.
If it stores status, use the existing rejected/unapproved representation.
Do not delete the draft.
```

Validation:

```text
Unknown draft_id returns safe 404 contract error.
Invalid draft_id returns safe 404 or 422 contract error.
```

Response data should include:

```json
{
  "draft_id": "...",
  "approved": false,
  "status": "rejected"
}
```

or equivalent existing status fields.

Safety:

```text
Must only run after explicit user confirmation.
Reject does not delete the draft.
Reject does not submit anything.
```

---

## Endpoint 3: POST /api/vue/drafts/{draft_id}/cover-letter

Add this endpoint if missing.

Behavior:

```text
Generate or fetch a cover letter using the existing cover-letter flow.
Return cover letter text/content in the Vue contract envelope.
```

Validation:

```text
Unknown draft_id returns safe 404 contract error.
Provider unavailable or setup required returns safe contract error.
```

Response data should include:

```json
{
  "draft_id": "...",
  "cover_letter": "..."
}
```

If the existing backend stores cover letters differently, preserve the useful safe fields and document them in tests.

Safety:

```text
May call LLM only after explicit user click.
Do not send email.
Do not approve draft automatically.
Do not submit application.
```

---

## Frontend Requirements: DraftDetailPage.vue

Make `/app/drafts/{draft_id}` support the migrated actions.

Required UI:

```text
Approve Draft button
Reject Draft button
Generate Cover Letter button
Cover letter display area
Loading/error/success states
```

Approve/reject requirements:

```text
- Require explicit confirmation before calling the endpoint.
- Use window.confirm or an equivalent simple confirmation.
- Disable buttons while request is in progress.
- After success, update local draft status without requiring full page reload.
```

Cover letter requirements:

```text
- Call only after explicit button click.
- Show loading state while generating.
- Display the generated cover letter inline.
- Show safe error message on provider/setup failure.
```

Do not implement:

```text
Revise
Polish
Clarify
Preview update
Bullet rewrite
Inferred additions
```

If those buttons already exist disabled, keep them disabled and marked as future work.

---

## Frontend Requirements: DraftsPage.vue

Add lightweight actions to the draft list only if the page already has enough draft status data.

Required if practical:

```text
Approve button per draft row/card
Reject button per draft row/card
Link to detail page
```

Rules:

```text
- Approve/reject must require confirmation.
- Do not generate cover letter from the list page unless already clearly supported by existing UI.
- Prefer cover letter only on detail page.
```

If the API list payload lacks enough fields, implement list actions only if safe and simple; otherwise document why detail-only actions were implemented.

---

## Frontend Navigation Rules

Draft detail route is already:

```text
/drafts/:id
```

Because Vue Router base is `/app`, the browser URL is:

```text
/app/drafts/{draft_id}
```

Use:

```vue
<RouterLink :to="`/drafts/${draft.id}`">Open</RouterLink>
```

Do not use:

```js
window.location.href = "/ui/drafts/..."
window.location.href = "/app/drafts/..."
```

---

## Tests Required

Add:

```text
tests/test_vue_draft_actions.py
```

Minimum backend contract tests:

```text
POST /api/vue/drafts/not-a-real-id/approve returns safe 404/422 contract error
POST /api/vue/drafts/not-a-real-id/reject returns safe 404/422 contract error
POST /api/vue/drafts/not-a-real-id/cover-letter returns safe 404/422 contract error
Approve endpoint no longer returns 501
Reject endpoint no longer returns 404 because route is missing
Cover-letter endpoint no longer returns 404 because route is missing
All error responses use contract envelope
All error responses expose no secrets/paths
```

If there are existing fixtures/helpers for creating a draft, add positive tests:

```text
create draft fixture
POST approve -> approved true/status approved
POST reject -> approved false/status rejected
POST cover-letter -> non-501 response or safe provider-unavailable/setup-required contract error
```

Avoid tests that require live external LLM provider.

Frontend static/source tests:

```text
DraftDetailPage.vue contains approve action
DraftDetailPage.vue contains reject action
DraftDetailPage.vue contains cover letter action
DraftDetailPage.vue does not contain window.location.href to /ui/drafts
DraftDetailPage.vue keeps revise/polish/HITL controls disabled or absent
```

Run existing hardening tests to ensure no regression.

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
1. Draft list loads.
2. Open a draft detail page.
3. Click Approve Draft.
4. Confirm dialog appears.
5. Cancel once and verify no API call/state change.
6. Click Approve Draft again and confirm.
7. Draft status updates in Vue.
8. Click Reject Draft and confirm.
9. Draft status updates in Vue.
10. Click Generate Cover Letter.
11. Cover letter appears or safe provider/setup error appears.
12. No email is sent.
13. No application is submitted.
14. Legacy /ui/drafts still loads.
```

Also verify fallback:

```text
http://127.0.0.1:8000/ui/drafts
```

Expected:

```text
Legacy draft UI still works.
```

---

## Acceptance Criteria

This task is complete only if:

1. `/app/drafts/{draft_id}` can approve a draft after explicit confirmation.
2. `/app/drafts/{draft_id}` can reject/unapprove a draft after explicit confirmation.
3. `/app/drafts/{draft_id}` can request a cover letter after explicit click.
4. Cover letter appears inline or safe provider/setup error appears.
5. `/api/vue/drafts/{draft_id}/approve` no longer returns 501.
6. `/api/vue/drafts/{draft_id}/reject` exists.
7. `/api/vue/drafts/{draft_id}/cover-letter` exists.
8. All new Vue draft-action endpoints use contract envelope.
9. Unknown draft IDs return safe contract errors.
10. No email is sent.
11. No application is submitted.
12. No draft is auto-approved.
13. No revise/polish/HITL rewrite is migrated in this task.
14. `/ui/drafts` remains active.
15. `/ui/drafts/{draft_id}` remains active.
16. Tests for Vue draft actions are added.
17. `npm run build:vue` passes.
18. Full `pytest` passes.
19. Settings/security hardening tests still pass.
20. No secrets/paths are exposed.
21. Vue Router base remains `/app`.
22. No legacy UI deletion happens.

---

## Forbidden Outcomes

Do not:

- remove /ui/drafts
- remove /ui/drafts/{draft_id}
- redirect /ui/drafts to Vue
- auto-approve draft
- approve without confirmation
- reject without confirmation
- delete drafts
- send email
- submit application
- auto-generate cover letter on page load
- migrate revise/polish/clarify/HITL rewrite
- expose secrets
- expose local paths
- expose provider URLs or model names
- change Vue Router base
- change Vite base
- change /app bridge
- remove Jinja templates
- remove legacy static JS
- remove HTMX
- remove Alpine
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
3. backend endpoints upgraded/added
4. frontend draft actions implemented
5. commands run
6. `npm run build:vue` result
7. `npm run css:build` result
8. focused draft-action test result
9. apply-flow regression test result
10. migration/security focused test result
11. full `pytest` result
12. manual validation result
13. known issues
14. recommended next step

Do not continue to Spec 025.
