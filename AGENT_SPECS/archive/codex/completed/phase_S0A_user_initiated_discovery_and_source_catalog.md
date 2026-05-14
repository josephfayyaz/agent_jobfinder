# Phase S0A — User-Initiated Discovery and Source Catalog

## Goal

Make job discovery fully user-initiated and remove silent startup job creation.

The app may continue long-running search work in the background after the user
clicks the job-search action, but it must not create job posts merely because
the API or worker started.

## Why this phase exists

Fresh test runs currently become polluted by jobs that were never requested by
the user. The root cause is a mix of:

1. hardcoded company career pages seeded into runtime data
2. worker idle loops that can discover jobs without a user action
3. direct-company discovery using a biased technology/software company list
   before the user has confirmed country, region, role, or source preferences

This breaks clean testing and makes the dashboard misleading after onboarding.

## Career-ops reference findings

The local reference repo at:

- `/Users/youseffayyaz/Downloads/Great_Github_Repos/career-ops-main/`

uses a different discovery contract:

1. `templates/portals.example.yml` is a configurable template, not automatic
   runtime data.
2. Users copy/customize it into `portals.yml`.
3. The scan is an explicit command (`/career-ops scan` or `node scan.mjs`), not
   an app-start side effect.
4. Discovery has three tiers:
   - direct career pages / Playwright
   - structured ATS APIs and feeds
   - broad WebSearch queries with liveness checks
5. The example config does contain preconfigured companies and search queries,
   but they are explicitly editable and user-owned.
6. Results go into a pipeline/inbox first and are deduplicated against scan
   history and prior applications.

Adapt the useful parts only:

- explicit user-triggered scan
- source configuration owned by the user/search run
- direct ATS/API discovery as a supplement, not the default source of truth
- scan history/dedup semantics

Do not copy career-ops' hardcoded AI/tech/company bias into this app.

## Required behavior after this phase

1. Fresh runtime + onboarding + dashboard must show zero discovered jobs unless
   the user imported/pasted/searched jobs.
2. The worker must never run JobSpy, career-page, or ATS discovery from an idle
   loop.
3. Clicking the job-search button must enqueue a persisted discovery task.
4. The worker may continue that queued discovery task while the app window is
   minimized or the user is doing other work.
5. Seeded company career pages must not be inserted as active runtime sources on
   startup.
6. Direct-company/ATS sources must be selected by the user or derived from the
   explicit search scope, not silently activated from a global Italy tech list.
7. Existing users with old seeded career-page rows must not have those rows
   silently scanned after upgrade.
8. Settings must not present scheduled automatic job discovery as a supported
   product mode.

## Alignment with active pending specs

This phase must be implemented before:

- `phase_S1_strict_discovery_geography_and_queue_scope.md`
- `phase_S2_jd_ready_default_queue_cap.md`
- `phase_S3_job_detail_dialog_and_posted_time.md`

Reason:

- `S1` assumes discovery runs have a clear country/region scope. This phase
  ensures a discovery run exists only after explicit user intent.
- `S2` assumes the queue contains results from a meaningful run. This phase
  prevents unsolicited career-page results from entering that queue.
- `S3` improves review of job rows. This phase prevents irrelevant rows from
  appearing before there is anything valid to review.

This phase does not touch the `T` intake/provenance track.

## Files to inspect first

- `/Users/youseffayyaz/Local_LLM/job_agent/worker.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/seed.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/seed_companies.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/services/job_discovery_workflow.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/services/ats_discovery.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/services/career_scanner.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/routers/jobs.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/routers/system.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/config.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/user_config.py`
- `/Users/youseffayyaz/Local_LLM/frontend/templates/partials/settings/discovery_section.html`
- `/Users/youseffayyaz/Local_LLM/frontend/templates/partials/jobs/discovery_panel.html`
- `/Users/youseffayyaz/Local_LLM/frontend/static/onboarding/search.js`
- `/Users/youseffayyaz/Local_LLM/temp_mac_test/reset_state.sh`
- `/Users/youseffayyaz/Local_LLM/temp_mac_test/runtime_env.sh`

## Exact implementation requirements

### 1. Remove idle discovery from the worker

In `/Users/youseffayyaz/Local_LLM/job_agent/worker.py`, remove or permanently
disable idle-loop discovery for:

- career-page scanning
- scheduled JobSpy discovery
- any other discovery that creates `JobPost` rows without a queued task

The worker should still:

- process pending workflow tasks
- perform non-discovery maintenance only when it does not create new job posts
- continue queued discovery tasks after the user starts them

Do not remove task-based job discovery.

### 2. Remove scheduled auto-search settings

Remove or deprecate product support for scheduled automatic search settings.

At minimum:

- remove `CAREER_PAGE_AUTO_SCAN` from active settings after this phase if it was
  introduced as a temporary guard
- remove idle `jobspy_discover_interval_hours` behavior from the worker
- update settings UI copy so it does not imply the app will search
  periodically without a user action

Keep provider/source capability settings that are needed for explicit searches,
for example:

- whether JobSpy is available
- default result limit
- default source list for an explicit search

### 3. Stop seeding active company career pages

`seed_reference_data()` must no longer insert the Italy technology company
watchlist into `career_page_sources` as active runtime data.

Acceptable implementation options:

1. remove `seed_career_pages(session)` from `seed_reference_data()`, or
2. convert the list into an inactive catalog that is never scanned unless the
   user imports/selects entries for a specific run.

Do not delete the list outright if it is useful as an optional example/catalog,
but do not allow it to become active runtime data silently.

### 4. Handle existing seeded rows safely

For existing databases that already contain rows from
`job_agent/seed_companies.py`:

- do not scan them automatically
- either mark them inactive, tag them as catalog/example rows, or exclude them
  from default ATS discovery unless explicitly selected
- do not delete user-added career-page sources

If schema support is needed, add a minimal column such as:

- `source_origin`: `user`, `catalog_seed`, `imported`, `legacy_seed`

Default behavior must treat unknown old rows conservatively:

- no automatic scan
- no inclusion in explicit ATS discovery unless the run source policy allows it

### 5. Make source selection run-scoped

Discovery task payloads should carry source intent explicitly.

Extend queued discovery payloads to include fields such as:

- `sources`: external boards/providers selected by the user
- `include_direct_company_sources`: boolean
- `career_source_ids`: optional list of user-selected career-page source IDs
- `source_policy`: e.g. `job_boards_only`, `selected_companies`, `catalog_suggestions`

Default should be:

- job board discovery only
- no direct-company seeded catalog scan

The UI may later offer optional catalog suggestions, but this phase must not
silently include them.

### 6. Keep ATS/direct-company discovery compatible with S1

If direct-company/ATS discovery remains available in the explicit search flow,
it must respect:

- selected country as a hard filter
- optional region as a narrowing hint
- selected roles
- seniority

Do not query all active career-page sources globally.

### 7. Dashboard empty state

After onboarding, the dashboard/jobs surface should clearly show an empty state
when no user-initiated search/import has happened.

The empty state should guide the user to:

- start a job search
- paste/import a job description

It should not imply that hidden background discovery is running.

### 8. Temp test harness reset guarantee

After:

```bash
cd /Users/youseffayyaz/Local_LLM/temp_mac_test
bash reset_state.sh
bash bootstrap.sh
bash start_full.sh
```

the temp database must remain free of discovered jobs until the test explicitly
starts discovery or imports jobs.

## Do not touch

- CV generation routes
- draft preview/editing behavior
- provider adapter internals
- PDF/CV intake logic
- `T` intake provenance specs

## Tests required

Add or update tests covering:

1. worker idle iteration does not create `JobPost` rows
2. worker still processes queued discovery tasks
3. `seed_reference_data()` does not insert active career-page runtime sources
4. existing seeded company rows are not scanned by default
5. explicit discovery payload contains run-scoped source intent
6. explicit discovery with default payload does not call `AtsDiscoveryService`
   against all active/global career-page sources
7. settings UI no longer advertises scheduled automatic discovery
8. temp harness defaults do not enable automatic discovery

## Browser validation required

1. Reset temp runtime.
2. Bootstrap and start the app.
3. Complete onboarding.
4. Open dashboard/jobs page.
5. Confirm there are no discovered jobs.
6. Start a job search explicitly.
7. Confirm a queued discovery task appears/runs.
8. Minimize or leave the page, return later, and confirm the user-started task
   continued.
9. Confirm direct-company/career-page sources are not used unless explicitly
   selected.

## Completion notes

When this phase is completed:

1. move this file to `/Users/youseffayyaz/Local_LLM/AGENT_SPECS/archive/codex/completed/`
2. write a completion report in `/Users/youseffayyaz/Local_LLM/AGENT_SPECS/completed/`
3. append the completion line to `completed_agent_specs.txt`
4. then continue with `phase_S1_strict_discovery_geography_and_queue_scope.md`
