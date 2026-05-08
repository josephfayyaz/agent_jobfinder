1. Current State Summary

 ┌──────────────────┬───────────────────────────────────────────┬────────────────────────────────────────────────┐
 │      Layer       │                 Location                  │                     Status                     │
 ├──────────────────┼───────────────────────────────────────────┼────────────────────────────────────────────────┤
 │ Vue SPA          │ /app/* (20 routes)                        │ All pages fetch real data; zero mutations      │
 ├──────────────────┼───────────────────────────────────────────┼────────────────────────────────────────────────┤
 │ Vue API contract │ /api/vue/* (38 endpoints)                 │ ~12 return 501 not_implemented; rest read-only │
 ├──────────────────┼───────────────────────────────────────────┼────────────────────────────────────────────────┤
 │ Bare JSON APIs   │ /apply/*, /drafts/*, etc. (94+ endpoints) │ Fully functional; used by legacy JS only       │
 ├──────────────────┼───────────────────────────────────────────┼────────────────────────────────────────────────┤
 │ Legacy Jinja UI  │ /ui/* (32 renderers)                      │ All mutation surfaces active                   │
 ├──────────────────┼───────────────────────────────────────────┼────────────────────────────────────────────────┤
 │ Legacy static JS │ frontend/static/ (16 files, ~3 635 LOC)   │ Handles all mutations via 43 fetch() calls     │
 └──────────────────┴───────────────────────────────────────────┴────────────────────────────────────────────────┘

 ---
 2. Vue Pages: Full vs Shell

 Partial (real data displayed, no mutations)

 Dashboard · Jobs · Companies · Applications · Drafts list · DraftDetail · Analytics ·
 Settings (display only) · Onboarding (status only) · Story Bank · Verified Facts ·
 Thesis · Offer Compass · About · Help · Workspace Reset · Setup Required

 Static shells (nothing works)

 - ApplyPage — 4-step UI built with disabled buttons; alerts user to use /ui/apply
 - NotFoundPage — static 404

 ---
 3. Legacy /ui Flows with Real Behavior

 ┌──────────────────────────────────────────────────┬─────────────────┬──────────────────────────────┬────────────┬────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                       Flow                       │     Surface     │           JS file            │ Complexity │                                                     Key endpoints                                                      │
 ├──────────────────────────────────────────────────┼─────────────────┼──────────────────────────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ Apply (parse → score → questions → draft → poll) │ /ui/apply       │ apply.js 205 LOC             │ High       │ /apply/parse, /apply/questions, /apply/generate, /apply/status/{id}                                                    │
 ├──────────────────────────────────────────────────┼─────────────────┼──────────────────────────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ Draft approval + cover letter                    │ /ui/drafts/{id} │ draft_detail.js 7.6 K        │ High       │ /drafts/{id}/approve, /drafts/{id}/reject, /drafts/{id}/cover-letter                                                   │
 ├──────────────────────────────────────────────────┼─────────────────┼──────────────────────────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ Draft list approve/reject                        │ /ui/drafts      │ (HTMX attrs)                 │ Low        │ /ui/drafts/{id}/approve, /ui/drafts/{id}/reject                                                                        │
 ├──────────────────────────────────────────────────┼─────────────────┼──────────────────────────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ Provider settings save                           │ /ui/settings    │ settings/provider.js 362 LOC │ High       │ /settings/save, /providers/validate, /lm-studio/models, /ollama/models                                                 │
 ├──────────────────────────────────────────────────┼─────────────────┼──────────────────────────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ Gmail OAuth                                      │ /ui/settings    │ settings/integrations.js     │ Medium     │ /gmail/oauth/start, /gmail/oauth/disconnect, /settings/reload                                                          │
 ├──────────────────────────────────────────────────┼─────────────────┼──────────────────────────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ Job queue mutations + discovery                  │ /ui/jobs        │ jobs.js 18 K                 │ High       │ /jobs/{id}/queue-state, /jobs/sync-gmail, /jobs/scan-career-pages, /jobs/{id}/enrich, /jobs/discover                   │
 ├──────────────────────────────────────────────────┼─────────────────┼──────────────────────────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ Companies add + toggle                           │ /ui/companies   │ companies.js                 │ Medium     │ POST /career-pages, /career-pages/{id}/toggle-active                                                                   │
 ├──────────────────────────────────────────────────┼─────────────────┼──────────────────────────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ Onboarding wizard (5 steps)                      │ /ui/onboarding  │ onboarding/*.js ~900 LOC     │ Very High  │ /providers/validate, /settings/save, /candidates/{id}/intake/start, /intake/answer, /candidates/{id}/onboarding-review │
 ├──────────────────────────────────────────────────┼─────────────────┼──────────────────────────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ Analytics lazy sections                          │ /ui/analytics   │ (HTMX attrs)                 │ Low        │ /analytics/skill-gaps, /analytics/discovery-health                                                                     │
 ├──────────────────────────────────────────────────┼─────────────────┼──────────────────────────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ Story bank rebuild                               │ /ui/story-bank  │ (HTMX form)                  │ Low        │ /ui/story-bank/rebuild                                                                                                 │
 ├──────────────────────────────────────────────────┼─────────────────┼──────────────────────────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ Offer compass add/delete                         │ /ui/offers      │ (HTMX form)                  │ Medium     │ POST /offers, /ui/offers/{id}/delete                                                                                   │
 ├──────────────────────────────────────────────────┼─────────────────┼──────────────────────────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ Thesis CRUD + outreach                           │ /ui/thesis      │ (Jinja forms)                │ High       │ /thesis-targets CRUD, /thesis-targets/{id}/generate-email, /outreach-drafts/{id}/approve                               │
 ├──────────────────────────────────────────────────┼─────────────────┼──────────────────────────────┼────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ Draft bullet rewrite (HITL)                      │ /ui/drafts/{id} │ draft_detail.js              │ Very High  │ /drafts/{id}/clarify, /drafts/{id}/preview/update, /drafts/{id}/inferred-additions/*                                   │
 └──────────────────────────────────────────────────┴─────────────────┴──────────────────────────────┴────────────┴────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

 ---
 4. Backend Readiness for Each Vue Page

 Apply (Spec 022 target)

 All four backend endpoints exist and are fully functional in jobs.py:
 - POST /apply/parse → score + gaps + matched skills
 - POST /apply/questions → LLM-generated gap-filling questions
 - POST /apply/generate → spawns WorkflowTask, returns task_id
 - GET /apply/status/{task_id} → polls WorkflowTask, returns {status, draft_id}

 Vue stubs in vue_api.py: three /api/vue/apply/* stubs exist but return 501.
 Missing: GET /api/vue/apply/status/{task_id} — no stub exists yet.

 Draft Actions (Spec 023 target)

 Backend endpoints exist: POST /drafts/{id}/approve, /drafts/{id}/cover-letter,
 POST /ui/drafts/{id}/approve (Jinja), POST /ui/drafts/{id}/reject (Jinja).
 Vue stubs in vue_api.py: /api/vue/drafts/{id}/approve exists (501), reject and cover-letter missing.

 Settings Mutations (Spec 024 target)

 Backend: POST /settings/save, POST /providers/validate, GET /lm-studio/models,
 GET /ollama/models all exist as bare endpoints.
 Vue stubs: none for any of these — SettingsPage.vue has zero editable form fields.
 Requires new /api/vue/settings POST route AND Vue UI redesign for the settings forms.

 Jobs Mutations (Spec 025 target)

 Backend: POST /jobs/{id}/queue-state, POST /jobs/sync-gmail,
 POST /jobs/scan-career-pages, POST /jobs/{id}/enrich all exist.
 Vue stubs: none.

 Onboarding (Spec 026 target)

 Backend: All candidate + intake endpoints exist in candidates.py.
 Vue stubs: GET endpoints for status/steps exist; no mutation wrappers.
 Depends on Spec 024 patterns (provider validation), Spec 022 patterns (intake polling).

 Companies (Spec 027), Career Tools (Spec 028), Thesis (Spec 029)

 All backend endpoints exist. No Vue contract wrappers.

 ---
 5. Missing /api/vue Endpoints (full list)

 ┌────────────────────────────────────────────────┬──────────────────────────────┬──────┐
 │                    Endpoint                    │            Status            │ Spec │
 ├────────────────────────────────────────────────┼──────────────────────────────┼──────┤
 │ POST /api/vue/apply/score                      │ stub (501) → needs real impl │ 022  │
 ├────────────────────────────────────────────────┼──────────────────────────────┼──────┤
 │ POST /api/vue/apply/questions                  │ stub (501) → needs real impl │ 022  │
 ├────────────────────────────────────────────────┼──────────────────────────────┼──────┤
 │ POST /api/vue/apply/draft                      │ stub (501) → needs real impl │ 022  │
 ├────────────────────────────────────────────────┼──────────────────────────────┼──────┤
 │ GET /api/vue/apply/status/{task_id}            │ missing entirely             │ 022  │
 ├────────────────────────────────────────────────┼──────────────────────────────┼──────┤
 │ POST /api/vue/drafts/{id}/approve              │ stub (501) → needs real impl │ 023  │
 ├────────────────────────────────────────────────┼──────────────────────────────┼──────┤
 │ POST /api/vue/drafts/{id}/reject               │ missing                      │ 023  │
 ├────────────────────────────────────────────────┼──────────────────────────────┼──────┤
 │ POST /api/vue/drafts/{id}/cover-letter         │ missing                      │ 023  │
 ├────────────────────────────────────────────────┼──────────────────────────────┼──────┤
 │ POST /api/vue/settings (save)                  │ missing                      │ 024  │
 ├────────────────────────────────────────────────┼──────────────────────────────┼──────┤
 │ POST /api/vue/providers/validate               │ missing                      │ 024  │
 ├────────────────────────────────────────────────┼──────────────────────────────┼──────┤
 │ GET /api/vue/providers/lm-studio/models        │ missing                      │ 024  │
 ├────────────────────────────────────────────────┼──────────────────────────────┼──────┤
 │ GET /api/vue/providers/ollama/models           │ missing                      │ 024  │
 ├────────────────────────────────────────────────┼──────────────────────────────┼──────┤
 │ POST /api/vue/gmail/oauth/start                │ missing                      │ 024  │
 ├────────────────────────────────────────────────┼──────────────────────────────┼──────┤
 │ POST /api/vue/gmail/oauth/disconnect           │ missing                      │ 024  │
 ├────────────────────────────────────────────────┼──────────────────────────────┼──────┤
 │ POST /api/vue/jobs/{id}/queue-state            │ missing                      │ 025  │
 ├────────────────────────────────────────────────┼──────────────────────────────┼──────┤
 │ POST /api/vue/jobs/sync-gmail                  │ missing                      │ 025  │
 ├────────────────────────────────────────────────┼──────────────────────────────┼──────┤
 │ POST /api/vue/jobs/scan-career-pages           │ missing                      │ 025  │
 ├────────────────────────────────────────────────┼──────────────────────────────┼──────┤
 │ POST /api/vue/jobs/{id}/enrich                 │ missing                      │ 025  │
 ├────────────────────────────────────────────────┼──────────────────────────────┼──────┤
 │ POST /api/vue/candidates/{id}/intake/start     │ missing                      │ 026  │
 ├────────────────────────────────────────────────┼──────────────────────────────┼──────┤
 │ POST /api/vue/candidates/{id}/intake/answer    │ missing                      │ 026  │
 ├────────────────────────────────────────────────┼──────────────────────────────┼──────┤
 │ POST /api/vue/settings (already in 024)        │ reused                       │ 026  │
 ├────────────────────────────────────────────────┼──────────────────────────────┼──────┤
 │ GET /api/vue/candidates/{id}/onboarding-review │ missing                      │ 026  │
 ├────────────────────────────────────────────────┼──────────────────────────────┼──────┤
 │ POST /api/vue/career-pages                     │ missing                      │ 027  │
 ├────────────────────────────────────────────────┼──────────────────────────────┼──────┤
 │ POST /api/vue/career-pages/{id}/toggle-active  │ missing                      │ 027  │
 ├────────────────────────────────────────────────┼──────────────────────────────┼──────┤
 │ POST /api/vue/story-bank/rebuild               │ missing                      │ 028  │
 ├────────────────────────────────────────────────┼──────────────────────────────┼──────┤
 │ POST /api/vue/offers                           │ missing                      │ 028  │
 ├────────────────────────────────────────────────┼──────────────────────────────┼──────┤
 │ DELETE /api/vue/offers/{id}                    │ missing                      │ 028  │
 ├────────────────────────────────────────────────┼──────────────────────────────┼──────┤
 │ All thesis mutations (5 endpoints)             │ missing                      │ 029  │
 └────────────────────────────────────────────────┴──────────────────────────────┴──────┘

 ---
 6. Recommended Migration Order

 Priority rationale:
 1. Apply first — backend fully ready, clean 4-step JS pattern (205 LOC), Vue shell already has
 all 4 step cards built, 501 stubs exist to upgrade. Lowest risk to start.
 2. Draft approval second — small number of actions (approve/reject/cover-letter), no LLM wait,
 users need this daily. Bullet rewrite (HITL) deferred to a later spec (too complex).
 3. Settings mutations third — needed by everything downstream; unblocks Gmail OAuth in Vue.
 Security-critical: must maintain all hardening tests.
 4. Jobs mutations fourth — queue-state and discovery triggers; high user value.
 5. Onboarding fifth — depends on settings patterns (024) and intake patterns (022).
 6. Companies, Career Tools, Thesis — lower daily traffic; migrate in order.
 7. Deprecation + Deletion — after all mutation flows verified.

 ---
 7. Spec Sequence

 022  Apply flow (parse → score → questions → draft → poll → navigate to /app/drafts/{id})
 023  Draft approval (approve + reject on list and detail; cover letter generation)
 024  Settings mutations (provider save, Gmail OAuth, model discovery)
 025  Jobs mutations (queue-state, discovery triggers, enrichment)
 026  Onboarding Vue migration (full 5-step wizard)
 027  Companies Vue mutations (add, toggle active)
 028  Career tools Vue mutations (story bank rebuild, offer compass add/delete)
 029  Thesis Vue mutations (targets CRUD, generate-email, approve/mark-sent outreach)
 030  /ui deprecation (redirect banners, legacy-UI notice, /ui → /app redirects)
 031  /ui deletion (remove Jinja renderers, legacy templates, legacy static JS)

 ---
 8. Spec Details

 ---
 Spec 022 — Apply Flow Vue Migration

 Purpose: Wire the 4-step ApplyPage.vue shell (already built, currently disabled) to the fully-
 functional backend apply endpoints. Implement state management, LLM polling, and router navigation
 to /app/drafts/{id} on completion.

 Files modified:
 - job_agent/routers/vue_api.py — upgrade 3 stubs; add GET /api/vue/apply/status/{task_id}
 - frontend/vue/src/pages/ApplyPage.vue — implement all 4 step transitions + polling

 Endpoints used/added:
 - POST /api/vue/apply/score → delegates to /apply/parse; returns {score, matched, gaps, job_data}
 - POST /api/vue/apply/questions → delegates to /apply/questions; returns {questions}
 - POST /api/vue/apply/draft → delegates to /apply/generate; returns {task_id}
 - GET /api/vue/apply/status/{task_id} → NEW; delegates to /apply/status/{task_id};
 returns {status, draft_id?}

 Payload alignment note: Legacy uses job_text (Form), Vue stubs use job_description. The
 new backend handlers must accept the Vue contract field names and translate before calling the
 underlying service logic (or the stubs must be rebuilt from scratch using the service layer directly
 rather than delegating to the legacy endpoints, which accept Form data).

 Tests required: tests/test_vue_apply_flow.py
 - POST /api/vue/apply/score with valid text → 200, contract envelope, score + gaps present
 - POST /api/vue/apply/score with empty text → 422
 - POST /api/vue/apply/questions with job_data + gaps → 200, questions array
 - POST /api/vue/apply/draft with job_data + answers → 200, task_id UUID
 - GET /api/vue/apply/status/{task_id} with valid UUID → 200, status in allowed enum
 - GET /api/vue/apply/status/not-a-uuid → 404

 Safety constraints:
 - Require explicit "Generate draft" button click — no auto-generation
 - Poll interval: 3 s with _errors >= 3 guard (matching legacy apply.js pattern already tested)
 - On completion, navigate with router.push("/drafts/{draft_id}") — NOT window.location.href
 - Never navigate to /ui/drafts/* from Vue

 Acceptance criteria:
 - User can paste JD in Vue → score shown → questions rendered → draft generated →
 navigates to /app/drafts/{draft_id} with draft visible
 - tests/test_vue_apply_flow.py all pass
 - All pre-existing tests still pass (no regression)
 - /ui/apply still functional (untouched)

 ---
 Spec 023 — Draft Actions Vue Migration

 Purpose: Enable approve, reject, and cover-letter actions in DraftsPage.vue and
 DraftDetailPage.vue. Defers HITL bullet rewrite (too complex) to a later spec.

 Files modified:
 - job_agent/routers/vue_api.py — upgrade approve stub; add reject and cover-letter endpoints
 - frontend/vue/src/pages/DraftDetailPage.vue — wire approve/reject/cover-letter buttons
 - frontend/vue/src/pages/DraftsPage.vue — add inline approve/reject per row

 Endpoints used/added:
 - POST /api/vue/drafts/{id}/approve → upgrade existing 501 stub; delegates to /drafts/{id}/approve
 - POST /api/vue/drafts/{id}/reject → NEW; sets approved = False on ResumeDraft
 - POST /api/vue/drafts/{id}/cover-letter → NEW; delegates to /drafts/{id}/cover-letter

 Tests required: tests/test_vue_draft_actions.py
 - Approve → draft.approved is True, response is contract envelope
 - Reject → draft.approved is False (or null)
 - Cover-letter → returns cover letter text in contract envelope
 - All three with missing draft_id → 404
 - Revise/polish stubs still return 501 (not upgraded in this spec)

 Safety constraints:
 - Approve button must show a confirmation dialog ("Approve this draft?") before calling the endpoint
 - Never auto-approve; no background approvals
 - Reject does NOT delete draft — just sets status

 Acceptance criteria:
 - Approve/reject visible and functional in both DraftsPage and DraftDetailPage
 - Cover letter button generates and displays letter inline
 - HITL bullet rewrite buttons remain disabled (deferred)
 - /ui/drafts and /ui/drafts/{id} still functional

 ---
 Spec 024 — Settings Mutations Vue Migration

 Purpose: Enable provider configuration, Gmail OAuth, and model discovery in SettingsPage.vue.
 Requires adding editable form fields to the Vue page (currently display-only) AND new backend
 contract endpoints. Most security-critical spec in the series.

 Files modified:
 - job_agent/routers/vue_api.py — add POST /api/vue/settings, POST /api/vue/providers/validate,
 GET /api/vue/providers/lm-studio/models, GET /api/vue/providers/ollama/models,
 POST /api/vue/gmail/oauth/start, POST /api/vue/gmail/oauth/disconnect
 - frontend/vue/src/pages/SettingsPage.vue — add provider form section with provider radio buttons,
 API key password fields, local URL inputs; Gmail connect/disconnect buttons; save + validate buttons

 Endpoints used/added:
 - POST /api/vue/settings → delegates to /settings/save; returns safe settings envelope
 (NEVER echoes back secrets in response — same rule as GET /api/vue/settings)
 - POST /api/vue/providers/validate → delegates to /providers/validate
 - GET /api/vue/providers/lm-studio/models?base_url=... → delegates to /lm-studio/models
 - GET /api/vue/providers/ollama/models?base_url=... → delegates to /ollama/models
 - POST /api/vue/gmail/oauth/start → delegates to /gmail/oauth/start; returns {auth_url}
 (Vue then does window.location.href = auth_url)
 - POST /api/vue/gmail/oauth/disconnect → delegates to /gmail/oauth/disconnect

 Tests required: tests/test_vue_settings_mutations.py
 - POST /api/vue/settings with valid payload → 200, response has NO api_key / token / secret fields
 - POST /api/vue/settings with provider_mode only → 200 (partial save)
 - POST /api/vue/providers/validate with openai mode + key → 200 or provider error (not 501)
 - GET /api/vue/providers/lm-studio/models → 200 or {"ok": false} with provider-unavailable code
 - POST /api/vue/gmail/oauth/start → 200, response has auth_url, no client_secret
 - POST /api/vue/gmail/oauth/disconnect → 200
 - Existing tests/test_settings_copy_consistency.py still passes
 - Existing tests/test_legacy_ui_settings_surface_hardening.py still passes

 Safety constraints:
 - POST /api/vue/settings response MUST include secrets_exposed: false
 - API key fields: type="password", never prefilled with current values
 - Placeholder text must follow the safe vocabulary from spec 020 ("Leave blank to keep the current
 setting", not actual key prefixes)
 - Gmail OAuth: redirect is server-side; Vue only receives auth_url, never client_secret
 - Provider model fields: use same safe placeholder copy from spec 020

 Acceptance criteria:
 - User can change provider mode + save from Vue settings page
 - User can enter/update API keys from Vue settings page
 - User can connect/disconnect Gmail OAuth from Vue settings page
 - All existing settings hardening tests pass without modification
 - /ui/settings still functional

 ---
 Spec 025 — Jobs Mutations Vue Migration

 Purpose: Enable job queue-state changes (shortlist, archive, etc.), Gmail sync, career-page
 scans, and enrichment triggers in JobsPage.vue.

 Files modified:
 - job_agent/routers/vue_api.py — add 4 endpoints
 - frontend/vue/src/pages/JobsPage.vue — add queue-action buttons per row; sync/scan toolbar buttons

 Endpoints used/added:
 - POST /api/vue/jobs/{id}/queue-state → delegates to /jobs/{id}/queue-state
 - POST /api/vue/jobs/sync-gmail → delegates to /jobs/sync-gmail
 - POST /api/vue/jobs/scan-career-pages → delegates to /jobs/scan-career-pages
 - POST /api/vue/jobs/{id}/enrich → delegates to /jobs/{id}/enrich

 Tests required: tests/test_vue_jobs_mutations.py
 - Queue-state change → job.queue_state updated in DB
 - sync-gmail returns 200 with contract envelope (or provider-unavailable)
 - scan-career-pages returns 200 with contract envelope
 - enrich: queues enrichment task, returns task info

 Safety constraints:
 - Queue-state "apply" action must NOT auto-generate a draft — only moves job to apply queue
 - Discovery triggers return immediately (async); Vue polls or reloads after a delay
 - No LLM calls triggered directly from contract endpoints

 Acceptance criteria:
 - User can shortlist/archive jobs from /app/jobs
 - Sync and scan buttons trigger backend workflows
 - /ui/jobs still functional

 ---
 Spec 026 — Onboarding Vue Migration

 Purpose: Replace the legacy 5-step onboarding wizard (/ui/onboarding) with a fully functional
 equivalent in /app/onboarding. Most complex spec due to multi-step state, file uploads, intake
 polling, and review editing.

 Depends on: Spec 022 (intake polling pattern), Spec 024 (provider validation pattern).

 Files modified:
 - job_agent/routers/vue_api.py — add intake start, intake answer, onboarding-review, readiness
 check endpoints
 - frontend/vue/src/pages/OnboardingPage.vue — replace status-display shell with full 5-step wizard

 Endpoints used/added:
 - POST /api/vue/candidates/{id}/intake/start → delegates to /candidates/{id}/intake/start
 - POST /api/vue/candidates/{id}/intake/answer → delegates to /candidates/{id}/intake/answer
 - GET /api/vue/candidates/{id}/onboarding-review → delegates to /candidates/{id}/onboarding-review
 - GET /api/vue/candidates/{id}/readiness → delegates to /candidates/{id}/readiness
 - Provider validate + settings save reused from Spec 024

 Tests required: tests/test_vue_onboarding_flow.py
 - Setup wizard shows provider step first
 - After provider validation, advances to intake step
 - File upload + intake/start returns questions or review
 - intake/answer saves answers
 - Readiness check reflects completion status

 Safety constraints:
 - File upload: accept only PDF/TXT (same as legacy intake.js restriction)
 - Provider validation must require explicit "Validate & Continue" button click
 - Never auto-advance steps without user action

 Acceptance criteria:
 - New user can complete full 5-step onboarding from /app/onboarding
 - /ui/onboarding still functional (for rollback)

 ---
 Spec 027 — Companies Vue Mutations

 Purpose: Enable add-company form and toggle-active from CompaniesPage.vue.

 Files modified:
 - job_agent/routers/vue_api.py — add 2 endpoints
 - frontend/vue/src/pages/CompaniesPage.vue — add add-company form + toggle buttons

 Endpoints used/added:
 - POST /api/vue/career-pages → delegates to POST /career-pages
 - POST /api/vue/career-pages/{id}/toggle-active → delegates to existing toggle endpoint

 Tests required: tests/test_vue_companies_mutations.py

 Acceptance criteria: User can add a company and toggle active state from /app/companies.

 ---
 Spec 028 — Career Tools Vue Mutations

 Purpose: Enable story bank rebuild and offer compass add/delete from Vue.

 Files modified:
 - job_agent/routers/vue_api.py — add 3 endpoints
 - frontend/vue/src/pages/StoryBankPage.vue — add rebuild button
 - frontend/vue/src/pages/OfferCompassPage.vue — add offer form + delete buttons

 Endpoints used/added:
 - POST /api/vue/story-bank/rebuild → delegates to /ui/story-bank/rebuild logic (or refactored)
 - POST /api/vue/offers → delegates to POST /offers
 - DELETE /api/vue/offers/{id} → delegates to /ui/offers/{id}/delete logic

 Tests required: tests/test_vue_career_tools_mutations.py

 Acceptance criteria: User can rebuild stories and manage offers from /app.

 ---
 Spec 029 — Thesis Vue Mutations

 Purpose: Enable thesis target CRUD, email generation, and outreach draft approval from
 ThesisPage.vue.

 Files modified:
 - job_agent/routers/vue_api.py — add 5+ endpoints
 - frontend/vue/src/pages/ThesisPage.vue — add create/edit/delete targets, generate email, approve
 outreach buttons

 Endpoints used/added:
 - POST /api/vue/thesis-targets → create
 - PATCH /api/vue/thesis-targets/{id} → update
 - DELETE /api/vue/thesis-targets/{id} → archive
 - POST /api/vue/thesis-targets/{id}/generate-email → LLM call; returns draft
 - POST /api/vue/outreach-drafts/{id}/approve → approve (requires confirm dialog)
 - POST /api/vue/outreach-drafts/{id}/mark-sent → mark sent (requires confirm dialog)

 Safety constraints:
 - Mark-sent and approve MUST require an explicit confirmation dialog — no auto-send
 - Email generation is LLM-backed; show loading state and error recovery

 Tests required: tests/test_vue_thesis_mutations.py

 Acceptance criteria: Full thesis outreach flow available from /app/thesis.

 ---
 Spec 030 — /ui Deprecation

 Purpose: Mark all /ui/* routes as deprecated, add redirect banners to /app equivalents,
 and add HTTP-level soft redirects where safe to do so.

 Pre-conditions: Specs 022–029 all passing, all mutation flows verified in Vue.

 Files modified:
 - job_agent/routers/ — add deprecation notice to all /ui/* Jinja renderers (banner in HTML)
 - frontend/templates/base.html — add legacy-mode notice bar at top of every /ui page
 - Optionally add 301 redirects for /ui/dashboard → /app/dashboard etc. (only for routes
 with no form state)

 Tests required: tests/test_ui_deprecation.py
 - Each /ui/* page returns 200 AND contains deprecation notice text
 - /ui/* pages with form state (apply, settings, onboarding) do NOT redirect — still serve HTML

 Acceptance criteria:
 - Every /ui/* page shows a banner: "This page is deprecated. Use the new interface at /app."
 - /app/* equivalents are fully functional

 ---
 Spec 031 — /ui Deletion

 Purpose: Remove all Jinja renderers, legacy templates, and legacy static JS that are no longer
 needed.

 Pre-conditions: Spec 030 has been live for at least one release cycle; user confirms no
 /ui/* route traffic observed.

 Files deleted:
 - All 32 /ui/* route handlers from routers
 - frontend/templates/*.html (all Jinja page templates)
 - frontend/templates/partials/ (all partials)
 - frontend/static/*.js (apply.js, companies.js, draft_detail.js, jobs.js, onboarding.js,
 settings.js, verified_facts.js, workspace_reset.js)
 - frontend/static/onboarding/ (entire directory)
 - frontend/static/settings/ (entire directory)
 - frontend/static/app.js (legacy bootstrap — Vue handles this)

 Files kept:
 - frontend/static/app.css (still used by onboarding.html during transition)
 - frontend/static/dist/ (Vue build output)
 - frontend/static/tailwind.css

 Tests modified:
 - Remove all test_legacy_surface_hardening.py, test_legacy_ui_settings_surface_hardening.py
 assertions that reference /ui/*
 - Add smoke-test assertions that /ui/* returns 404

 Acceptance criteria:
 - pytest still green
 - No references to /ui/* in any route registration
 - frontend/templates/ directory empty or removed

 ---
 9. When It Becomes Safe to Deprecate /ui/*

 All three conditions must be true:

 1. Feature parity: Specs 022–029 all pass; every legacy mutation flow has a working Vue
 equivalent with tests
 2. No secret regression: All hardening tests still pass (test_settings_copy_consistency.py,
 test_vue_api_contracts.py, test_legacy_surface_hardening.py)
 3. Human confirmation: User explicitly confirms they can complete their daily workflow from
 /app alone

 Earliest possible date: After spec 029 is complete and verified.

 ---
 10. When It Becomes Safe to Delete /ui + Legacy Templates/JS

 All three conditions must be true:

 1. Deprecation active: Spec 030 has been deployed and working for at least one full week
 2. Zero test dependencies on /ui: No existing test makes a request to /ui/* and asserts
 on mutation behavior
 3. Human confirmation: User confirms deletion
     - frontend/templates/ directory empty or removed
                                                                            
     ---
     9. When It Becomes Safe to Deprecate /ui/*
                                
     All three conditions must be true:
                                                                                                                                                                                  
     1. Feature parity: Specs 022–029 all pass; every legacy mutation flow has a working Vue                                                                                      
     equivalent with tests                                                                                                                                                        
     2. No secret regression: All hardening tests still pass (test_settings_copy_consistency.py,                                                                                  
     test_vue_api_contracts.py, test_legacy_surface_hardening.py)                                                                                                                 
     3. Human confirmation: User explicitly confirms they can complete their daily workflow from                                                                                  
     /app alone                                                                                                                                                                   
                                                                                                                                                                                  
     Earliest possible date: After spec 029 is complete and verified.                                                                                                             
                                                                                                                                                                                  
     ---                                                                                                                                                                          
     10. When It Becomes Safe to Delete /ui + Legacy Templates/JS                                                                                                                 
                                                                                                                                                                                  
     All three conditions must be true:                                                                                                                                           
                                                                                                                                                                                  
     1. Deprecation active: Spec 030 has been deployed and working for at least one full week                                                                                     
     2. Zero test dependencies on /ui: No existing test makes a request to /ui/* and asserts                                                                                      
     on mutation behavior
     3. Human confirmation: User confirms deletion
                                                        
     The deletion is irreversible. Do NOT delete until user explicitly approves.
                                                                                   
     ---
     11. Risks and Rollback Strategy
                                                 
     ┌────────────────────────────────────────────────────────┬──────────────────────┬───────────────────────────────────────────────────────────────────────────────────────────────┐
     │                          Risk                          │      Likelihood      │                                          Mitigation                                           │
     ├────────────────────────────────────────────────────────┼──────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────┤
     │ New /api/vue endpoints break existing hardening tests  │ Medium               │ Every spec runs full test suite before marking complete                                       │
     ├────────────────────────────────────────────────────────┼──────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────┤
     │ Vue settings form exposes secrets                      │ High risk if skipped │ Spec 024 explicitly repeats all hardening tests; response MUST include secrets_exposed: false │
     ├────────────────────────────────────────────────────────┼──────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────┤
     │ Apply polling breaks if task takes longer than 3 × 3 s │ Medium               │ Inherit _errors >= 3 guard from legacy; reset error count on success                          │
     ├────────────────────────────────────────────────────────┼──────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────┤
     │ OAuth redirect loop if /app settings page is broken    │ Medium               │ /gmail/oauth/callback still redirects to /ui/settings until Spec 030; safe fallback           │
     ├────────────────────────────────────────────────────────┼──────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────┤
     │ User deletes /ui before Vue parity                     │ Low (plan gates it)  │ Spec 031 pre-condition requires explicit human confirmation                                   │
     ├────────────────────────────────────────────────────────┼──────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────┤
     │ HITL bullet rewrite not in any spec                    │ By design            │ DraftDetailPage retains disabled "Revise draft" button; deferred to post-031 stretch goal     │
     ├────────────────────────────────────────────────────────┼──────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────┤
     │ Contract version mismatch on Safari/cached Vue build   │ Low                  │ Keep ?v=N cache-busting; Vue contract version stays 1 throughout                              │                                                         
     └────────────────────────────────────────────────────────┴──────────────────────┴───────────────────────────────────────────────────────────────────────────────────────────────┘
                                                                                 
     Rollback at any spec:
     - All specs leave /ui/* fully functional until Spec 030
     - If a Vue spec breaks something, user can fall back to /ui/* immediately
     - Git revert of the spec commit restores prior state; tests must pass after revert
                                
     ---                                     
     - Git revert of the spec commit restores prior state; tests must pass after revert

     ---
     12. Notes on Spec Ordering vs Pending Phases K–O

     The pending Codex specs K–O (provider controller deduplication, state modularization, CSS isolation,
     cost UX, discovery quality) are independent of and compatible with the Vue migration specs 022+.
     They target the legacy JS internals and backend services, not the Vue pages or contract layer.

     They may be run in parallel or interleaved, but:
     - Spec K (provider controller deduplication) would simplify settings/provider.js before it gets
     removed in Spec 031 — run K before Spec 031 but it is not a blocker for Specs 022–030
     - Spec N (LLM token usage) adds to the workflow service layer — compatible with Spec 022 as long
     as the new apply endpoint handles the updated generate() signature

     Recommended order if running both tracks:
     K → 022 → L → 023 → M → 024 → N → 025 → O → 026 → 027 → 028 → 029 → 030 → 031
     (Interleaved so legacy JS cleanup happens before the corresponding Vue migration makes the legacy
     code redundant)

⏺ The plan is complete. Here's a quick summary of the roadmap:

  10-spec migration sequence (022 → 031):

  ┌──────┬────────────────────┬──────────────────────────────────────────────────────────────────────┐
  │ Spec │        What        │                              Key change                              │
  ├──────┼────────────────────┼──────────────────────────────────────────────────────────────────────┤
  │ 022  │ Apply flow         │ Wire 4-step ApplyPage.vue + upgrade 3 stubs + add status poller      │
  ├──────┼────────────────────┼──────────────────────────────────────────────────────────────────────┤
  │ 023  │ Draft actions      │ Approve/reject/cover-letter in DraftDetailPage + DraftsPage          │
  ├──────┼────────────────────┼──────────────────────────────────────────────────────────────────────┤
  │ 024  │ Settings mutations │ Provider form + Gmail OAuth in SettingsPage (most security-critical) │
  ├──────┼────────────────────┼──────────────────────────────────────────────────────────────────────┤
  │ 025  │ Jobs mutations     │ Queue-state, sync-gmail, scan, enrich in JobsPage                    │
  ├──────┼────────────────────┼──────────────────────────────────────────────────────────────────────┤
  │ 026  │ Onboarding wizard  │ Full 5-step Vue wizard (depends on 022 + 024 patterns)               │
  ├──────┼────────────────────┼──────────────────────────────────────────────────────────────────────┤
  │ 027  │ Companies          │ Add/toggle in CompaniesPage                                          │
  ├──────┼────────────────────┼──────────────────────────────────────────────────────────────────────┤
  │ 028  │ Career tools       │ Story bank rebuild + offer compass add/delete                        │
  ├──────┼────────────────────┼──────────────────────────────────────────────────────────────────────┤
  │ 029  │ Thesis             │ Full CRUD + generate-email + outreach approval                       │
  ├──────┼────────────────────┼──────────────────────────────────────────────────────────────────────┤
  │ 030  │ Deprecation        │ Banner on every /ui/* page redirecting to /app                       │
  ├──────┼────────────────────┼──────────────────────────────────────────────────────────────────────┤
  │ 031  │ Deletion           │ Remove all Jinja renderers, legacy templates, legacy static JS       │
  └──────┴────────────────────┴──────────────────────────────────────────────────────────────────────┘

  First target confirmed: Spec 022 — apply flow is the right start. All four backend endpoints (/apply/parse, /apply/questions, /apply/generate, /apply/status/{id}) are fully functional. The Vue shell already has all 4 step cards built.
  The three /api/vue/apply/* stubs just need their 501s replaced with real delegating implementations, plus one new status endpoint.

  The K–O Codex specs remain compatible and can run interleaved (K → 022 → L → 023 → M → 024 → N → 025 → O → 026 → ...).

  Ready to start with Spec 022 whenever you say go — or if you want spec files written first (e.g. AGENT_SPECS/pending/claude/022_apply_flow_vue_migration.md), say the word.