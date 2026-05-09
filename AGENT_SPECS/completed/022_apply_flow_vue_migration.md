# 022 Apply Flow Vue Migration

## Goal

Make the Vue `/app/apply` page fully functional.

The current Vue Apply page is a read-only shell. This task must wire the full apply workflow into Vue:

```text
Paste job description
→ Score / parse job
→ Ask clarifying questions
→ Generate draft
→ Poll task status
→ Navigate to /app/drafts/{draft_id}
```

Do not remove the legacy `/ui/apply` route yet.

Keep `/ui/apply` working as rollback until Vue apply flow is fully tested.

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
```

Current expected state before this task:

```text
pytest passes fully
Vue app is served under /app
Legacy /ui/* is still active
/api/* and /api/vue/* are protected
/app/apply is currently a read-only shell
/ui/apply contains the real legacy apply workflow
```

---

## Backend Reality To Verify

Before editing, inspect the actual existing backend routes and service logic.

Expected legacy endpoints:

```text
POST /apply/parse
POST /apply/questions
POST /apply/generate
GET /apply/status/{task_id}
```

Expected existing Vue contract stubs:

```text
POST /api/vue/apply/score       currently 501
POST /api/vue/apply/questions   currently 501
POST /api/vue/apply/draft       currently 501
```

Missing Vue endpoint to add:

```text
GET /api/vue/apply/status/{task_id}
```

Do not assume exact payload names. Inspect the real handlers first.

---

## Hard Constraints

Do not remove `/ui/apply`.

Do not redirect `/ui/apply` to Vue.

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

Do not auto-generate drafts without explicit user click.

Do not auto-submit applications.

Do not send emails.

Do not approve drafts.

Do not mutate verified facts.

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
frontend/vue/src/pages/ApplyPage.vue
frontend/vue/src/api/client.js
frontend/vue/src/router/index.js
job_agent/routers/vue_api.py
job_agent/routers/
job_agent/services/
frontend/static/apply.js
tests/
```

Search:

```bash
rg -n "apply/parse|apply/questions|apply/generate|apply/status|WorkflowTask|task_id|draft_id|job_description|job_text|Form\\(" job_agent frontend tests
rg -n "api/vue/apply|ApplyPage|vueApiFetch|router.push|setInterval|poll" frontend/vue job_agent tests
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
frontend/vue/src/pages/ApplyPage.vue
tests/test_vue_apply_flow.py
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
frontend/static/apply.js
frontend/static/onboarding/
frontend/static/settings/
temp_mac_test/
```

unless investigation proves absolutely necessary.

Default preference:

```text
Do not touch legacy apply.js.
Do not touch /ui/apply.
Add Vue-safe wrappers under /api/vue.
```

---

## API Contract Requirements

All `/api/vue/apply/*` responses must use the existing Vue API envelope style.

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
    "code": "validation_error",
    "message": "..."
  }
}
```

Use the helper style already present in `job_agent/routers/vue_api.py`.

Do not add global exception handlers.

Do not return raw legacy response shapes directly if they do not match the Vue envelope.

---

## Endpoint 1: POST /api/vue/apply/score

Upgrade the existing 501 stub.

Input:

```json
{
  "job_description": "..."
}
```

Validation:

```text
job_description must be non-empty after trimming.
Return 422 contract error if empty.
```

Behavior:

```text
Use existing backend logic equivalent to POST /apply/parse.
Return parsed/scored job data for Vue.
```

Response data should include whatever the legacy endpoint produces, normalized safely if needed:

```json
{
  "score": 0,
  "matched_skills": [],
  "gaps": [],
  "job_data": {},
  "raw": {}
}
```

If exact names differ, preserve useful fields but document them in tests.

Safety:

```text
Do not call LLM unless the existing parse endpoint does so.
Do not save drafts.
Do not approve anything.
Do not enqueue generation.
```

---

## Endpoint 2: POST /api/vue/apply/questions

Upgrade the existing 501 stub.

Input:

```json
{
  "job_data": {},
  "gaps": [],
  "answers": {}
}
```

or the minimal shape required by the existing backend.

Validation:

```text
job_data must be present.
Return 422 contract error if missing/invalid.
```

Behavior:

```text
Use existing backend logic equivalent to POST /apply/questions.
Return clarifying questions.
```

Response data:

```json
{
  "questions": []
}
```

Safety:

```text
This may call LLM if the existing backend does.
It must only happen after explicit user click in Vue.
No draft generation here.
```

---

## Endpoint 3: POST /api/vue/apply/draft

Upgrade the existing 501 stub.

Input:

```json
{
  "job_data": {},
  "answers": {},
  "questions": []
}
```

or the minimal shape required by the existing backend.

Validation:

```text
job_data must be present.
Return 422 contract error if missing/invalid.
```

Behavior:

```text
Use existing backend logic equivalent to POST /apply/generate.
This should create or enqueue a WorkflowTask.
Return task_id.
```

Response data:

```json
{
  "task_id": "..."
}
```

Safety:

```text
Must only be called by explicit Generate Draft click.
Do not approve draft.
Do not submit application.
Do not send email.
```

---

## Endpoint 4: GET /api/vue/apply/status/{task_id}

Add this new endpoint.

Behavior:

```text
Use existing backend logic equivalent to GET /apply/status/{task_id}.
Return task status and draft_id if complete.
```

Response data:

```json
{
  "status": "pending|running|completed|failed",
  "draft_id": "...",
  "message": "..."
}
```

Status naming should match existing backend if different, but document it in tests.

Validation:

```text
Invalid or unknown task_id should return safe 404 or 422 contract error.
Do not crash with stacktrace.
```

---

## Frontend Requirements: ApplyPage.vue

Replace the read-only shell with a real Vue workflow.

Must include:

```text
textarea for job description
Score button
Score result section
Questions section
Answer fields
Generate Draft button
Polling/loading state
Error state
Success state
Navigation to draft detail
```

Workflow:

```text
1. User pastes job description.
2. User clicks Score.
3. Vue calls POST /api/vue/apply/score.
4. Score/parse results are displayed.
5. User clicks Generate Questions.
6. Vue calls POST /api/vue/apply/questions.
7. Vue displays questions with answer inputs.
8. User clicks Generate Draft.
9. Vue calls POST /api/vue/apply/draft.
10. Vue polls GET /api/vue/apply/status/{task_id}.
11. When completed with draft_id, Vue navigates to /drafts/{draft_id} using router.push.
```

Because Vue Router base is `/app`, this must result in browser URL:

```text
/app/drafts/{draft_id}
```

Use:

```js
router.push(`/drafts/${draftId}`)
```

Do not use:

```js
window.location.href = "/ui/drafts/..."
window.location.href = "/app/drafts/..."
```

---

## Frontend State Rules

Use local component state unless there is already a clear Pinia pattern for apply workflow.

Required states:

```text
jobDescription
scoreLoading
questionsLoading
draftLoading
polling
errorMessage
scoreResult
questions
answers
taskId
draftId
```

Disable buttons while their request is in progress.

Do not allow:

```text
Score with empty job description
Generate Questions before score result exists
Generate Draft before score result exists
```

If questions are empty, allow draft generation with an empty answers object if backend supports it.

Poll behavior:

```text
Interval: 3 seconds
Stop polling when completed or failed
Stop polling on unmount
Stop polling after repeated errors
```

Match legacy apply.js pattern if it already uses an `_errors >= 3` guard.

---

## Frontend Safety Copy

Remove the old read-only safety message that says Vue cannot run the flow.

Replace it with active safety copy:

```text
Draft generation only starts after you click Generate Draft.
Generated drafts remain reviewable before approval.
No application is submitted from this page.
```

Do not claim that no LLM calls are made after the flow is wired.

Do not claim that no draft generation happens.

Do not mention `/ui/apply` as the primary path anymore.

A small fallback link may remain:

```text
Legacy fallback: /ui/apply
```

but it must not be the main instruction.

---

## Tests Required

Add:

```text
tests/test_vue_apply_flow.py
```

Minimum backend contract tests:

```text
POST /api/vue/apply/score with empty job_description returns 422 contract error
POST /api/vue/apply/score with valid job_description returns non-501 response
POST /api/vue/apply/questions with missing job_data returns 422 contract error
POST /api/vue/apply/questions with valid minimal payload returns non-501 response or safe provider-unavailable contract error
POST /api/vue/apply/draft with missing job_data returns 422 contract error
POST /api/vue/apply/draft with valid minimal payload returns non-501 response or safe provider-unavailable contract error
GET /api/vue/apply/status/not-a-real-task returns safe 404/422 contract error
```

Avoid tests that require a live external LLM provider.

If the backend requires configured provider/model for questions/draft generation, tests may accept safe provider-unavailable responses, but must assert:

```text
not 501
contract envelope exists
no secrets/paths exposed
```

Frontend static/build tests:

```text
npm run build:vue passes
built ApplyPage bundle does not contain "This Vue shell does not call"
built ApplyPage bundle does not contain "use the legacy interface at /ui/apply" as primary text
```

If exact bundle text is hard to test, assert the source file changed instead:

```text
ApplyPage.vue does not contain the old read-only-only copy.
```

Run existing hardening tests to ensure no regression.

---

## Validation Commands

Run:

```bash
npm run build:vue
npm run css:build
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
http://127.0.0.1:8000/app/apply
```

Test:

```text
1. Page is no longer read-only.
2. Paste a realistic job description.
3. Click Score.
4. Score results appear.
5. Click Generate Questions.
6. Questions appear or a safe provider-unavailable error appears.
7. Fill answers if questions appear.
8. Click Generate Draft.
9. Task polling starts.
10. If task completes, browser navigates to /app/drafts/{draft_id}.
11. Draft detail page loads.
12. No automatic approval/submission happens.
```

Also verify fallback:

```text
http://127.0.0.1:8000/ui/apply
```

Expected:

```text
Legacy apply still works.
```

---

## Acceptance Criteria

This task is complete only if:

1. `/app/apply` is no longer read-only.
2. Vue can score/parse a job description through `/api/vue/apply/score`.
3. Vue can request clarifying questions through `/api/vue/apply/questions`.
4. Vue can start draft generation through `/api/vue/apply/draft`.
5. Vue can poll `/api/vue/apply/status/{task_id}`.
6. Vue navigates to `/app/drafts/{draft_id}` after successful completion.
7. No auto-generation happens before explicit user click.
8. No draft approval happens.
9. No application submission happens.
10. `/ui/apply` remains active.
11. `/api/vue/apply/*` responses use contract envelope.
12. Apply endpoints no longer return 501 except for unrelated intentionally deferred features.
13. Tests for Vue apply flow are added.
14. `npm run build:vue` passes.
15. Full `pytest` passes.
16. Settings/security hardening tests still pass.
17. No secrets/paths are exposed.
18. Vue Router base remains `/app`.
19. No legacy UI deletion happens.

---

## Forbidden Outcomes

Do not:

- remove /ui/apply
- redirect /ui/apply to Vue
- auto-generate draft on page load
- auto-submit application
- auto-approve draft
- send email
- mutate verified facts
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
4. frontend workflow implemented
5. commands run
6. `npm run build:vue` result
7. `npm run css:build` result
8. focused apply-flow test result
9. migration/security focused test result
10. full `pytest` result
11. manual validation result
12. known issues
13. recommended next step

Do not continue to Spec 023.
