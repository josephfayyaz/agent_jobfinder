# Phase O — Discovery Enrichment Audit and Fact-Table Wiring

## Priority
Medium.

This phase should be treated as two sub-phases:

- `O-A` shortlist-gated enrichment
- `O-B` fact-table wiring

They may be completed together only if the audit shows both are still needed.

## Goal

1. Verify whether expensive enrichment is already effectively gated to
   shortlisted jobs, and tighten it only if necessary.
2. Wire currently underused ORM support tables only against the **real** model
   fields and **real** ingestion paths.

## Why this spec was rewritten

The older version used invented field names and stale assumptions about the
current enrichment flow. That is unsafe for this repo and especially unsafe for
a smaller local implementation agent.

This rewrite is audit-first and explicitly grounded in the current models.

## Aider-Safe Constraints

1. Read the live models before writing any ORM code.
2. Do not invent model fields that do not exist.
3. Do not add columns unless the audit proves there is no way to use the
   existing schema.
4. Keep `O-A` and `O-B` logically separate.
5. Reuse existing enrichment services rather than creating new enrichment logic.
6. Catch both `ProviderUnavailableError` and `ValueError` where relevant.
7. Keep write scope as small as possible after the audit.

## Real Model Reminder

Current support-table fields in `job_agent/models.py` are:

- `FactConflict`: `field`, `source_a`, `source_b`, `note`, `resolved`
- `EvidenceIndexItem`: `source_type`, `source_name`, `quote_or_summary`
- `FactSheetChangeLog`: `message`

If a proposed implementation cannot fit these real fields, stop and redesign.

## O-A — Shortlist-Gated Enrichment

### Mandatory Audit First

Run:

```bash
rg -n "CompanySnapshot|company_snapshot|enrichment_status|shortlisted|queue_state|company_resolver|ats" \
  job_agent/services \
  job_agent/routers \
  job_agent/worker.py
```

Read at least:

- `job_agent/services/company_snapshot.py`
- `job_agent/services/job_fetcher.py`
- `job_agent/services/jobspy_service.py`
- `job_agent/routers/job_queue_actions.py`
- `job_agent/routers/jobs.py`

### Decision Gate

Before changing code, answer:

1. Is enrichment already effectively gated by shortlist state or strong-fit unlock rules?
2. Which exact function currently performs deep enrichment?
3. Is there already a task queue path for deferred enrichment?

If the answer to `1` is effectively yes, do not force a rewrite. Convert `O-A`
into a report-only cleanup or a very small tightening patch.

### If O-A Still Needs Code Changes

Keep the change minimal:

- do not create a brand new enrichment architecture
- hook shortlist transitions into the existing task or service path
- keep `enrichment_status` semantics consistent with current UI expectations

Likely writable files, only if audit justifies them:

- `job_agent/routers/job_queue_actions.py`
- `job_agent/services/company_snapshot.py`
- `job_agent/worker.py`
- one related test file

### Tests for O-A

Use targeted tests only:

- shortlisting triggers enrichment entrypoint or task creation
- discovery ingest does not eagerly perform the expensive enrichment path if that is the intended change
- `enrichment_status` transitions remain valid for job views

Do not write tests against invented service names.

## O-B — Fact-Table Wiring

### Mandatory Audit First

Run:

```bash
rg -n "FactConflict|EvidenceIndexItem|FactSheetChangeLog" job_agent --glob "*.py"
```

Also inspect the real canonical intake/ingestion path. At minimum read:

- `job_agent/services/intake.py`
- `job_agent/services/fact_sheet_json.py`
- `job_agent/services/fact_ingestion.py`

Then decide:

1. Which of the three tables are currently unused?
2. Which single ingestion path is actually authoritative for onboarding/fact-sheet writes?
3. Where is the safest place to append these records without duplicating writes?

### O-B1 — `FactConflict`

Only add `FactConflict` records when there is a real conflict worth preserving:

- same candidate
- same logical field path
- old and new values both non-empty
- values materially differ

Map the data into the real schema:

- `field`: dotted logical path
- `source_a`: old value summary
- `source_b`: new value summary
- `note`: optional explanation such as iteration/source context

Do not invent `value_a`, `value_b`, `field_name`, or similar fields.

### O-B2 — `EvidenceIndexItem`

Populate `EvidenceIndexItem` from the authoritative fact ingestion path using the
real fields:

- `source_type`
- `source_name`
- `quote_or_summary`

Use short, searchable summaries.

Do not assume there is a `fact_id` column if the model does not have one.

### O-B3 — `FactSheetChangeLog`

Append a plain-text message at meaningful write boundaries, for example:

- intake iteration completed
- fact sheet updated from structured source
- review save overwrote fact-sheet data

Use the real `message` field. Do not invent `changed_fields`, `iteration`, or
`timestamp` columns unless they are already present.

## Implementation Order

1. complete the audit
2. decide whether `O-A` needs code changes at all
3. if yes, implement `O-A`
4. audit `O-B` against the real ingestion path
5. wire only the currently unused tables
6. test each sub-phase separately

## Tests

Create only the tests justified by the audit.

Recommended filenames:

- `tests/test_discovery_quality.py`
- `tests/test_orm_table_wiring.py`

### Minimum assertions if O-B is implemented

1. a real conflicting overwrite creates a `FactConflict`
2. ingested evidence creates `EvidenceIndexItem` rows
3. a fact-sheet write appends at least one `FactSheetChangeLog` message

Keep the tests model-accurate. Build them from current schema, not from old spec examples.

## Verification

Run only the targeted suites that match the actual changed files, for example:

```bash
/Users/youseffayyaz/miniforge3/envs/ML/bin/python -m pytest \
  tests/test_discovery_quality.py \
  tests/test_orm_table_wiring.py -q
```

Then add the closest affected existing suites after implementation, for example:

```bash
/Users/youseffayyaz/miniforge3/envs/ML/bin/python -m pytest \
  tests/test_intake.py \
  tests/test_api.py \
  tests/test_ui.py -q
```

Then:

```bash
/Users/youseffayyaz/miniforge3/envs/ML/bin/python -m ruff check job_agent tests/test_discovery_quality.py tests/test_orm_table_wiring.py tests/test_intake.py tests/test_api.py tests/test_ui.py
```

## Stop Conditions

Stop and write a report instead of forcing code if:

- enrichment is already sufficiently shortlist-gated
- the real ingestion path would cause duplicate support-table writes
- the existing schema is too small for the desired audit trail and would need a
  separate schema design phase

In that case, document the exact blocker and convert the unfinished part into a
follow-up planning note.

## Completion

After implementation:

1. write `AGENT_SPECS/completed/phase_O_discovery_quality_and_orm_wiring.md`
2. explicitly record:
   - whether `O-A` required code or was already effectively satisfied
   - which ingestion path was treated as authoritative for `O-B`
   - which support tables were newly wired
   - tests run
3. append to `completed_agent_specs.txt`
