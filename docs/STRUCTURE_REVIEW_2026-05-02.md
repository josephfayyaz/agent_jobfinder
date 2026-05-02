# Structure Review — 2026-05-02

This note records the current structural hotspots in the app before the next
UI/UX rebuild.

## Main findings

### 1. Oversized backend modules

The largest backend files are already beyond the size where ownership stays
obvious:

- `job_agent/services/workflows.py` — ~1634 lines
- `job_agent/services/prompts.py` — ~1374 lines
- `job_agent/routers/jobs.py` — ~1334 lines
- `job_agent/routers/drafts.py` — ~1027 lines
- `job_agent/routers/candidates.py` — ~529 lines

This creates three problems:

- UI routes and API routes are mixed together
- workflow orchestration and persistence are mixed together
- feature additions keep landing in the same large files

### 2. Oversized frontend screens

The largest frontend files are also carrying too much state:

- `frontend/static/onboarding.js` — ~1198 lines
- `frontend/static/settings.js` — ~682 lines
- `frontend/static/jobs.js` — ~311 lines
- `frontend/templates/draft_detail.html` — ~536 lines
- `frontend/templates/jobs.html` — ~348 lines
- `frontend/templates/onboarding.html` — ~355 lines

The app is currently UI-fragile because screen logic, async orchestration, and
copy are tightly interwoven.

### 3. Product framing is too broad in the shell

`frontend/templates/base.html` still exposes too many areas in the primary
navigation. The app is trying to be:

- an end-user onboarding tool
- a job review queue
- a CV authoring tool
- an application tracker
- a research/thesis workspace
- an analytics cockpit

That breadth makes the UX harder to scan and harder to redesign cleanly.

### 4. Workflow contracts are improving, but still not isolated enough

The app has better contracts than before for:

- profile readiness
- target fit map
- preview annotations
- candidate-bound drafts

But the route handlers still know too much about payload shaping and UI
concerns.

### 5. Test/runtime hygiene was a real structural problem

The older disposable sandbox had become polluted with many overlapping runtimes,
saved artifacts, and legacy assumptions. That was creating false confidence and
extra debugging overhead.

## Most important risks

1. `jobs.py` and `drafts.py` will keep accumulating behavior until every bugfix
   gets slower and riskier.
2. `onboarding.js` will become hard to safely redesign without splitting by
   responsibility.
3. `workflows.py` is becoming the single place where too many CV behaviors meet.
4. historical QA artifacts can mislead validation unless the sandbox remains
   aggressively disposable.

## Recommended priorities

1. Keep `temp_mac_test/` as the only accepted QA sandbox.
2. Split route files before any major frontend rewrite lands.
3. Split onboarding, jobs, and draft-detail screen logic into smaller units.
4. Keep architecture notes close to the code so future AI systems can navigate
   ownership boundaries faster.
