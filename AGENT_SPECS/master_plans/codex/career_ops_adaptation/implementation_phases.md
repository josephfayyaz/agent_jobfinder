# Implementation Phases — Career-Ops Ideas Adapted for Job Agent

## Phase C1 — Review Queue

## Goal

Convert the jobs page from a flat list into a real review queue.

## Build

- `New for you`
- `Shortlist`
- `Not for me`
- `Already applied`

### Ranking inputs
- fit score
- job-language fit
- freshness
- hiring velocity
- legitimacy signal

## Why first

This gives immediate product value without changing the core generation pipeline.

---

## Phase C2 — Legitimacy + Freshness Signals

## Goal

Add job trust signals before the user spends time on a draft.

## Build

- freshness age badge
- recent-scan confidence
- apply-link live check
- suspicious posting signal

### UI wording
- `Fresh`
- `Still active`
- `Needs verification`
- `Older posting`

Avoid words like `ghost job` in the main UI.

---

## Phase C3 — Discovery Pipeline Upgrade

## Goal

Make discovery stronger without increasing AI cost too much.

## Build

- ATS API/feed-first ingestion
- better company careers scanning
- stronger dedup against existing jobs
- source confidence metadata

## Why here

The queue becomes much more useful when discovery improves.

---

## Phase C4 — Shortlist-Centric Apply Flow

## Goal

Only push users into draft generation after the job survives review.

## Build

- `Move to shortlist`
- `Generate application package`
- readiness summary before generation
- lighter friction on strong-fit jobs

## Why

This is the strongest “career-ops idea in your product style.”

---

## Phase C5 — Tracker Integrity Service

## Goal

Make the system self-checking.

## Build

- dedup service
- stale job cleanup
- missing artifact detector
- draft/application/job consistency check
- background maintenance status

## Why

This gives long-term robustness as data volume grows.

---

## Phase C6 — Interview Story Bank

## Goal

Turn repeated evidence into reusable stories.

## Build

- story extraction from approved drafts and verified facts
- tag by role family, tool, impact, leadership, collaboration
- interview prep page using those stories

## Why later

Great feature, but not as foundational as queue/discovery/tracker quality.

---

## Phase C7 — Deep Company Brief

## Goal

Help users understand a shortlisted company before applying or interviewing.

## Build

- company mission summary
- product signals
- role-team clues
- red flags
- interview hooks

## Constraint

Only run this for shortlisted or high-fit jobs to control cost.

---

## Phase C8 — Offer Evaluation and Negotiation

## Goal

Expand beyond job search into decision support.

## Build

- offer comparison
- comp notes
- relocation / remote / visa considerations
- negotiation preparation

## Why last

High value, but only after the search and application engine is strong.

## Final Priority Order

1. Review Queue
2. Legitimacy + Freshness
3. Discovery Upgrade
4. Shortlist-Centric Apply Flow
5. Tracker Integrity
6. Story Bank
7. Company Brief
8. Offer Evaluation

## What I would implement immediately

If choosing only the next three:

1. `C1 Review Queue`
2. `C2 Legitimacy + Freshness`
3. `C5 Tracker Integrity`

Those will move the product most, fastest.
