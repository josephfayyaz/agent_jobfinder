# Spec C3 — Discovery Pipeline Upgrade

## Goal

Strengthen discovery quality without increasing token spend linearly.

## Product Rule

Prefer:
- ATS/feed/company-page evidence
- deterministic dedup
- source confidence metadata

Only use LLMs after the acquisition layer has already found a likely job object.

## Build

1. Source confidence model
   - add source confidence metadata per `JobPost`
   - record acquisition path: `company_scan`, `ats_api`, `gmail_alert`, `jobspy_linkedin`, `manual_import`
   - rank ATS/API/company-page sources above board reposts

2. Dedup upgrade
   - dedup by canonical apply URL first
   - then source URL
   - then company + normalized title + location heuristic
   - persist why a job was treated as canonical

3. Enrichment priority queue
   - only enrich jobs that survive the review queue threshold
   - prioritize missing-description jobs in `review` and `shortlist` lanes

4. Discovery transparency
   - show source badges in the queue
   - expose confidence reasons in the UI

5. Lightweight health metrics
   - discovery count by source
   - dedup hit rate
   - percent of jobs with full descriptions

## Routes / Services

- extend `career_scanner.py`
- extend `jobspy_service.py`
- extend Gmail ingestion metadata
- add a shared source-confidence helper

## UX

Queue cards should answer:
- where did this job come from?
- how trustworthy is this source?
- is this a direct company opportunity or a repost?

## Success Metric

- lower duplicate rate
- higher percentage of queue jobs with usable descriptions
- lower token spend per useful job reviewed
