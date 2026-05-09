# 028 Vue Settings Mutations Migration

## Goal

Make the Vue `/app/settings` page fully functional for safe settings mutations.

Migrate the core legacy settings behavior into Vue:

```text
provider mode save
provider credential update with empty safe password fields
provider validation
local provider model discovery if supported
Gmail OAuth connect/disconnect
```

Keep legacy `/ui/settings` active as rollback.

This task is security-critical.

Do not expose raw secrets.
Do not expose masked secrets.
Do not expose local filesystem paths.
Do not expose provider URLs/model names through public status responses.
Do not regress the settings hardening work from specs 017–020.

---

## Current State

Completed specs include:

```text
001–027 completed or in-progress
022 Apply flow Vue migration completed
023 Apply setup-required UX completed
024 Draft actions completed
025 Draft metadata enrichment completed
026 Draft related navigation completed
027 Context detail routes should be completed before this task
```

Current expected behavior before this task:

```text
/app/settings is read-only/safe
/ui/settings has real legacy settings forms
/settings/current is hardened and tightened
/api/vue/settings is safe read-only
full pytest is green
```

Known safety vocabulary:

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

---

## Backend Reality To Verify

Before editing, inspect the actual existing backend routes and service logic.

Expected existing legacy/bare endpoints may include:

```text
POST /settings/save
POST /providers/validate
GET /lm-studio/models
GET /ollama/models
POST /gmail/oauth/start
POST /gmail/oauth/disconnect
POST /settings/reload
GET /settings/current
GET /api/vue/settings
```

Expected current Vue endpoint:

```text
GET /api/vue/settings
```

Likely missing Vue mutation endpoints:

```text
POST /api/vue/settings
POST /api/vue/providers/validate
GET /api/vue/providers/lm-studio/models
GET /api/vue/providers/ollama/models
POST /api/vue/gmail/oauth/start
POST /api/vue/gmail/oauth/disconnect
```

Do not assume exact legacy payloads. Inspect the real handlers first.

---

## Hard Constraints

Do not remove `/ui/settings`.

Do not redirect `/ui/settings` to Vue.

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

Do not call LLMs.

Do not generate CV content.

Do not submit applications.

Do not approve drafts.

Do not mutate verified facts.

Do not reset/delete workspace data.

Do not create backups.

Do not expose secrets.

Do not expose masked secrets.

Do not expose local filesystem paths.

Do not expose keyring values.

Do not expose environment values.

Do not expose provider URLs/model names/client IDs in public status responses.

Do not prefill API key/password fields with existing values.

Do not use Vuex.

Keep Pinia.

Do not add TypeScript.

Do not add Docker.

---

## Required Investigation Before Editing

Inspect:

```text
frontend/vue/src/pages/SettingsPage.vue
frontend/vue/src/api/client.js
job_agent/routers/vue_api.py
job_agent/routers/system.py
job_agent/routers/
job_agent/services/
frontend/templates/settings.html
frontend/templates/partials/settings/
frontend/static/settings/
tests/test_settings_current_hardening.py
tests/test_settings_public_contract_tightening.py
tests/test_legacy_ui_settings_surface_hardening.py
tests/test_settings_copy_consistency.py
tests/test_vue_api_contracts.py
```

Search:

```bash
rg -n "settings/save|providers/validate|lm-studio/models|ollama/models|gmail/oauth|settings/current|api/vue/settings" job_agent frontend tests
rg -n "api_key|token|secret|password|credential|keyring|base_url|model|client_id|configured|available|provider_status" job_agent frontend/vue frontend/static tests
```

Run baseline:

```bash
pytest
```

If baseline is not green, stop and report.

---

## Files To Modify

Likely modify:

```text
job_agent/routers/vue_api.py
frontend/vue/src/pages/SettingsPage.vue
tests/test_vue_settings_mutations.py
```

Possibly modify:

```text
frontend/vue/src/api/contracts.js
tests/test_vue_api_contracts.py
```

Only if useful and consistent with existing patterns.

Do not modify unless necessary:

```text
job_agent/main.py
frontend/vue/src/router/index.js
vite.config.js
frontend/templates/
frontend/static/settings/
temp_mac_test/
```

Default preference:

```text
Do not touch legacy /ui/settings implementation.
Add Vue-safe wrappers under /api/vue.
Keep legacy settings JS/forms as rollback.
```

---

## API Contract Requirements

All new `/api/vue/settings` and `/api/vue/providers/*` responses must use the existing Vue API envelope.

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

Do not return raw legacy response shapes if they do not match the Vue envelope.

Do not add global exception handlers.

Do not echo secrets in any response.

Every settings mutation response must include or preserve safe signals:

```text
secrets_exposed: false
paths_exposed: false
```

---

## Endpoint 1: POST /api/vue/settings

Add this endpoint.

Purpose:

```text
Save provider/settings updates from Vue.
```

Expected behavior:

```text
Delegate to existing settings-save logic or shared service logic.
Return only safe public status data.
```

Input should support the minimal safe settings update fields after inspection. Likely categories:

```text
provider_mode
remote provider credentials typed by user
local provider input fields typed by user
gmail/oauth-related safe toggles if already supported
workflow/search preferences if existing UI supports them
```

Important:

```text
API key/password fields may be submitted by the user.
They must never be echoed back.
Empty fields should mean "leave existing value unchanged" if legacy behavior supports that.
```

Response must not contain:

```text
api_key
token
secret
password
credential
keyring
env
environment
path
dir
url
base_url
host
port
model
client_id
raw/masked secret values
```

Response should contain safe status only:

```text
provider_status
providers
*_configured
*_available
gmail_configured
secrets_exposed: false
paths_exposed: false
```

---

## Endpoint 2: POST /api/vue/providers/validate

Add this endpoint.

Purpose:

```text
Validate the currently selected provider settings explicitly after user click.
```

Behavior:

```text
Delegate to existing /providers/validate logic or shared service logic.
Return a safe validation result.
```

Response data may include:

```json
{
  "valid": true,
  "provider": "openai",
  "message": "Provider configured"
}
```

Do not include:

```text
provider URL
model names
API key fragments
raw provider response bodies if they include sensitive data
```

If validation fails because provider is unavailable, return safe contract error or safe data:

```json
{
  "valid": false,
  "message": "Provider unavailable"
}
```

Do not require live external provider in tests.

---

## Endpoint 3: GET /api/vue/providers/lm-studio/models

Add only if safely supported.

Purpose:

```text
Discover local provider models for explicit user action.
```

Risk:

```text
Model names and local URLs were removed from public settings status in previous hardening specs.
```

Rules:

```text
- This endpoint may return model names only as a result of explicit model-discovery action.
- It must not be called automatically on page load.
- It must not expose base URL in response.
- It must not expose local paths.
- It must return safe provider-unavailable error if local service is unavailable.
```

If the project security posture should not expose model names at all, do not implement model listing; return safe `not_supported` contract response and document it.

---

## Endpoint 4: GET /api/vue/providers/ollama/models

Same rules as LM Studio model discovery.

Do not expose base URL in response.

Do not call automatically on page load.

---

## Endpoint 5: POST /api/vue/gmail/oauth/start

Add this endpoint.

Purpose:

```text
Start Gmail OAuth flow from Vue settings.
```

Behavior:

```text
Delegate to existing Gmail OAuth start logic.
Return only auth_url or a safe redirect target if the existing route uses redirects.
```

Response:

```json
{
  "auth_url": "..."
}
```

Safety:

```text
Do not include client_secret.
Do not include credentials.
Do not include token.
Do not include raw OAuth config.
```

If OAuth is not configured, return safe contract error.

---

## Endpoint 6: POST /api/vue/gmail/oauth/disconnect

Add this endpoint.

Purpose:

```text
Disconnect Gmail OAuth from Vue settings after explicit click.
```

Behavior:

```text
Delegate to existing Gmail disconnect logic.
Return safe public settings status.
```

Safety:

```text
Must be explicit click only.
Do not expose tokens.
Do not expose token file paths.
```

---

## Frontend Requirements: SettingsPage.vue

Replace read-only-only settings page with an editable Vue settings page.

Must include:

```text
Current safe status summary
Provider mode selection
Remote provider credential inputs
Local provider inputs if supported
Save settings button
Validate provider button
Optional explicit model discovery buttons
Gmail connect/disconnect section
Loading/error/success states
Read-safe security notice
```

Do not prefill secrets.

Sensitive inputs:

```text
type="password"
placeholder="Leave blank to keep the existing value"
autocomplete="off"
```

Do not render:

```text
raw keys
masked keys
token fragments
client secrets
paths
local URLs/model names from public status
```

If editable local provider URL/model fields are needed for saving, they may be blank inputs with safe labels. They must not be prefilled from `/settings/current`.

Allowed safe labels:

```text
Local provider configured
Remote provider configured
Configured
Not configured
Available
Unavailable
Leave blank to keep the existing value
No secret values are rendered
No local paths are rendered
```

Avoid unsafe labels:

```text
API key saved
Token present
Secret configured
Base URL shown from current settings
Model currently selected
```

---

## Frontend Behavior Rules

On mount:

```text
GET /api/vue/settings
```

Do not call:

```text
model discovery endpoints
provider validation endpoint
settings save endpoint
gmail oauth endpoints
```

without explicit user click.

Save flow:

```text
User edits fields -> clicks Save settings -> POST /api/vue/settings -> refresh safe status
```

Provider validation:

```text
User clicks Validate provider -> POST /api/vue/providers/validate -> show result
```

Model discovery:

```text
User clicks Discover models -> GET model endpoint -> show result or safe unavailable error
```

Gmail OAuth:

```text
User clicks Connect Gmail -> POST /api/vue/gmail/oauth/start -> if auth_url returned, navigate to it
User clicks Disconnect Gmail -> confirm -> POST /api/vue/gmail/oauth/disconnect
```

Navigation to OAuth `auth_url` may use `window.location.href` because it is an external OAuth flow.

Do not use `window.location.href` for Vue internal routes.

---

## Tests Required

Add:

```text
tests/test_vue_settings_mutations.py
```

Minimum backend contract tests:

```text
GET /api/vue/settings remains safe
POST /api/vue/settings returns contract envelope
POST /api/vue/settings response does not contain api_key/token/secret/password/credential/keyring/path/url/model/client_id fields
POST /api/vue/settings supports partial safe payload
POST /api/vue/providers/validate returns non-404/non-501 contract response
GET /api/vue/providers/lm-studio/models returns non-404 contract response or safe not_supported/provider_unavailable
GET /api/vue/providers/ollama/models returns non-404 contract response or safe not_supported/provider_unavailable
POST /api/vue/gmail/oauth/start returns safe auth_url or safe configuration error, never client_secret/token
POST /api/vue/gmail/oauth/disconnect returns safe contract response
```

Frontend source/build tests:

```text
SettingsPage.vue contains password inputs with safe placeholder
SettingsPage.vue does not contain hardcoded secret-shaped placeholder values
SettingsPage.vue does not prefill secret values
SettingsPage.vue does not call model discovery on mount
SettingsPage.vue does not use Vuex
SettingsPage.vue still uses vueApiFetch
```

Existing hardening tests must still pass:

```text
tests/test_settings_current_hardening.py
tests/test_settings_public_contract_tightening.py
tests/test_legacy_ui_settings_surface_hardening.py
tests/test_settings_copy_consistency.py
```

Avoid tests that require live external providers.

---

## Validation Commands

Run:

```bash
npm run build:vue
npm run css:build
pytest tests/test_vue_settings_mutations.py -v
pytest tests/test_vue_apply_flow.py -v
pytest tests/test_vue_draft_actions.py -v
pytest tests/test_vue_draft_metadata.py -v
pytest tests/test_vue_context_detail_routes.py -v
pytest tests/test_vue_api_contracts.py tests/test_vue_spa_serving.py tests/test_legacy_surface_hardening.py tests/test_settings_current_hardening.py tests/test_legacy_ui_settings_surface_hardening.py tests/test_settings_public_contract_tightening.py tests/test_settings_copy_consistency.py -v
pytest
```

If `tests/test_vue_context_detail_routes.py` does not exist because spec 027 was not run, skip it and report that clearly.

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
http://127.0.0.1:8000/app/settings
```

Test:

```text
1. Page loads safe status.
2. Secret fields are empty.
3. Secret fields use safe placeholder.
4. No keys/tokens/secrets/paths/URLs/model names are visible.
5. Save settings with a harmless partial payload.
6. Safe success message appears.
7. Validate provider returns safe result/error.
8. Model discovery only runs after explicit click.
9. Gmail connect shows OAuth redirect behavior or safe configuration error.
10. Gmail disconnect asks confirmation and returns safe status.
11. Legacy /ui/settings still loads.
```

Also verify:

```text
http://127.0.0.1:8000/settings/current
http://127.0.0.1:8000/api/vue/settings
http://127.0.0.1:8000/ui/settings
```

Expected:

```text
All remain safe.
```

---

## Acceptance Criteria

This task is complete only if:

1. `/app/settings` supports settings save through Vue.
2. `/app/settings` supports provider validation through Vue.
3. `/app/settings` supports Gmail OAuth start/disconnect through Vue or safe configuration errors.
4. Model discovery is available only through explicit click, or safely reported as not supported.
5. No secret fields are prefilled.
6. No raw secrets are rendered.
7. No masked secrets are rendered.
8. No local filesystem paths are rendered.
9. Public status responses do not reintroduce URLs/models/client IDs.
10. `/settings/current` remains tightened.
11. `/api/vue/settings` remains safe.
12. `/ui/settings` remains active.
13. Tests for Vue settings mutations are added.
14. `npm run build:vue` passes.
15. Full `pytest` passes.
16. Vue Router base remains `/app`.
17. No legacy UI deletion happens.

---

## Forbidden Outcomes

Do not:

- remove /ui/settings
- redirect /ui/settings to Vue
- expose API keys
- expose masked API keys
- expose tokens
- expose client secrets
- expose keyring values
- expose environment values
- expose filesystem paths
- expose provider URLs/base URLs in public status
- expose model names in public status
- prefill secret fields
- call model discovery on page load
- call provider validation on page load
- start Gmail OAuth on page load
- change /settings/current back to broad unsafe shape
- break /api/vue/settings
- change Vue Router base
- change Vite base
- change /app bridge
- remove Jinja templates
- remove legacy static JS
- call LLMs
- generate CV content
- mutate verified facts
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
3. backend endpoints added/upgraded
4. frontend settings mutations implemented
5. security/hardening protections preserved
6. commands run
7. `npm run build:vue` result
8. `npm run css:build` result
9. focused settings-mutation test result
10. apply/draft/context regression test result
11. migration/security focused test result
12. full `pytest` result
13. manual validation result
14. known issues
15. recommended next step

Do not continue to jobs/onboarding migration.
