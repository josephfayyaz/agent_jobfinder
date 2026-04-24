# Phase I8 — Market Skill Gap Dashboard

Status: COMPLETE
Completed: 2026-04-23T16:21:57+02:00

## Summary

Implemented market-level skill-gap analytics for generated CV drafts. The CV
workflow now stores `review_feedback["missing_keywords"]` by comparing extracted
JD keywords against candidate known skills, and `/ui/analytics` now lazy-loads a
Market Skill Gaps dashboard.

## Implementation Notes

- Added zero-token `missing_keywords` computation in `CVWorkflowService`.
- Added `SkillGapAnalyticsService` to aggregate missing keywords across
  non-archived drafts.
- Adapted the spec to this schema: `ResumeDraft` does not have
  `candidate_id` or `application_status`, so the service keeps the public
  `candidate_id` argument for future compatibility and excludes drafts whose
  linked applications are all archived.
- Added `GET /analytics/skill-gaps` with JSON and HTMX partial responses.
- Added `partials/skill_gaps.html` with a CSS-only horizontal bar chart.
- Updated `/ui/analytics` to load the new dashboard while preserving the older
  rejection-analytics skill-gap summary when present.
- Updated roadmap docs and completion log.

## Verification

- `python -m pytest tests/test_skill_gap_analytics.py -q`
  - Result: `6 passed`
- `python -m pytest tests/test_skill_gap_analytics.py tests/test_ui_analytics.py -q`
  - Result: `9 passed`
- `python -m pytest --tb=short -q`
  - Result: `392 passed, 4 warnings`
- `ruff check`
  - Result: clean
