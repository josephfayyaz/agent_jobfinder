# Recommended Product Experiments

## Goal

Validate the strongest career-ops-inspired ideas in Job Agent without overbuilding them first.

## Experiment 1 — Queue vs Flat Jobs List

### Hypothesis

Users will reach better jobs faster if the app presents a review queue instead of a flat discovered-jobs table.

### Test

- A: current jobs list
- B: queue with `Review now`, `Shortlist`, `Pass`

### Success metric

- time to first shortlisted job
- shortlist rate
- draft generation rate from shortlisted jobs

---

## Experiment 2 — Readiness Before Draft

### Hypothesis

Showing a compact readiness summary before drafting reduces wasted draft generation.

### Test

- A: direct generate
- B: readiness summary first

### Success metric

- draft generation conversion on high-fit jobs
- abandonment rate on low-fit jobs
- user trust feedback

---

## Experiment 3 — Legitimacy Signal Framing

### Hypothesis

Neutral wording works better than “ghost job” framing.

### Test copy

- `Fresh and active`
- `Needs verification`
- `Older posting`

versus more aggressive suspicion wording.

### Success metric

- user action rate after seeing warning
- false-alarm complaints

---

## Experiment 4 — Discovery Source Visibility

### Hypothesis

Users trust recommendations more when they can see whether a role came from ATS API, company page, Gmail, or imported alert.

### Test

Add source badges to queue cards.

### Success metric

- click-through rate to review
- shortlist rate by source

---

## Experiment 5 — Shortlist Gate

### Hypothesis

Requiring a user to move a job to shortlist before generating a draft improves overall application quality.

### Test

- A: generate from any job
- B: generate only from shortlist

### Success metric

- approval rate of generated drafts
- number of weak-fit drafts avoided

## Recommendation

Run Experiments 1 and 2 first.

They most directly test whether the career-ops philosophy improves your app in a way users actually feel.
