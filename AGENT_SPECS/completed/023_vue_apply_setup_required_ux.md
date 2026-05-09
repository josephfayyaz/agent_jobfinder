# 023 Vue Apply Setup Required UX

## Goal

Improve the Vue `/app/apply` user experience when the backend returns:

```text
setup_required
```
![img.png](img.png)
The Vue apply flow is now functional, but in an incomplete local setup it returns a generic error block:

```json
{
  "ok": false,
  "contract_version": 1,
  "error": {
    "code": "setup_required",
    "message": "Finish the quick setup first so Job Agent has a candidate profile and target roles."
  }
}
```

This task must add a clear setup-required UX to `/app/apply`.

Do not bypass the backend setup gate.

Do not generate drafts without setup.

Do not modify the apply backend workflow except if needed to preserve the existing contract error shape.

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
```

Current expected behavior:

```text
/app/apply is active
POST /api/vue/apply/score works
POST /api/vue/apply/questions works
POST /api/vue/apply/draft works
GET /api/vue/apply/status/{task_id} works
In incomplete setup, /api/vue/apply/score returns setup_required
/ui/apply remains active as rollback
```

---

## Hard Constraints

Do not bypass setup checks.

Do not create fake candidate/profile data.

Do not seed target roles.

Do not auto-generate drafts.

Do not auto-submit applications.

Do not approve drafts.

Do not send emails.

Do not mutate verified facts.

Do not remove `/ui/apply`.

Do not redirect `/ui/apply`.

Do not remove Jinja templates.

Do not remove legacy static JS.

Do not change Vue Router base.

Do not change Vite base.

Do not change `/app` SPA bridge.

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
frontend/vue/src/router/index.js
frontend/vue/src/api/client.js
job_agent/routers/vue_api.py
tests/test_vue_apply_flow.py
tests/test_vue_spa_serving.py
```

Search:

```bash
rg -n "setup_required|setup required|errorMessage|ApplyPage|router.push|/onboarding|/settings|/ui/apply" frontend/vue job_agent tests
```

Run baseline:

```bash
pytest tests/test_vue_apply_flow.py -v
```

If baseline fails, stop and report.

---

## Files To Modify

Likely modify:

```text
frontend/vue/src/pages/ApplyPage.vue
tests/test_vue_apply_flow.py
```

Optional:

```text
tests/test_vue_apply_setup_required_ux.py
```

Only add a new test file if cleaner than extending `tests/test_vue_apply_flow.py`.

Do not modify:

```text
job_agent/routers/vue_api.py
frontend/vue/src/router/index.js
vite.config.js
job_agent/main.py
frontend/templates/
frontend/static/
temp_mac_test/
```

unless investigation proves strictly necessary.

Default expectation:

```text
This is frontend UX + tests only.
```

---

## UX Requirements

When any Vue apply endpoint returns a contract error with:

```text
error.code === "setup_required"
```

the page must show a dedicated setup-required panel, not just a generic error.

The panel must include:

```text
Title: Setup required before applying
Message: Use the setup flow to create a candidate profile and choose target roles before generating a tailored CV draft.
Primary button/link: Go to Onboarding
Secondary button/link: Open Settings
Small fallback link: Legacy apply fallback
```

Vue routes:

```text
Go to Onboarding -> /onboarding
Open Settings -> /settings
```

Because Vue Router base is `/app`, these must result in browser URLs:

```text
/app/onboarding
/app/settings
```

Use:

```vue
<RouterLink to="/onboarding">Go to Onboarding</RouterLink>
<RouterLink to="/settings">Open Settings</RouterLink>
```

or equivalent `router.push("/onboarding")`.

Do not use:

```js
window.location.href = "/app/onboarding"
window.location.href = "/ui/onboarding"
```

Legacy fallback may use a normal anchor:

```html
<a href="/ui/apply">Legacy apply fallback</a>
```

---

## Behavior Requirements

When `setup_required` happens:

```text
- show setup-required panel
- preserve the pasted job description in the textarea
- do not clear score/question/draft state unless necessary
- stop loading indicators
- do not continue to questions
- do not call draft generation
- do not start polling
```

Generic errors should still use the existing error block.

Only `setup_required` should show the special panel.

If the user edits the job description after a setup-required error, keep the panel visible until they retry or navigate away. This is acceptable.

---

## Copy Requirements

Use clear, non-technical copy:

```text
Setup required before applying
Use the setup flow to create a candidate profile and choose target roles before generating a tailored CV draft.
```

Do not mention:

```text
backend gate
contract error
501
LLM internals
provider URLs
model names
secrets
paths
```

---

## Tests Required

Update or add tests for:

```text
ApplyPage.vue contains setup-required UX copy
ApplyPage.vue links to /onboarding with RouterLink or safe router navigation
ApplyPage.vue links to /settings with RouterLink or safe router navigation
ApplyPage.vue does not redirect setup_required to /ui/onboarding
ApplyPage.vue keeps /ui/apply only as legacy fallback
tests/test_vue_apply_flow.py still passes
```

If backend tests can simulate setup_required cheaply, add/extend a TestClient assertion:

```text
POST /api/vue/apply/score in incomplete setup returns code setup_required
response is contract envelope
response does not expose secrets/paths
```

Do not make tests depend on live external provider or LLM.

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

Start dev mode or FastAPI-served app.

Dev:

```bash
npm run dev:vue
```

Open:

```text
http://127.0.0.1:5173/app/apply
```

Production-like:

```bash
npm run build:vue
npm run css:build
uvicorn job_agent.main:app --host 127.0.0.1 --port 8000 --reload
```

Open:

```text
http://127.0.0.1:8000/app/apply
```

Manual test in an incomplete setup:

```text
1. Paste a job description.
2. Click Score.
3. Confirm setup-required panel appears.
4. Confirm job description remains in textarea.
5. Click Go to Onboarding.
6. Confirm browser goes to /app/onboarding.
7. Return to /app/apply.
8. Click Open Settings.
9. Confirm browser goes to /app/settings.
10. Confirm legacy fallback still points to /ui/apply.
```

---

## Acceptance Criteria

This task is complete only if:

1. `/app/apply` shows dedicated setup-required UX when backend returns setup_required.
2. The setup-required panel has a link/button to Vue onboarding.
3. The setup-required panel has a link/button to Vue settings.
4. The setup-required panel keeps `/ui/apply` only as fallback.
5. The page does not redirect to `/ui/onboarding`.
6. The page does not bypass setup checks.
7. The pasted job description remains visible after setup_required.
8. No draft generation starts after setup_required.
9. No polling starts after setup_required.
10. `npm run build:vue` passes.
11. Full `pytest` passes.
12. No backend business logic changes.
13. No Vue Router base changes.
14. No legacy UI deletion happens.

---

## Forbidden Outcomes

Do not:

- bypass setup_required
- create fake setup state
- seed candidate/profile data
- auto-generate draft
- auto-submit application
- auto-approve draft
- send email
- remove /ui/apply
- redirect /ui/apply
- redirect setup_required to /ui/onboarding
- use window.location.href for Vue routes
- expose secrets
- expose local paths
- expose provider URLs or model names
- change Vue Router base
- change Vite base
- change /app bridge
- remove Jinja templates
- remove legacy static JS
- use Vuex
- add TypeScript
- add Docker
- continue to draft-action migration

---

## Final Codex Response

Report:

1. files added
2. files modified
3. setup-required UX implemented
4. commands run
5. `npm run build:vue` result
6. `npm run css:build` result
7. focused apply-flow test result
8. migration/security focused test result
9. full `pytest` result
10. manual validation result
11. known issues
12. recommended next step

Do not continue to Spec 024.
