# Phase T1 — Source Dossier And Multi-File Provenance

## Goal

Stop flattening all onboarding source inputs into one opaque intake blob.
Persist a reviewable per-source dossier so multi-file CV intake is durable and
debuggable.

## Required behavior after this phase

1. Each uploaded onboarding source remains individually identifiable.
2. Mixed source sets are supported:
   - one PDF
   - multiple PDFs
   - PDF + manual notes
3. Intake can assemble a dossier from multiple sources without losing
   per-source provenance.
4. Re-running intake replaces the active onboarding dossier cleanly for that
   candidate instead of silently appending stale source state.

## Files to inspect first

- `/Users/youseffayyaz/Local_LLM/job_agent/models.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/services/intake.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/services/file_extraction.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/routers/candidates.py`
- `/Users/youseffayyaz/Local_LLM/tests/test_intake.py`

## Exact implementation requirements

### 1. Add an explicit source dossier structure

Persist an intermediate dossier structure that includes, per uploaded source:

- source id
- source filename / label
- source type
- extracted plain text
- normalized text preview
- extraction warnings if present

Use either an existing stable metadata field or a dedicated structured payload
attached to the intake draft. Do not force canonical fact-sheet tables to store
this intermediate layer yet.

### 2. Preserve multi-file source boundaries

Do not concatenate all extracted source text before preserving the individual
source entries.

Only build the merged dossier view after the per-source rows exist.

### 3. Replace onboarding source state on rerun

When the onboarding facts step is re-run for the same candidate:

- previous active onboarding source dossier for that candidate must be replaced
- old raw sources may remain archived if the current code already does that
- the active dossier used for questions/review must point only to the latest
  source set

### 4. Keep current supported file types

Do not shrink support for:

- `.pdf`
- `.docx`
- `.txt`
- `.md`

## Do not touch

- jobs discovery code
- CV rendering pipeline
- provider routing

## Tests required

1. multiple uploaded PDFs produce multiple dossier entries
2. PDF + notes produces two distinct source entries
3. re-running onboarding intake replaces the active dossier cleanly
4. dossier preserves source ordering and labels

## Browser validation required

1. upload two PDFs and confirm intake still progresses
2. upload one PDF plus notes and confirm questions still generate
3. go back, replace sources, re-run intake, and confirm the new source set is active
