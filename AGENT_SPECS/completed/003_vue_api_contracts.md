# 003 Vue API Contracts

## Goal

Add a small, read-safe `/api/vue/*` JSON contract layer for future Vue page migrations.

This task prepares backend API contracts only.

Do not migrate page UI behavior.
Do not connect Vue placeholder pages to real data yet.
Do not modify existing `/ui/*` routes.
Do not change backend business logic, LLM routing, CV generation, verified-fact validation, Gmail sync, workspace reset/delete behavior, or worker behavior.

Keep Pinia.
Do not use Vuex.

---

## Current State

The Vue infrastructure and route skeleton already exist from:

```text
AGENT_SPECS/completed/codex/001_vue_infrastructure.md
AGENT_SPECS/completed/codex/002_vue_layout_router.md
```

The Vue app currently contains placeholder routes only.

This task must create the backend JSON contract layer that later Vue pages will consume.

---

## Hard Constraints

Do not migrate frontend pages.

Do not convert Jinja templates.

Do not delete or rewrite:

```text
frontend/templates/
frontend/static/
```

Do not change:

```text
LLMRouter
provider routing
CV generation logic
verified-fact validation rules
human approval workflow
Gmail sync logic
background worker behavior
SQLite app-data location
onboarding business rules
workspace reset/delete logic
```

Do not move business rules into Vue.

Do not add a FastAPI SPA catch-all route.

Do not change existing `/ui/*` routes.

Do not call LLMs.

Do not generate CV content.

Do not approve drafts.

Do not reset/delete workspace data.

Do not create workspace backup files in this task.

Do not expose secrets.

Do not expose absolute local filesystem paths.

Do not add Docker.

Do not switch package manager.

Do not use Vuex.

Do not replace Pinia.

Do not use TypeScript.

Do not invent candidate/CV facts.

Do not create fake business data that looks real.

Placeholder API responses must clearly identify themselves as contract/status responses when real data is not yet wired.

---

## Required Investigation Before Editing

Before making changes, inspect the actual backend structure.

Run or inspect with equivalent commands:

```bash
find . -maxdepth 3 -type f | sort
find job_agent -maxdepth 4 -type f | sort
find start_apply -maxdepth 3 -type f | sort
rg "APIRouter|FastAPI|@.*\.get|@.*\.post|@.*\.patch|@.*\.delete" .
rg "/api|/ui|include_router|Jinja2Templates|TemplateResponse" .
```

Read these files if they exist:

```text
README.md
AGENTS.md
CLAUDE.md
package.json
pyproject.toml
job_agent/main.py
frontend/vue/src/router/index.js
frontend/vue/src/api/client.js
frontend/templates/base.html
```

Follow the existing FastAPI router conventions.

---

## Backend Location

Add:

```text
job_agent/routers/vue_api.py
```

Modify only for router registration:

```text
job_agent/main.py
```

Register the router in `job_agent/main.py`.

Use the existing router import style.

Expected pattern:

```py
from job_agent.routers import vue_api

app.include_router(vue_api.router)
```

If `job_agent/main.py` already imports multiple routers in one import, merge `vue_api` into the existing style.

Do not reorganize existing routers.

---

## Router Definition

In `job_agent/routers/vue_api.py`, define:

```py
from fastapi import APIRouter

router = APIRouter(prefix="/api/vue", tags=["Vue API"])
```

Define lightweight Pydantic request/response models inside `job_agent/routers/vue_api.py`.

Do not expand `job_agent/schemas.py` unless the project convention absolutely requires it.

Do not add a global FastAPI exception handler in this task.

Use `JSONResponse` helpers for expected 404, 422, and 501 responses so the contract envelope is preserved.

Unknown `/api/vue/*` routes may use FastAPI’s default JSON 404.

---

## Response Rules

All handled `/api/vue/*` responses must use snake_case JSON.

### Success Envelope

```json
{
  "ok": true,
  "contract_version": 1,
  "data": {}
}
```

### Placeholder Envelope

```json
{
  "ok": true,
  "contract_version": 1,
  "status": "placeholder",
  "message": "This API contract is reserved for future Vue migration.",
  "data": {}
}
```

### Contract Error Envelope

For expected contract errors, return JSON shaped like:

```json
{
  "ok": false,
  "contract_version": 1,
  "error": {
    "code": "not_implemented",
    "message": "This endpoint is defined as a Vue API contract but is not implemented yet."
  }
}
```

For expected missing resources:

```json
{
  "ok": false,
  "contract_version": 1,
  "error": {
    "code": "not_found",
    "message": "Resource not found."
  }
}
```

For expected validation failures handled manually:

```json
{
  "ok": false,
  "contract_version": 1,
  "error": {
    "code": "validation_error",
    "message": "job_description must not be empty."
  }
}
```

Do not leak stack traces.

Do not return HTML from handled `/api/vue/*` routes.

---

## Security Rules

Do not expose keys with names containing or resembling:

```text
api_key
token
secret
password
credential
private_key
access_key
refresh_token
auth
```

Do not expose secret values, even masked.

`/api/vue/settings` must return curated provider/setup status only.

`/api/vue/session` must return safe local app/session status only.

`/api/vue/workspace/status` must not expose absolute filesystem paths; return booleans/counts/status flags only.

Do not proxy raw `/settings/current`.

Do not proxy raw workspace status if it includes local filesystem paths.

Do not call backup creation code from `/api/vue/workspace/backup`.

Do not call LLM providers.

Do not generate CV text.

Do not approve drafts.

Do not reset/delete workspace data.

---

## Required Endpoints

### Read/Safe Endpoints

Implement these endpoints:

```text
GET /api/vue/health
GET /api/vue/navigation
GET /api/vue/setup/state
GET /api/vue/session
GET /api/vue/dashboard/summary
GET /api/vue/jobs
GET /api/vue/jobs/{job_id}
GET /api/vue/companies
GET /api/vue/companies/{company_id}
GET /api/vue/applications
GET /api/vue/applications/{application_id}
GET /api/vue/drafts
GET /api/vue/drafts/{draft_id}
GET /api/vue/onboarding/state
GET /api/vue/onboarding/steps
GET /api/vue/settings
GET /api/vue/verified-facts
GET /api/vue/verified-facts/schema
GET /api/vue/story-bank
GET /api/vue/offer-compass
GET /api/vue/analytics/summary
GET /api/vue/thesis/targets
GET /api/vue/workspace/status
GET /api/vue/help
GET /api/vue/about
```

### Contract-Only Endpoints Returning 501 After Safe Validation

Implement these endpoints:

```text
POST /api/vue/apply/score
POST /api/vue/apply/questions
POST /api/vue/apply/draft
PATCH /api/vue/drafts/{draft_id}
POST /api/vue/drafts/{draft_id}/revise
POST /api/vue/drafts/{draft_id}/polish
POST /api/vue/drafts/{draft_id}/approve
POST /api/vue/workspace/backup
```

These endpoints must not perform the real action yet.

They must return HTTP `501` with the contract error envelope after request shape validation succeeds.

### Safe Read-Only Preview Endpoint

Implement:

```text
POST /api/vue/workspace/reset-preview
```

This endpoint must return HTTP `200`.

It must not delete, reset, or mutate anything.

---

## Request Body Models

Define lightweight request models.

### ApplyScoreRequest

```json
{
  "job_description": "string",
  "source_url": "string optional"
}
```

Validation:

- `job_description` must not be empty or whitespace-only.

### ApplyQuestionsRequest

```json
{
  "job_description": "string",
  "candidate_context": "object optional"
}
```

Validation:

- `job_description` must not be empty or whitespace-only.

### ApplyDraftRequest

```json
{
  "job_description": "string",
  "approved_fact_ids": ["string"],
  "answers": {}
}
```

Validation:

- `job_description` must not be empty or whitespace-only.
- `approved_fact_ids` must be a list if provided.

### DraftPatchRequest

```json
{
  "title": "string optional",
  "notes": "string optional"
}
```

### DraftActionRequest

```json
{
  "user_confirmed": true,
  "notes": "string optional"
}
```

Validation:

- `user_confirmed` must be required for approve contract.
- Do not approve anything in this task.

### WorkspaceResetPreviewRequest

```json
{
  "include_generated_files": false,
  "include_cached_results": false
}
```

Validation:

- Must not delete anything.
- Must not reset anything.
- Must only return a preview envelope.

---

## Safe Placeholder Data

For read-only endpoints, return useful empty contract shapes.

Do not return fake business data.

### GET `/api/vue/health`

Return:

```json
{
  "ok": true,
  "contract_version": 1,
  "data": {
    "service": "vue-api",
    "status": "ok"
  }
}
```

### GET `/api/vue/navigation`

Return the same navigation groups as:

```text
frontend/vue/src/constants/navigation.js
```

Include all groups:

```text
Main
Profile
Career Tools
Workspace
Dev
```

### GET `/api/vue/setup/state`

Return a safe contract response:

```json
{
  "ok": true,
  "contract_version": 1,
  "status": "placeholder",
  "message": "This API contract is reserved for future Vue migration.",
  "data": {
    "loaded": true,
    "setup_complete": true,
    "provider_configured": true,
    "requires_setup": false
  }
}
```

If an existing safe setup state service exists and does not expose secrets, it may be used.

Do not change setup business rules.

### GET `/api/vue/session`

Return:

```json
{
  "ok": true,
  "contract_version": 1,
  "data": {
    "authenticated": true,
    "local_first": true,
    "secrets_exposed": false
  }
}
```

Do not expose secrets.

### List Endpoints

Use:

```json
{
  "ok": true,
  "contract_version": 1,
  "status": "placeholder",
  "message": "This list endpoint is ready for Vue migration but not wired to real data yet.",
  "data": {
    "items": [],
    "total": 0
  }
}
```

### Detail Endpoints

Use either:

Preferred if no real safe DB-backed lookup is wired:

```json
{
  "ok": true,
  "contract_version": 1,
  "status": "placeholder",
  "message": "This detail endpoint is ready for Vue migration but not wired to real data yet.",
  "data": {
    "id": "requested-id"
  }
}
```

Or if using existing DB-backed safe lookup:

- return real safe data if found
- return contract 404 envelope if not found

Do not return fake job/company/draft/application content.

### GET `/api/vue/settings`

Return a curated safe shape only.

Example:

```json
{
  "ok": true,
  "contract_version": 1,
  "status": "placeholder",
  "message": "This settings endpoint is curated to avoid exposing secrets.",
  "data": {
    "providers": [],
    "secrets_exposed": false
  }
}
```

Do not include secret-looking keys.

### GET `/api/vue/workspace/status`

Return a curated safe shape only.

Example:

```json
{
  "ok": true,
  "contract_version": 1,
  "status": "placeholder",
  "message": "This workspace status endpoint avoids exposing local filesystem paths.",
  "data": {
    "available": true,
    "paths_exposed": false
  }
}
```

Do not include absolute paths.

### POST `/api/vue/workspace/reset-preview`

Return safe read-only preview:

```json
{
  "ok": true,
  "contract_version": 1,
  "status": "placeholder",
  "message": "This reset preview is read-only and does not delete or reset anything.",
  "data": {
    "destructive_action_performed": false,
    "would_affect": []
  }
}
```

---

## Frontend API Client Update

Modify only:

```text
frontend/vue/src/api/client.js
```

Add:

```js
export async function vueApiFetch(path, options = {}) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return apiFetch(`/api/vue${normalizedPath}`, options);
}
```

Keep the existing `apiFetch` function.

Do not update pages to call APIs yet.

Do not migrate placeholder pages.

---

## Optional API Contract Helpers

Optionally add:

```text
frontend/vue/src/api/contracts.js
```

Allowed content:

```js
import { vueApiFetch } from "./client";

export function fetchVueHealth() {
  return vueApiFetch("/health");
}

export function fetchVueNavigation() {
  return vueApiFetch("/navigation");
}

export function fetchVueSetupState() {
  return vueApiFetch("/setup/state");
}
```

Do not call these helpers from migrated pages yet.

If adding a non-blocking health check to `VueSmokePage`, it must not break page rendering if the backend is offline.

---

## Documentation Required

Add:

```text
docs/vue_api_contracts.md
```

Keep it short and precise.

The document must include:

1. Purpose of `/api/vue/*`
2. Contract version
3. Endpoint list
4. Envelope shapes
5. Security rules:
   - no secrets in settings/session responses
   - no absolute filesystem paths in workspace responses
   - no CV generation in contract endpoints
   - no LLM calls in contract endpoints
   - no workspace deletion/reset from reset-preview
   - no backup file creation from backup endpoint yet
6. Statement that legacy `/ui/*` routes remain active during migration

---

## Tests Required

Add:

```text
tests/test_vue_api_contracts.py
```

Follow the existing FastAPI TestClient/app fixture conventions.

Minimum assertions:

```text
GET /api/vue/health returns 200, ok=true, contract_version=1
GET /api/vue/navigation returns 200 and groups list
GET /api/vue/setup/state returns 200 and setup fields
GET /api/vue/session returns 200 and contains no secret-looking keys
GET /api/vue/dashboard/summary returns JSON envelope
GET /api/vue/jobs returns items and total
GET /api/vue/jobs/example-id returns placeholder id or contract 404 envelope
GET /api/vue/settings contains no api_key/token/secret/password/credential-like keys
GET /api/vue/workspace/status does not expose absolute local filesystem paths
POST /api/vue/apply/score with empty job_description returns 422 JSON contract error or FastAPI JSON validation error
POST /api/vue/apply/score with non-empty text returns 501 JSON contract error
POST /api/vue/workspace/backup returns 501 and does not create backup file
POST /api/vue/workspace/reset-preview returns 200 and performs no destructive action
unknown /api/vue/* route returns JSON, not HTML
```

Do not fix unrelated known failures in:

```text
tests/test_frontend_null_guards.py
tests/test_temp_harness.py
```

unless they are directly caused by this task.

---

## Validation Commands

Run:

```bash
npm run build:vue
```

Run existing frontend CSS build if present:

```bash
npm run css:build
```

Run focused tests:

```bash
pytest tests/test_vue_api_contracts.py
```

Run full tests:

```bash
pytest
```

If full `pytest` still fails because of known pre-existing failures, report them exactly and state whether this task introduced any new failures.

---

## Manual Validation

Start the backend using the project’s documented command.

Check these URLs in browser or curl:

```text
http://localhost:8000/api/vue/health
http://localhost:8000/api/vue/navigation
http://localhost:8000/api/vue/setup/state
http://localhost:8000/api/vue/session
http://localhost:8000/api/vue/dashboard/summary
http://localhost:8000/api/vue/jobs
http://localhost:8000/api/vue/settings
http://localhost:8000/api/vue/workspace/status
```

Expected:

- all return JSON
- no HTML returned
- no secrets returned
- no absolute filesystem paths returned from workspace status
- `contract_version` is `1`
- `ok` field exists
- legacy `/ui/*` routes still work

Also run Vue dev server:

```bash
npm run dev:vue
```

Expected:

- Vue placeholder routes still load
- `/vue-smoke` still works
- no browser console errors caused by this task

---

## Acceptance Criteria

This task is complete only if:

1. `job_agent/routers/vue_api.py` exists.
2. `job_agent/main.py` registers the Vue API router.
3. `/api/vue/health` exists and returns JSON.
4. `/api/vue/navigation` exists and returns navigation groups.
5. `/api/vue/setup/state` exists and returns setup readiness fields.
6. `/api/vue/session` exists and does not expose secrets.
7. All required endpoint groups are defined.
8. Mutating/generative endpoints return safe 501 contract responses.
9. Apply/CV endpoints do not call LLMs or generate CV text.
10. Workspace backup endpoint does not create a backup file.
11. Workspace reset preview does not delete or reset anything.
12. Workspace status does not expose absolute local filesystem paths.
13. Settings endpoint does not expose API keys, tokens, passwords, credentials, or secrets.
14. Vue API client has `vueApiFetch`.
15. Backend tests for Vue API contracts are added.
16. API contract documentation is added.
17. `npm run build:vue` passes.
18. Focused Vue API contract tests pass.
19. Existing Jinja templates are untouched.
20. Existing static JS files are untouched except `frontend/vue/src/api/client.js`.
21. Existing `/ui/*` routes are unchanged.
22. Backend business rules are unchanged.
23. Pinia remains installed and configured.
24. Vuex is not introduced.

---

## Forbidden Outcomes

Do not:

- migrate page UI
- connect Vue pages to real APIs yet
- remove Jinja templates
- delete static JS
- add SPA catch-all route
- modify `/ui/*` routes
- call LLMs from new contract endpoints
- generate CV content
- invent verified facts
- expose secrets
- expose absolute local filesystem paths
- create workspace backup files
- perform workspace reset/delete
- approve drafts
- change provider configuration logic
- change background worker behavior
- change database location
- use Vuex
- remove Pinia
- add TypeScript
- add Docker

---

## Final Codex Response

Report:

1. files added
2. files modified
3. backend router location
4. endpoint list implemented
5. commands run
6. `npm run build:vue` result
7. focused test result
8. full `pytest` result
9. whether full-test failures are pre-existing or caused by this task
10. manual validation result
11. known issues

Do not continue to page migration.
