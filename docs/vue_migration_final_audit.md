# Vue Migration Final Audit

## Summary

The Vue migration is currently operating as a separate SPA bridge under `/app` while the legacy UI remains available under `/ui`.

The Vue shell is read-only for any route that would otherwise mutate business data or trigger LLM-backed workflows. Legacy templates, HTMX, Alpine, and existing static JavaScript remain in place and were not removed during this audit.

## Final Route Strategy

- Vue SPA entry: `/app` and `/app/*`
- Legacy UI: `/ui/*`
- Backend routes: `/api/*`
- Vue contract routes: `/api/vue/*`
- Static assets: `/static/*`
- Existing backend JSON dashboard route remains `/dashboard`

Vue Router uses `createWebHistory("/app")` and keeps internal client routes as bare paths such as `/dashboard`, `/jobs`, and `/drafts/:id`.

## Converted Vue Pages

Current Vue routes implemented in `frontend/vue/src/router/index.js`:

- `/dashboard`
- `/jobs`
- `/companies`
- `/apply`
- `/applications`
- `/drafts`
- `/drafts/:id`
- `/onboarding`
- `/settings`
- `/setup-required`
- `/verified-facts`
- `/story-bank`
- `/offer-compass`
- `/analytics`
- `/thesis`
- `/workspace-reset`
- `/help`
- `/about`
- `/vue-smoke`
- `/:pathMatch(.*)*`

No current page in `frontend/vue/src/pages/` still imports or renders `PlaceholderPage`.

## API Contract Layer

The Vue frontend uses `vueApiFetch()` from `frontend/vue/src/api/client.js`, which scopes all contract traffic to `/api/vue/*`.

Read-only contract endpoints are used for migrated pages. The only non-GET Vue contract call currently present is `POST /api/vue/workspace/reset-preview`, which is a safe preview endpoint and does not mutate data.

Forbidden mutating or generative contract calls were not found in Vue source:

- no apply score/questions/draft calls
- no draft revise/polish/approve calls
- no workspace backup/reset/delete calls
- no settings write/update calls

## Safety Boundaries Verified

- `/dashboard` still resolves to the existing backend route and is not swallowed by Vue
- `/api/vue/*` returns JSON and is not swallowed by the SPA bridge
- `/ui/*` remains legacy HTML and is not swallowed by the SPA bridge
- `/static/*` remains static-file territory and is not swallowed by the SPA bridge
- built Vue assets resolve under `/static/dist/assets/`
- Vuex is not installed; Pinia is installed and used

The dashboard Vue contract was tightened during this audit so `/api/vue/dashboard/summary` no longer exposes `pdflatex_path`.

## How To Run

FastAPI:

```bash
uvicorn job_agent.main:app --host 127.0.0.1 --port 8000 --reload
```

Open:

- `http://127.0.0.1:8000/app`
- `http://127.0.0.1:8000/app/dashboard`

Vite dev server:

```bash
npm run dev:vue
```

Open:

- `http://127.0.0.1:5173/app`
- `http://127.0.0.1:5173/app/dashboard`

## Known Pre-Existing Test Failures

These failures were still present after the audit and are not caused by the Vue SPA bridge:

- `tests/test_frontend_null_guards.py::test_intake_js_has_null_guard_on_full_name`
- `tests/test_frontend_null_guards.py::test_intake_js_has_null_guard_on_email`
- `tests/test_temp_harness.py::test_temp_harness_bootstrap_does_not_hardcode_repo_root`

## Recommended Next Step

Keep legacy and Vue implementations side by side for now, then move to a dedicated cleanup spec that removes dead Vue placeholders and legacy-only duplication only after the team is ready to retire `/ui/*` flows intentionally.
