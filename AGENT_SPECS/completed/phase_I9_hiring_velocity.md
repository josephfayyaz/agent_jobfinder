# Phase I9 — Hiring Velocity Signal

Status: COMPLETE
Completed: 2026-04-23T15:30:06+02:00

## Summary

Implemented a zero-token hiring velocity signal for company career-page scans.
Companies are marked as surging when at least two scan logs in the last seven
days report `new_jobs > 0`.

## Changes

- Added `GET /career-pages/{source_id}/velocity` for single-source scan history
  and surge status.
- Added `GET /career-pages/velocity/bulk` for efficient companies-page badge
  decoration.
- Updated `/ui/companies` with non-blocking progressive enhancement that adds a
  ⚡ badge next to surging companies and a legend below the table.
- Added regression tests for no logs, surging sources, single-scan non-surges,
  and old-scan exclusion.
- Updated project roadmap docs to mark I9 complete.

## Verification

- `python -m pytest tests/test_hiring_velocity.py tests/test_setup_gate.py -q`
  - Result: `7 passed`
- `python -m pytest --tb=short -q`
  - Result: `380 passed, 4 warnings`
- `ruff check`
  - Result: clean
