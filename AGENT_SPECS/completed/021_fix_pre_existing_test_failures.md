# 021 Fix Pre Existing Test Failures

## Goal

Fix the three known pre-existing test failures that remained throughout the Vue migration and hardening work.

Known failures:

```text
tests/test_frontend_null_guards.py::test_intake_js_has_null_guard_on_full_name
tests/test_frontend_null_guards.py::test_intake_js_has_null_guard_on_email
tests/test_temp_harness.py::test_temp_harness_bootstrap_does_not_hardcode_repo_root
```

This task must be a narrow cleanup task.

Do not continue Vue migration.
Do not remove legacy UI.
Do not refactor unrelated systems.
Do not change backend business logic except if strictly required by the failing tests, which is unlikely.

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
```

Current expected project behavior:

```text
Vue app is served under /app
Legacy /ui/* is still active
/api/* and /api/vue/* are protected
/settings/current is hardened
/ui/settings is hardened
```

These three tests were failing before this task and should now be fixed.

---

## Hard Constraints

Do not modify Vue route strategy.

Do not change Vue Router base.

Do not change Vite base.

Do not change the `/app` SPA bridge.

Do not remove Jinja templates.

Do not remove legacy static JavaScript.

Do not remove HTMX.

Do not remove Alpine.

Do not remove `/ui/*` routes.

Do not remove `/api/*` routes.

Do not remove `/api/vue/*` routes.

Do not change settings hardening contracts.

Do not expose secrets.

Do not expose local filesystem paths.

Do not call LLMs.

Do not generate CV content.

Do not mutate business data.

Do not reset/delete workspace data.

Do not create backups.

Do not add Docker.

Do not use Vuex.

Keep Pinia.

Do not use TypeScript.

---

## Required Investigation Before Editing

Inspect the failing tests first.

Run:

```bash
pytest tests/test_frontend_null_guards.py tests/test_temp_harness.py -v
```

Inspect:

```text
tests/test_frontend_null_guards.py
tests/test_temp_harness.py
frontend/static/onboarding/intake.js
temp_mac_test/bootstrap.sh
temp_mac_test/
```

Search:

```bash
rg -n 'full-name|email|getElementById|optional chaining|BOOTSTRAP|hardcode|/Users/|Local_LLM|temp_mac_test' tests frontend/static/onboarding temp_mac_test
```

Before modifying anything, understand exactly what each test asserts.

Do not guess.

---

## Files To Modify

Likely modify:

```text
frontend/static/onboarding/intake.js
temp_mac_test/bootstrap.sh
```

Possibly modify tests only if the tests are clearly wrong.

But default preference:

```text
fix source files, not tests
```

Do not modify:

```text
frontend/vue/
vite.config.js
job_agent/main.py
job_agent/routers/
frontend/templates/
AGENT_SPECS/completed/
```

unless investigation proves it is absolutely necessary, which is unlikely.

---

## Failure 1 And 2: Null Guards In intake.js

Failing tests:

```text
tests/test_frontend_null_guards.py::test_intake_js_has_null_guard_on_full_name
tests/test_frontend_null_guards.py::test_intake_js_has_null_guard_on_email
```

Expected issue:

```text
frontend/static/onboarding/intake.js reads DOM elements full-name and email without optional chaining or safe null guards.
```

Required fix:

Update `frontend/static/onboarding/intake.js` so DOM reads for:

```text
full-name
email
```

are null-safe.

Preferred style:

```js
const fullName = document.getElementById("full-name")?.value || "";
const email = document.getElementById("email")?.value || "";
```

or equivalent safe guards if the file’s existing style requires it.

Rules:

```text
- Do not rewrite the whole intake flow.
- Do not change onboarding business behavior.
- Do not change endpoint calls.
- Do not change field names.
- Do not remove existing validation.
- Only make DOM reads null-safe.
```

If there are multiple reads of the same elements, make all relevant reads safe.

Acceptance for this part:

```bash
pytest tests/test_frontend_null_guards.py -v
```

must pass.

---

## Failure 3: temp_mac_test Bootstrap Hardcoded Repo Root

Failing test:

```text
tests/test_temp_harness.py::test_temp_harness_bootstrap_does_not_hardcode_repo_root
```

Expected issue:

```text
temp_mac_test/bootstrap.sh contains a hardcoded local repository path, likely something like /Users/.../Local_LLM/temp_mac_test or another absolute path.
```

Required fix:

Update `temp_mac_test/bootstrap.sh` so it computes paths relative to the script location or current repository root.

Preferred shell pattern:

```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
```

Then use:

```bash
"${SCRIPT_DIR}"
"${REPO_ROOT}"
```

instead of hardcoded absolute paths.

Rules:

```text
- Do not hardcode /Users/... paths.
- Do not hardcode a developer machine path.
- Do not change unrelated harness behavior.
- Keep script executable if it was executable before.
- Preserve existing env variable behavior if present.
```

Acceptance for this part:

```bash
pytest tests/test_temp_harness.py -v
```

must pass.

---

## Tests Required

Run focused tests:

```bash
pytest tests/test_frontend_null_guards.py tests/test_temp_harness.py -v
```

Run migration safety tests:

```bash
pytest tests/test_vue_api_contracts.py tests/test_vue_spa_serving.py tests/test_legacy_surface_hardening.py tests/test_settings_current_hardening.py tests/test_legacy_ui_settings_surface_hardening.py tests/test_settings_public_contract_tightening.py tests/test_settings_copy_consistency.py -v
```

If some listed test files do not exist, run the existing subset and report exactly which files were absent.

Run build checks:

```bash
npm run build:vue
npm run css:build
```

Run full suite:

```bash
pytest
```

Expected final full pytest result:

```text
all tests pass
```

If any tests still fail, they must be new and must be fixed unless clearly unrelated to this task. Report honestly.

---

## Manual Validation

No full browser validation is required for this cleanup.

But verify:

```text
- onboarding legacy JS still loads syntactically
- temp_mac_test/bootstrap.sh no longer contains hardcoded local absolute paths
```

Useful checks:

```bash
node --check frontend/static/onboarding/intake.js
bash -n temp_mac_test/bootstrap.sh
rg -n '/Users/|Local_LLM|temp_mac_test' temp_mac_test/bootstrap.sh
```

The last grep should not find a hardcoded absolute repo path. If it finds legitimate relative references, explain them.

---

## Acceptance Criteria

This task is complete only if:

1. `tests/test_frontend_null_guards.py` passes.
2. `tests/test_temp_harness.py` passes.
3. `frontend/static/onboarding/intake.js` safely reads `full-name`.
4. `frontend/static/onboarding/intake.js` safely reads `email`.
5. `temp_mac_test/bootstrap.sh` no longer hardcodes a local repo root.
6. `temp_mac_test/bootstrap.sh` computes paths dynamically.
7. Vue migration focused tests still pass.
8. Settings/security focused tests still pass.
9. `npm run build:vue` passes.
10. Full `pytest` passes, or any remaining failure is clearly unrelated and reported.
11. No Vue route strategy changed.
12. No backend business logic changed.
13. No legacy UI removal happened.
14. No secrets or paths were exposed.

---

## Forbidden Outcomes

Do not:

- rewrite onboarding intake flow
- change onboarding backend endpoints
- change field IDs
- remove validation
- hardcode another local path
- modify Vue Router base
- modify Vite base
- change /app bridge
- remove /ui routes
- remove Jinja templates
- remove legacy static JS
- call LLMs
- generate CV content
- mutate business data
- expose secrets
- expose local paths
- add Docker
- use Vuex
- add TypeScript
- start legacy cleanup/removal

---

## Final Codex/Claude Response

Report:

1. files added
2. files modified
3. root cause of each failing test
4. exact fixes made
5. commands run
6. focused failing-test result
7. migration/security focused test result
8. `npm run build:vue` result
9. `npm run css:build` result
10. full `pytest` result
11. manual/syntax validation result
12. known issues
13. recommended next step

Do not continue to refactoring or legacy cleanup.
