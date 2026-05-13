# Phase T1 Completion Report — Source Dossier And Multi-File Provenance

Completed: 2026-05-13T17:09:49+0200

## Outcome

Implemented persistent onboarding source dossiers on `CandidateIntakeDraft` so
uploaded CV/source inputs remain individually identifiable through intake.

## Delivered

- Added `candidate_intake_drafts.source_dossier` with SQLite bootstrap support.
- Stored ordered per-source entries with source id, label, type, raw text,
  normalized preview, and warnings.
- Kept PDF/manual notes as separate dossier entries.
- Made rerun/reset replace the active dossier used by intake/review instead of
  reviving stale prior-source state.

## Validation

- `python -m ruff check job_agent/models.py job_agent/db.py job_agent/services/intake.py job_agent/routers/candidates.py tests/test_intake.py`
- `python -m pytest tests/test_intake.py tests/test_onboarding.py tests/test_fact_sheet_json.py -q`
