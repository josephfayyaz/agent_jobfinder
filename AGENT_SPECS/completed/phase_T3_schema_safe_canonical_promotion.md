# Phase T3 Completion Report — Schema-Safe Canonical Promotion

Completed: 2026-05-13T17:09:49+0200

## Outcome

Centralized intake promotion through a schema-safe canonicalization step that
normalizes known provider shape drift and records non-fatal draft issues.

## Delivered

- Added `_promote_intake_draft_to_canonical` as the single intake promotion path.
- Normalized deterministic string/dict/list variants before strict schema
  ingestion.
- Preserved strict fact-sheet validation by fixing provider draft shape upstream
  instead of relaxing the schema.
- Stored draft issues in the active source dossier for later review.

## Validation

- `python -m ruff check job_agent/models.py job_agent/db.py job_agent/services/intake.py job_agent/routers/candidates.py tests/test_intake.py`
- `python -m pytest tests/test_intake.py tests/test_onboarding.py tests/test_fact_sheet_json.py -q`
