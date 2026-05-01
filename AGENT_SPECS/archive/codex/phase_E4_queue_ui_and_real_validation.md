# Phase E4 — Queue UI And Real Validation

## Goal

Make the jobs UI truthful after the enrichment changes, then validate the whole
flow with real browser runs and the live configured provider.

This phase must convert the technical fixes from E1-E3 into a user-visible,
release-meaningful queue.

## Files in scope

- `/Users/youseffayyaz/Local_LLM/job_agent/routers/jobs.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/routers/job_views.py`
- `/Users/youseffayyaz/Local_LLM/frontend/templates/jobs.html`
- `/Users/youseffayyaz/Local_LLM/frontend/templates/partials/job_row.html`
- `/Users/youseffayyaz/Local_LLM/frontend/static/jobs.js`
- `/Users/youseffayyaz/Local_LLM/job_agent/services/workflows.py`
- `/Users/youseffayyaz/Local_LLM/tests/test_api.py`
- `/Users/youseffayyaz/Local_LLM/tests/test_review_queue.py`
- add a real-runtime report under:
  - `/Users/youseffayyaz/Local_LLM/mac_full_test_data_temp/results/`

## Exact implementation requirements

### 1. Add a truthful lane or visibility path for not-yet-scorable jobs

Jobs that are awaiting enrichment must not disappear behind the default fit
threshold as if they were true low-fit matches.

Implement a visible UI path for them, using one of these acceptable patterns:

- a dedicated queue lane such as `awaiting enrichment`
- or a dedicated grouped section on the jobs page

Whichever pattern is chosen, it must be:

- explicit
- queryable
- testable
- not hidden behind `show_all=true`

### 2. Update threshold logic

Threshold behavior must distinguish:

- `threshold_eligible = true` scored jobs
- `threshold_eligible = false` awaiting-enrichment jobs

Required rule:

- only threshold-eligible jobs participate in the `>= threshold` visibility rule
- awaiting-enrichment jobs remain visible through their dedicated truthful path

### 3. Update row copy and badges

The row UI must stop implying that a thin JD has a trustworthy fallback fit.

Required copy changes:

- replace `Fallback score` for weak-JD rows with a truthful label such as
  `Awaiting enrichment`
- show `JD quality` status in the job row
- explain why the job is not yet fully scored

Keep provider-unavailable fallback distinct from awaiting-enrichment.

### 4. Extend discovery progress and summaries

The discovery task result payload should report at least:

- `awaiting_enrichment_count`
- `provider_scored_count`
- `fallback_scored_count`
- `ready_for_threshold_count`

The jobs page should show the new stage counts without implying that the search
failed.

### 5. Perform real runtime validation

Use the real app, real `ML` environment, real database, real configured
provider, and real browser testing.

Do not use fake LM Studio.
If the model is not available, stop and ask the user to load it.

Minimum runtime validation:

1. rerun two non-tech users
2. verify jobs are still real and contextually aligned
3. verify the default queue is now truthful even when some jobs remain unscored
4. verify improved ATS/direct-source rows can reach real provider scoring
5. save results into `mac_full_test_data_temp/results/`

## Validation requirements

Run in `ML`:

1. `pytest tests/test_api.py tests/test_review_queue.py tests/test_job_fit_scoring.py tests/test_job_fetcher.py -q`
2. `ruff check job_agent/routers/jobs.py job_agent/routers/job_views.py job_agent/services/workflows.py frontend/static/jobs.js tests/test_api.py tests/test_review_queue.py`

Then run the real browser/runtime audit and save:

- one combined summary report
- one report per user case

## Acceptance gate

This phase passes only if the final runtime result is more truthful than the
current baseline.

Minimum acceptance:

- real jobs still appear for both non-tech users
- jobs with thin JDs no longer masquerade as low-fit shortlist failures
- the default UI clearly separates scored results from awaiting-enrichment work

## Completion report

Write:

- `/Users/youseffayyaz/Local_LLM/AGENT_SPECS/completed/phase_E4_queue_ui_and_real_validation.md`

Then append this phase to
`/Users/youseffayyaz/Local_LLM/completed_agent_specs.txt`.
