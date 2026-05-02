# Phase F1 — Profile Readiness And Onboarding Review Gate

## Goal

Introduce the candidate-data readiness layer that the CV workflow currently
lacks.

After this phase:

- onboarding ends with a final extracted-data review step
- CV generation can detect whether the profile is strong enough
- the app gives truthful readiness states instead of attempting a strong CV on
  obviously insufficient evidence

This is a contract and UX phase. Do not implement manual JD or PDF renderer
work here.

## Required outcome

1. The app has explicit CV readiness states:
   - `ready`
   - `usable_with_warnings`
   - `insufficient_profile_data`
2. Onboarding ends with a final review of the extracted candidate data before
   setup completes.
3. The user can edit the extracted data from that review step.
4. CV workflow entry points can check readiness before draft generation.
5. The readiness result is derived from candidate evidence, not from role bias.

## Non-goals

Do not do any of the following in F1:

- build the manual JD entry flow
- implement requirement-to-evidence mapping
- add semantic CV-vs-JD scoring
- redesign the final PDF output
- add domain-specific templates

## Read these files first

1. `frontend/templates/onboarding.html`
2. `frontend/static/onboarding.js`
3. `job_agent/routers/setup_state.py`
4. `job_agent/routers/system.py`
5. `job_agent/routers/drafts.py`
6. `job_agent/services/workflows.py`
7. `job_agent/parsers/fact_sheet.py`
8. `job_agent/services/fact_ingestion.py`
9. `job_agent/models.py`
10. `tests/test_onboarding.py`
11. `tests/test_intake.py`
12. `tests/test_candidate_workflow.py`

## Implementation instructions

### Part 1: CV readiness model

Introduce a deterministic readiness evaluator that scores whether the current
candidate profile can support a competitive CV draft.

Minimum checks:

- contact identity present
- education present
- at least one meaningful evidence block from:
  - structured experience
  - structured project
  - verified fact
  - curated profile-note evidence
- enough section content to populate a one-page CV honestly
- dates present where applicable
- skills present

Output shape should include at least:

- `status`
- `reasons`
- `missing_sections`
- `warnings`

### Part 2: Final onboarding review step

Add a final onboarding step that shows the user:

- name / email / core identity
- education
- experiences
- projects / profile evidence
- skills
- languages and levels
- search focus / provider

This must be editable before onboarding is finalized.

### Part 3: CV workflow gate

Before CV drafting begins, the app must run the readiness check and expose one
of these behaviors:

- `ready`: allow normal workflow
- `usable_with_warnings`: allow workflow but show warnings
- `insufficient_profile_data`: block final-CV generation and explain what is
  missing

Blocking the final PDF here is acceptable if the profile is too weak.

### Part 4: Domain neutrality

The readiness logic must not assume:

- GitHub exists
- a portfolio exists
- technical projects exist
- quantified metrics always exist
- English-first roles

The evaluator should ask: "Is there enough evidence for a credible CV in this
domain?" not "Does the user look like a tech candidate?"

## Acceptance criteria

1. Onboarding ends with a visible profile review step.
2. The user can edit extracted profile data before setup completes.
3. CV entry points expose readiness instead of silently generating weak output.
4. Sparse profiles are flagged clearly and truthfully.
5. Existing onboarding persistence does not regress.

## Required tests

Add or update targeted tests for:

- onboarding final review presence and persistence
- readiness state classification for:
  - strong profile
  - partial profile
  - weak profile
- CV workflow blocking or warning behavior when readiness is insufficient

Minimum commands to run in `ML`:

```bash
/Users/youseffayyaz/miniforge3/envs/ML/bin/python -m pytest tests/test_onboarding.py tests/test_intake.py tests/test_candidate_workflow.py -q
```

If you add new readiness-specific tests, include them in the same run.

## Completion report

When complete, write:

- `AGENT_SPECS/completed/phase_F1_profile_readiness_and_onboarding_review_gate.md`

Then append this phase to `completed_agent_specs.txt` using the required format
from `phase_F0_cv_quality_execution_order.md`.
