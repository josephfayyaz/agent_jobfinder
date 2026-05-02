# Workflow Overview

This is the high-level map for the current product workflow.

## 1. Onboarding

Owned mainly by:

- `job_agent/routers/candidates.py`
- `job_agent/services/intake.py`
- `frontend/templates/onboarding.html`
- `frontend/static/onboarding.js`

Goal:

- create or update the single active candidate
- collect evidence-rich profile data
- review extracted data before continuing
- store search preferences and AI-provider choices

## 2. Job discovery and manual targets

Owned mainly by:

- `job_agent/routers/jobs.py`
- `job_agent/services/jobspy_service.py`
- `job_agent/services/ats_discovery.py`
- `job_agent/services/job_fetcher.py`
- `job_agent/services/job_fit_scoring.py`

Goal:

- pull or accept target roles
- enrich job descriptions
- score jobs against the current candidate
- separate ready jobs from awaiting-enrichment jobs

## 3. CV workflow

Owned mainly by:

- `job_agent/services/workflows.py`
- `job_agent/services/profile_readiness.py`
- `job_agent/services/job_target_profile.py`
- `job_agent/services/draft_preview.py`
- `job_agent/services/documents.py`

Goal:

- check candidate readiness
- generate a truthful draft
- review and revise it
- expose preview annotations and fit/gap mapping
- render final PDF/TeX outputs

## 4. Draft review and approval

Owned mainly by:

- `job_agent/routers/drafts.py`
- `frontend/templates/draft_detail.html`
- `frontend/static/draft_detail.js`

Goal:

- let the user inspect the PDF
- review readiness and evidence alignment
- confirm or reject risky paraphrases
- approve only when the draft is defensible

## 5. Applications and downstream tracking

Owned mainly by:

- `job_agent/routers/applications.py`
- `frontend/templates/applications.html`
- `frontend/templates/analytics.html`

Goal:

- track status after the draft is ready
- keep the application state readable and persistent
- support later analytics and iteration
