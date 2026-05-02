# Refactor Boundaries — 2026-05-02

This file defines the recommended split boundaries for the next cleanup pass.

## Backend

### `job_agent/routers/jobs.py`

Split into:

- `jobs_read.py`
  queue listing, filtering, counts, manual target reads
- `jobs_mutation.py`
  create/update/manual target save/state changes
- `jobs_discovery.py`
  discovery queueing, progress, ATS/JobSpy entrypoints
- `jobs_ui.py`
  Jinja page assembly for `/ui/jobs`

### `job_agent/routers/drafts.py`

Split into:

- `drafts_read.py`
  list/get/pdf/compliance/preview-state reads
- `drafts_mutation.py`
  generate/approve/reject/preview updates
- `drafts_clarify.py`
  bullet clarification and promotion flows
- `drafts_ui.py`
  Jinja page assembly for `/ui/drafts/*`

### `job_agent/services/workflows.py`

Split into:

- `workflow_context.py`
  candidate/profile/job/track loading
- `workflow_generation.py`
  draft generation and keyword extraction
- `workflow_review.py`
  reviewer/reviser decision logic
- `workflow_persistence.py`
  draft/task/result persistence
- `workflow_discovery.py`
  queued discovery orchestration

## Frontend

### `frontend/static/onboarding.js`

Split into:

- `onboarding_state.js`
- `onboarding_questions.js`
- `onboarding_review.js`
- `onboarding_search_setup.js`

### `frontend/static/jobs.js`

Split into:

- `jobs_discovery.js`
- `jobs_manual_target.js`
- `jobs_filters.js`

### `frontend/static/settings.js`

Split into:

- `settings_provider.js`
- `settings_search.js`
- `settings_integrations.js`
- `settings_advanced.js`

### `frontend/templates/draft_detail.html`

Break into partials:

- `_draft_header.html`
- `_draft_pdf_preview.html`
- `_draft_readiness.html`
- `_draft_fit_map.html`
- `_draft_preview_editor.html`
- `_draft_actions.html`

## Why these boundaries matter

They align ownership with user tasks instead of letting files grow by endpoint
or by accident. That makes future UI changes less likely to break workflow
logic, and future backend changes less likely to force template rewrites.
