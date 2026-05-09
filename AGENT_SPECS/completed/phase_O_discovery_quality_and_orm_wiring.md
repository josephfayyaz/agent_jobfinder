# Phase O — Discovery Quality and ORM Wiring

Status: complete  
Completed: 2026-05-07

## Outcome

`O-A` required only a small tightening patch. `O-B` was implemented by
strengthening the existing authoritative fact-sheet JSON ingestion path instead
of creating a second writer.

## O-A

`job_agent/services/company_snapshot.py` now refuses snapshot unlocks when:

- enrichment is `needs_input` or `failed`
- the job still has no real description text

Shortlisted jobs and strong-fit jobs with valid descriptions still unlock as
before.

## O-B

`job_agent/services/fact_sheet_json.py` now:

- auto-derives `EvidenceIndexItem` rows when the incoming payload omits
  `evidence_index`
- auto-appends a fallback `FactSheetChangeLog` message when the payload omits
  `change_log`
- auto-records simple scalar overwrite conflicts when a later structured intake
  replaces existing candidate identity/work-authorization fields

## Key Files

- `job_agent/services/company_snapshot.py`
- `job_agent/services/fact_sheet_json.py`

## Verification

- `tests/test_discovery_quality.py`
- `tests/test_orm_table_wiring.py`
- `tests/test_fact_sheet_json.py`
- combined final suite: `71 passed`
