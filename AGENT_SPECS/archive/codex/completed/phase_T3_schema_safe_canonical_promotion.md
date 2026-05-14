# Phase T3 — Schema-Safe Canonical Promotion

## Goal

Make canonical fact-sheet promotion resilient by promoting from an intermediate
profile draft instead of assuming provider output is already in final schema
shape.

## Required behavior after this phase

1. Intake result handling uses a draft/intermediate structure before final schema
   validation.
2. Canonical promotion performs centralized normalization for unstable fields.
3. New field-shape surprises fail as structured draft issues instead of raw
   `500` errors wherever possible.
4. Canonical fact-sheet validation remains strict.

## Files to inspect first

- `/Users/youseffayyaz/Local_LLM/job_agent/services/intake.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/services/fact_sheet_json.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/resources/fact_sheet/fact_sheet_schema.json`
- `/Users/youseffayyaz/Local_LLM/tests/test_intake.py`
- `/Users/youseffayyaz/Local_LLM/tests/test_fact_sheet_json.py`

## Exact implementation requirements

### 1. Centralize canonical promotion

Do not scatter new one-off field fixes across multiple route handlers.

Use one clear canonical-promotion path in intake that:

- normalizes provider draft shapes
- applies stable defaults
- records non-fatal draft issues where useful
- emits a schema-valid canonical fact sheet

### 2. Keep strict schema validation

Do not weaken the JSON schema to accept arbitrary field shapes.

The fix must be upstream normalization, not schema dilution.

### 3. Promote only known visible fields and safe inferred fields

If a provider returns a malformed value for a low-confidence field:

- normalize it if the mapping is deterministic
- otherwise keep it out of canonical output and record it for review

### 4. Prepare for provenance-aware review

The promoted draft should preserve enough source/draft context for `T4`, even
if the full provenance UI is not implemented yet.

## Do not touch

- jobs discovery pipeline
- provider validation route
- PDF renderer

## Tests required

1. provider draft with string/object/list variants normalizes cleanly
2. malformed optional fields do not crash canonical promotion
3. canonical output remains schema-valid
4. prior fixes for `work_authorization` and `current_location` remain covered

## Browser validation required

1. finish onboarding with a messy PDF and confirm question/review progression no longer crashes on known shape drift
