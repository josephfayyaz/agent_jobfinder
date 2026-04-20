# Codex Completion Report — Phase F5 + G5

## Phase
Phase F5+G5 — Zero-Token ATS Discovery + Posting Velocity Alerts

## Status
COMPLETE

## Completion Timestamp
2026-04-19T15:40:53+02:00

## Files Created
AGENT_SPECS/completed/phase_F5_G5_report.md
job_agent/services/ats_scanner.py
tests/test_ats_scanner.py

## Files Modified
job_agent/models.py — added `CareerPageSource.ats_type`, `CareerPageSource.ats_slug`, and new `CareerPageScanLog` model
job_agent/db.py — added `ALTER TABLE` for ATS columns and `CREATE TABLE/INDEX` for `career_page_scan_logs`
job_agent/services/career_scanner.py — added ATS-first scan path with HTML fallback, scan logging, and velocity spike detection
job_agent/worker.py — now checks velocity spikes after each career scan cycle and logs warnings
job_agent/config.py — added `VELOCITY_SPIKE_THRESHOLD` setting
job_agent/main.py — extended `POST /career-pages` with `ats_type`/`ats_slug` validation and added `GET /analytics/posting-velocity`
.env.example — documented `VELOCITY_SPIKE_THRESHOLD`
tests/test_worker.py — patched scan test to stub `check_velocity_spikes`
completed_agent_specs.txt — appended phase completion entry

## DB Changes Applied
Tables created via Base.metadata.create_all():
- `career_page_scan_logs`

Columns added to prepare_database():
- `career_page_sources.ats_type`
- `career_page_sources.ats_slug`

Additional DDL in `prepare_database()`:
- `CREATE TABLE IF NOT EXISTS career_page_scan_logs (...)`
- `CREATE INDEX IF NOT EXISTS ix_scan_logs_source_id`
- `CREATE INDEX IF NOT EXISTS ix_scan_logs_scanned_at`

## Tests Added
test_ats_scanner_greenhouse_parses_response  [tests/test_ats_scanner.py]
test_ats_scanner_lever_parses_response  [tests/test_ats_scanner.py]
test_ats_scanner_ashby_parses_response  [tests/test_ats_scanner.py]
test_scan_one_ats_creates_job_posts  [tests/test_ats_scanner.py]
test_scan_one_ats_deduplicates_existing_urls  [tests/test_ats_scanner.py]
test_scan_one_falls_back_to_html_on_ats_failure  [tests/test_ats_scanner.py]
test_check_velocity_spikes_returns_spikes_above_threshold  [tests/test_ats_scanner.py]
test_velocity_spike_threshold_filters_below_threshold  [tests/test_ats_scanner.py]
test_create_career_page_with_ats_type  [tests/test_ats_scanner.py]
test_create_career_page_rejects_invalid_ats_type  [tests/test_ats_scanner.py]
test_posting_velocity_endpoint_returns_grouped_data  [tests/test_ats_scanner.py]

## Test Run Output
265 passed, 3 warnings in 5.90s

## Ruff Output
All checks passed!

## Deviations From Spec
Added one extra endpoint test (`test_posting_velocity_endpoint_returns_grouped_data`) to verify `GET /analytics/posting-velocity`.

## Issues Encountered
None.
