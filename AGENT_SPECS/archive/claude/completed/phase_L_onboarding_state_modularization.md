# Phase L — Onboarding State Modularization

## Priority
Medium.

Implement after Phase K, but only if the provider-controller extraction is
already stable.

## Goal

Refactor onboarding state into clearer nested namespaces inside the existing
`window.OnboardingApp.state` object.

This is **not** a rewrite to five new file-scope globals. The current repo
already uses a namespaced app object, and this phase should build on that.

## Why this spec was rewritten

The older version assumed a flat `onboardingState` global that does not match
the real codebase. A local model following that spec literally would rewrite
working code in the wrong direction.

This version keeps the current architecture:

- `window.OnboardingApp`
- one shared `app.state`
- nested state buckets per concern

## Aider-Safe Constraints

1. Frontend-only phase. Do not touch backend files.
2. No build step, no ES module import/export.
3. Preserve existing function names and externally-used globals.
4. Do not change onboarding step order in this phase.
5. Do not redesign onboarding UI in this phase.
6. Keep write scope to these files unless the audit proves one more is necessary:
   - `frontend/static/onboarding/core.js`
   - `frontend/static/onboarding/intake.js`
   - `frontend/static/onboarding/hydrate.js`
   - `frontend/static/onboarding/review.js`
   - `frontend/static/onboarding/search.js`
7. Do not invent new persistence behavior. This is a state-shape cleanup only.

## Do Not Touch

- templates
- settings UI
- provider backend logic
- onboarding CSS
- route responses

## Mandatory Audit First

Run:

```bash
rg -n "app\\.state|state\\.|candidateId|questions|reviewFactSheet|languagesTouched|introIndex|searchRecommendationsLoaded" \
  frontend/static/onboarding/core.js \
  frontend/static/onboarding/intake.js \
  frontend/static/onboarding/hydrate.js \
  frontend/static/onboarding/review.js \
  frontend/static/onboarding/search.js
```

Before editing, map current fields to one of these buckets:

- `provider`
- `intake`
- `review`
- `search`
- `ui`

## Target State Shape

Inside `frontend/static/onboarding/core.js`, reshape the current state to:

```javascript
app.state = {
  provider: {
    mode: "",
    lastValidation: null,
  },
  intake: {
    candidateId: "",
    questions: [],
  },
  review: {
    factSheet: null,
  },
  search: {
    recommendationsLoaded: false,
    languageOptions: [...],
    levelOptions: [...],
    languagesTouched: false,
  },
  ui: {
    introIndex: 0,
    currentStep: 1,
  },
};
```

Notes:

- keep field names close to existing semantics
- if a current field name is already better than the example above, keep it
- do not store live `File` objects in state unless the current code already does

## Implementation Steps

### L1 — Reshape `app.state` only in `core.js`

Introduce the nested buckets in `frontend/static/onboarding/core.js`.

Do not move logic yet. First make the state shape explicit.

### L2 — Migrate intake references

Update `frontend/static/onboarding/intake.js` to use:

- `app.state.intake.candidateId`
- `app.state.intake.questions`
- `app.state.provider.mode` if needed

Do not reach into `review` or `search` unless the current flow truly depends on it.

### L3 — Migrate hydrate references

Update `frontend/static/onboarding/hydrate.js` so hydration writes into the
correct nested buckets:

- provider values -> `app.state.provider`
- candidate/question values -> `app.state.intake`
- review payload -> `app.state.review`
- search defaults -> `app.state.search`
- current step / intro state -> `app.state.ui`

### L4 — Migrate review and search references

Update:

- `frontend/static/onboarding/review.js`
- `frontend/static/onboarding/search.js`

Use nested state consistently.

### L5 — Navigation bookkeeping

In `core.js`, ensure `goToStep()` updates `app.state.ui.currentStep`.

Do not add a router, event bus, or new lifecycle abstraction in this phase.

## What Not To Do

- do not create five new `var providerState = ...` globals
- do not rewrite onboarding into classes
- do not rewrite every step file for style consistency
- do not add localStorage persistence in this phase
- do not move provider logic here if Phase K already extracted it

## Tests

Create:

- `tests/test_frontend_state_modularization.py`

### Minimum assertions

1. `core.js` contains nested state buckets under `app.state`
2. step files no longer rely on stale flat-state references
3. `intake.js` references `app.state.intake`
4. `review.js` references `app.state.review`
5. `search.js` references `app.state.search`
6. `hydrate.js` touches multiple nested buckets

Keep these as structural tests. Do not overfit exact line positions.

## Verification

Run:

```bash
/Users/youseffayyaz/miniforge3/envs/ML/bin/python -m pytest \
  tests/test_frontend_state_modularization.py \
  tests/test_onboarding.py -q
```

Then run:

```bash
/Users/youseffayyaz/miniforge3/envs/ML/bin/python -m ruff check frontend tests/test_frontend_state_modularization.py tests/test_onboarding.py
```

## Stop Conditions

Stop and scale down if:

- a field is clearly cross-cutting and does not fit one bucket cleanly
- the refactor starts requiring template changes
- onboarding behavior changes while renaming state access

In that case, keep the nested `app.state` cleanup partial and document the
remaining cross-step fields.

## Completion

After implementation:

1. write `AGENT_SPECS/completed/phase_L_onboarding_state_modularization.md`
2. record:
   - old state shape
   - new nested state shape
   - any fields intentionally left cross-cutting
   - tests run
3. append to `completed_agent_specs.txt`
