# Phase F4 — CV Preview, Edit, And Safe Paraphrase Controls

## Goal

Add the missing user-facing draft review step before final PDF generation.

After this phase:

- the user can preview the CV as structured content before final PDF
- the app can safely paraphrase for JD alignment without inventing facts
- the user can review and edit high-impact sections before committing to the
  final artifact

This preview step must feel like a native app review experience, not a copied
operator report from another repository.

## Files likely in scope

- `job_agent/routers/drafts.py`
- `job_agent/services/workflows.py`
- `job_agent/services/prompts.py`
- `frontend/templates/draft_detail.html`
- `frontend/templates/partials/fit_gaps.html`
- add preview/edit partials if needed
- `frontend/static/` scripts related to draft detail
- `tests/test_ui_draft_detail.py`
- `tests/test_api.py`
- `tests/test_candidate_workflow.py`

## Exact implementation requirements

### 1. Pre-PDF preview state

Before final PDF generation, expose a reviewable draft state that shows:

- headline
- professional summary
- selected experiences
- selected projects / evidence blocks
- skills
- top modifications
- gap severity summary
- readiness warnings

This preview must not depend on the PDF renderer.
It must also use app-native panel titles and interaction patterns.

### 2. Editable review step

Allow the user to:

- edit summary text
- approve or reject proposed paraphrases
- remove weak bullets
- adjust evidence ordering
- confirm or reject inferred additions

### 3. Safe paraphrase model

Every rewritten or proposed text item should be internally tagged as one of:

- `direct_fact`
- `safe_paraphrase`
- `adjacent_inference`
- `needs_user_confirmation`

Rules:

- `direct_fact` and `safe_paraphrase` may flow automatically
- `adjacent_inference` and `needs_user_confirmation` must not silently enter the
  final CV without user review

### 4. Top 3 modifications panel

Promote a compact user-facing list such as:

- `Top 3 modifications before applying`

Each item should include:

- the change
- why it matters
- whether it is fixable now
- whether it needs confirmation

You may rename this panel to a stronger app-native title such as
`Recommended Improvements` or `Best Next Edits`, but do not copy external tool
section naming.

### 5. Differentiated UX shape

The review screen should not be a plain markdown-style report.

Required direction:

- use distinct cards, summaries, and editable sections
- keep the layout aligned with the existing web app
- avoid reproducing another product's exact report ordering
- prefer concise end-user copy over operator-style instructions

## Non-goals

Do not do any of the following in F4:

- major final PDF design overhaul
- new discovery integrations
- cover-letter redesign

## Acceptance criteria

1. The app has a clear preview step before final PDF generation.
2. Unsupported paraphrases do not silently pass into the final CV.
3. Users can review and adjust the highest-impact changes before PDF output.
4. Existing truthful sparse-profile behavior does not regress.

## Validation requirements

Run in `ML`:

```bash
/Users/youseffayyaz/miniforge3/envs/ML/bin/python -m pytest tests/test_ui_draft_detail.py tests/test_api.py tests/test_candidate_workflow.py -q
```

Add tests for:

- preview rendering
- paraphrase tag behavior
- confirmation gating
- top-3 modification visibility

## Completion report

Write:

- `AGENT_SPECS/completed/phase_F4_cv_preview_edit_and_safe_paraphrase_controls.md`

Then append this phase to
`/Users/youseffayyaz/Local_LLM/completed_agent_specs.txt`.
