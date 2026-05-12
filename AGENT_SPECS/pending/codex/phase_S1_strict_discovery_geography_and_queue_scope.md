# Phase S1 — Strict Discovery Geography and Queue Scope

## Goal

Make country targeting strict and predictable so a user who chooses Italy sees
Italy-only discovery by default, rather than a persistent mixed-country queue.

## Problems to solve

1. search preferences already store a target country, but users still see
   out-of-scope jobs in the review surface
2. imported rows from previous runs can remain visible even when a new search
   target is stricter
3. region/city preference is not first-class enough yet
4. the queue does not explain clearly which search scope produced the current run

## Required behavior after this phase

1. Discovery run scope must include:
   - one required country
   - one optional region/city string
2. Import filters must reject rows outside the selected country.
3. The jobs UI must surface the active search geography clearly.
4. Existing old out-of-scope jobs must not pollute the default review lane for a
   new scoped run.

## Files to inspect first

- `/Users/youseffayyaz/Local_LLM/job_agent/services/job_discovery_workflow.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/services/jobspy_service.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/services/ats_discovery.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/routers/jobs.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/routers/job_queue_actions.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/routers/system.py`
- `/Users/youseffayyaz/Local_LLM/frontend/templates/jobs.html`
- `/Users/youseffayyaz/Local_LLM/frontend/templates/partials/settings/discovery_section.html`
- `/Users/youseffayyaz/Local_LLM/frontend/static/onboarding/search.js`
- `/Users/youseffayyaz/Local_LLM/frontend/static/onboarding/hydrate.js`

## Exact implementation requirements

### 1. Add explicit optional region/city preference

Add a persisted user setting field for optional region/city preference if it
does not already exist under a stable name. Use one clear field name such as:

- `job_search_region`

Update:

- config model
- user-config persistence
- settings save sanitization
- onboarding search save/hydrate
- settings discovery section

Do not add any remote/hybrid/onsite question.

### 2. Tighten discovery payload shape

In discovery queueing and workflow payload construction, ensure the active
search scope includes:

- `country`
- `region`
- `location`

Use the country as the hard filter and the region only as an optional narrowing
hint for search queries and display.

### 3. Enforce country at import time across all discovery sources

Re-audit both:

- JobSpy discovery
- ATS discovery

Ensure the same selected country is used as a hard acceptance rule.

Do not accept a row into persisted discovery results if its normalized location
fails the selected-country test.

### 4. Prevent old out-of-scope rows from dominating the default lane

Implement a run-scope marker in extracted metadata or another existing stable
job metadata area so the default review surface can prefer the latest scope.

At minimum:

- rows imported under a different country scope must not be blended into the
  latest default review lane
- `Show all` can still expose older rows if desired

### 5. UI copy

The jobs page must clearly show:

- target country
- optional region if set
- that the visible queue belongs to the current search scope

## Do not touch

- CV generation routes
- draft preview behavior
- provider configuration logic

## Tests required

Add or update tests covering:

1. country-only discovery payload generation
2. country + region payload generation
3. out-of-country ATS row rejection
4. out-of-country JobSpy row rejection
5. default queue scoped to latest country target
6. onboarding/settings save-hydrate for the new region field

## Browser validation required

1. Save country `Italy` and region blank, run discovery, confirm the jobs page
   labels the run as Italy-only.
2. Save country `Italy` and region `Turin`, run discovery, confirm the jobs page
   shows both.
3. Confirm the default queue does not surface previously imported out-of-scope jobs.
