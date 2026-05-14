# Phase T5 — Intake Regression Corpus And Diagnostics

## Goal

Stop fixing intake failures one traceback at a time by creating a durable
regression corpus and a diagnostics surface for odd CV layouts.

## Required behavior after this phase

1. The test suite includes multiple real-world layout variants as sanitized
   fixtures.
2. Intake failures emit clearer structured diagnostics for debugging.
3. Mixed-source intake remains covered after future refactors.
4. This track becomes a safety net for both `T` and `S4`.

## Files to inspect first

- `/Users/youseffayyaz/Local_LLM/tests/test_intake.py`
- `/Users/youseffayyaz/Local_LLM/tests/test_fact_sheet_json.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/services/file_extraction.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/services/intake.py`

## Exact implementation requirements

### 1. Add a sanitized fixture corpus

Add representative fixtures for:

- clean single-column CV
- two-column CV
- icon-heavy / section-light CV
- multi-page CV
- PDF + notes mixed intake

Use extracted text fixtures if committed PDFs are impractical, but keep the
layout families explicit.

### 2. Add structured diagnostics

When intake still fails, the system should expose enough detail to distinguish:

- extraction failure
- normalization failure
- provider draft-shape failure
- schema-promotion failure

Do not leak raw stack traces into the UI.

### 3. Keep the fixtures future-refactor friendly

Tests must assert behavior contracts, not fragile exact wording, so future
refactors of prompts and copy do not create noise.

## Do not touch

- jobs discovery UI
- draft action layout
- provider onboarding cards

## Tests required

1. regression fixture coverage for at least four layout families
2. mixed-source fixture coverage
3. structured diagnostics assertions for failure classes

## Browser validation required

1. confirm at least one messy CV now reaches review instead of 500
2. confirm a still-failing pathological case shows a clear UI error instead of an internal traceback
