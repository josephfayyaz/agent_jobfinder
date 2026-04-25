# Adapted Product Blueprint — Job Agent Version

## Product Thesis

Job Agent should not become “career-ops with a nicer UI.”

It should become:

> a private, local-first recruiting copilot for one candidate, guiding them from setup to shortlist to tailored application materials

## New Target Workflow

```text
Setup
  ↓
Profile + role focus + provider setup
  ↓
Discovery engine finds jobs
  ↓
Review queue ranks and filters them
  ↓
User opens a job
  ↓
Readiness map + legitimacy/freshness signals
  ↓
Apply flow gathers clarifications
  ↓
Draft + cover letter generated
  ↓
User approves / revises / stores verified facts
  ↓
Tracker + analytics improve next iterations
```

## Adapted Core Modules

## 1. Discovery Engine

### Borrow from career-ops
- direct ATS/API scanning
- dedup discipline
- liveness/freshness checks

### Job Agent version
- keep database-backed sources and jobs
- add multi-source confidence scoring
- highlight new/urgent/high-fit jobs in the web UI
- use Gmail/LinkedIn ingestion as a supporting source, not the only source

### UX
- `New for you`
- `Worth review`
- `Low fit / hidden by default`

## 2. Review Queue

### Borrow from career-ops
- not every job deserves effort

### Job Agent version
- build a first-class review queue page
- jobs enter queue with:
  - fit score
  - language match
  - freshness
  - legitimacy signal
  - role alignment

### UX
- `Review now`
- `Save for later`
- `Not for me`

This is better than dropping every discovered job into a flat list.

## 3. Role Readiness Before Drafting

### Borrow from career-ops
- evaluate before spending effort on assets

### Job Agent version
- keep your existing readiness map
- show it before draft generation
- add a top summary:
  - `Ready now`
  - `Needs a few stronger details`
  - `Weak fit`

This is more user-friendly than long markdown evaluation blocks.

## 4. Clarification Loop

### Borrow from career-ops
- context improves over time

### Job Agent version
- your current clarified apply flow is the right base
- continue storing verified candidate facts
- let the app learn what evidence matters for future roles

This is one of your strongest advantages over career-ops.

## 5. Draft Generation

### Borrow from career-ops
- tailored assets per job

### Job Agent version
- preserve the web-first draft detail workflow
- keep rewrite and approval steps
- add stronger “why this draft looks like this” explainability:
  - matched requirements
  - inserted evidence
  - omitted weak claims

## 6. Tracker Integrity

### Borrow from career-ops
- verification, dedup, status normalization

### Job Agent version
- nightly or on-demand integrity check
- reconcile:
  - duplicate jobs
  - draft without job
  - application without draft
  - stale scan source
  - missing output artifact references

### UX
- hidden maintenance by default
- visible only as:
  - `System healthy`
  - `3 items need review`

## 7. Analytics

### Borrow from career-ops
- treat the pipeline as a system to learn from

### Job Agent version
- keep your current skill gap dashboard
- expand with:
  - top rejection patterns
  - strongest recurring fit signals
  - best company clusters
  - most productive role focus

## 8. Story Bank

### Borrow from career-ops
- repeated interview stories become reusable assets

### Job Agent version
- later add a structured story bank from:
  - fact sheet
  - approved drafts
  - verified facts
  - accepted bullet rewrites

This should feed:
- interview prep
- outreach messages
- cover letters

## Product Boundaries

## Keep
- local-first privacy
- SQLite
- web onboarding
- provider switching
- explicit setup gating
- user-owned keys

## Avoid
- terminal-first workflows
- markdown file sprawl
- hidden AI-only reasoning without visible UI states
- repo configuration as the user-facing setup layer

## Main Product Recommendation

The best version of Job Agent is:

- **cloud-first onboarding**
- **scan and filter before writing**
- **show why a job is worth effort**
- **use the draft workflow only on shortlisted jobs**
- **learn from every approval, rejection, and clarification**

That is the strongest adaptation of career-ops into your app.
