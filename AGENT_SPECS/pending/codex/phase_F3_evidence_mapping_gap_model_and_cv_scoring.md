# Phase F3 — Evidence Mapping, Gap Model, And CV Scoring

## Goal

Convert the extracted job requirements and candidate profile into a structured,
truthful fit model that the CV workflow can use.

After this phase:

- each job/CV pair has a requirement-to-evidence map
- gaps are classified into 4 levels
- the app produces more than one score, not just a vague single fit number
- the app can surface top CV modifications grounded in evidence

## Files likely in scope

- `job_agent/services/workflows.py`
- `job_agent/services/prompts.py`
- `job_agent/services/compliance_matrix.py`
- `job_agent/services/matching.py`
- `job_agent/services/job_fit_scoring.py`
- add a dedicated CV-fit service if needed
- `job_agent/models.py`
- `frontend/templates/partials/fit_gaps.html`
- `tests/test_job_fit_scoring.py`
- `tests/test_compliance_matrix.py`
- `tests/test_candidate_workflow.py`

## Exact implementation requirements

### 1. Requirement-to-evidence mapping

For every relevant JD requirement, map:

- requirement text
- requirement tier
- matching evidence from candidate profile / draft
- evidence source type
- confidence

Evidence source types should distinguish at least:

- direct structured experience
- direct structured project
- verified candidate fact
- profile-note evidence
- skill-only evidence
- no evidence

This structure should be presented as this app's own fit-analysis model. Avoid
copying external report headings or matrix naming verbatim.

### 2. 4-level gap model

Classify every requirement into exactly one of:

- `strong_match`
- `partial_match`
- `stretch_match`
- `high_gap`

This classification must be stored in structured data, not left only in prose.

### 3. Multi-score model

Add at least these CV-related scores:

- `semantic_fit_score`
- `evidence_coverage_score`
- `truthfulness_safety_score`
- `overall_match_score`

Optional but recommended if the design fits cleanly:

- `presentation_quality_score`
- `apply_readiness_score`

UI-facing labels may differ from internal field names. Prefer product labels
such as `Fit Score`, `Evidence Coverage`, `Truthfulness Safety`, and `Gap
Severity` rather than imported wording from external tools.

### 4. Top modifications

Generate an explicit high-impact modification list from the gap model.

Each item should include:

- what is missing or weak
- why it matters
- whether it can be fixed from existing evidence
- whether it needs user confirmation
- whether it cannot be fixed honestly

This should become the basis for the preview/edit phase.

## Non-goals

Do not do any of the following in F3:

- implement the final preview UI
- implement final PDF renderer changes
- redesign onboarding

## Acceptance criteria

1. Every relevant requirement has a structured evidence mapping row.
2. The 4-level gap model is persisted or otherwise queryable.
3. The app exposes explicit top modifications derived from the mapping.
4. Scores remain truthful and do not reward unsupported paraphrase.

## Validation requirements

Run in `ML`:

```bash
/Users/youseffayyaz/miniforge3/envs/ML/bin/python -m pytest tests/test_job_fit_scoring.py tests/test_compliance_matrix.py tests/test_candidate_workflow.py -q
```

Add targeted tests for:

- requirement tier mapping
- gap classification
- score calculation
- top modification generation
- no unsupported-evidence promotion

## Completion report

Write:

- `AGENT_SPECS/completed/phase_F3_evidence_mapping_gap_model_and_cv_scoring.md`

Then append this phase to
`/Users/youseffayyaz/Local_LLM/completed_agent_specs.txt`.
