# Spec C4 — Shortlist-Centric Apply Flow

## Goal

Make shortlist the explicit gate before expensive drafting work starts.

## Product Rule

The default user journey should be:

`discover -> review -> shortlist -> generate -> approve -> track`

not:

`discover -> generate immediately`

## Build

1. Draft gate
   - generation from the jobs page should prefer shortlisted jobs
   - non-shortlisted jobs should show a short confirmation first

2. Shortlist summary
   - show why the role is shortlisted:
     - fit
     - freshness
     - trust signals
     - readiness summary

3. Strong-fit fast lane
   - if fit is high and trust signals are healthy, keep friction low
   - one click from shortlist to apply flow

4. Weak-fit friction
   - if readiness is weak or trust is uncertain, prompt the user before spending tokens

5. Draft package concept
   - CV draft
   - cover letter
   - saved clarifications
   - tracker record

## UX

Shortlist becomes the user’s “serious applications” shelf.

## Success Metric

- higher draft approval rate
- fewer low-fit drafts generated
- lower abandon rate after draft creation
