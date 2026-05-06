# Phase E1 — Truthful JD Readiness And Quality Gate

## Goal

Stop weak job descriptions from being treated as trustworthy low-fit scores.

The app currently falls back too easily when a job has only a thin board
snippet. This phase must create a truthful readiness contract that later phases
can build on.

## Files in scope

- `/Users/youseffayyaz/Local_LLM/job_agent/services/job_fetcher.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/services/job_fit_scoring.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/services/workflows.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/routers/job_views.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/models.py`
- `/Users/youseffayyaz/Local_LLM/tests/test_job_fetcher.py`
- `/Users/youseffayyaz/Local_LLM/tests/test_job_fit_scoring.py`
- add `/Users/youseffayyaz/Local_LLM/tests/test_job_description_quality.py`
- add `/Users/youseffayyaz/Local_LLM/job_agent/services/job_description_quality.py`

## Exact implementation requirements

### 1. Add a reusable JD quality evaluator

Create `job_agent/services/job_description_quality.py` with a single
responsibility: judge whether a description is good enough for provider scoring.

It must expose a function with a stable output contract equivalent to:

```python
def evaluate_job_description(
    *,
    description: str | None,
    source_name: str | None,
    source_url: str | None,
    company_url: str | None,
) -> dict[str, object]:
    ...
```

Required output keys:

- `score`: integer `0-100`
- `label`: one of `missing`, `thin`, `usable`, `strong`
- `ready_for_provider_scoring`: boolean
- `reason_codes`: short machine-readable strings
- `reason_summary`: short human-readable explanation
- `source_kind`: one of `ats_structured`, `company_page`, `linkedin_enriched`,
  `linkedin_snippet`, `manual`, `unknown`

Use deterministic heuristics only in this phase. Do not call the LLM here.

Minimum heuristics:

- description presence
- normalized text length
- enough alphabetic content
- presence of role-detail signals such as requirements / responsibilities /
  qualifications sections or bullet-style content
- source-family boost for ATS/company descriptions

### 2. Reinterpret readiness states truthfully

Do not add a new DB column in this phase unless it is strictly necessary.
Prefer existing `JobPost.enrichment_status` plus structured metadata.

Required readiness behavior:

- `pending`: retrieved but not yet enriched
- `partial`: some detail exists, but JD is not yet strong enough for provider scoring
- `ok`: JD quality passed the provider-scoring gate
- `needs_input`: no readable JD after automated attempts
- `failed`: an automated fetch/extract path failed and left the JD unready

Stamp JD quality into `job.extracted_metadata["jd_quality"]`.

Required metadata shape:

```json
{
  "score": 42,
  "label": "thin",
  "ready_for_provider_scoring": false,
  "reason_codes": ["short_text", "board_snippet_only"],
  "reason_summary": "Thin board snippet; needs stronger enrichment before provider scoring.",
  "source_kind": "linkedin_snippet"
}
```

### 3. Change candidate-fit behavior for weak descriptions

In `job_fit_scoring.py`, do not treat weak descriptions as normal fallback
matches.

When JD quality is not ready:

- persist a candidate-fit payload
- set `score_source` to `awaiting_enrichment`
- keep `fit_score` as a deterministic low-cost fallback value only for
  secondary sorting, not as a trustworthy shortlist signal
- add `threshold_eligible: false`
- add `awaiting_enrichment: true`
- set `short_reason` to a truthful statement such as:
  `Job description is too weak for provider scoring; awaiting stronger enrichment.`

Do not label these jobs as `fallback` in the UI anymore.

### 4. Preserve compatibility for provider-offline fallback

Keep the existing provider-unavailable path, but distinguish it from the weak-JD
path.

Required distinction:

- provider unavailable -> `score_source = "fallback"`
- weak JD -> `score_source = "awaiting_enrichment"`

### 5. Surface the new metadata to job views

Update the existing job-row payload shaping so each job row exposes:

- `jd_quality_score`
- `jd_quality_label`
- `jd_ready_for_provider_scoring`
- `fit_source`
- `threshold_eligible`
- `awaiting_enrichment`

This phase does not need to redesign the page yet. It must only make the data
available for Phase E4.

## Validation requirements

Run in `ML`:

1. `pytest tests/test_job_fetcher.py tests/test_job_fit_scoring.py tests/test_job_description_quality.py -q`
2. `ruff check job_agent/services/job_description_quality.py job_agent/services/job_fetcher.py job_agent/services/job_fit_scoring.py job_agent/services/workflows.py job_agent/routers/job_views.py tests/test_job_fetcher.py tests/test_job_fit_scoring.py tests/test_job_description_quality.py`

Required tests:

- missing description -> `label=missing`, not ready
- short LinkedIn snippet -> `label=thin`, not ready
- strong ATS/company/plaintext description -> ready
- weak JD scoring path persists `score_source=awaiting_enrichment`
- provider-offline path still persists `score_source=fallback`

## Completion report

Write:

- `/Users/youseffayyaz/Local_LLM/AGENT_SPECS/completed/phase_E1_truthful_jd_readiness_and_quality_gate.md`

Then append this phase to
`/Users/youseffayyaz/Local_LLM/completed_agent_specs.txt`.
