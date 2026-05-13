# Codex Completion Report — Phase S0A User-Initiated Discovery and Source Catalog

## Phase
Phase S0A — User-Initiated Discovery and Source Catalog

## Status
COMPLETE

## Completion Timestamp
2026-05-13T16:37:29+0200

## Files Created
None.

## Files Modified
job_agent/worker.py — removed idle Gmail, career-page, and scheduled JobSpy job-creation paths; kept queued task processing and enrichment.
job_agent/seed.py — stopped inserting startup career-page watchlist rows through reference seeding.
job_agent/db.py — stopped seeding Italy tech company sources during database preparation.
job_agent/config.py — removed automatic career-page scan setting and scheduled JobSpy interval; clarified explicit discovery descriptions.
job_agent/user_config.py — removed career_page_auto_scan from editable settings.
job_agent/routers/jobs.py — changed explicit discovery payloads to job-board-only by default with run-scoped source fields.
job_agent/routers/job_queue_actions.py — aligned secondary discovery queue helper with job-board-only defaults.
job_agent/services/job_discovery_workflow.py — defaulted ATS/direct-company discovery off unless selected source IDs are provided.
job_agent/services/ats_discovery.py — required explicit source IDs for ATS discovery.
job_agent/services/jobspy_service.py — updated disabled-discovery wording to explicit searches.
job_agent/onboard.py — renamed JobSpy onboarding prompt to explicit job searches.
frontend/templates/jobs.html — updated discovery copy to user-started search behavior.
frontend/templates/partials/settings/discovery_section.html — removed scheduled/automatic discovery wording.
frontend/static/jobs.js — updated disabled-discovery message.
.env.example — removed automatic career-page and scheduled JobSpy interval examples.
temp_mac_test/runtime_env.sh — removed temporary career-page auto-scan override.
tests/test_worker.py — changed worker expectations to no idle job discovery.
tests/test_jobspy_scheduler.py — updated scheduled discovery tests for queued-only behavior and selected ATS sources.
tests/test_ats_scanner.py — updated ATS discovery calls to pass explicit source IDs.
tests/test_career_scanner.py — updated career-page seed test to expect no runtime seeding.
tests/test_seed_companies.py — added reference-data test proving no career-page runtime seeding.
tests/test_api.py — updated discovery task payload assertions and UI copy expectation.
tests/test_onboarding.py — updated JobSpy onboarding prompt expectation.
AGENT_SPECS/pending/codex/README.md — removed S0A from active pending order and added future company-source catalog note.
AGENT_SPECS/master_plans/codex/phase_S0_search_quality_and_cv_usability_execution_plan.md — added S0A to the historical execution order and rationale.

## DB Changes Applied
None.

## Tests Added
test_worker_does_not_run_gmail_sync_from_idle_loop [tests/test_worker.py]
test_worker_does_not_scan_career_pages_from_idle_loop [tests/test_worker.py]
test_worker_does_not_run_scheduled_jobspy_from_idle_loop [tests/test_worker.py]
test_reference_data_does_not_seed_career_page_sources [tests/test_seed_companies.py]
test_job_discovery_default_payload_does_not_call_ats [tests/test_jobspy_scheduler.py]

## Test Run Output
125 passed in 2.34s

Fresh runtime smoke:
{'before': (0, 0, 0), 'after': (0, 0, 0)}

Full suite:
6 failed, 730 passed, 1 skipped in 38.75s

## Ruff Output
All checks passed.

## Deviations From Spec
No schema column was added for source origin. The implementation avoids scanning legacy seeded rows by removing idle discovery and making ATS/company discovery require explicit source IDs, which satisfies the safety requirement without a migration.

## Issues Encountered
Existing Gmail auto-sync was also an idle job-creation path, so it was removed from worker idle behavior to keep the S0A contract strict. Manual Gmail sync remains available through the route.

Full-suite failures remained in the same unrelated areas observed before S0A:
legacy CV workflow e2e score/status expectations, brittle intake JS string guards,
and stale LLMRouter._call_lm_studio test coverage.
