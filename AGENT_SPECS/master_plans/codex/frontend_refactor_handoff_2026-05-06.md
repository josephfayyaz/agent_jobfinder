# Frontend Refactor Handoff — 2026-05-06

## Why this pass should happen

The current frontend works, but the onboarding/provider work exposed several
structural weaknesses:

- CSS visibility rules are too easy to override accidentally
- provider behavior is duplicated across onboarding and settings
- onboarding logic is split across multiple global scripts with shared mutable state
- app-wide styling, component styling, and onboarding-specific styling are too mixed together

This is not a rewrite recommendation. It is a targeted refactor recommendation.

## Highest-priority refactor targets

### 1. Provider UI behavior

Create one shared provider-controller module for:

- selected-provider state
- panel visibility
- provider-card selected styling
- saved-settings hydration
- validation status messaging

Current duplication exists between:

- `frontend/static/onboarding/core.js`
- `frontend/static/onboarding/hydrate.js`
- `frontend/static/onboarding/intake.js`
- `frontend/static/settings/provider.js`

### 2. Onboarding state management

Reduce cross-file global coupling inside:

- `frontend/static/onboarding/core.js`
- `frontend/static/onboarding/review.js`
- `frontend/static/onboarding/hydrate.js`
- `frontend/static/onboarding/intake.js`
- `frontend/static/onboarding/search.js`
- `frontend/static/onboarding.js`

Recommended shape:

- one bootstrap entry
- one explicit shared state object
- smaller modules with clear ownership:
  - `provider`
  - `profile`
  - `intake`
  - `review`
  - `search`
  - `intro`

### 3. CSS isolation

The provider-config regression happened because shared CSS overrode a hide/show
utility. The stylesheet should be split more safely:

- theme tokens
- shared layout primitives
- reusable components
- onboarding-only styles
- provider-card/provider-panel styles

Recommended follow-up:

- move onboarding-specific styles out of the global collision zone in `frontend/static/app.css`
- use stronger component selectors for behavior-critical visibility
- prefer attribute-driven state like `[hidden]` or explicit component modifiers for critical panels

### 4. Template cleanup

Clean out onboarding remnants that no longer fit the live UX:

- obsolete sidebar assumptions
- stale helper copy
- duplicated button/link entry points
- unnecessary provider-copy repetition between onboarding and settings

## Medium-priority cleanup

### 5. Shared copy and labels

Define one source of truth for provider labels and help copy:

- `Local Gateway`
- `Ollama`
- `OpenAI`
- `Google Gemini`
- `Claude`

This should drive both onboarding and settings so the wording cannot drift.

### 6. View-specific script loading

The app still relies on global browser behavior more than necessary.
Tighten page ownership so each major page loads only what it owns.

## What should not be done

- do not rewrite the app into a frontend framework just to clean this up
- do not redesign the whole UI again before the manual-JD/CV path is stabilized
- do not merge provider/settings/onboarding logic into one giant script

## Recommended execution order

1. extract shared provider controller
2. split onboarding state by responsibility
3. isolate onboarding/provider CSS
4. normalize provider/help copy
5. remove dead template/UI remnants
