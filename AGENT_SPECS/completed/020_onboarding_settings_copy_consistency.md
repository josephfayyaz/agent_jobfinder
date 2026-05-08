# 020 Onboarding Settings Copy Consistency

## Goal

Review and polish user-facing copy and compatibility wording around provider/settings status after the settings hardening passes.

Make wording consistent across:

```text
/settings/current
/ui/settings
/app/settings
legacy onboarding hydration
CLI settings display
docs
```

This task is copy/compatibility polish only.

No backend contract expansion.
No secrets.
No URLs.
No model names.
No local paths.
No new behavior.

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
```

Known current safe vocabulary:

```text
*_configured
*_available
artifacts_available
fact_sheet_configured
gmail_configured
secrets_exposed: false
paths_exposed: false
provider_status
providers
local_providers_available
remote_providers_configured
```

Known full-suite failures before this task:

```text
tests/test_frontend_null_guards.py::test_intake_js_has_null_guard_on_full_name
tests/test_frontend_null_guards.py::test_intake_js_has_null_guard_on_email
tests/test_temp_harness.py::test_temp_harness_bootstrap_does_not_hardcode_repo_root
```

Do not fix these in this task unless directly caused by this task.

---

## Purpose

After hardening, several surfaces may now display different but equivalent language for provider status.

This task should align wording so users see consistent, safe language.

Preferred wording examples:

```text
Configured
Not configured
Available
Unavailable
Local provider configured
Remote provider configured
Secrets are not exposed
Local paths are not exposed
Leave blank to keep the existing value
```

Avoid wording that suggests secrets or paths are shown:

```text
API key: ****
Token saved: ****
Client secret: configured as ****
Model: qwen...
Base URL: http://...
Artifact folder: /Users/...
```

---

## Hard Constraints

Do not expand `/settings/current`.

Do not reintroduce removed fields.

Do not expose provider URLs/base URLs.

Do not expose model names.

Do not expose client IDs.

Do not expose raw secrets.

Do not expose masked secrets.

Do not expose local filesystem paths.

Do not expose keyring values.

Do not expose environment values.

Do not change Vue `/app` serving strategy.

Do not change Vue Router base.

Do not remove `/ui/settings`.

Do not remove Jinja templates.

Do not remove legacy static JS unless a minimal wording-only update is needed.

Do not call LLMs.

Do not generate CV content.

Do not mutate business data.

Do not save provider settings as part of this task.

Do not add Docker.

Do not use Vuex.

Keep Pinia.

Do not use TypeScript.

---

## Required Investigation Before Editing

Inspect all relevant settings/onboarding surfaces:

```text
job_agent/routers/system.py
job_agent/cli.py
frontend/static/onboarding/hydrate.js
frontend/static/settings/
frontend/templates/settings.html
frontend/templates/partials/settings/
frontend/vue/src/pages/SettingsPage.vue
frontend/vue/src/pages/OnboardingPage.vue
docs/settings_current_hardening.md
docs/settings_public_contract_tightening.md
docs/legacy_ui_settings_surface_hardening.md
tests/
```

Search:

```bash
rg -n 'Configured|configured|Not configured|placeholder|Leave blank|API key|token|secret|password|base URL|Base URL|model|client id|client_id|artifact|folder|path|\*\*\*|sk-' job_agent frontend docs tests
```

Classify each result:

```text
safe copy
unsafe copy
test fixture
blocked-pattern list
documentation note
```

Only change unsafe or inconsistent user-facing copy.

---

## Files To Modify

Likely modify:

```text
frontend/templates/partials/settings/*.html
frontend/static/settings/*.js
frontend/static/onboarding/hydrate.js
frontend/vue/src/pages/SettingsPage.vue
frontend/vue/src/pages/OnboardingPage.vue
job_agent/cli.py
docs/*.md
tests/*.py
```

Add tests if needed:

```text
tests/test_settings_copy_consistency.py
```

Do not modify:

```text
frontend/vue/src/router/index.js
vite.config.js
job_agent/main.py
temp_mac_test/
```

Do not modify backend contracts unless a typo or copy value is clearly unsafe.

---

## Required Copy Rules

### Provider Status

Use:

```text
Configured
Not configured
Available
Unavailable
Local provider configured
Remote provider configured
```

Avoid:

```text
API key saved
Token present
Secret configured
Key configured
```

### Secret Inputs

Use:

```text
Leave blank to keep the existing value
```

Avoid:

```text
****
*** configured
sk-****
existing key hidden
```

### Local Provider Settings

Use:

```text
Local provider configured
Local provider available
```

Avoid:

```text
Base URL
localhost
127.0.0.1
port
model name
runtime model
```

### Artifact/Fact Sheet Status

Use:

```text
Generated files storage available
Fact sheet configured
```

Avoid:

```text
Artifact folder
Artifact path
Fact sheet path
/Users/...
```

### Security Notices

Use:

```text
No secret values are rendered.
No local paths are rendered.
Secrets are stored outside this page.
```

Avoid:

```text
Secrets are masked below.
The path is hidden.
Key value: ****
```

---

## Compatibility Requirements

Keep existing save/connect actions functional.

If legacy settings JS maps safe DOM field names back to backend save payload keys internally, preserve that behavior.

Do not remove form fields needed for user input.

Do not prefill sensitive fields.

Do not display current sensitive values.

Do not change backend save endpoint payloads unless already required by previous hardening specs.

This task is mostly wording and consistency.

---

## Tests Required

Add or update tests to cover copy consistency only if useful.

Recommended test file:

```text
tests/test_settings_copy_consistency.py
```

Minimum assertions if added:

```text
GET /ui/settings returns 200
GET /ui/settings contains safe copy:
- Leave blank to keep the existing value
- No Secret Values Rendered
- No Local Paths Rendered
GET /ui/settings does not contain:
- API key saved
- Token present
- Secret configured
- Base URL
- localhost
- 127.0.0.1
- model name
- Artifact folder
- Fact sheet path
- ***
- sk-
/settings/current still does not expose unsafe fields
/api/vue/settings still does not expose unsafe fields
```

Be careful:

- Do not fail safe documentation text inside unrelated docs unless it is rendered to users.
- Test rendered surfaces, not internal comments.
- Do not overconstrain copy if exact casing already differs safely.

---

## Documentation Required

Add or update:

```text
docs/settings_copy_consistency.md
```

Keep it concise.

Include:

```text
- purpose of copy consistency pass
- safe vocabulary
- surfaces reviewed
- statement that no contracts were expanded
- statement that no secrets/paths/URLs/models are exposed
```

Optionally update:

```text
docs/settings_public_contract_tightening.md
docs/legacy_ui_settings_surface_hardening.md
```

if wording changed.

---

## Validation Commands

Run:

```bash
npm run build:vue
```

Run:

```bash
npm run css:build
```

Run focused tests:

```bash
pytest tests/test_vue_api_contracts.py tests/test_vue_spa_serving.py tests/test_legacy_surface_hardening.py tests/test_settings_current_hardening.py tests/test_legacy_ui_settings_surface_hardening.py tests/test_settings_public_contract_tightening.py -v
```

If adding `tests/test_settings_copy_consistency.py`, include it:

```bash
pytest tests/test_settings_copy_consistency.py -v
```

Run full tests:

```bash
pytest
```

Do not fix unrelated known failures unless this task directly caused them.

---

## Manual Validation

Start backend using the project’s documented command.

Check:

```text
http://localhost:8000/ui/settings
http://localhost:8000/settings/current
http://localhost:8000/api/vue/settings
http://localhost:8000/app/settings
http://localhost:8000/app/onboarding
```

Expected:

```text
/ui/settings uses safe consistent copy
/app/settings uses safe consistent copy
/app/onboarding uses safe read-only onboarding copy
/settings/current remains small safe JSON
/api/vue/settings remains safe JSON
No secrets, paths, URLs, models, or masked values appear
```

---

## Acceptance Criteria

This task is complete only if:

1. Settings/onboarding user-facing copy is consistent.
2. `/ui/settings` remains active.
3. `/app/settings` remains active.
4. `/app/onboarding` remains active.
5. `/settings/current` remains tightened.
6. `/api/vue/settings` remains safe.
7. No provider URLs/base URLs are reintroduced.
8. No model names are reintroduced.
9. No raw secrets are rendered.
10. No masked secrets are rendered.
11. No local filesystem paths are rendered.
12. No backend contracts are expanded.
13. Existing save/connect compatibility is preserved.
14. `npm run build:vue` passes.
15. Focused tests pass.
16. Full pytest has no new failures beyond known pre-existing failures.
17. No Vue routing strategy is changed.
18. No business logic is changed.

---

## Forbidden Outcomes

Do not:

- reintroduce URL fields
- reintroduce model fields
- reintroduce client ID fields
- reintroduce artifact/fact-sheet paths
- show API keys
- show masked keys
- show tokens
- show secrets
- show keyring values
- show environment values
- show local filesystem paths
- remove /ui/settings
- redirect /ui/settings to Vue
- break /settings/current
- break /api/vue/settings
- break /app/settings
- break /app/onboarding
- change Vue Router base
- change /app bridge strategy
- remove Jinja templates
- remove legacy static JS
- call LLMs
- generate CV content
- mutate business data
- add Docker
- use Vuex
- add TypeScript

---

## Final Codex Response

Report:

1. files added
2. files modified
3. surfaces reviewed
4. unsafe/inconsistent copy found
5. copy changes made
6. compatibility impact
7. commands run
8. `npm run build:vue` result
9. focused test result
10. full `pytest` result
11. whether full-test failures are pre-existing or caused by this task
12. manual validation result
13. known issues
14. recommended next step

Do not continue to legacy cleanup/removal.
