# Frontend Map

The frontend is intentionally separated from `job_agent/` so page and UI work can stay in one place.

## Structure

- `templates/`
  - page templates and partials
- `static/app.css`
  - shared design system and layout styles
- `static/app.js`
  - shared browser helpers: toasts, HTMX response notifications, profile-memory badge
- `static/*.js`
  - page-specific behavior

## Page script map

- `static/onboarding.js` -> `templates/onboarding.html`
- `static/settings.js` -> `templates/settings.html`
- `static/apply.js` -> `templates/apply.html`
- `static/draft_detail.js` -> `templates/draft_detail.html`
- `static/companies.js` -> `templates/companies.html`
- `static/verified_facts.js` -> `templates/verified_facts.html`
- `static/workspace_reset.js` -> `templates/workspace_reset.html`

## Guidelines

- Keep large behavior out of inline `<script>` blocks.
- Prefer DOM-safe updates and `textContent` when rendering LLM or user-provided content.
- If a page needs server data for JavaScript, pass it through a small JSON script tag or `data-*` attributes.
- Do not hardcode candidate-specific data or machine-specific filesystem paths.
