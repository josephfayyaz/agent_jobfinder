# Phase P2b — Enrichment Hardening and Source Quality Gates

## Scope delivered

- Completed enrichment status tiering with explicit transitions:
  - `pending`, `ok`, `partial`, `needs_input`, `failed`
- Improved enrichment classification logic in fetcher:
  - short/low-detail descriptions now marked `partial`
  - missing source + existing description marked `partial`
  - empty description with no useful fetch marked `needs_input` / `failed` by path.
- Improved posted-date handling:
  - keeps JSON-LD `datePosted` extraction
  - persists `posted_date` from fetch details in threaded enrichment and single-job enrichment.
- Preserved compatibility with legacy monkeypatched fetch hook in threaded path.
- Draft lockout semantics maintained and surfaced:
  - queue/draft blocked for `needs_input` or empty description
  - UI now clearly explains lock reason and next action.
- Jobs row now carries `has_description` for lock-state rendering.

## Files changed (main)

- [job_fetcher.py](/Users/youseffayyaz/Local_LLM/job_agent/services/job_fetcher.py)
- [jobs.py](/Users/youseffayyaz/Local_LLM/job_agent/routers/jobs.py)
- [job_views.py](/Users/youseffayyaz/Local_LLM/job_agent/routers/job_views.py)
- [job_row.html](/Users/youseffayyaz/Local_LLM/frontend/templates/partials/job_row.html)

## Tests updated/added

- [test_job_fetcher.py](/Users/youseffayyaz/Local_LLM/tests/test_job_fetcher.py)
- [test_job_enrichment_lock.py](/Users/youseffayyaz/Local_LLM/tests/test_job_enrichment_lock.py)
- Existing provider/date extraction checks remain covered:
  - [test_provider_resilience.py](/Users/youseffayyaz/Local_LLM/tests/test_provider_resilience.py)

## Validation

- Targeted tests:
  - `tests/test_job_fetcher.py`
  - `tests/test_job_enrichment_lock.py`
  - `tests/test_parallel_ingestion.py::test_enrich_parallel_writes_descriptions`
- Full suite:
  - `pytest --tb=short -q` → pass
- Lint:
  - `ruff check` → pass

## Notes

- No new DB migration was required in this phase because `enrichment_status` already exists and is idempotently added in `db.py`.
