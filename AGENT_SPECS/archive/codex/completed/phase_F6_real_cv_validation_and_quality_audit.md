# Phase F6 — Real CV Validation And Quality Audit

## Goal

Validate the full CV workflow with the real app, real provider, real saved
profiles, and browser/runtime review.

This phase must prove both:

- truthfulness is preserved
- output quality meaningfully improves when profile evidence is strong enough

## Files in scope

- runtime validation artifacts under:
  - `/Users/youseffayyaz/Local_LLM/mac_full_test_data_temp/results/`
- `job_agent/TEST_HANDOFF.md`
- test files touched by prior F-phases if final fixes are needed

## Exact implementation requirements

### 1. Real-runtime validation set

Run at least:

- two rich-profile users
- one non-tech-rich user if available
- one tech-rich user if available

Use real app state, real database, real configured provider, and real browser or
live HTTP validation.

Do not use fake LM Studio.

### 2. Validate both workflow entry types

Minimum validation:

- one discovered-job-driven CV flow
- one manual-JD-driven CV flow

### 3. Validate preview and final output

For each audited case verify:

- readiness state
- requirement/gap map
- top modifications
- preview state
- final PDF output
- saved artifact naming
- persistence across restart where applicable

### 4. Save artifacts

Save at least:

- one report per user case
- final PDFs
- preview screenshots or rendered page captures
- one combined summary report

## Non-goals

Do not use synthetic fake-provider validation in F6.

## Acceptance gate

This phase passes only if the final runtime result is better than the current
baseline in both honesty and competitiveness.

Minimum acceptance:

1. sparse profiles still remain truthful and do not hallucinate
2. rich profiles produce visibly stronger CVs than the sparse-profile baseline
3. manual JD flow works
4. pre-PDF review works
5. top modifications are meaningful
6. final output naming and persistence are stable

## Validation requirements

Run in `ML`:

```bash
/Users/youseffayyaz/miniforge3/envs/ML/bin/python -m pytest tests/test_documents.py tests/test_workflows.py tests/test_candidate_workflow.py tests/test_api.py -q
```

Then perform the real runtime/browser audit and save the artifacts.

## Completion report

Write:

- `AGENT_SPECS/completed/phase_F6_real_cv_validation_and_quality_audit.md`

Then append this phase to
`/Users/youseffayyaz/Local_LLM/completed_agent_specs.txt`.
