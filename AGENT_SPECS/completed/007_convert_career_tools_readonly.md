# 007 Convert Career Tools Readonly

## Goal

Convert four career-tools Vue pages from placeholders into real Vue pages:

```text
/story-bank
/offer-compass
/analytics
/thesis
```

Use the existing Vue API contract endpoints:

```text
GET /api/vue/story-bank
GET /api/vue/offer-compass
GET /api/vue/analytics/summary
GET /api/vue/thesis/targets
```

This task must be read-only.

Do not implement any mutation endpoints. Do not call LLMs.

Keep all legacy `/ui/*` routes active.

---

## Current State

Completed specs:

```text
AGENT_SPECS/completed/codex/001_vue_infrastructure.md
AGENT_SPECS/completed/codex/002_vue_layout_router.md
AGENT_SPECS/completed/codex/003_vue_api_contracts.md
AGENT_SPECS/completed/codex/004_convert_static_pages.md
AGENT_SPECS/completed/codex/005_convert_dashboard_jobs_companies.md
AGENT_SPECS/completed/claude/006_convert_applications_drafts_readonly.md
```

Already converted to real Vue pages:

```text
/about
/help
/setup-required
/dashboard
/jobs
/companies
/applications
/drafts
/drafts/:id
```

This task converts only:

```text
frontend/vue/src/pages/StoryBankPage.vue
frontend/vue/src/pages/OfferCompassPage.vue
frontend/vue/src/pages/AnalyticsPage.vue
frontend/vue/src/pages/ThesisPage.vue
```

Do not convert any other page.

---

## Hard Constraints

Do not modify backend business logic.

Do not modify LLM routing.

Do not call LLMs.

Do not generate CV content.

Do not revise CV drafts.

Do not polish CV drafts.

Do not approve CV drafts.

Do not submit applications.

Do not modify apply flow.

Do not modify verified-fact validation.

Do not modify human approval workflow.

Do not modify Gmail sync.

Do not modify background worker behavior.

Do not modify onboarding business rules.

Do not modify settings/provider/keyring logic.

Do not modify workspace reset/delete/backup behavior.

Do not add FastAPI SPA catch-all route.

Do not change existing `/ui/*` routes.

Do not delete or rewrite legacy Jinja templates.

Do not delete or rewrite existing static JS.

Do not migrate these pages yet:

```text
Apply
Onboarding
Settings
Verified Facts
Workspace Reset
```

Do not use Vuex.

Keep Pinia.

Do not use TypeScript.

Do not add Docker.

Do not switch package manager.

---

## Files To Modify

Modify only:

```text
frontend/vue/src/pages/StoryBankPage.vue
frontend/vue/src/pages/OfferCompassPage.vue
frontend/vue/src/pages/AnalyticsPage.vue
frontend/vue/src/pages/ThesisPage.vue
```

You may reuse shared Vue components already in `frontend/vue/src/components/`.

You may NOT modify:

```text
frontend/templates/
frontend/static/
start_apply/
config/
temp_mac_test/
```

Backend exception:

- Do not modify backend files unless one of the required `/api/vue/*` read-only contract endpoints is broken.
- If an endpoint is broken, fix only the contract endpoint implementation in `job_agent/routers/vue_api.py`.

---

## API Usage

The converted pages must use:

```js
vueApiFetch
```

from:

```text
frontend/vue/src/api/client.js
```

Use only these calls:

```text
vueApiFetch("/story-bank")
vueApiFetch("/offer-compass")
vueApiFetch("/analytics/summary")
vueApiFetch("/thesis/targets")
```

Do not call any mutation endpoints.

---

## Response Envelope

All endpoints use the same envelope:

```json
{
  "ok": true,
  "contract_version": 1,
  "status": "placeholder",
  "message": "...",
  "data": { ... }
}
```

`status` and `message` are optional and only present when relevant.

When `status == "placeholder"` the backend is not yet wired to real data.

Pages must handle both states safely.

---

## API Response Shapes

### `/story-bank`

Real data:
```json
{
  "data": {
    "items": [
      {
        "id": "uuid",
        "title": "Story title",
        "context": "STAR narrative context",
        "confidence_source": "intake_qa",
        "role_family_tags": ["engineering", "backend"],
        "updated_at": "2026-01-01T00:00:00"
      }
    ],
    "total": 1
  }
}
```

No data (placeholder):
```json
{
  "ok": true,
  "status": "placeholder",
  "message": "This list endpoint is ready for Vue migration but not wired to real data yet.",
  "data": { "items": [], "total": 0 }
}
```

### `/offer-compass`

Real data:
```json
{
  "data": {
    "items": [
      {
        "id": "uuid",
        "company": "Example Corp",
        "title": "Senior Engineer",
        "status": "offer",
        "overall_score": 87
      }
    ],
    "total": 1
  }
}
```

No data (placeholder):
```json
{
  "ok": true,
  "status": "placeholder",
  "message": "This list endpoint is ready for Vue migration but not wired to real data yet.",
  "data": { "items": [], "total": 0 }
}
```

### `/analytics/summary`

Real data (≥5 applications):
```json
{
  "data": {
    "funnel": {
      "total": 20,
      "applied": 20,
      "responded": 8,
      "interview": 4,
      "offer": 1,
      "rejected": 10,
      "discarded": 2,
      "response_rate_pct": 40,
      "interview_rate_pct": 20,
      "offer_rate_pct": 5
    },
    "score_analysis": {
      "buckets": [],
      "recommended_threshold": 70,
      "current_threshold": 60,
      "threshold_note": "..."
    },
    "skill_gaps": [
      { "gap": "Docker", "occurrences": 5 },
      { "gap": "Kubernetes", "occurrences": 3 }
    ],
    "weekly_activity": [
      { "week": "2026-W01", "applied": 3 },
      { "week": "2026-W02", "applied": 2 }
    ]
  }
}
```

Placeholder (fewer than 5 applications or service ValueError):
```json
{
  "ok": true,
  "status": "placeholder",
  "message": "This API contract is reserved for future Vue migration.",
  "data": { "items": [], "total": 0 }
}
```

**IMPORTANT:** Analytics has a different data shape from the list endpoints.
Detect real data by checking `data.funnel !== undefined`.
When `data.funnel` is undefined the response is placeholder and items/total are safe fallbacks.

### `/thesis/targets`

Always real data (never returns placeholder):
```json
{
  "data": {
    "items": [
      {
        "id": "uuid",
        "type": "professor",
        "name": "Prof Example",
        "institution": "Example University",
        "country": "Italy",
        "status": "prospect",
        "priority": 1,
        "updated_at": "2026-01-01T00:00:00"
      }
    ],
    "total": 1
  }
}
```

Empty (no targets yet):
```json
{
  "data": { "items": [], "total": 0 }
}
```

---

## Required Behavior

### `/story-bank`

Convert `StoryBankPage.vue` from placeholder to real Vue page.

It must:

1. Fetch data from `GET /api/vue/story-bank`.
2. Show loading state.
3. Show error state.
4. Handle placeholder API response safely.
5. Render story list if `data.items` exists and is non-empty.
6. Render empty state if no stories exist.
7. Show total count if available.
8. Show placeholder notice when `status == "placeholder"`.

Required visible sections:

```text
Story Bank
Narrative library status
Saved stories
Next actions
```

Allowed links:

```text
/apply
/verified-facts
/applications
```

Safe fields to render per story item:

```text
id
title
context
confidence_source
role_family_tags (array of strings — render as inline tags)
updated_at
```

---

### `/offer-compass`

Convert `OfferCompassPage.vue` from placeholder to real Vue page.

It must:

1. Fetch data from `GET /api/vue/offer-compass`.
2. Show loading state.
3. Show error state.
4. Handle placeholder API response safely.
5. Render offer list if `data.items` exists and is non-empty.
6. Render empty state if no offers exist.
7. Show total count if available.
8. Show placeholder notice when `status == "placeholder"`.

Required visible sections:

```text
Offer Compass
Offer comparison status
Ranked offers
Next actions
```

Allowed links:

```text
/applications
/drafts
/jobs
```

Safe fields to render per offer item:

```text
id
company
title
status
overall_score (number — display as score out of 100 if value exists)
```

---

### `/analytics`

Convert `AnalyticsPage.vue` from placeholder to real Vue page.

It must:

1. Fetch data from `GET /api/vue/analytics/summary`.
2. Show loading state.
3. Show error state.
4. Handle placeholder API response safely.
5. When placeholder: show info notice "Not enough data yet — analytics require at least 5 applications."
6. When real data exists (i.e. `data.funnel !== undefined`): render four sections.

Real data sections:

**Funnel** — show these fields if present:
```text
total, applied, responded, interview, offer, rejected, discarded
response_rate_pct, interview_rate_pct, offer_rate_pct
```

**Score Analysis** — show if present:
```text
recommended_threshold
current_threshold
threshold_note
```

**Skill Gaps** — render list of `{gap, occurrences}` pairs. Show empty notice if list is empty.

**Weekly Activity** — render list of `{week, applied}` pairs. Show empty notice if list is empty.

Required visible sections:

```text
Analytics
Pipeline analytics
Application funnel
Score analysis
Skill gaps
Weekly activity
Next actions
```

Allowed links:

```text
/applications
/drafts
/jobs
```

**IMPORTANT:** Do not render `score_analysis.buckets` (complex sub-object — omit from display).
Do not assume any field exists. Use optional chaining throughout.

---

### `/thesis`

Convert `ThesisPage.vue` from placeholder to real Vue page.

It must:

1. Fetch data from `GET /api/vue/thesis/targets`.
2. Show loading state.
3. Show error state.
4. Always treat as real data (endpoint never returns placeholder).
5. Render target list if `data.items` is non-empty.
6. Render empty state if no targets exist.
7. Show total count.

Required visible sections:

```text
Thesis
Thesis target tracking
Tracked targets
Next actions
```

Allowed links:

```text
/applications
/jobs
/companies
```

Safe fields to render per target item:

```text
id
type (display as badge: "professor" | "lab" | "company")
name
institution
country
status
priority (display as number if present)
updated_at
```

---

## Data Handling Rules

Pages must safely handle:

```text
response.data
response.data.items
response.data.total
response.data.funnel (analytics only)
response.status
response.message
missing fields
empty objects
network errors
backend offline
```

Use optional chaining and safe defaults throughout.

Do not invent missing values.

Do not render any field that looks like a secret.

Do not render absolute local filesystem paths.

If fields are missing, use fallback labels:

```text
Untitled story
Untitled offer
Unknown company
Status unavailable
```

---

## Recommended Implementation Pattern

Each page should use:

```js
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import AppPageHeader from "../components/AppPageHeader.vue";
import { vueApiFetch } from "../api/client";

const loading = ref(true);
const error = ref("");
const payload = ref(null);

onMounted(async () => {
  try {
    payload.value = await vueApiFetch("/story-bank");
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Request failed";
  } finally {
    loading.value = false;
  }
});

const responseData = computed(() => payload.value?.data ?? {});
const responseStatus = computed(() => payload.value?.status ?? "");
const responseMessage = computed(() => payload.value?.message ?? "");
const isPlaceholder = computed(() => responseStatus.value === "placeholder");
const items = computed(() =>
  Array.isArray(responseData.value.items) ? responseData.value.items.filter(Boolean) : []
);
const total = computed(() => responseData.value.total ?? items.value.length ?? 0);
```

For analytics, detect real data:

```js
const hasRealData = computed(() => responseData.value.funnel !== undefined);
const funnel = computed(() => responseData.value.funnel ?? {});
const scoreAnalysis = computed(() => responseData.value.score_analysis ?? {});
const skillGaps = computed(() =>
  Array.isArray(responseData.value.skill_gaps) ? responseData.value.skill_gaps : []
);
const weeklyActivity = computed(() =>
  Array.isArray(responseData.value.weekly_activity) ? responseData.value.weekly_activity : []
);
```

---

## Styling Requirements

Use Tailwind only.

Match current Vue shell:

```text
slate background
white cards
rounded-2xl
border border-slate-200
shadow-sm
text-slate-950
text-slate-600
```

Placeholder notice: amber-50 background, amber-900 text (matches existing pages).

Do not add new CSS files.

Do not install icon libraries.

Do not add animation libraries.

---

## Tests Required

Do not force a new Vue test framework.

Run existing tests and builds.

At minimum:

```bash
npm run build:vue
npm run css:build
pytest tests/test_vue_api_contracts.py
pytest
```

Do not fix unrelated known failures:

```text
tests/test_frontend_null_guards.py
tests/test_temp_harness.py
```

unless this task directly caused them.

If build fails because of Vue code, fix it.

If API contract tests fail because of this task, fix them.

---

## Manual Validation

Run Vue dev server:

```bash
npm run dev:vue
```

Open:

```text
http://localhost:5173/story-bank
http://localhost:5173/offer-compass
http://localhost:5173/analytics
http://localhost:5173/thesis
```

Expected `/story-bank`:

```text
- page loads without console errors
- not the old placeholder card
- shows "Narrative library status" section heading
- shows total count
- shows empty state or story list
- shows placeholder notice when backend not wired
```

Expected `/offer-compass`:

```text
- page loads without console errors
- not the old placeholder card
- shows "Offer comparison status" section heading
- shows total count
- shows empty state or offer list
- shows placeholder notice when backend not wired
```

Expected `/analytics`:

```text
- page loads without console errors
- not the old placeholder card
- shows "Pipeline analytics" section heading
- shows placeholder/insufficient-data notice when no real data
- shows funnel metrics when real data exists
- shows skill gaps section
- shows weekly activity section
```

Expected `/thesis`:

```text
- page loads without console errors
- not the old placeholder card
- shows "Thesis target tracking" section heading
- shows total count
- shows empty state or target list
```

Also verify these routes remain unchanged:

```text
http://localhost:5173/about
http://localhost:5173/help
http://localhost:5173/setup-required
http://localhost:5173/dashboard
http://localhost:5173/jobs
http://localhost:5173/companies
http://localhost:5173/applications
http://localhost:5173/drafts
http://localhost:5173/apply
http://localhost:5173/onboarding
http://localhost:5173/settings
http://localhost:5173/verified-facts
```

---

## Acceptance Criteria

This task is complete only if:

1. `StoryBankPage.vue` is converted from placeholder to real Vue page.
2. `OfferCompassPage.vue` is converted from placeholder to real Vue page.
3. `AnalyticsPage.vue` is converted from placeholder to real Vue page.
4. `ThesisPage.vue` is converted from placeholder to real Vue page.
5. Story Bank uses `vueApiFetch("/story-bank")`.
6. Offer Compass uses `vueApiFetch("/offer-compass")`.
7. Analytics uses `vueApiFetch("/analytics/summary")`.
8. Thesis uses `vueApiFetch("/thesis/targets")`.
9. Loading states exist on all pages.
10. Error states exist on all pages.
11. Placeholder API responses are handled safely on all pages.
12. Empty list states are handled safely on all pages.
13. Analytics shows insufficient-data notice when placeholder response.
14. Analytics shows funnel/score/gaps/activity sections only when real data present.
15. No mutation API calls are made.
16. No apply flow is migrated.
17. No CV generation is added.
18. No LLM calls are added.
19. No database mutation is added.
20. Existing Jinja templates are untouched.
21. Existing static JS files are untouched.
22. Existing `/ui/*` routes are unchanged.
23. Backend business logic is unchanged.
24. `npm run build:vue` passes.
25. `pytest tests/test_vue_api_contracts.py` passes.
26. Any full-test failures are reported and identified as pre-existing or caused by this task.

---

## Forbidden Outcomes

Do not:

- call any mutation endpoint
- call apply endpoints
- call draft revise/polish/approve endpoints
- generate CV content
- mutate any data
- migrate onboarding
- migrate settings
- migrate verified facts
- migrate workspace reset
- delete Jinja templates
- delete static JS
- call `/ui/*` from Vue
- scrape HTML
- call LLMs
- trigger Gmail sync
- trigger worker tasks
- create applications or drafts
- mutate database data
- expose secrets
- expose local filesystem paths
- add router guards
- add SPA catch-all route
- use Vuex
- replace Pinia
- add TypeScript
- add Docker
- add a new frontend testing framework

---

## Final Report

Report:

1. files added
2. files modified
3. routes/pages converted
4. API endpoints used
5. commands run
6. `npm run build:vue` result
7. `pytest tests/test_vue_api_contracts.py` result
8. full `pytest` result
9. whether full-test failures are pre-existing or caused by this task
10. manual validation result
11. known issues

Do not continue to the next migration phase.
