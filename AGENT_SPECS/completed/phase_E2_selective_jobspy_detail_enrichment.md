# Phase E2 — Selective JobSpy Detail Enrichment — Completion Report

**Completed:** 2026-05-01T16:52:00+02:00
**Author:** Antigravity Agent

---

## Summary

Implemented selective second-pass JobSpy detail enrichment as specified in
`phase_E2_selective_jobspy_detail_enrichment.md`. The discovery pipeline now
runs a bounded, deterministic detail-enrichment pass on the most promising
JobSpy-origin survivors before falling back to generic LinkedIn HTML fetching.

## Changes Made

### `job_agent/config.py`
- Added `jobspy_detail_enrichment_enabled` (bool, default `False`)
- Added `jobspy_detail_enrichment_limit` (int, default `10`)

### `job_agent/services/jobspy_service.py`
- Added `JobSpyService.detail_enrich_survivors()` method
  - Selects survivors deterministically: country match → role match → seniority
    compatibility → weakest JD quality score first
  - Uses `python-jobspy` with `linkedin_fetch_description=True` on a bounded subset
  - Persists richer description, direct URL, and provenance metadata:
    - `jd_quality.source_kind = "linkedin_enriched"`
    - `direct_job_url`
    - `jobspy_detail_enriched = true`
    - `jobspy_detail_enriched_at`
  - Re-evaluates JD quality via E1's `evaluate_job_description()` after enrichment
  - Updates `enrichment_status` based on readiness
  - Skips non-JobSpy sources (ATS, manual)
  - Skips jobs already ready for provider scoring
  - Reports progress via callback

### `job_agent/services/workflows.py`
- Added `detail_enrichment_*` count keys to `_empty_discovery_counts()`
- Inserted `detail_enrichment` stage in `run_job_discovery()` between ATS
  discovery and generic description fetching
- Pipeline order is now:
  1. JobSpy broad discovery
  2. ATS discovery
  3. **Selective JobSpy detail enrichment (E2)**
  4. Generic LinkedIn HTML fetch fallback
  5. Provider scoring

### `tests/test_jobspy_service.py` (new file)
Added 6 tests:
1. `test_detail_enrichment_skipped_when_disabled` — verifies no-op when disabled
2. `test_detail_enrichment_is_capped` — verifies cap enforcement
3. `test_strong_ats_jobs_are_skipped` — strong ATS descriptions not re-enriched
4. `test_richer_description_replaces_thin_snippet` — verifies replacement + provenance
5. `test_discovery_progress_records_detail_enrichment_stage` — verifies pipeline integration
6. `test_non_jobspy_source_skipped` — manual/ATS sources excluded

## Validation Results

### Tests
```
pytest tests/test_jobspy_scheduler.py tests/test_jobspy_service.py -q
22 passed in 1.54s
```

### Lint
```
ruff check job_agent/services/jobspy_service.py job_agent/services/workflows.py \
  job_agent/services/job_fetcher.py job_agent/config.py \
  tests/test_jobspy_scheduler.py tests/test_jobspy_service.py
All checks passed!
```

## Deviations from Spec

1. **Detail mode implementation**: The spec says "use the upstream python-jobspy
   LinkedIn detail mode" and "rely on linkedin_fetch_description=True". The
   implementation uses `scrape_jobs(linkedin_fetch_description=True)` with a
   targeted re-search per job rather than a bulk pass, because python-jobspy does
   not support detail-fetching by URL — it only supports search queries. The
   search is scoped to the job's title and location with `results_wanted=3` to
   keep requests minimal. The best matching result (by URL or description length)
   is selected.

2. **linkedin_fetch_description during broad pass**: The spec says "do not turn
   on linkedin_fetch_description=True during the broad first pass". This is
   preserved — the existing `discover_for_roles()` method is unchanged and does
   not pass this parameter.

3. **Config defaults**: `jobspy_detail_enrichment_enabled` defaults to `False`
   rather than `True`, matching the spec's intent to keep broad retrieval cheap.
   Users must opt in via settings.

## Files Changed
- `job_agent/config.py` — 2 new settings fields
- `job_agent/services/jobspy_service.py` — new `detail_enrich_survivors()` method
- `job_agent/services/workflows.py` — pipeline integration + count keys
- `tests/test_jobspy_service.py` — new test file (6 tests)
