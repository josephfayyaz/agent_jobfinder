# Phase T5 Completion Report — Intake Regression Corpus And Diagnostics

Completed: 2026-05-14T00:44:29+0200

## Outcome

Added a sanitized intake regression corpus and structured intake diagnostics so
layout-heavy source failures are categorized without leaking stack traces or
private source text.

## Delivered

- Added five sanitized extracted-text fixtures under `tests/fixtures/intake_corpus/`:
  clean single-column, two-column, icon-heavy/section-light, multi-page, and
  mixed notes.
- Extended intake dossier structure to persist `source_dossier["diagnostics"]`
  with structured entries (`stage`, `code`, `severity`, `message`, optional
  source metadata/details).
- Added diagnostics emission paths for:
  extraction failures, normalization failures, provider draft-shape failures,
  and schema-promotion/ingestion failures.
- Added regression tests for four layout families, mixed-source intake
  (uploaded text + notes), and diagnostic-category behavior contracts with
  explicit non-leakage assertions.

## Validation

- `python -m ruff check job_agent tests`
- `python -m pytest tests/test_intake.py tests/test_fact_sheet_json.py -q`
- `python -m pytest tests/test_intake.py -q -k "layout_regression_corpus or mixed_uploaded_text_and_manual_notes or diagnostics_capture"`
- `python -m pytest tests -q` *(known unrelated failures remain in e2e/frontend null guards/llm hardening tracks)*
