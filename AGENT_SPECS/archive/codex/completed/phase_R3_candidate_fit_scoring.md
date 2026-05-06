# Phase R3 — Candidate Fit Scoring

## Goal

Replace the current queue’s generic track-based ranking with a candidate-aware
fit score that compares the active candidate’s fact sheet against the job
description using the currently active provider.

This is the core intelligence phase for the release workflow.

## Current problem

Today the visible queue is primarily ranked by `ResumeTrack` keyword / embedding
scores. That is not the desired product behavior for this release.

The release behavior must be:

- retrieve jobs cheaply first
- then score promising jobs against the actual candidate fact sheet
- then show only jobs meeting the configured fit threshold

## Release rules

1. AI scoring uses exactly one active provider:
   - LM Studio, or
   - Ollama, or
   - OpenAI, or
   - Anthropic
2. Language is a soft scoring signal, not a hard exclusion rule.
3. The default fit visibility threshold is `70`.
4. The default visible queue cap is `80`.

## Read these files first

1. `job_agent/services/matching.py`
2. `job_agent/services/fit_gap.py`
3. `job_agent/services/fact_sheet_renderer.py`
4. `job_agent/routers/jobs.py`
5. `job_agent/routers/job_views.py`
6. `job_agent/llm.py`
7. `job_agent/models.py`
8. `job_agent/config.py`
9. `tests/test_search_profile_preferences.py`
10. `tests/test_api.py`

## Implementation instructions

### Part 1: Add configuration knobs

Add release-grade config fields for discovery visibility:

- `DISCOVERY_MIN_FIT_SCORE` default `70`
- `DISCOVERY_MAX_VISIBLE_JOBS` default `80`

Expose them through settings save / settings current if that is how discovery
configuration is already managed.

Do not remove the legacy `match_min_score` yet if it would create large
regression risk. If both exist temporarily, make the new discovery threshold the
source of truth for discovery visibility and document any compatibility bridge.

### Part 2: Add a candidate-fit scoring service

Create a dedicated service for candidate-aware job scoring.

Recommended file:

- `job_agent/services/job_fit_scoring.py`

Required inputs:

- active candidate id
- rendered fact sheet summary or short fact sheet text
- job title
- job location / country
- job seniority hints
- job description
- stored search profile:
  - one country
  - target roles
  - seniority
  - languages with proficiency

Required structured output:

- `fit_score` from `0-100`
- `score_source` such as `provider` or `fallback`
- `provider_mode`
- `matched_evidence`
- `top_gaps`
- `language_assessment`
- `seniority_assessment`
- `short_reason`

### Part 3: Use the active provider only

This service must use `LLMRouter` and respect the current provider mode.

Do not implement provider-splitting logic.

### Part 4: Fallback behavior

If the provider is unavailable or the JD is too weak for proper scoring:

- fall back to the existing keyword / embedding logic from
  `job_agent/services/matching.py`
- mark the score source explicitly as fallback
- do not crash the whole discovery run because one job could not be scored well

### Part 5: Language as a soft signal

Do not exclude jobs only because the language fit is weak.

Required behavior:

- language contributes to fit score and risk messaging
- if the user has weak proficiency, the job can still be shown
- if the job has no detectable language, score it without a language exclusion

### Part 6: Persistence

Persist candidate-fit results in a way the queue can reuse without recomputing
on every page load.

Prefer storing structured fit data in `JobPost.extracted_metadata` keyed by the
active candidate id if that stays simple and does not create schema churn.

If you choose a different persistence shape, justify it in the completion
report.

## Acceptance criteria

1. The queue can distinguish provider-scored jobs from fallback-scored jobs.
2. The active provider mode is respected for fit scoring.
3. Language influences score but does not hard-reject jobs.
4. Discovery visibility threshold defaults to `70`.
5. The visible queue can later be capped cleanly at `80`.

## Required tests

Add or update tests for:

- active-provider scoring path
- fallback scoring path when provider fails
- language as soft signal, not hard exclusion
- threshold behavior at `70`
- persistence of candidate-fit metadata

Minimum commands to run in `ML`:

```bash
CONDA_BASE="$(conda info --base 2>/dev/null)"
"$CONDA_BASE/envs/ML/bin/python" -m pytest tests/test_api.py tests/test_search_profile_preferences.py --tb=short -q
```

Add any new scoring-specific test files to the command and report.

## Completion report

When complete, write:

- `AGENT_SPECS/completed/phase_R3_candidate_fit_scoring.md`

Use `AGENT_SPECS/completed/REPORT_TEMPLATE.md`.

Then append this phase to `completed_agent_specs.txt` using the required format
from `phase_R0_discovery_execution_order.md`.
