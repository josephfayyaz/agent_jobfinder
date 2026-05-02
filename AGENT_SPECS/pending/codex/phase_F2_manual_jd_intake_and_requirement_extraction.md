# Phase F2 — Manual JD Intake And Requirement Extraction

## Goal

Make a manually pasted or linked job description a first-class CV workflow
entrypoint.

After this phase:

- the user can paste a JD or JD URL directly
- the app can parse it into a structured internal representation
- the same downstream CV workflow can run whether the job came from discovery
  or manual input

This phase is about intake and extraction, not full CV scoring or final PDF
polish.

## Files likely in scope

- `job_agent/routers/jobs.py`
- `job_agent/routers/drafts.py`
- `job_agent/routers/job_views.py`
- `job_agent/services/job_description_extractor.py`
- `job_agent/services/job_description_quality.py`
- `job_agent/services/workflows.py`
- `frontend/templates/jobs.html`
- `frontend/templates/draft_detail.html`
- add a dedicated manual-JD UI partial or page if needed
- `tests/test_api.py`
- `tests/test_job_description_extractor.py`
- add manual-JD specific tests as needed

## Exact implementation requirements

### 1. Manual JD workflow entry

Add a user-facing entrypoint that accepts:

- raw pasted JD text
- or a JD URL

This flow must use this app's own product copy and interaction language. Do not
mirror `career-ops` operator wording, command style, or report naming.

Required behavior:

- if raw text is provided, parse directly
- if URL is provided, extract text using the current extraction stack
- persist or stage the resulting job object in the same internal shape used by
  discovered jobs whenever practical

### 2. Structured JD extraction

Parse at least:

- title
- company if available
- location / country if available
- language
- seniority
- responsibilities
- requirements
- tools / platforms
- education or certification requirements
- contextual company background

When surfaced in the UI, prefer app-native labels such as `Role Snapshot`,
`Requirement Breakdown`, or `Target Details` rather than borrowed external
section names.

### 3. Requirement classification

Every extracted JD requirement should be categorized as one of:

- `must_have`
- `important`
- `nice_to_have`
- `contextual`

`contextual` is critical. Company-branding or mission copy must not be treated
as if it were a hard job requirement.

### 4. Shared downstream contract

The manual JD path must feed the same downstream CV pipeline contract as a
discovered job.

Do not build a second incompatible CV-generation path.

## Non-goals

Do not do any of the following in F2:

- final gap scoring
- final top-3 modifications panel
- preview/edit UI
- final renderer overhaul

## Acceptance criteria

1. A user can paste a JD and reach the same CV workflow entrypoint as a
   discovered job.
2. Structured requirement extraction is persisted or otherwise available to the
   next phases.
3. Company-background text is separated into `contextual` instead of polluting
   real requirements.
4. URL and raw-text manual input both work.

## Validation requirements

Run in `ML`:

```bash
/Users/youseffayyaz/miniforge3/envs/ML/bin/python -m pytest tests/test_api.py tests/test_job_description_extractor.py -q
```

Add any manual-JD tests required to prove:

- raw text intake
- URL intake
- requirement tier extraction
- contextual filtering

## Completion report

Write:

- `AGENT_SPECS/completed/phase_F2_manual_jd_intake_and_requirement_extraction.md`

Then append this phase to
`/Users/youseffayyaz/Local_LLM/completed_agent_specs.txt`.
