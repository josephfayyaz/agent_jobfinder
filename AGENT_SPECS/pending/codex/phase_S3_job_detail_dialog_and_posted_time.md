# Phase S3 — Job Detail Dialog and Posted Time

## Goal

Make each job row easier to evaluate without leaving the app by showing:

1. posting time / freshness directly in the role area
2. full JD content in an in-app dialog instead of forcing a new tab

## Required behavior after this phase

1. Each job row should surface posted/seen time clearly near the role title.
2. Each job row should expose a `View JD` action.
3. `View JD` should open an in-app dialog/modal with:
   - title
   - company
   - location
   - posted date / freshness
   - source/apply links
   - full job description text
4. No new browser tab should be required for the main JD read path.

## Files to inspect first

- `/Users/youseffayyaz/Local_LLM/job_agent/routers/job_views.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/services/job_signals.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/models.py`
- `/Users/youseffayyaz/Local_LLM/frontend/templates/partials/job_row.html`
- `/Users/youseffayyaz/Local_LLM/frontend/templates/jobs.html`
- `/Users/youseffayyaz/Local_LLM/frontend/static/jobs.js`
- `/Users/youseffayyaz/Local_LLM/frontend/static/app.css`

## Exact implementation requirements

### 1. Include posted-time data in row payload

Extend the UI job payload so each row has a stable display field such as:

- `posted_label`
- `posted_at_iso`

Use existing `posted_date`, `created_at`, or signal-derived freshness data in a
truthful order. Do not invent exact posting timestamps when only “last seen” is known.

### 2. Add a dedicated JD dialog route or payload path

Implement one explicit UI path for the full JD body, either:

- server-rendered partial endpoint for one job detail modal, or
- inline dialog shell hydrated from the current row payload if that payload is
  sufficient

Prefer the server-rendered partial if the full JD text is already in the DB and
the payload should stay light.

### 3. Modal requirements

The modal should:

- be keyboard closable
- not require Alpine if a simpler JS pattern is already used on jobs page
- degrade safely if JD is missing by saying so clearly

### 4. Row action placement

Add `View JD` close to the role title or primary action zone. Do not hide it in
secondary badges.

## Do not touch

- queue-state backend semantics
- CV workflow generation code

## Tests required

1. job row payload includes posted-time fields
2. JD modal partial/route returns 200 for known job
3. modal route handles missing JD gracefully
4. rendered jobs page includes a visible JD action

## Browser validation required

1. Open jobs page.
2. Click `View JD`.
3. Confirm a dialog opens in-page.
4. Confirm full JD text is readable inside the app.
5. Confirm posted-time text is visible in the role area.
