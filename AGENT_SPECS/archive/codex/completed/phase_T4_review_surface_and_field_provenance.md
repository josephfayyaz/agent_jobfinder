# Phase T4 — Review Surface And Field Provenance

## Goal

Expose the dossier-backed intake result to the user clearly enough that the
profile review step is honest about where important fields came from.

## Alignment note

This phase is the substrate that `S4` depends on.

- `T4` adds dossier-backed visibility and provenance plumbing
- `S4` finalizes the simplified user-facing profile review surface

Do not collapse both concerns into one oversized refactor.

## Required behavior after this phase

1. Review data can show the important persisted identity fields with their draft
   values.
2. The review layer can surface source provenance or at least source-origin
   hints for high-value fields.
3. The user can correct draft values before canonical persistence is treated as
   final.
4. Provenance support must not make onboarding more verbose or add extra
   questions.

## Files to inspect first

- `/Users/youseffayyaz/Local_LLM/frontend/static/onboarding/review.js`
- `/Users/youseffayyaz/Local_LLM/frontend/templates/partials/onboarding/step_review.html`
- `/Users/youseffayyaz/Local_LLM/job_agent/services/intake.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/routers/candidates.py`
- `/Users/youseffayyaz/Local_LLM/tests/test_onboarding.py`

## Exact implementation requirements

### 1. Prepare review payload with provenance-friendly shape

The review payload should clearly separate:

- editable value
- optional source hint / provenance summary
- unresolved draft issue if present

### 2. Keep the visible field set focused

Support the `S4` target fields well:

- name
- email
- phone
- current location
- LinkedIn
- GitHub
- headline
- work authorization

Do not add remote/hybrid/onsite/start-date onboarding questions here.

### 3. Preserve overwrite semantics

User edits in review must overwrite the active canonical draft cleanly without
reviving stale prior-source values.

## Do not touch

- discovery queue ranking
- jobs page modal work
- provider adapter logic

## Tests required

1. review payload includes provenance-friendly entries for key fields
2. editing one key field overwrites the active review state
3. stale prior-source values do not reappear after save

## Browser validation required

1. finish intake
2. open review
3. confirm key fields are visible and editable
4. edit at least one field and save
