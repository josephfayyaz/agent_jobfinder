# Phase T2 Completion Report — Normalized Markdown Intake Layer

Completed: 2026-05-13T17:09:49+0200

## Outcome

Added a deterministic normalized markdown-like intake layer and switched
provider prompts to use normalized dossier blocks while preserving raw text.

## Delivered

- Added source normalization for headings, bullets, spacing, source labels, and
  readable previews.
- Preserved raw extracted text beside normalized text in each dossier entry.
- Fed normalized dossier blocks through the existing provider-aware prompt
  shaping path.
- Kept deduplication and truncation after normalization, while deduplicating
  identical content across differently named duplicate sources.

## Validation

- `python -m ruff check job_agent/models.py job_agent/db.py job_agent/services/intake.py job_agent/routers/candidates.py tests/test_intake.py`
- `python -m pytest tests/test_intake.py tests/test_onboarding.py tests/test_fact_sheet_json.py -q`
