# Phase S0 — Search Quality and CV Usability Execution Plan

## Purpose

This execution pack addresses the current user-facing weaknesses in the jobs
queue and draft-review workflow:

1. too many weak or JD-missing jobs reach the main queue
2. country targeting is not enforced strictly enough at import/display time
3. users cannot read the full JD inside the app
4. job posting time is not surfaced clearly where decisions happen
5. some profile fields are persisted implicitly from intake without a sufficiently
   transparent review surface
6. queue and draft controls are too small and too utility-like for primary usage
7. discovery can still be started implicitly by worker/source behavior rather
   than only by explicit user action

This track is intentionally product-facing and must be validated in both the
backend and rendered frontend after each phase.

## User decisions already made

- Default jobs view should show only `30–40` JD-ready roles.
- Quality is more important than quantity.
- Users should be able to open the full JD inside the app in a dialog, not a new tab.
- Job posting time should be shown in the role area.
- Country targeting must be strict at import time.
- Region/city preference may be optional and should be added now.
- Do **not** ask for remote / hybrid / onsite preference right now.
- Do **not** ask for start-date availability right now.
- Keep future support possible for those preferences without surfacing them in onboarding yet.
- Queue and draft actions must be larger, clearer, and easier to use.
- Job discovery should run in the background only after the user explicitly
  starts a search/import flow.
- Seeded/direct-company sources must be optional source inputs, not silent
  runtime search targets.

## Current code reality from audit

### Search and queue

- The worker has historically had idle-loop discovery behavior, which can create
  job posts before the user starts a search.
- Discovery payloads already derive `country` and `location` from
  `job_search_countries` and `jobspy_discover_location` in
  `/Users/youseffayyaz/Local_LLM/job_agent/services/job_discovery_workflow.py`.
- The default visible queue cap still comes from `settings.discovery_max_visible_jobs`
  and the current product default is much higher than desired in:
  - `/Users/youseffayyaz/Local_LLM/job_agent/routers/jobs.py`
  - `/Users/youseffayyaz/Local_LLM/job_agent/services/job_discovery_workflow.py`
- The main queue still mixes many `awaiting_enrichment` rows into the user’s
  default experience even though those jobs are not trustworthy enough for
  immediate CV work.
- JobSpy and ATS both have country filters, but strict geography is not enforced
  uniformly enough across all stored/discovered rows, and old out-of-scope rows
  can remain visible in a persistent queue.

### JD visibility

- The queue currently exposes only `description_snippet`, not full JD content, in
  `/Users/youseffayyaz/Local_LLM/job_agent/routers/job_views.py` and
  `/Users/youseffayyaz/Local_LLM/frontend/templates/partials/job_row.html`.

### Profile review / “static” fields

- The canonical fact sheet schema has a stable `person` block and `match_profile`
  block:
  - `person.full_name`
  - `person.current_location`
  - `person.contact.email`
  - `person.contact.phone`
  - `person.contact.linkedin_url`
  - `person.contact.github_url`
  - `person.headline`
  - `match_profile.location_preferences.*`
  - `match_profile.work_authorization`
  - `match_profile.availability.*`
- The onboarding review UI currently exposes only:
  - full name
  - email
  - education
  - experience
  - projects/evidence
  - skills
  - languages
- This means some persisted identity/preference fields can exist in canonical
  JSON without being visible enough in review.

### Actions and usability

- Jobs and draft pages are now technically functioning again, but the control
  hierarchy is still too dense and too low-contrast for high-frequency use.

## Execution order

1. `phase_S0A_user_initiated_discovery_and_source_catalog.md`
2. `phase_S1_strict_discovery_geography_and_queue_scope.md`
3. `phase_S2_jd_ready_default_queue_cap.md`
4. `phase_S3_job_detail_dialog_and_posted_time.md`
5. `phase_T1_source_dossier_and_multi_file_provenance.md`
6. `phase_T2_normalized_markdown_intake_layer.md`
7. `phase_T3_schema_safe_canonical_promotion.md`
8. `phase_T4_review_surface_and_field_provenance.md`
9. `phase_S4_profile_review_visibility_and_preference_simplification.md`
10. `phase_S5_jobs_and_drafts_action_ux.md`

## Cross-track dependency note

`S4` is now intentionally dependent on the new `T` intake-hardening pack.

Reason:

- `S4` expands profile-review visibility
- `T1` through `T4` make that review substrate trustworthy and provenance-aware

`S0A` through `S3` remain safe to implement immediately because they do not
depend on intake refactoring.

`S0A` must run before `S1` because it defines the user-initiated discovery
contract and removes silent seeded-company discovery. `S1` then tightens the
country/region behavior inside that explicit run contract.

## Validation rule for this track

Each phase must be verified at three levels:

1. backend tests for route/service behavior
2. template or JS tests for rendered contract
3. live browser validation on the relevant page

Do not mark any `S` phase complete without all three.
