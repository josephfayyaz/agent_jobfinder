# Phase M — Onboarding CSS Isolation and Dead-Code Cleanup

## Priority
Low-medium.

Run after Phases K and L stabilize.

## Goal

Reduce onboarding-specific CSS bleed and clean stale onboarding remnants without
changing product behavior.

This phase is intentionally narrower than the earlier version:

- move verified onboarding-only CSS into `onboarding.css`
- verify deleted profile-step remnants are gone
- document remaining server-rendered provider labels

## Why this spec was rewritten

The older version mixed three tasks together and assumed some stale cleanup work
had not already happened. This rewrite keeps the risky part small and treats
label work mainly as audit/documentation.

## Aider-Safe Constraints

1. Frontend-only phase.
2. No backend/template logic changes outside onboarding asset loading and stale-copy cleanup.
3. No Tailwind rebuild work in this phase.
4. Move CSS only after proving a selector is onboarding-only.
5. Keep write scope to:
   - `frontend/static/app.css`
   - `frontend/static/onboarding.css` (new)
   - `frontend/templates/onboarding.html`
   - optional onboarding JS files only if dead references still exist
   - new/updated frontend tests
6. Do not redesign styles while moving them.

## Do Not Touch

- `frontend/templates/base.html`
- settings UI
- provider backend behavior
- non-onboarding page layouts

## Mandatory Audit First

### M1 — CSS usage audit

Run:

```bash
rg -n "\\.setup-|\\.onboarding-|#onboarding|#setup" frontend/static/app.css
```

Then verify candidate selectors are onboarding-only:

```bash
rg -n "setup-|onboarding-" frontend/templates --glob "*.html"
```

Before moving any selector block, confirm it is not used by non-onboarding
templates.

### M2 — Dead-reference audit

Run:

```bash
rg -n "step_profile|createProfile\\b|profile step|save identity" frontend --glob "*.html" --glob "*.js"
```

### M3 — Provider-label audit

Run:

```bash
rg -n "Local Gateway|Ollama|OpenAI|Claude|Google Gemini" frontend/templates --glob "*.html"
```

Do not treat every match as a bug. Separate:

- acceptable static page copy
- duplicated server-rendered labels that might deserve a later backend context helper

## Implementation Steps

### M1 — Create `frontend/static/onboarding.css`

Create the file and move only verified onboarding-exclusive CSS from `app.css`.

Copy first, test, then delete from `app.css`.

Do not move shared utility styles or component primitives.

### M2 — Load `onboarding.css` only on onboarding

Update `frontend/templates/onboarding.html` to include:

```html
<link rel="stylesheet" href="/static/onboarding.css?v=1">
```

Place it after `app.css`.

Do not add it to `base.html`.

### M3 — Verify profile-step remnants are gone

The current repo should already have removed the separate profile step.

Only clean references that still exist:

- `step_profile`
- `createProfile()`
- stale copy mentioning the old identity step

Do not remove review-step identity confirmation copy.

### M4 — Document provider label duplication, do not over-refactor

If hardcoded provider labels remain in templates, note them in the completion
report.

Only change JS hardcoded labels if they are clearly stale and if Phase K already
provided the shared label helper.

## Tests

Create:

- `tests/test_frontend_css_isolation.py`

### Minimum assertions

1. `frontend/static/onboarding.css` exists
2. `onboarding.html` links `onboarding.css`
3. `base.html` does not link `onboarding.css`
4. no `step_profile` include remains in onboarding templates
5. no `createProfile()` references remain in onboarding JS

Do not write brittle tests that depend on exact CSS line numbers.

## Verification

Run:

```bash
/Users/youseffayyaz/miniforge3/envs/ML/bin/python -m pytest \
  tests/test_frontend_css_isolation.py \
  tests/test_onboarding.py \
  tests/test_frontend_accessibility.py -q
```

Then:

```bash
/Users/youseffayyaz/miniforge3/envs/ML/bin/python -m ruff check frontend tests/test_frontend_css_isolation.py tests/test_onboarding.py tests/test_frontend_accessibility.py
```

## Stop Conditions

Stop and scale down if:

- a selector thought to be onboarding-only is reused elsewhere
- moving CSS changes non-onboarding layouts
- the phase starts requiring design changes rather than isolation

In that case, keep the phase to dead-code cleanup plus a report of selectors not
safe to move yet.

## Completion

After implementation:

1. write `AGENT_SPECS/completed/phase_M_css_isolation_labels_dead_code.md`
2. record:
   - which selectors moved
   - which selectors were kept in `app.css`
   - whether any stale profile-step references were removed
   - remaining hardcoded server-rendered provider labels
   - tests run
3. append to `completed_agent_specs.txt`
