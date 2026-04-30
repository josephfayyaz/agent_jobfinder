# Phase R4 — Jobs Progress And Results UI

## Goal

Make discovery visibly reliable in the web app.

After this phase, the user should be able to start discovery from the Jobs page
and see:

- that work has started
- what phase it is in
- how many jobs were found / filtered / scored / saved
- whether the run failed, found zero jobs, or completed successfully

The current blind reload behavior must be removed from the main discovery
interaction.

## Read these files first

1. `frontend/templates/jobs.html`
2. `frontend/static/app.js`
3. `job_agent/routers/jobs.py`
4. `job_agent/routers/job_views.py`
5. `job_agent/routers/ui_context.py`
6. `job_agent/services/job_signals.py`
7. Any new backend files created in R2 and R3

## Implementation instructions

### Part 1: Discovery action UX

Replace the current `Discover (JobSpy)` flow that posts and reloads
immediately.

Required behavior:

- click starts a discovery run
- button becomes disabled while active
- page shows a progress panel or progress bar
- frontend polls backend task status until terminal state
- terminal states are:
  - `completed`
  - `failed`
  - `completed_zero_results`

Do not use the current “always reload after request” behavior for this action.

### Part 2: Progress phases

Show human-readable phases. At minimum:

- `Preparing search`
- `Querying JobSpy`
- `Deduplicating`
- `Applying basic filters`
- `Scoring jobs`
- `Saving results`
- `Completed`

### Part 3: Summary panel

When a run completes, show a concise summary like:

- roles queried
- raw hits
- duplicates
- filtered out
- scored
- saved
- visible after threshold / cap

The summary must distinguish:

- true failure
- valid zero-result run
- successful completion

### Part 4: Queue behavior

Update the visible queue behavior to match the release contract:

- default visible threshold is the discovery fit threshold
- default visible cap is `80`
- `show_all=true` remains the escape hatch

If there are more than `80` qualifying jobs, show the best `80` in the default
view and surface that truncation in the UI.

### Part 5: Country / language / provider visibility

The Jobs page should make the active search scope obvious:

- active provider
- one selected country
- roles
- seniority
- languages with proficiency

Do not over-design this. Keep it readable and consistent with the existing app.

### Part 6: De-emphasize non-release discovery paths

For this release phase, JobSpy is the primary discovery source.

Do not remove existing career-page code, but do not make `Scan Career Pages`
the default recommended path on the Jobs screen. If needed, visually demote it
or label it as secondary/internal.

## Acceptance criteria

1. Starting discovery gives immediate visual feedback.
2. Long-running discovery no longer looks broken.
3. Failed runs and zero-result runs are distinguishable.
4. Default queue shows only scored jobs above threshold, capped at `80`.
5. The Jobs page reflects the active provider and search scope.

## Required tests

Add or update tests for:

- discovery start / poll / complete flow
- zero-result completion rendering
- failed-run rendering
- default cap of `80`
- `show_all` bypass behavior

Minimum commands to run in `ML`:

```bash
CONDA_BASE="$(conda info --base 2>/dev/null)"
"$CONDA_BASE/envs/ML/bin/python" -m pytest tests/test_api.py tests/test_e2e_full_journey.py --tb=short -q
```

If you add UI-specific tests, include them in the command and report.

## Completion report

When complete, write:

- `AGENT_SPECS/completed/phase_R4_jobs_progress_and_results_ui.md`

Use `AGENT_SPECS/completed/REPORT_TEMPLATE.md`.

Then append this phase to `completed_agent_specs.txt` using the required format
from `phase_R0_discovery_execution_order.md`.
