# Phase S5 — Jobs and Drafts Action UX

## Goal

Make the jobs queue and draft review controls look and behave like primary
workflow actions instead of tiny utility chips.

## Required behavior after this phase

1. Primary actions must be large enough to notice and click comfortably.
2. Actions must be grouped by decision type:
   - primary
   - review utility
   - destructive
3. Draft review should not hide important actions behind hover-only patterns.
4. Jobs rows should not feel overloaded with equal-weight buttons.

## Files to inspect first

- `/Users/youseffayyaz/Local_LLM/frontend/templates/partials/job_row.html`
- `/Users/youseffayyaz/Local_LLM/frontend/templates/jobs.html`
- `/Users/youseffayyaz/Local_LLM/frontend/templates/draft_detail.html`
- `/Users/youseffayyaz/Local_LLM/frontend/templates/partials/drafts/header.html`
- `/Users/youseffayyaz/Local_LLM/frontend/templates/partials/drafts/footer_panels.html`
- `/Users/youseffayyaz/Local_LLM/frontend/static/app.css`

## Exact implementation requirements

### 1. Jobs queue action hierarchy

Use this hierarchy:

- primary: `Shortlist`, `Save`, `Pass`
- JD/evaluation: `View JD`, `Readiness`, `Snapshot`
- maintenance: `Refresh trust`, `Enrich`

Do not place all actions in one flat row with equal visual weight.

### 2. Draft page action hierarchy

Use this hierarchy:

- top primary: `Approve`, `Reject`, `Download PDF`
- section actions: `Save summary`, `Confirm`, `Remove`, `Rewrite`
- supporting actions: `Save to profile memory`, `Generate cover letter`

Do not hide rewrite/remove behind hover-only visibility.

### 3. Copy cleanup

Replace jargon-heavy labels where a shorter action is clearer, for example:

- `Application Snapshot` may need a shorter, user-facing label if it remains
  in the primary row
- `Refresh trust` may need tooltip help if the label stays technical

### 4. Layout discipline

- keep large surfaces but avoid tiny action controls
- align actions consistently
- preserve mobile usability

## Do not touch

- provider runtime
- onboarding provider step
- PDF parsing

## Tests required

1. template tests that primary actions still render
2. no hover-only requirement for draft critical controls
3. action grouping remains present after rerender/HTMX swaps

## Browser validation required

1. open jobs page and confirm actions are visually grouped
2. open draft detail and confirm edit/review actions are always visible
3. test at least one action in each group after the redesign
