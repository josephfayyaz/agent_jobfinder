# Phase R2 — JobSpy Discovery Backend

## Goal

Replace the current one-click, opaque `Discover (JobSpy)` behavior with a
structured backend discovery run that:

- uses `JobSpy` only for this release phase
- fans out across all configured desired roles, not just the first role
- applies cheap hard filters before expensive work
- records explicit progress and result counts
- fails loudly when JobSpy is disabled or unavailable

This phase is backend-first. Do not build the UI progress panel here.

## Current problems to fix

The current implementation has these release blockers:

1. `/ui/jobs/discover` silently uses only `_default_jobspy_query()` and ignores
   roles 2-4.
2. JobSpy disabled and JobSpy missing-package cases are not surfaced as
   meaningful discovery results.
3. The route returns `204` with no summary, making zero-result and broken runs
   indistinguishable.
4. There is no durable progress model for long-running discovery.

## Scope

Implement a reusable backend discovery run system for JobSpy only.

Do not activate:

- career-page scanning as part of the main user discovery action
- ATS retrieval in the user discovery action
- Apify
- Gmail discovery

## Read these files first

1. `job_agent/routers/jobs.py`
2. `job_agent/worker.py`
3. `job_agent/services/jobspy_service.py`
4. `job_agent/search_preferences.py`
5. `job_agent/models.py`
6. `job_agent/schemas.py`
7. `tests/test_jobspy_scheduler.py`
8. `tests/test_api.py`
9. `tests/test_e2e_full_journey.py`

## Architecture requirement

Prefer reusing `WorkflowTask` for discovery runs instead of creating a brand-new
table. Only add a new model if there is a hard blocker that cannot be solved
cleanly with `WorkflowTask`.

Recommended shape:

- `WorkflowTask.kind = "job_discovery"`
- `status`: `pending | running | completed | failed`
- `payload` stores requested search scope
- `result` stores progress counts and summary

If `WorkflowTask` reuse works cleanly, use it.

## Implementation instructions

### Part 1: Discovery task creation

Add a backend API that creates a discovery run rather than executing JobSpy
inline inside the request.

Required behavior:

- it captures:
  - active candidate id
  - active provider mode
  - one selected country
  - all desired roles (up to 4)
  - seniority target
- it creates one `WorkflowTask` of kind `job_discovery`
- it returns a task id immediately

### Part 2: Worker processing

Teach `job_agent/worker.py` and related services to process `job_discovery`
tasks.

Required behavior:

- query JobSpy once per configured role
- dedupe results across all queried roles
- track counts for:
  - roles queried
  - raw hits
  - duplicates
  - rejected by country
  - rejected by role
  - rejected by seniority
  - queued for scoring
  - saved jobs
- write progress updates into the task state while running

### Part 3: Hard filters before scoring

Before any expensive enrichment or AI work, apply cheap filters.

For this release, these are hard constraints:

- selected country
- role relevance
- seniority relevance

Notes:

- use title/location/seniority metadata first
- keep the logic deterministic and cheap
- do not use AI to decide basic retrieval eligibility

### Part 4: Error behavior

Required explicit failures:

- if `use_jobspy` is off, discovery task creation or execution must surface a
  meaningful error state
- if the `jobspy` package is missing in `ML`, the task must fail explicitly
- zero-result runs must complete with a summary, not look like a crash

Do not keep the current silent-zero behavior for disabled / unavailable cases.

### Part 5: Retrieval scope

Keep the active source scope narrow:

- source used in task execution: `JobSpy` only
- do not trigger `CareerPageScanner` from this path
- do not mix manual/career-page discovery counts into the run summary

## Acceptance criteria

1. Discovery tasks fan out across every configured desired role.
2. Backend progress and summary counts exist for a run.
3. Disabled/missing JobSpy becomes an explicit failure, not a fake success.
4. Zero-result runs still produce a usable summary payload.
5. No UI work is required yet, but the backend APIs are ready for polling.

## Required tests

Add or update tests covering:

- multi-role JobSpy fan-out
- disabled JobSpy failure reporting
- missing-package failure reporting
- worker processing of `job_discovery` tasks
- dedupe across multiple role queries

Minimum commands to run in `ML`:

```bash
CONDA_BASE="$(conda info --base 2>/dev/null)"
"$CONDA_BASE/envs/ML/bin/python" -m pytest tests/test_jobspy_scheduler.py tests/test_api.py --tb=short -q
```

If you add dedicated discovery task tests, include them in the command and the
report.

## Completion report

When complete, write:

- `AGENT_SPECS/completed/phase_R2_jobspy_discovery_backend.md`

Use `AGENT_SPECS/completed/REPORT_TEMPLATE.md`.

Then append this phase to `completed_agent_specs.txt` using the required format
from `phase_R0_discovery_execution_order.md`.
