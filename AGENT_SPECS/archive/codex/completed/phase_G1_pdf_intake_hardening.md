# Phase G1 — PDF Intake Hardening

## Goal

Strengthen onboarding/source-file intake so uploaded PDF CVs and notes produce
cleaner extracted text before the model sees them.

## Why this phase is still needed

The current extraction stack still relies mainly on `pdfminer` through:

- `job_agent/services/file_extraction.py`

This is fragile for real-world CV PDFs with:

- multi-column layouts
- broken line wrapping
- decorative headings
- odd spacing/order issues

## Required outcome

1. PDF remains the primary user upload path.
2. Extraction is improved with a stronger public-license Python dependency if needed.
3. Extracted text is normalized into cleaner structured text before intake.
4. The normalized extraction becomes the text passed into onboarding intake.
5. Failures stay truthful and debuggable.

## Constraints

- Use a public-license dependency only.
- Keep the flow local-first.
- Do not ask the model to “figure out” messy raw PDF text if deterministic cleanup can do it first.
- Do not break `.txt`, `.md`, or `.rst` source handling.

## Likely files in scope

- `job_agent/services/file_extraction.py`
- `job_agent/services/intake.py`
- `job_agent/routers/candidates.py`
- `tests/test_intake.py`
- add PDF-extraction-specific tests as needed

## Acceptance criteria

1. Realistic PDF CV text extraction is cleaner than the current baseline.
2. Intake receives normalized text rather than raw noisy extraction where possible.
3. Broken/empty PDF extraction reports a clear truthful error.
4. Existing non-PDF source ingestion does not regress.
