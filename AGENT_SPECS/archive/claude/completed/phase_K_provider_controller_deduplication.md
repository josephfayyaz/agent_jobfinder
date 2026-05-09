# Phase K — Provider Controller Deduplication

## Priority
High.

Ship this before larger onboarding/frontend cleanup phases.

## Goal

Reduce duplicated provider UI logic between onboarding and settings without
changing backend behavior.

The target is a small shared frontend helper for provider labels, panel
visibility, provider validation calls, and local-model default selection.

## Live Audit Snapshot

The current frontend is narrower than the older rewrite assumed.

Observed in live code:

- `frontend/static/onboarding/core.js` already contains shared local-model
  default selection via `chooseLocalModelDefaults()` and non-embedding model
  filtering via `nonEmbeddingModels()`.
- `frontend/static/onboarding/core.js` contains onboarding-only provider panel
  visibility logic in `toggleProviderFields()`.
- `frontend/static/settings/provider.js` contains settings-only panel
  visibility logic in `syncProviderVisibility()`.
- The strongest real duplication is between:
  - onboarding `validateAndSaveProvider()`
  - settings `validateProviderForm()`
- Duplicated concerns in those two flows include:
  - collecting provider validation payload fields
  - posting to `/providers/validate`
  - defaulting LM Studio and Ollama base URLs
  - building the shared provider save payload
  - mapping provider mode to shared provider flags
- There is not enough proven duplication right now to justify moving
  `chooseLocalModelDefaults()` out of onboarding core unless the extraction
  becomes clearly simpler after wiring.
- There is not enough proven duplication right now to justify a label registry
  unless the implementation needs one for settings and onboarding together.

## Why this spec was rewritten

The older version assumed stale frontend structure and pushed a more aggressive
rewrite than a local `aider` + Qwen 3.5 27B agent should attempt in one pass.

This version is intentionally narrower:

- audit first
- extract only logic that is truly duplicated
- preserve current app behavior
- avoid broad frontend architecture changes

## Aider-Safe Constraints

1. Use the existing repo style. No build step, no bundler, no ES module import/export.
2. Keep the implementation frontend-only.
3. Do not change backend routes or payload contracts in this phase.
4. Do not rename existing HTML IDs or backend-rendered form field names.
5. Do not redesign the provider UI in this phase.
6. Keep write scope to at most these files unless the audit proves one more is necessary:
   - `frontend/static/provider_controller.js` (new)
   - `frontend/static/onboarding/core.js`
   - `frontend/static/onboarding/intake.js`
   - `frontend/static/settings/provider.js`
   - `frontend/templates/onboarding.html`
   - `frontend/templates/settings.html`
7. If the current code differs from this spec, follow the live code and record the deviation in the completion report.

## Do Not Touch

- `job_agent/`
- onboarding step order/state model
- search/review logic
- provider backend persistence rules
- CSS, except if a script tag must be added to a template

## Mandatory Audit First

Run:

```bash
rg -n "provider|validateAndSaveProvider|toggleProviderFields|providerFlags|validateProviderForm|lm_studio|gemini|anthropic|ollama|openai" \
  frontend/static/onboarding/core.js \
  frontend/static/onboarding/intake.js \
  frontend/static/onboarding/hydrate.js \
  frontend/static/settings/provider.js
```

Then write a short local note for yourself:

- which functions are actually duplicated
- which functions are onboarding-specific
- which functions are settings-specific
- which label strings are duplicated

If the duplication is smaller than expected, keep the extracted controller small.
Do not invent abstractions just because the old spec expected them.

## Required Design

Create one plain global helper:

- file: `frontend/static/provider_controller.js`
- export shape: `window.ProviderController = ...`

It should contain only shared provider concerns that are already duplicated in
the live code.

### Expected Shared Responsibilities

1. Provider validation request helper
   - call `/providers/validate`
   - normalize common success/error handling

2. Shared provider save-payload assembly helper
   - only if onboarding and settings currently build near-identical payloads

3. Shared provider flags helper
   - `llm_provider_mode`
   - `use_openai_review`
   - `use_claude_final_review`

4. Shared local-provider model assignment helper
   - only for the repeated LM Studio / Ollama payload shaping
   - do not move `chooseLocalModelDefaults()` unless the audit proves that
     doing so reduces duplication instead of spreading responsibilities

5. Panel visibility helpers only if they stay small
   - onboarding provider field toggling may stay local
   - settings panel toggling may stay local
   - do not force both into the controller if their DOM contracts differ too much

### Explicit Non-Goals

Do not force all provider code into one mega-controller.

It is acceptable for onboarding and settings to keep:

- their own status message rendering
- their own button loading states
- their own DOM-query details

as long as the duplicated provider logic is centralized.

## Implementation Steps

### K1 — Create the shared controller

Create `frontend/static/provider_controller.js`.

Use an IIFE and attach to `window`.

The controller should expose only what the audit proves useful. Prefer this
minimal shape:

- `buildProviderFlags(mode)`
- `buildValidationPayload(input)`
- `validateProvider(payload, fetchJson)`
- `buildBaseSavePayload(mode, input)`
- `applyLocalProviderModels(mode, chosenModels, payload, options)`

Optional only if clearly justified:

- `showOnboardingFields(mode)`
- `showSettingsPanels(form, mode)`

Do not add `getLabel(mode)` unless the live code actually needs it.
Do not move `chooseLocalModelDefaults(models)` unless both onboarding and
settings benefit materially from the move.

### K2 — Wire onboarding to the controller

Update:

- `frontend/static/onboarding/core.js`
- `frontend/static/onboarding/intake.js`

Replace duplicated provider-specific logic with calls into
`window.ProviderController`.

Important:

- `toggleProviderFields()` may remain in `core.js` if the DOM handling stays
  onboarding-specific.
- If `chooseLocalModelDefaults()` stays in `core.js`, the new controller may
  call it through `window.OnboardingApp.chooseLocalModelDefaults(...)` rather
  than moving it in this phase.

Do not refactor unrelated onboarding logic in this phase.

### K3 — Wire settings to the controller

Update:

- `frontend/static/settings/provider.js`

Use the shared helper for label lookup, visibility, validation call shape, and
shared local-model selection logic if applicable.

In live code, prioritize these replacements:

- provider flag generation
- validation request payload assembly
- shared save payload assembly
- repeated LM Studio / Ollama model assignment

Do not rewrite `syncProviderVisibility()` unless the extracted helper is
obviously cleaner than the current local implementation.

### K4 — Load the controller

Add the script include before the dependent onboarding/settings scripts in:

- `frontend/templates/onboarding.html`
- `frontend/templates/settings.html`

Use `/static/provider_controller.js?v=...`.

### K5 — Remove only proven duplication

After wiring, remove old duplicate helpers from onboarding/settings JS files.

Do not delete a function unless you have already moved or replaced its behavior.

Minimum acceptable implementation for this phase:

- new `frontend/static/provider_controller.js`
- onboarding validation/save flow uses it
- settings validation/save flow uses it
- templates load it
- tests cover the new contract

This phase is still successful even if visibility helpers remain local.

## Tests

Create:

- `tests/test_frontend_provider_controller.py`

Keep tests structural and low-risk, but include at least one behavioral HTML/JS
contract check.

### Minimum assertions

1. `provider_controller.js` exists
2. it exposes `window.ProviderController`
3. onboarding template loads it
4. settings template loads it
5. onboarding provider JS references `ProviderController`
6. settings provider JS references `ProviderController`

Recommended additional assertions:

7. shared controller contains a validation helper
8. shared controller contains a provider-flag helper
9. onboarding no longer inlines the full `/providers/validate` request body shape
10. settings no longer duplicates the same provider-flag mapping inline

### Also update existing tests if needed

If current onboarding/settings tests assert exact script ordering or exact file
counts, update them minimally.

## Verification

Run:

```bash
/Users/youseffayyaz/miniforge3/envs/ML/bin/python -m pytest \
  tests/test_frontend_provider_controller.py \
  tests/test_onboarding.py \
  tests/test_settings_ui.py -q
```

If those pass, optionally run:

```bash
/Users/youseffayyaz/miniforge3/envs/ML/bin/python -m ruff check frontend tests/test_frontend_provider_controller.py tests/test_onboarding.py tests/test_settings_ui.py
```

## Stop Conditions

Stop and do not continue if any of these are true:

- onboarding and settings provider flows are less duplicated than expected
- the extraction would require backend payload changes
- the controller starts needing knowledge of unrelated onboarding state

In that case, scale the phase down and record what was actually deduplicated.

For the current live code, this specifically means:

- if only provider flag generation is safely shareable, extract only that plus
  the validation payload helper
- do not force onboarding DOM toggling and settings panel toggling into the
  same abstraction
- do not move general onboarding helpers just to satisfy the older rewrite idea

## Completion

After implementation:

1. write `AGENT_SPECS/completed/phase_K_provider_controller_deduplication.md`
2. record:
   - which helpers were centralized
   - which logic intentionally stayed local
   - which files changed
   - tests run
3. append to `completed_agent_specs.txt`
