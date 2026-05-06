# Phase E2 — Selective JobSpy Detail Enrichment

## Goal

Use `python-jobspy` more intelligently before the app falls back to brittle
LinkedIn guest-page scraping.

This phase must keep broad retrieval cheap, then selectively spend extra
requests on the most promising JobSpy survivors.

## Files in scope

- `/Users/youseffayyaz/Local_LLM/job_agent/services/jobspy_service.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/services/workflows.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/services/job_fetcher.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/config.py`
- `/Users/youseffayyaz/Local_LLM/tests/test_jobspy_scheduler.py`
- add `/Users/youseffayyaz/Local_LLM/tests/test_jobspy_service.py` if needed

## Exact implementation requirements

### 1. Keep the current two-stage retrieval model explicit

Stage 1 remains the cheap discovery pass:

- query all selected roles
- save normalized rows
- apply country / role / seniority filters
- deduplicate before expensive enrichment

Stage 2 is a new selective detail pass for JobSpy-origin jobs only.

### 2. Add a selective detail-enrichment helper to JobSpyService

Extend `JobSpyService` with a second-pass helper for LinkedIn-origin rows.

The helper must:

- use the upstream `python-jobspy` LinkedIn detail mode
- rely on `linkedin_fetch_description=True`
- only run for a bounded subset of survivors
- persist any richer description text and any direct apply/company URL returned
  by JobSpy

Do not turn on `linkedin_fetch_description=True` during the broad first pass.

### 3. Choose survivors deterministically

The second pass must not run on every ingested JobSpy job.

Select candidates for second-pass enrichment using a deterministic priority such
as:

1. correct country
2. role-title match
3. seniority compatibility
4. best existing fallback/track score
5. no strong ATS description already present
6. current JD quality below ready threshold

Make the second-pass cap configurable.

Add settings in `config.py` for at least:

- `jobspy_detail_enrichment_enabled`
- `jobspy_detail_enrichment_limit`

### 4. Persist source provenance improvements

For rows improved by this pass, stamp metadata such as:

- `jd_quality.source_kind = "linkedin_enriched"`
- `direct_job_url`
- `jobspy_detail_enriched = true`
- `jobspy_detail_enriched_at`

If a direct URL is returned, preserve it for later company-page extraction in
Phase E3.

### 5. Integrate into the queued discovery workflow

Update `workflows.py` so the queued discovery task runs:

1. cheap JobSpy discovery
2. ATS discovery
3. selective JobSpy detail enrichment
4. generic fetch/extract fallback
5. provider scoring

Progress messages must remain truthful and granular enough for the jobs page.

## Validation requirements

Run in `ML`:

1. `pytest tests/test_jobspy_scheduler.py tests/test_jobspy_service.py -q`
2. `ruff check job_agent/services/jobspy_service.py job_agent/services/workflows.py job_agent/services/job_fetcher.py job_agent/config.py tests/test_jobspy_scheduler.py tests/test_jobspy_service.py`

Required tests:

- second pass is skipped when disabled
- second pass is capped
- strong ATS jobs are not redundantly re-enriched through JobSpy
- richer description/direct URL data replaces thin LinkedIn snippets
- discovery progress records the detail-enrichment stage

## Completion report

Write:

- `/Users/youseffayyaz/Local_LLM/AGENT_SPECS/completed/phase_E2_selective_jobspy_detail_enrichment.md`

Then append this phase to
`/Users/youseffayyaz/Local_LLM/completed_agent_specs.txt`.
