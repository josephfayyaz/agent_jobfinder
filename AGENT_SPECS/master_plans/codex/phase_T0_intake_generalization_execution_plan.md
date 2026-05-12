# Phase T0 — Intake Generalization And CV Source Robustness Execution Plan

## Purpose

This execution pack hardens onboarding intake so the app can accept multiple CV
PDFs and mixed free-text notes without repeatedly failing on layout variation or
provider-shaped schema drift.

The track is intentionally aligned with the existing `S` pack and must not
duplicate it:

- `S1` through `S3` improve discovery scope, queue quality, and JD readability
- `T1` through `T4` stabilize the intake substrate that `S4` depends on
- `S5` remains the primary jobs/drafts action-UX pass
- `T5` is the intake regression and diagnostics gate for the whole program

## Why this track exists

The current onboarding flow is still too direct:

`PDF/docx/text -> extracted text -> LLM canonical JSON -> schema validation`

That works for clean CV exports, but brittle PDF layouts can still cause
provider outputs that do not map cleanly to the canonical fact-sheet schema.

The app already has:

- stronger local PDF extraction in `job_agent/services/file_extraction.py`
- schema-safe ingestion in `job_agent/services/fact_sheet_json.py`
- many normalizers in `job_agent/services/intake.py`

What it still lacks is a durable intermediate source layer between extraction
and canonical fact-sheet promotion.

## Design principles for this track

1. Preserve user-owned source material.
2. Normalize into a reviewable intermediate dossier before canonical promotion.
3. Keep canonical schema strict, but stop treating raw PDF text as canonical.
4. Add provenance and diagnostics so weird CVs are debuggable.
5. Avoid contradicting the `S` pack or reworking discovery/UI concerns already
   assigned there.

## Cross-track alignment with `S`

### Safe to implement before this track

- `S1` strict discovery geography
- `S2` JD-ready default queue cap
- `S3` in-app JD dialog and posted time

These do not depend on intake refactoring.

### Must be aligned with this track

- `S4` profile review visibility

`S4` should not be finalized against the current intake substrate alone. The
review UI needs the dossier/provenance work from `T1` through `T4` so the newly
visible fields come from a trustworthy intermediate representation.

### Should follow after this track

- `S5` jobs and drafts action UX

`S5` is mostly presentation, but it should land after the new intake review
surfaces are stable so the interaction hierarchy is not redesigned twice.

## Execution order

1. `phase_T1_source_dossier_and_multi_file_provenance.md`
2. `phase_T2_normalized_markdown_intake_layer.md`
3. `phase_T3_schema_safe_canonical_promotion.md`
4. `phase_T4_review_surface_and_field_provenance.md`
5. `phase_T5_intake_regression_corpus_and_diagnostics.md`

## Combined recommended product order

1. `phase_S1_strict_discovery_geography_and_queue_scope.md`
2. `phase_S2_jd_ready_default_queue_cap.md`
3. `phase_S3_job_detail_dialog_and_posted_time.md`
4. `phase_T1_source_dossier_and_multi_file_provenance.md`
5. `phase_T2_normalized_markdown_intake_layer.md`
6. `phase_T3_schema_safe_canonical_promotion.md`
7. `phase_T4_review_surface_and_field_provenance.md`
8. `phase_S4_profile_review_visibility_and_preference_simplification.md`
9. `phase_S5_jobs_and_drafts_action_ux.md`
10. `phase_T5_intake_regression_corpus_and_diagnostics.md`

## Validation rule

No `T` phase is complete unless it is verified at all of these levels:

1. backend/service tests
2. schema-safety tests
3. rendered onboarding review behavior where applicable
4. at least one mixed-source intake scenario:
   - multiple PDFs
   - PDF + notes
   - malformed/odd-layout PDF
