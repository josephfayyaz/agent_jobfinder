# Task: Migrate Legacy Settings JavaScript into Vue Component-Based Settings Routes

## Goal

Migrate the legacy server-rendered settings behavior from:

- `settings.html`
- `static/provider_controller.js`
- `static/settings/core.js`
- `static/settings/provider.js`
- `static/settings/search.js`
- `static/settings/integrations.js`
- `static/settings/maintenance.js`
- `static/settings.js`

into Vue.

Create two separate Vue routes:

1. `/settings/ai-provider`
   - Only AI provider configuration and validation.

2. `/settings/workspace`
   - All non-provider settings:
     - job discovery roles
     - countries
     - job search languages
     - Gmail OAuth integration
     - CV/review thresholds
     - fact sheet / profile maintenance actions if already supported
     - workspace reset/delete maintenance actions
     - share link copy if currently available

The migration must be component-based and must separate logic from UI.

---

## Hard Constraints

Do not keep new behavior in global `window.SettingsApp`.

Do not use inline DOM querying such as:

```js
document.getElementById(...)
document.querySelector(...)
```

inside Vue pages/components except where absolutely unavoidable for browser APIs like clipboard.

Do not port the old files as one large Vue component.

Do not duplicate provider logic between onboarding and settings if shared provider helpers already exist or can be extracted.

Do not change backend behavior unless a Vue endpoint is missing and a minimal compatibility endpoint is required.

Use existing Vue API conventions in the project, especially:

- `frontend/vue/src/api/client.js`
- `vueApiFetch`
- existing router style
- existing page/component styling conventions

Preserve existing backend endpoints where possible:

- `POST /settings/save`
- `POST /providers/validate`
- `GET /lm-studio/models`
- `GET /ollama/models`
- `GET /search/preferences/recommendations`
- `POST /gmail/oauth/start`
- `POST /gmail/oauth/disconnect`
- `POST /settings/reload`
- `POST /workspace/reset`
- `POST /workspace/delete`

---

## Files to Inspect First

Inspect these before coding:

- `frontend/vue/src/router/index.js`
- `frontend/vue/src/api/client.js`
- current Vue settings/page patterns if any
- backend route that serves current settings page
- backend route that exposes Vue settings data, if any
- templates/partials used by `settings.html`
- existing tests around settings/provider/onboarding

Also inspect the legacy files:

- `settings.html`
- `provider_controller.js`
- `core.js`
- `provider.js`
- `search.js`
- `integrations.js`
- `maintenance.js`
- `settings.js`

---

## Required Vue Files

Create:

```text
frontend/vue/src/pages/settings/AiProviderSettingsPage.vue
frontend/vue/src/pages/settings/WorkspaceSettingsPage.vue
```

Create components as needed under:

```text
frontend/vue/src/components/settings/
```

Suggested components:

```text
SettingsPageShell.vue
ProviderModeSelector.vue
ProviderCredentialsForm.vue
LocalProviderPanel.vue
ProviderValidationStatus.vue
SearchPreferencesForm.vue
LanguageRowsEditor.vue
GmailIntegrationPanel.vue
CvSettingsForm.vue
WorkspaceMaintenancePanel.vue
SettingsStatusMessage.vue
```

Create composables as needed under:

```text
frontend/vue/src/composables/settings/
```

Suggested composables:

```text
useSettingsData.js
useSettingsSave.js
useProviderSettings.js
useLocalModels.js
useSearchPreferences.js
useGmailSettings.js
useWorkspaceMaintenance.js
```

Create API wrappers:

```text
frontend/vue/src/api/settingsApi.js
frontend/vue/src/api/providerApi.js
```

---

## Route Requirements

Add these routes:

```text
/settings/ai-provider
/settings/workspace
```

If an old Vue route `/settings` exists, redirect it to:

```text
/settings/ai-provider
```

Both routes should render inside the existing Vue app shell and should follow existing layout/navigation conventions.

Add navigation links/tabs between:

- AI Provider
- Workspace Settings

---

## Backend Data Requirement

The Vue settings pages need initial settings data.

If a suitable endpoint already exists, reuse it.

If not, add a minimal read endpoint, preferably:

```text
GET /api/vue/settings
```

It should return enough data for both pages, including:

```json
{
  "provider": {
    "llm_provider_mode": "...",
    "openai_configured": true,
    "gemini_configured": true,
    "anthropic_configured": false,
    "lm_studio_base_url": "...",
    "ollama_base_url": "...",
    "lm_studio_small_model": "...",
    "lm_studio_writer_model": "...",
    "lm_studio_mid_model": "...",
    "ollama_fast_model": "...",
    "ollama_writer_model": "..."
  },
  "search": {
    "jobspy_discover_queries": [],
    "job_search_countries": [],
    "job_search_languages": []
  },
  "language_options": [],
  "language_level_options": [],
  "gmail": {
    "gmail_label_filter": "...",
    "gmail_auto_sync": false,
    "gmail_oauth_configured": false,
    "gmail_connected": false
  },
  "cv": {
    "cv_pass_score": 0,
    "cv_revise_score": 0,
    "bullet_clarify_word_limit": 0
  },
  "discovery": {
    "match_min_score": 0,
    "discovery_min_fit_score": 0,
    "discovery_max_visible_jobs": 0
  },
  "share_url": "...",
  "active_candidate_id": "..."
}
```

Do not expose secret API keys back to the frontend. Only expose configured booleans.

For provider key fields, the UI should allow entering a new key but should not display stored secret values.

---

## API Wrapper Requirements

Create provider API helpers:

```js
validateProvider(payload)
fetchLmStudioModels(baseUrl)
fetchOllamaModels(baseUrl)
saveSettings(payload)
```

Create settings API helpers:

```js
fetchSettings()
saveSettings(payload)
fetchSearchRecommendations({ candidateId, countries })
connectGmailOAuth(payload)
disconnectGmailOAuth()
reloadSettings()
runWorkspaceAction(action, phrase)
```

Use `vueApiFetch`.

---

## AI Provider Page Behavior

The AI provider page must support the behavior from the legacy provider files.

It must include:

- provider mode selection
- OpenAI API key entry
- Gemini API key entry
- Anthropic API key entry
- LM Studio base URL entry
- Ollama base URL entry
- LM Studio local model select/input
- Ollama local model select/input
- test LM Studio button
- test Ollama button
- validate selected provider button
- save button
- status messages

Preserve logic from `provider_controller.js`:

- filter embedding models
- choose local model defaults
- build provider flags
- build validation payload
- build base save payload
- apply local provider models

Important behavior:

- When mode is `openai`, save:
  - `llm_provider_mode: "openai"`
  - `use_openai_review: true`
  - `use_claude_final_review: false`

- When mode is `anthropic`, save:
  - `llm_provider_mode: "anthropic"`
  - `use_openai_review: false`
  - `use_claude_final_review: true`

- Other modes should set both review booleans to false unless old logic says otherwise.

- For LM Studio mode, one selected local model should populate:
  - `lm_studio_small_model`
  - `lm_studio_writer_model`
  - `lm_studio_mid_model`

- For Ollama mode, one selected local model should populate:
  - `ollama_fast_model`
  - `ollama_writer_model`

- Do not save empty API key fields.
- Do not overwrite existing secrets with empty strings.
- If local provider mode is selected and no usable chat model exists, show an error and do not save.

---

## Workspace Settings Page Behavior

The workspace settings page must support the behavior from:

- `core.js`
- `search.js`
- `integrations.js`
- `maintenance.js`

It must include:

### Search Preferences

- editable target roles textarea/list
- role count display
- visual warning if more than 4 roles
- refresh role suggestions button
- country input
- save behavior that only keeps one country, defaulting to Italy if empty
- language rows editor
  - language name select
  - language level select
  - add row
  - remove row
  - dedupe languages case-insensitively
  - default to English/professional if empty

### Gmail Integration

- Gmail label filter
- Gmail auto sync checkbox
- OAuth client ID input
- OAuth client secret input
- connect Gmail button
- disconnect Gmail button
- save OAuth settings before starting OAuth flow
- redirect browser to `auth_url` returned by `/gmail/oauth/start`
- show connected status if URL query contains `gmail_oauth=connected`

### CV / Discovery / System Settings

Include fields equivalent to old settings page partials.

Preserve numeric parsing for:

- `match_min_score`
- `discovery_min_fit_score`
- `discovery_max_visible_jobs`
- `cv_pass_score`
- `cv_revise_score`
- `bullet_clarify_word_limit`

### Maintenance

Implement confirmation phrase behavior for destructive actions.

- User must type the exact expected phrase.
- If phrase is empty, show:
  - `Enter the confirmation phrase first.`
- If phrase is wrong, show:
  - `Type exactly: {expectedPhrase}`
- On success:
  - reset redirects to `/ui/workspace-reset?mode=reset`
  - if open backups checkbox is checked, redirect to `/ui/workspace-reset?mode=reset&open=1`
  - delete redirects to `/ui/workspace-reset?mode=delete`

---

## Component Design Rules

Components should be controlled by props and emits where practical.

Example structure:

```text
AiProviderSettingsPage.vue
  uses useProviderSettings()
  passes reactive state into:
    ProviderModeSelector
    ProviderCredentialsForm
    LocalProviderPanel
    ProviderValidationStatus
```

Do not put API details inside small UI components.

Small components should emit events like:

```text
save
validate
test-lm-studio
test-ollama
add-language
remove-language
refresh-suggestions
connect-gmail
disconnect-gmail
run-danger-action
```

Composables should own:

- API calls
- payload building
- validation
- status state
- loading state
- error handling

---

## Testing Requirements

Add or update tests.

At minimum add tests that verify:

1. Routes exist:
   - `/settings/ai-provider`
   - `/settings/workspace`

2. Old `/settings` redirects to `/settings/ai-provider`, if applicable.

3. AI Provider page references required endpoints:
   - `/providers/validate`
   - `/settings/save`
   - `/lm-studio/models`
   - `/ollama/models`

4. Provider payload behavior:
   - OpenAI mode sets `use_openai_review: true`
   - Anthropic mode sets `use_claude_final_review: true`
   - Empty API key fields are not sent
   - LM Studio selected model fills small/writer/mid
   - Ollama selected model fills fast/writer
   - embedding models are filtered out

5. Workspace page references required endpoints:
   - `/search/preferences/recommendations`
   - `/settings/save`
   - `/gmail/oauth/start`
   - `/gmail/oauth/disconnect`
   - `/workspace/reset`
   - `/workspace/delete`

6. Search behavior:
   - role count updates
   - more than 4 roles shows warning
   - countries save as one country only
   - empty countries default to Italy

7. Language behavior:
   - default English/professional row exists
   - add/remove works
   - duplicate languages are deduped case-insensitively

8. Maintenance behavior:
   - empty phrase blocks request
   - wrong phrase blocks request
   - correct phrase calls workspace action endpoint

Run the relevant existing test suite after implementation.

---

## Validation Command

Use the project’s existing test command.

If the project uses pytest, run:

```bash
pytest
```

If there are focused Vue tests already, run those too.

Do not mark the task complete unless all existing tests pass or any unrelated existing failures are clearly documented.

---

## Recommended Implementation Phases

### Phase 1 — AI Provider Route

Migrate only:

```text
provider_controller.js
provider.js
```

into:

```text
/settings/ai-provider
```

This phase is isolated and easier to test.

### Phase 2 — Workspace Settings Route

Migrate:

```text
core.js
search.js
integrations.js
maintenance.js
settings.js
```

into:

```text
/settings/workspace
```

This avoids mixing provider validation bugs with Gmail/search/maintenance behavior.

---

## Expected Final Output

When done, report:

- files created
- files modified
- routes added
- endpoints used
- behavior migrated
- tests added/updated
- test results
