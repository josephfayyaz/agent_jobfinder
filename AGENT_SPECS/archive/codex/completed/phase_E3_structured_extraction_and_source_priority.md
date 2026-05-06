# Phase E3 — Structured Extraction And Source Priority

## Goal

Prefer structured ATS or company-page job descriptions over thin board HTML, and
extract cleaner JD text before provider scoring.

This phase is the main enrichment-quality upgrade.

## Files in scope

- `/Users/youseffayyaz/Local_LLM/job_agent/services/job_fetcher.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/services/ats_discovery.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/services/ats_scanner.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/services/company_resolver.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/services/job_description_quality.py`
- add `/Users/youseffayyaz/Local_LLM/job_agent/services/job_description_extractor.py`
- `/Users/youseffayyaz/Local_LLM/pyproject.toml`
- add or extend:
  - `/Users/youseffayyaz/Local_LLM/tests/test_job_description_extractor.py`
  - `/Users/youseffayyaz/Local_LLM/tests/test_ats_scanner.py`
  - `/Users/youseffayyaz/Local_LLM/tests/test_job_fetcher.py`

## Exact implementation requirements

### 1. Introduce a dedicated extraction service

Create `job_agent/services/job_description_extractor.py`.

Its job is:

- fetch or accept HTML/plaintext
- extract the best available JD text
- return normalized text plus provenance and quality information

Required extraction order:

1. ATS-provided plaintext or HTML if already available
2. direct company or hosted apply URL if available
3. structured metadata extraction from page HTML
4. main-content extraction from page HTML
5. LinkedIn guest-page HTML fallback only if still necessary

### 2. Add deterministic extraction tools

Add and use:

- `extruct` for JSON-LD / Microdata / `JobPosting` extraction
- `trafilatura` for main-content extraction
- `readability-lxml` as a final cleanup fallback when needed

Do not add browser automation here.
Do not use the LLM to clean raw HTML.

### 3. Normalize ATS and company-page inputs

Make sure the extractor can cleanly consume:

- Greenhouse content payloads
- Lever plaintext / HTML description fields
- Ashby plaintext / HTML description fields
- direct company hosted job pages

If ATS already provides strong plaintext, do not re-fetch LinkedIn or the
company page for the same job unless quality remains below threshold.

### 4. Prefer direct sources over board sources

Update `job_fetcher.py` and related enrichment flow so source preference is:

1. ATS structured description
2. direct company/apply page
3. JobSpy LinkedIn enriched detail
4. LinkedIn guest-page HTML
5. existing thin snippet only as a temporary placeholder

Persist provenance into `extracted_metadata`, including:

- `jd_extraction_method`
- `jd_source_url`
- `jd_source_kind`
- `jd_last_enriched_at`

### 5. Re-run JD quality after extraction

Every enriched job must pass back through the Phase E1 quality evaluator.

This phase is not complete if extraction improves text but leaves stale
`jd_quality` metadata behind.

## Validation requirements

Run in `ML`:

1. install any new dependencies through the project package definition, not ad
   hoc
2. `pytest tests/test_job_description_extractor.py tests/test_job_fetcher.py tests/test_ats_scanner.py -q`
3. `ruff check job_agent/services/job_description_extractor.py job_agent/services/job_fetcher.py job_agent/services/ats_discovery.py job_agent/services/ats_scanner.py job_agent/services/job_description_quality.py tests/test_job_description_extractor.py tests/test_job_fetcher.py tests/test_ats_scanner.py`

Required tests:

- JSON-LD `JobPosting` extraction wins when present
- ATS plaintext descriptions are preserved as strong inputs
- company-page extraction improves a thin LinkedIn snippet
- extraction failure leaves a truthful unready state, not a fake ready state

## Completion report

Write:

- `/Users/youseffayyaz/Local_LLM/AGENT_SPECS/completed/phase_E3_structured_extraction_and_source_priority.md`

Then append this phase to
`/Users/youseffayyaz/Local_LLM/completed_agent_specs.txt`.
