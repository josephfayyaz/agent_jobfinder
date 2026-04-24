# Phase I10 — Role Readiness Map

Status: COMPLETE
Completed: 2026-04-23T16:14:25+02:00

## Summary

Implemented a Role Readiness Map that compares a job description against the
candidate fact sheet before CV generation. The feature is implemented as a new
`FitGapService`, cached on `JobPost.extracted_metadata["fit_gaps"]`, and exposed
through JSON and HTMX partial endpoints.

## Implementation Notes

- Adapted the spec for the current codebase: `JobPost.id` is a UUID, and
  `LLMRouter.generate()` requires `role`, `system_prompt`, and `user_prompt`.
- Added `FactSheetRenderer.render_short_summary(candidate)` as a reusable
  prompt-sized fact summary helper.
- Added idempotent SQLite migration guard for `job_posts.extracted_metadata`.
- Added `GET /jobs/{job_id}/fit-gaps` and `POST /jobs/{job_id}/fit-gaps/clear`.
- Added `partials/fit_gaps.html` with the 5 required user-facing columns:
  Fit Level, What They Ask For, What You Have, Best Next Move, Draft Readiness.
- Added an on-demand `Readiness` action on the jobs table so the page does not
  trigger LLM calls for every visible job.
- Added a draft-detail “Gaps to Address Before Sending” panel showing unresolved
  Thin Proof and Missing items.

## Verification

- `python -m pytest tests/test_fit_gap.py -q`
  - Result: `6 passed`
- `python -m pytest --tb=short -q`
  - Result: `386 passed, 4 warnings`
- `ruff check`
  - Result: clean
