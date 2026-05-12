# Phase T2 — Normalized Markdown Intake Layer

## Goal

Create a human-readable intermediate text layer between raw extraction and
canonical fact-sheet promotion so layout noise does not directly drive schema
decisions.

## Required behavior after this phase

1. Each source dossier entry can produce normalized markdown-like text.
2. The merged intake prompt uses this normalized layer instead of raw PDF text
   wherever possible.
3. The normalized layer keeps headings, bullets, and source boundaries clearer
   than the raw extractor output.
4. Extraction failure messages remain truthful when normalization still cannot
   recover usable content.

## Files to inspect first

- `/Users/youseffayyaz/Local_LLM/job_agent/services/file_extraction.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/services/intake.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/services/provider_input.py`
- `/Users/youseffayyaz/Local_LLM/tests/test_intake.py`

## Exact implementation requirements

### 1. Add a normalized dossier text builder

Build a deterministic formatter that produces markdown-like text with:

- source heading
- preserved bullets
- blank-line normalization
- field-section hints where obvious

The formatter must be deterministic and must not call the LLM.

### 2. Keep raw extraction alongside normalized text

Do not discard raw extracted text.

The normalized text is an intermediate view, not a replacement for raw source
retention.

### 3. Feed the normalized layer into intake prompts

Where onboarding start/answer prompts currently assemble source text for the
provider, switch them to use the normalized dossier blocks first.

Do not remove provider-aware shaping added in `Q4`.

### 4. Make truncation happen after normalization

The provider-aware trimming in `job_agent/services/provider_input.py` must act
on normalized blocks, not on raw pre-normalized fragments.

## Do not touch

- canonical fact-sheet schema
- jobs queue logic
- draft-detail templates

## Tests required

1. normalized markdown layer preserves bullets and headings better than raw text
2. mixed-source dossier formatting remains deterministic
3. provider shaping still respects total budget after normalization
4. empty/garbled PDFs still return clear extraction errors

## Browser validation required

1. run intake with a clean PDF and confirm behavior is unchanged
2. run intake with a messy PDF and confirm questions/review still render if extraction succeeds
