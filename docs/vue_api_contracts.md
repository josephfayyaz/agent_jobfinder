# Vue API Contracts

`/api/vue/*` provides a small JSON contract layer for the Vue migration shell.
Legacy `/ui/*` routes remain active during the migration.

Contract version: `1`

Endpoints:
- Global: `/api/vue/health`, `/api/vue/navigation`, `/api/vue/setup/state`, `/api/vue/session`
- Dashboard: `/api/vue/dashboard/summary`
- Jobs: `/api/vue/jobs`, `/api/vue/jobs/{job_id}`
- Companies: `/api/vue/companies`, `/api/vue/companies/{company_id}`
- Apply: `/api/vue/apply/score`, `/api/vue/apply/questions`, `/api/vue/apply/draft`
- Applications: `/api/vue/applications`, `/api/vue/applications/{application_id}`
- Drafts: `/api/vue/drafts`, `/api/vue/drafts/{draft_id}`, `/api/vue/drafts/{draft_id}`, `/api/vue/drafts/{draft_id}/revise`, `/api/vue/drafts/{draft_id}/polish`, `/api/vue/drafts/{draft_id}/approve`
- Onboarding: `/api/vue/onboarding/state`, `/api/vue/onboarding/steps`
- Settings: `/api/vue/settings`
- Verified facts: `/api/vue/verified-facts`, `/api/vue/verified-facts/schema`
- Career tools: `/api/vue/story-bank`, `/api/vue/offer-compass`, `/api/vue/analytics/summary`, `/api/vue/thesis/targets`
- Workspace: `/api/vue/workspace/status`, `/api/vue/workspace/backup`, `/api/vue/workspace/reset-preview`
- Static info: `/api/vue/help`, `/api/vue/about`

Envelope shapes:
- Success: `{ "ok": true, "contract_version": 1, "data": ... }`
- Placeholder: success envelope plus `status: "placeholder"` and `message`
- Error: `{ "ok": false, "contract_version": 1, "error": { "code": "...", "message": "..." } }`

Security rules:
- No secrets in settings or session responses
- No CV generation, LLM calls, or approval logic in contract endpoints
- No workspace deletion, reset, or backup creation from contract endpoints
- No absolute local filesystem paths in workspace responses
