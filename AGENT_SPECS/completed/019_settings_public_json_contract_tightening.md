# 019 Settings Public JSON Contract Tightening

## Goal

Tighten the remaining public JSON shape of:

```text
GET /settings/current
```

The previous tasks hardened obvious path and secret leaks, but the endpoint may still expose non-secret local provider implementation details such as local provider URLs, model names, or transport settings.

This task must align the public settings status surfaces around the same safe vocabulary:

```text
/settings/current
/api/vue/settings
/ui/settings
legacy onboarding/settings consumers
```

No secrets.
No masked secrets.
No local filesystem paths.
No keyring values.
No environment values.
No unnecessary local provider implementation details.

Keep compatibility with onboarding and legacy settings JavaScript.

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
```

Known hardened surfaces:

```text
/dashboard
/health
/settings/current
/ui/settings
/api/vue/settings
```

Known remaining issue from task 018:

```text
/settings/current still intentionally exposes some non-secret local provider configuration fields from the earlier contract.
```

This task decides which fields are safe to keep and removes anything that should not be public.

Known full-suite failures before this task:

```text
tests/test_frontend_null_guards.py::test_intake_js_has_null_guard_on_full_name
tests/test_frontend_null_guards.py::test_intake_js_has_null_guard_on_email
tests/test_temp_harness.py::test_temp_harness_bootstrap_does_not_hardcode_repo_root
```

Do not fix those in this task unless this task directly affects them.

---

## Purpose

Make the public settings JSON contract intentionally small and stable.

Preferred public vocabulary:

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
local_providers_available
remote_providers_configured
```

Avoid exposing internal implementation details unless the frontend needs them.

Examples of fields that should usually not be public:

```text
lm_studio_url
lm_studio_base_url
ollama_url
ollama_base_url
openai_model
anthropic_model
gemini_model
local_model
model_name
provider_url
base_url
host
port
timeout
transport
```

If a UI needs to display a provider/model value, prefer a safe label/status:

```text
lm_studio_configured: true
lm_studio_available: true
active_provider_label: "Local provider configured"
```

Do not expose raw local URLs or exact model identifiers unless an existing UI flow truly requires them.

---

## Hard Constraints

Do not remove `/settings/current`.

Do not redirect `/settings/current` to Vue.

Do not break onboarding/settings flows.

Do not remove `/ui/settings`.

Do not remove Jinja templates.

Do not remove legacy static JavaScript.

Do not remove HTMX.

Do not remove Alpine.

Do not remove `/ui/*` routes.

Do not remove `/api/*` routes.

Do not remove `/api/vue/*` routes.

Do not change the Vue `/app` SPA serving strategy.

Do not change Vue Router base.

Do not call LLMs.

Do not generate CV content.

Do not mutate business data except normal read-only status computation.

Do not reset/delete workspace data.

Do not create backups.

Do not expose secrets.

Do not expose masked secrets.

Do not expose absolute local filesystem paths.

Do not expose keyring values.

Do not expose environment variable values.

Do not add Docker.

Do not use Vuex.

Keep Pinia.

Do not use TypeScript.

---

## Required Investigation Before Editing

Inspect current settings payload and all consumers.

Run/search:

```bash
rg -n 'settings/current|lm_studio|ollama|base_url|provider_url|model|api_key|token|secret|password|credential|keyring|artifacts_available|fact_sheet_configured|configured' job_agent frontend tests docs
rg -n 'fetch\(|apiFetch|vueApiFetch|settings/current|openai_configured|lm_studio_configured|ollama_configured' frontend
```

Inspect likely files:

```text
job_agent/routers/system.py
job_agent/cli.py
frontend/static/settings/
frontend/static/onboarding/hydrate.js
frontend/templates/settings.html
frontend/templates/partials/settings/
tests/test_settings_current_hardening.py
tests/test_legacy_ui_settings_surface_hardening.py
tests/test_user_settings.py
tests/test_gmail_setup.py
docs/settings_current_hardening.md
docs/legacy_ui_settings_surface_hardening.md
```

Use TestClient or curl to inspect current `/settings/current` JSON.

Document the current fields before changing them.

---

## Files To Modify

Likely modify:

```text
job_agent/routers/system.py
job_agent/cli.py
frontend/static/settings/*.js
frontend/static/onboarding/hydrate.js
tests/*.py
docs/*.md
```

Add tests:

```text
tests/test_settings_public_contract_tightening.py
```

Optional documentation:

```text
docs/settings_public_contract_tightening.md
```

Do not modify:

```text
frontend/vue/src/router/index.js
vite.config.js
temp_mac_test/
```

Do not modify Vue pages unless absolutely required, which should not be necessary.

---

## Public Contract Rules

`GET /settings/current` must expose only public status fields.

Allowed field families:

```text
ok
providers
provider_status
*_configured
*_available
*_enabled
artifacts_available
fact_sheet_configured
gmail_configured
secrets_exposed
paths_exposed
local_providers_available
remote_providers_configured
```

Disallowed field families:

```text
*_api_key
*_token
*_secret
*_password
*_credential
*_key
*_path
*_dir
*_home
*_root
*_url
*_base_url
*_endpoint
*_host
*_port
*_model
model_name
provider_url
base_url
keyring
env
environment
```

Exception:

- A generic provider label like `"LM Studio"` or `"Ollama"` is allowed.
- Boolean availability/configuration status is allowed.
- Do not expose exact local URLs, ports, models, or filesystem paths.

---

## Required Response Shape Strategy

Prefer a small response shape such as:

```json
{
  "ok": true,
  "providers": [
    {
      "name": "lm_studio",
      "label": "LM Studio",
      "configured": true,
      "available": true,
      "local": true
    },
    {
      "name": "openai",
      "label": "OpenAI",
      "configured": false,
      "available": false,
      "local": false
    }
  ],
  "artifacts_available": true,
  "fact_sheet_configured": true,
  "gmail_configured": false,
  "secrets_exposed": false,
  "paths_exposed": false
}
```

Actual response shape may follow the existing project style, but it must not expose disallowed fields.

Do not expose masked secret values.

Do not expose exact local provider URLs or model names.

---

## Compatibility Requirements

Preserve legacy consumers by updating them to use safe fields.

If code previously relied on:

```text
lm_studio_url
ollama_url
openai_model
anthropic_model
gemini_model
```

replace UI behavior with safe status text:

```text
LM Studio configured
Ollama configured
Remote provider configured
```

If an actual edit form needs default values, do not prefill exact current URL/model values in public HTML/JSON.

Use empty fields or safe placeholder text such as:

```text
Leave blank to keep existing value
Configured
Not configured
```

Do not keep deprecated unsafe fields for compatibility.

Security wins over unsafe compatibility.

---

## Tests Required

Add:

```text
tests/test_settings_public_contract_tightening.py
```

Use existing FastAPI TestClient/app fixture conventions.

Minimum tests:

```text
GET /settings/current returns 200
GET /settings/current returns JSON
GET /settings/current contains safe configured/available booleans
GET /settings/current contains secrets_exposed=false
GET /settings/current contains paths_exposed=false
GET /settings/current does not contain API-key/token/secret/password/credential fields
GET /settings/current does not contain path/dir/home/root fields
GET /settings/current does not contain url/base_url/endpoint/host/port fields
GET /settings/current does not contain model/model_name fields
GET /settings/current does not contain absolute local filesystem path values
GET /settings/current does not contain raw or masked secret-like values
GET /ui/settings still returns safe legacy HTML
GET /api/vue/settings still returns safe Vue settings JSON
GET /app/settings still serves Vue
```

Add recursive JSON scanning helpers.

Unsafe key patterns:

```text
api_key
token
secret
password
credential
private_key
access_key
refresh_token
keyring
env
environment
path
file_path
absolute_path
artifacts_dir
fact_sheet_path
url
base_url
endpoint
host
port
model
model_name
```

Allowed safe keys:

```text
secrets_exposed
paths_exposed
configured
available
enabled
providers
provider_status
local
label
name
ok
```

Unsafe value patterns:

```text
/Users/
/home/
/var/
/tmp/
~/ 
file:
http://localhost
http://127.0.0.1
localhost:
127.0.0.1:
sk-
****
gpt-
claude-
gemini-
qwen
llama
```

Be careful:

- Do not fail ordinary route paths.
- Do not fail the provider label `LM Studio`.
- Do not fail provider name `lm_studio`.
- Do not fail boolean flags.
- Do not fail documentation text; tests should inspect endpoint responses.

Update existing tests only if they assert now-removed unsafe public fields.

---

## Documentation Required

Add:

```text
docs/settings_public_contract_tightening.md
```

Keep it concise.

Include:

```text
- purpose of tightening pass
- endpoint tightened: /settings/current
- unsafe field families removed
- safe replacement vocabulary
- compatibility notes
- statement that /ui/settings remains active
- statement that /app Vue bridge remains unchanged
```

Optionally update:

```text
docs/settings_current_hardening.md
docs/legacy_ui_settings_surface_hardening.md
docs/legacy_surface_hardening.md
```

to mention this final public settings contract tightening.

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
http://localhost:8000/settings/current
http://localhost:8000/ui/settings
http://localhost:8000/api/vue/settings
http://localhost:8000/app/settings
```

Expected:

```text
/settings/current returns small safe public JSON
/settings/current does not expose URLs/models/paths/secrets
/ui/settings remains safe legacy HTML
/api/vue/settings remains safe JSON
/app/settings serves Vue
```

---

## Acceptance Criteria

This task is complete only if:

1. `/settings/current` still exists.
2. `/settings/current` returns JSON.
3. `/settings/current` does not expose raw secrets.
4. `/settings/current` does not expose masked secrets.
5. `/settings/current` does not expose absolute local filesystem paths.
6. `/settings/current` does not expose local provider URLs/base URLs.
7. `/settings/current` does not expose local or remote model names.
8. `/settings/current` exposes safe configured/available/status fields instead.
9. `/ui/settings` remains functional and safe.
10. `/api/vue/settings` remains safe.
11. `/app/settings` still serves Vue.
12. Tests for public settings contract tightening are added.
13. Focused tests pass.
14. `npm run build:vue` passes.
15. Full pytest has no new failures beyond known pre-existing failures.
16. No Jinja templates are removed.
17. No legacy static JS is removed unless a minimal safe-field consumer update is necessary.
18. No Vue routing strategy is changed.
19. No backend business logic beyond response sanitization is changed.

---

## Forbidden Outcomes

Do not:

- remove /settings/current
- redirect /settings/current to Vue
- expose URLs/base URLs
- expose host/port
- expose model names
- expose artifacts_dir
- expose fact_sheet_path
- expose masked API keys
- expose raw API keys
- expose tokens
- expose secrets
- expose keyring values
- expose environment variable values
- expose absolute paths
- break /ui/settings
- break /api/vue/settings
- break /app/settings
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
3. endpoint audited
4. unsafe fields found
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
