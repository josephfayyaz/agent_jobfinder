# Phase S2 — JD-Ready Default Queue Cap

## Goal

Change the default queue from “many weak rows” to “small set of JD-ready rows”
without breaking enrichment lanes or the broader queue.

## User decision

Default visible jobs should be about `30–40` and should be JD-ready by default.

## Required behavior after this phase

1. Default lane should prefer jobs with:
   - readable description
   - JD quality marked ready for provider scoring
2. `awaiting_enrichment` jobs must be separated from the default decision lane.
3. Default visible cap must be reduced to the user-approved range.
4. The UI must explain that the default list is quality-gated.

## Files to inspect first

- `/Users/youseffayyaz/Local_LLM/job_agent/routers/jobs.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/routers/job_views.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/services/job_discovery_workflow.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/services/job_fit_scoring.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/services/job_description_quality.py`
- `/Users/youseffayyaz/Local_LLM/frontend/templates/jobs.html`
- `/Users/youseffayyaz/Local_LLM/frontend/templates/partials/jobs/discovery_panel.html`
- `/Users/youseffayyaz/Local_LLM/frontend/templates/partials/job_row.html`

## Exact implementation requirements

### 1. Reduce the default cap

Update the effective product default for `discovery_max_visible_jobs` to land in
the `30–40` range. Use one explicit number, preferably `40`, unless another
existing config constraint forces `30`.

### 2. Tighten default-lane eligibility

In the queue-building logic, define a stronger default-lane gate:

- only rows with `jd_ready_for_provider_scoring == true` should qualify for the
  default review lane
- `awaiting_enrichment` rows must go to the awaiting lane instead

Do not hide them from the system entirely. Only remove them from the default
decision lane.

### 3. Preserve explicit escape hatches

The user must still have:

- `Awaiting enrichment` lane
- `Show all`

But the default view must stop pretending weak-JD rows are equally ready.

### 4. Queue copy

Update the page copy to say the default review queue is:

- capped
- JD-ready
- quality-first

Avoid copy that implies the app is showing the “best 80 jobs” if most lack full
descriptions.

## Do not touch

- provider runtime code
- manual JD scoring flow
- PDF intake

## Tests required

1. queue context returns only JD-ready rows in default review lane
2. awaiting-enrichment rows stay visible in awaiting lane
3. default visible cap matches the new configured value
4. discovery summary counts still report awaiting-enrichment separately

## Browser validation required

1. Run discovery and confirm the default page presents only the small JD-ready set.
2. Open the awaiting lane and confirm weak-JD rows still exist there.
3. Use `Show all` and confirm the broader queue is still accessible.
