# 018 Legacy UI Settings Surface Hardening

## Goal

Harden the server-rendered legacy settings UI surface, especially:

```text
/ui/settings
```

The previous task hardened the JSON endpoint:

```text
GET /settings/current
```

This task must harden the legacy server-rendered settings page/context so it uses the same safe status vocabulary and does not expose paths, raw secrets, masked secrets, keyring values, or environment values.

Keep `/ui/settings` active.

Do not remove legacy UI yet.

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
```

Known hardened surfaces:

```text
/dashboard
/health
/settings/current
/api/vue/settings
```

Known remaining issue from task 017:

```text
Legacy /ui/settings server-rendered page/context may still expose artifact-folder display and provider placeholder/secret-like behavior.
```

Known full-suite failures before this task:

```text
tests/test_frontend_null_guards.py::test_intake_js_has_null_guard_on_full_name
tests/test_frontend_null_guards.py::test_intake_js_has_null_guard_on_email
tests/test_temp_harness.py::test_temp_harness_bootstrap_does_not_hardcode_repo_root
```

Do not fix those in this task unless this task directly affects them.

---

## Purpose

Make the legacy `/ui/settings` surface consistent with the hardened settings vocabulary introduced in task 017.

Use safe booleans/status fields such as:

```text
artifacts_available
fact_sheet_configured
openai_configured
gemini_configured
anthropic_configured
lm_studio_configured
ollama_configured
gmail_oauth_configured
gmail_legacy_configured
gmail_configured
secrets_exposed: false
paths_exposed: false
```

Do not expose:

```text
artifact folders
absolute local paths
raw secrets
masked secrets
keyring values
environment values
secret-shaped placeholders
```

---

## Hard Constraints

Do not remove `/ui/settings`.

Do not redirect `/ui/settings` to Vue.

Do not remove Jinja templates.

Do not remove legacy static JavaScript.

Do not remove HTMX.

Do not remove Alpine.

Do not remove `/ui/*` routes.

Do not remove `/settings/current`.

Do not remove `/api/*` routes.

Do not remove `/api/vue/*` routes.

Do not change the Vue `/app` SPA serving strategy.

Do not change Vue Router base.

Do not call LLMs.

Do not generate CV content.

Do not mutate business data except normal settings page rendering.

Do not save provider settings unless an existing user-submitted form explicitly does so; this task is about render/context hardening.

Do not reset/delete workspace data.

Do not create backups.

Do not expose secrets.

Do not expose masked secrets.

Do not expose absolute local filesystem paths.

Do not add Docker.

Do not use Vuex.

Keep Pinia.

Do not use TypeScript.

---

## Required Investigation Before Editing

Inspect the legacy settings route, template, and JS consumers.

Run/search:

```bash
rg -n 'ui/settings|settings.html|TemplateResponse|settings/current|artifacts_dir|fact_sheet_path|api_key|token|secret|password|credential|keyring|masked|placeholder|configured' job_agent frontend tests docs
rg -n 'settings' frontend/templates frontend/static job_agent/routers tests
```

Inspect likely files:

```text
job_agent/routers/
job_agent/services/
frontend/templates/settings.html
frontend/static/settings.js
frontend/static/onboarding/hydrate.js
tests/
docs/settings_current_hardening.md
docs/legacy_surface_hardening.md
```

Identify:

```text
- route handler for /ui/settings
- template context passed to settings.html
- fields rendered by settings.html
- JS that reads settings context or /settings/current
- tests asserting legacy settings page behavior
```

Do not assume exact file locations.

---

## Files To Modify

Likely modify:

```text
job_agent/routers/*.py
frontend/templates/settings.html
frontend/static/settings.js
tests/*.py
```

Add tests:

```text
tests/test_legacy_ui_settings_surface_hardening.py
```

Optional documentation:

```text
docs/legacy_ui_settings_surface_hardening.md
```

Do not modify:

```text
frontend/vue/src/router/index.js
vite.config.js
temp_mac_test/
```

Do not modify Vue pages unless required by tests, which should not be necessary.

---

## Sanitization Rules

The server-rendered `/ui/settings` HTML and its context must not expose keys or rendered text containing unsafe field names or values.

Unsafe field names:

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
artifacts_dir
fact_sheet_path
```

Allowed safe status names:

```text
secrets_exposed
paths_exposed
artifacts_available
fact_sheet_configured
openai_configured
gemini_configured
anthropic_configured
lm_studio_configured
ollama_configured
gmail_oauth_configured
gmail_legacy_configured
gmail_configured
configured
available
enabled
```

Unsafe rendered values:

```text
/Users/name/...
/home/name/...
/var/...
/tmp/...
~/...
file:///...
sk-****
****abcd
lmstudio-token
openai-api-key
anthropic-key
```

Do not render masked secrets either.

If a user-facing label currently says something like "API key: ****abcd", replace it with safe status language:

```text
OpenAI configured: Yes
Gemini configured: No
```

---

## Required Behavior

### `/ui/settings`

The legacy settings page must still render.

It may show:

```text
provider configured status
local provider availability
artifact availability
fact sheet configured status
Gmail configured status
safe setup status
```

It must not show:

```text
artifact folder
fact sheet path
raw key values
masked key values
secret placeholders
keyring names/values
environment variable names/values
absolute local paths
```

If forms exist for user-submitted provider settings, keep them functional only if they already existed.

However:

- Do not prefill inputs with raw or masked secrets.
- Do not render secret values into the DOM.
- Password/API key inputs should be empty placeholders such as "Leave blank to keep existing value" if the existing UI requires a field.
- Do not include existing secret values in HTML attributes.

---

## Compatibility Requirements

Use the same safe vocabulary as `/settings/current`:

```text
*_configured
artifacts_available
fact_sheet_configured
secrets_exposed: false
paths_exposed: false
```

If old template logic expected `artifacts_dir`, change it to use `artifacts_available`.

If old template logic expected masked API keys, change it to use `*_configured`.

If old JS expected unsafe fields, change it to use safe fields.

Do not keep deprecated unsafe fields for compatibility.

Security wins over unsafe compatibility.

---

## Tests Required

Add:

```text
tests/test_legacy_ui_settings_surface_hardening.py
```

Use existing FastAPI TestClient/app fixture conventions.

Minimum tests:

```text
GET /ui/settings returns 200
GET /ui/settings returns HTML
GET /ui/settings does not contain artifacts_dir
GET /ui/settings does not contain fact_sheet_path
GET /ui/settings does not contain absolute local filesystem paths
GET /ui/settings does not contain masked secret-looking values
GET /ui/settings does not contain raw secret-looking values
GET /ui/settings does not render API key/token/password/secret field names except safe explanatory text if unavoidable
GET /settings/current remains hardened
GET /api/vue/settings remains hardened
GET /app/settings still serves Vue
```

Add a helper that scans rendered HTML for unsafe patterns.

Unsafe value patterns:

```text
/Users/
/home/
/var/
/tmp/
~/ 
file:
sk-
****abcd
```

Be careful:

- Do not fail normal URLs solely because they contain `/`.
- Do not fail route paths like `/ui/settings` or `/app/settings`.
- Do not fail safe words like `secrets_exposed` and `paths_exposed` if they appear in JSON tests.
- For HTML, prefer checking explicit dangerous substrings.

Update existing tests only if they assert unsafe legacy behavior.

---

## Documentation Required

Add:

```text
docs/legacy_ui_settings_surface_hardening.md
```

Keep it concise.

Include:

```text
- purpose of hardening pass
- surface sanitized: /ui/settings
- unsafe fields/values removed
- safe replacement vocabulary
- compatibility notes
- statement that /ui/settings remains active
- statement that /app Vue bridge remains unchanged
```

Optionally update:

```text
docs/settings_current_hardening.md
docs/legacy_surface_hardening.md
```

to mention the legacy UI settings surface was handled.

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
pytest tests/test_vue_api_contracts.py tests/test_vue_spa_serving.py tests/test_legacy_surface_hardening.py tests/test_settings_current_hardening.py tests/test_legacy_ui_settings_surface_hardening.py -v
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
```

Expected:

```text
/ui/settings returns legacy HTML
/ui/settings does not expose artifact folder/path
/ui/settings does not expose raw or masked secrets
/settings/current remains hardened JSON
/api/vue/settings remains safe JSON
/app/settings serves Vue
```

---

## Acceptance Criteria

This task is complete only if:

1. `/ui/settings` still exists.
2. `/ui/settings` returns HTML.
3. `/ui/settings` does not expose `artifacts_dir`.
4. `/ui/settings` does not expose `fact_sheet_path`.
5. `/ui/settings` does not expose raw secrets.
6. `/ui/settings` does not expose masked secrets.
7. `/ui/settings` does not expose absolute local filesystem paths.
8. `/ui/settings` uses safe status vocabulary such as `*_configured` and `artifacts_available`.
9. `/settings/current` remains hardened.
10. `/api/vue/settings` remains hardened.
11. `/app/settings` still serves Vue.
12. Tests for legacy UI settings surface hardening are added.
13. Focused tests pass.
14. `npm run build:vue` passes.
15. Full pytest has no new failures beyond known pre-existing failures.
16. No Jinja templates are removed.
17. No legacy static JS is removed unless a minimal safe-field consumer update is necessary.
18. No Vue routing strategy is changed.
19. No backend business logic beyond response/template sanitization is changed.

---

## Forbidden Outcomes

Do not:

- remove /ui/settings
- redirect /ui/settings to Vue
- expose artifacts_dir
- expose fact_sheet_path
- expose masked API keys
- expose raw API keys
- expose tokens
- expose secrets
- expose keyring values
- expose environment variable values
- expose absolute paths
- prefill secret inputs with raw or masked values
- break /settings/current
- break /app/settings
- break /ui routes
- remove Jinja templates
- remove legacy static JS
- change /app SPA bridge strategy
- change Vue Router base
- call LLMs
- generate CV content
- mutate business data
- reset workspace
- delete workspace data
- create backups
- add Docker
- use Vuex
- add TypeScript

---

## Final Codex Response

Report:

1. files added
2. files modified
3. surface audited
4. unsafe fields/values found
5. sanitization changes made
6. compatibility updates made
7. commands run
8. `npm run build:vue` result
9. focused test result
10. full `pytest` result
11. whether full-test failures are pre-existing or caused by this task
12. manual validation result
13. known issues
14. recommended next step

Do not continue to legacy cleanup/removal.
