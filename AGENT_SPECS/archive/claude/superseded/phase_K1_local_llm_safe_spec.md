# Phase K1 — Shared Provider Validation Payload Helper

## Goal

Make a smaller local-LLM-safe first step of Phase K.

Do not attempt the full provider-controller refactor in this phase.

Extract only the duplicated provider validation/save payload logic that is
clearly shared between onboarding and settings.

## Target Files

Editable files:

- `frontend/static/provider_controller.js` (new)
- `frontend/static/onboarding/intake.js`
- `frontend/static/settings/provider.js`
- `frontend/templates/onboarding.html`
- `frontend/templates/settings.html`
- `tests/test_frontend_provider_controller.py` (new)

Read-only reference files:

- `frontend/static/onboarding/core.js`

Do not edit:

- `job_agent/`
- backend routes
- payload contracts
- onboarding step order
- search/review frontend files
- CSS

## Exact Scope

Create a small global helper:

- `window.ProviderController`

Only centralize these concerns:

1. build provider flags
   - `llm_provider_mode`
   - `use_openai_review`
   - `use_claude_final_review`

2. build `/providers/validate` request payload from already-read values

3. build base `/settings/save` payload
   - include default local base URLs

4. optionally apply repeated LM Studio / Ollama payload model assignments
   - only if this can be done cleanly without moving unrelated logic

## Explicit Non-Goals

Do not move or centralize:

- onboarding panel visibility
- settings panel visibility
- general onboarding state
- `chooseLocalModelDefaults()` unless absolutely necessary
- broad provider label registries

## Implementation Rules

1. Use an IIFE.
2. Attach the helper to `window.ProviderController`.
3. Keep onboarding DOM lookups in onboarding code.
4. Keep settings DOM lookups in settings code.
5. The shared helper should operate on plain data, not own the whole page flow.
6. Keep the helper small.

## Minimum Required Wiring

### onboarding

Update onboarding validation flow so that it uses shared helper calls for:

- provider flags
- validation payload
- base save payload

### settings

Update settings validation flow so that it uses the same shared helper calls
for:

- provider flags
- validation payload
- base save payload

### templates

Load `/static/provider_controller.js?v=...` before dependent onboarding and
settings scripts.

## Tests

Create:

- `tests/test_frontend_provider_controller.py`

Minimum assertions:

1. `frontend/static/provider_controller.js` exists
2. it exposes `window.ProviderController`
3. onboarding template loads it
4. settings template loads it
5. onboarding provider JS references `ProviderController`
6. settings provider JS references `ProviderController`

## Verification

Run:

```bash
/Users/youseffayyaz/miniforge3/envs/ML/bin/python -m pytest \
  tests/test_frontend_provider_controller.py \
  tests/test_onboarding.py \
  tests/test_settings_ui.py -q
```

## Stop Conditions

Stop if any of these become true:

- the helper starts owning page-specific status rendering
- the helper starts owning page-specific DOM queries
- the change requires backend payload changes
- the extraction cannot be kept small

If stopped, return a report describing the smallest safe shared seam that
actually exists.

## Done Means

This phase is done when:

- the shared helper file exists
- onboarding uses it for the shared payload logic
- settings uses it for the shared payload logic
- the templates load it
- the structural tests pass
- no unrelated frontend behavior is refactored
