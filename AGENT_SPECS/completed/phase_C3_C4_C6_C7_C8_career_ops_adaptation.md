# Phase C3/C4/C6/C7/C8 — Career-Ops Adaptation Report

## Summary

Adapted the remaining `career_ops_adaptation` phases into Job Agent with product-specific naming and UX:

- `C3` became `Source Trail` + `Discovery Health`
- `C4` became `Application Snapshot` + `Queue Package`
- `C6` became `Story Bank`
- `C7` became `Opportunity Snapshot`
- `C8` became `Offer Compass`

The implementation keeps the `career-ops` ideas that fit Job Agent's local-first workflow, but avoids copying the original names or operator-style UX directly.

## Implemented

### C3 — Discovery Pipeline Upgrade

- Added shared discovery metadata and dedup helpers in `job_agent/services/discovery_hub.py`
- Stamped source-trail metadata and discovery events in:
  - `job_agent/services/jobspy_service.py`
  - `job_agent/services/career_scanner.py`
  - `job_agent/services/gmail.py`
  - existing manual job creation path in `job_agent/routers/jobs.py`
- Prioritized enrichment for shortlist/review lanes in `job_agent/services/job_fetcher.py`
- Exposed discovery-health analytics in `job_agent/routers/applications.py`
- Added Discovery Health analytics partial at `frontend/templates/partials/discovery_health.html`
- Surfaced source badges and confidence details on the jobs queue in `frontend/templates/partials/job_row.html`

### C4 — Shortlist-Centric Apply Flow

- Added `package_summary` and fast-lane logic to queue payloads in `job_agent/routers/job_views.py`
- Added `Application Snapshot` partial route and UI in:
  - `job_agent/routers/jobs.py`
  - `frontend/templates/partials/apply_package_check.html`
  - `frontend/templates/jobs.html`
  - `frontend/templates/partials/job_row.html`
- Preserved low-friction package generation for shortlist/high-readiness jobs while requiring explicit confirmation for weaker cases

### C6 — Story Bank

- Added persistent `InterviewStory` model in `job_agent/models.py`
- Added `InterviewBankService` in `job_agent/services/interview_bank.py`
- Stories now rebuild from:
  - verified candidate facts
  - approved drafts
  - accepted bullet clarifications
- Added Story Bank UI and rebuild action in:
  - `job_agent/routers/career_tools.py`
  - `frontend/templates/story_bank.html`

### C7 — Opportunity Snapshot

- Added persistent `CompanySnapshot` model in `job_agent/models.py`
- Added `CompanySnapshotService` in `job_agent/services/company_snapshot.py`
- Added snapshot UI route and lazy-loaded partial in:
  - `job_agent/routers/jobs.py`
  - `frontend/templates/partials/company_snapshot.html`
  - `frontend/templates/jobs.html`
  - `frontend/templates/partials/job_row.html`
- Snapshot availability is limited to shortlisted or high-fit roles

### C8 — Offer Compass

- Added persistent `OfferDecision` model in `job_agent/models.py`
- Added `OfferCompassService` in `job_agent/services/offer_compass.py`
- Added Offer Compass UI in:
  - `job_agent/routers/career_tools.py`
  - `frontend/templates/offer_compass.html`

## Verification

- `python -m py_compile ...` on all touched Python files passed
- `ruff check ...` on all touched Python files passed
- Targeted regression suite passed:
  - `pytest tests/test_career_ops_adaptation.py tests/test_career_scanner.py tests/test_gmail.py tests/test_job_fetcher.py tests/test_review_queue.py tests/test_ui_analytics.py --tb=short -q`
  - Result: `27 passed`
- Full test suite passed:
  - `pytest --tb=short -q`
  - Result: `464 passed`

## Live Smoke Check

Ran a temporary local server with a clean workspace and verified:

- `GET /health` → `200`
- `GET /ui/story-bank` → `200`
- `GET /ui/offers` → `200`
- `GET /analytics/discovery-health` with `HX-Request` → `200`

Confirmed rendered output contained:

- `Story Bank`
- `Offer Compass`
- `Discovery Health`

## Notes

- The remaining master-plan files can stay in `AGENT_SPECS/master_plans/codex/career_ops_adaptation/` as historical planning references.
- The shipped UX uses Job Agent’s own vocabulary rather than mirroring `career-ops` labels directly.
