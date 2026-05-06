# Phase G1 — PDF Intake Hardening

Status: Complete  
Completed: 2026-05-06

## Outcome

The onboarding intake path now handles real-world PDF CV input more safely and
more truthfully before the model sees it.

## What changed

- Replaced the old PDF-only extraction dependency path with a stronger local
  extraction stack centered on `pdfplumber`, with `pdfminer.six` fallback.
- Added deterministic extraction cleanup so whitespace, bullets, and noisy line
  breaks are normalized before intake uses the text.
- Preserved support for multiple uploaded PDFs plus mixed PDF and manual text
  notes in the onboarding intake flow.
- Kept non-PDF text ingestion intact for `.txt`, `.md`, `.rst`, `.html`, and
  `.docx` sources.
- Added truthful error reporting when a PDF yields no readable text.

## Main files

- `job_agent/services/file_extraction.py`
- `job_agent/services/intake.py`
- `pyproject.toml`
- `tests/test_intake.py`

## Notes

This phase was implemented alongside the onboarding-flow cleanup that now:

- removes the separate identity step after provider setup
- creates a candidate shell automatically after provider selection
- lets provider changes replace the old provider configuration cleanly
- moves the user from final intake answers into profile review reliably
