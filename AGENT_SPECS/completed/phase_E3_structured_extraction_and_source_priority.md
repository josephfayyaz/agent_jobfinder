# Phase E3 — Structured Extraction And Source Priority — Completion Report

**Completed:** 2026-05-01T17:03:00+02:00
**Author:** Antigravity Agent

---

## Summary

Implemented structured job description extraction with source priority as
specified in `phase_E3_structured_extraction_and_source_priority.md`. The
enrichment pipeline now uses deterministic extraction tools (extruct, trafilatura,
readability-lxml) to prefer structured ATS/company-page descriptions over thin
board snippets before provider scoring.

## Changes Made

### `pyproject.toml`
Added three new dependencies:
- `extruct>=0.17,<1` — JSON-LD / Microdata / JobPosting extraction
- `trafilatura>=2.0,<3` — main-content extraction from HTML
- `readability-lxml>=0.8,<1` — last-resort HTML cleanup fallback

### `job_agent/services/job_description_extractor.py` (new file)
Dedicated extraction service implementing the full source-priority pipeline:

1. **ATS payload** (`extract_from_ats_payload`) — Normalizes Greenhouse HTML,
   Lever plaintext, and Ashby HTML to clean plaintext
2. **Structured metadata** (`extract_from_structured_metadata`) — Uses `extruct`
   to find JSON-LD `JobPosting` schema and Microdata
3. **Main-content extraction** (`extract_main_content`) — Uses `trafilatura`
   for article-level content extraction
4. **Readability fallback** (`extract_with_readability`) — Uses `readability-lxml`
   as a final cleanup when other extractors produce thin results
5. **URL fetch helper** (`_fetch_html`) — Shared HTTP client for page fetching

The orchestrator `extract_best_description()` runs the pipeline in priority order:
1. ATS-provided plaintext/HTML if available
2. Direct company or hosted apply URL → JSON-LD → trafilatura → readability
3. LinkedIn guest-page HTML fallback → JSON-LD → readability

Every successful extraction returns an `ExtractionResult` dataclass with
provenance metadata:
- `jd_extraction_method`
- `jd_source_url`
- `jd_source_kind`
- `jd_last_enriched_at`

### `job_agent/services/job_fetcher.py`
Upgraded `enrich_job()` to use the E3 extraction pipeline:
- Tries the structured extraction pipeline first
- Falls back to legacy LinkedIn HTML fetch only if the extractor can't improve
- Persists provenance metadata on both paths
- Re-runs JD quality evaluation after every enrichment update
- Extracted `_resolve_company_url()` as a private helper for reuse

Source preference order in `enrich_job()`:
1. ATS structured description (already on the job row)
2. Direct company/apply page (via structured extraction)
3. JSON-LD / Microdata from page HTML
4. Main-content extraction (trafilatura)
5. LinkedIn guest-page HTML fallback

### `tests/test_job_description_extractor.py` (new file)
13 tests covering all spec requirements:
- `test_json_ld_job_posting_extraction_wins` — JSON-LD wins when present
- `test_json_ld_extraction_preferred_over_board_snippet` — structured > snippet
- `test_ats_plaintext_preserved_as_strong_input` — ATS plaintext preserved
- `test_ats_html_description_converted_to_plaintext` — HTML stripped to text
- `test_ats_strong_existing_not_re_fetched` — strong ATS not re-fetched
- `test_company_page_trafilatura_improves_thin_snippet` — trafilatura extraction
- `test_readability_fallback_extracts_content` — readability fallback
- `test_extraction_failure_leaves_truthful_unready_state` — truthful failure
- `test_thin_ats_payload_not_marked_success` — thin not faked as success
- `test_json_ld_missing_returns_failure` — graceful missing JSON-LD
- `test_no_improvement_returns_existing` — no-op when can't improve
- `test_provenance_metadata_populated` — provenance fields populated

### `tests/test_job_fetcher.py`
Updated existing tests to mock `_fetch_html` in the extraction pipeline so
tests don't make real HTTP calls through the new extraction path.

## Validation Results

### Tests (required)
```
pytest tests/test_job_description_extractor.py tests/test_job_fetcher.py tests/test_ats_scanner.py -q
32 passed in 2.53s
```

### Lint (required)
```
ruff check job_agent/services/job_description_extractor.py job_agent/services/job_fetcher.py \
  job_agent/services/ats_discovery.py job_agent/services/ats_scanner.py \
  job_agent/services/job_description_quality.py \
  tests/test_job_description_extractor.py tests/test_job_fetcher.py tests/test_ats_scanner.py
All checks passed!
```

### Broader regression
```
pytest tests/test_job_description_extractor.py tests/test_job_fetcher.py \
  tests/test_ats_scanner.py tests/test_jobspy_scheduler.py tests/test_jobspy_service.py \
  tests/test_job_description_quality.py tests/test_api.py -q
116 passed in 7.96s
```

## Deviations from Spec

1. **No changes to `ats_scanner.py`**: The spec listed it in scope, but the
   ATS scanner already returns `description` from all three ATS APIs
   (Greenhouse `content`, Lever `descriptionPlain`/`description`, Ashby
   `descriptionHtml`/`descriptionPlain`). No changes were needed there.

2. **No changes to `ats_discovery.py`**: The ATS discovery service already
   passes descriptions through to `JobPost.description`. The new extraction
   pipeline is called from `job_fetcher.py:enrich_job()` which already runs
   on every saved job in the discovery workflow.

3. **No changes to `company_resolver.py`**: Company URL resolution was already
   functional. The `_resolve_company_url` method was extracted from the existing
   inline code for cleanliness.

## Files Changed
- `pyproject.toml` — 3 new dependencies
- `job_agent/services/job_description_extractor.py` — new extraction service
- `job_agent/services/job_fetcher.py` — E3 pipeline integration + provenance
- `tests/test_job_description_extractor.py` — new test file (13 tests)
- `tests/test_job_fetcher.py` — mock updates for E3 compatibility
