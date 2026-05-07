# Phase O — Discovery Quality and ORM Table Wiring

## Priority
MEDIUM — can be implemented independently of phases K–N.
Two separate sub-tasks (O-A and O-B) that can be done sequentially in one Codex session.

## Purpose

### Part A — Shortlist-gated enrichment
Deep enrichment (company snapshot, ATS system detection) currently runs during job discovery
for every ingested job. This wastes LLM budget on jobs that will never be reviewed.
Enrichment should run only when a job is explicitly moved to the **shortlist** queue,
where the user has already decided it is worth investing attention.

### Part B — ORM table wiring
Three tables were added to `models.py` but are not populated anywhere:
- `FactConflict` — records when two intake sources disagree on a candidate fact
- `EvidenceIndexItem` — a searchable index of extracted facts
- `FactSheetChangeLog` — per-iteration audit trail of fact-sheet changes

This spec wires them into the intake pipeline so the data they are designed to hold is
actually written.

---

## Global Constraints (READ THESE FIRST)

1. **Python environment:** `conda run -n ML` for all runs. Never create a venv.
2. **No Alembic.** Any new column must be added via
   `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` in `db.py`'s `prepare_database()`.
3. **Never share a DB session across threads.** Each worker task gets its own `SessionLocal()`.
4. **LLMRouter exceptions:** Always catch both `ProviderUnavailableError` AND `ValueError`.
5. **Verify before writing.** Steps O-A1 and O-B0 both require you to read the existing code
   before making any changes. Do not add code that may already exist.
6. **Starlette TemplateResponse** requires keyword args — not positional.
7. **ORM field names** — use the exact field names from `models.py`. Do not guess:
   - `ExperienceFact.role_title`, `.verified_core_facts`, `.tools_and_tech`
   - `ProjectFact.project_name`, `.short_resume_line`
   - `ResumeDraft.review_feedback`

---

## Part O-A — Shortlist-Gated Enrichment

### O-A0: Audit current enrichment location

First, find where `CompanySnapshot` records are created and where company-URL resolution or
ATS-type detection is triggered during discovery. Run:

```bash
grep -rn "CompanySnapshot\|company_resolver\|ats_scanner\|enrich" \
  job_agent/services/jobspy_service.py \
  job_agent/services/career_scanner.py \
  job_agent/services/discovery_hub.py \
  job_agent/routers/jobs.py \
  job_agent/worker.py \
  --include="*.py" | grep -v "__pycache__"
```

Also check:
```bash
grep -rn "enrichment_status" job_agent/ --include="*.py" | grep -v "__pycache__"
```

Read the output carefully. Understand the current enrichment flow before making changes.
If enrichment is already gated to the shortlist queue, document that in the report and
skip O-A1 through O-A4.

### O-A1: Remove enrichment from discovery services

In `job_agent/services/jobspy_service.py` and/or `job_agent/services/career_scanner.py`:
- Find calls to company URL resolution (`company_resolver.find_company_url(...)`) or
  `CompanySnapshot` creation that happen during job ingestion
- Remove or skip those calls
- Jobs should be ingested with `enrichment_status = "pending"` (this field already exists
  on `JobPost` — verify with: `grep -n "enrichment_status" job_agent/models.py`)

### O-A2: Trigger enrichment on shortlist action

In `job_agent/routers/job_queue_actions.py` (or wherever the shortlist queue-move action
is handled — find it with:
`grep -rn "shortlist\|queue_state" job_agent/routers/ --include="*.py"`):

After the `queue_state = "shortlist"` assignment and DB commit, create an async task:

```python
from job_agent.models import WorkflowTask
enrich_task = WorkflowTask(
    kind="enrich_job",
    status="pending",
    payload={"job_post_id": str(job_post.id)}
)
db.add(enrich_task)
db.commit()
```

### O-A3: Handle `enrich_job` task in worker

In `job_agent/worker.py`, find where `WorkflowTask` records are dispatched (look for
`task.kind == "cv_workflow"` or similar). Add a handler for `"enrich_job"`:

```python
elif task.kind == "enrich_job":
    job_post_id = task.payload.get("job_post_id")
    if job_post_id:
        # Run company URL resolution and ATS type detection
        # Use existing services — do not write new logic here
        # Example (adapt to actual service APIs):
        from job_agent.services.company_resolver import CompanyResolverService
        from job_agent.services.ats_scanner import ATSScannerService
        resolver = CompanyResolverService(db=session)
        scanner = ATSScannerService(db=session)
        try:
            resolver.resolve_for_job(job_post_id)
            scanner.detect_for_job(job_post_id)
            # Mark enrichment complete
            job = session.get(JobPost, job_post_id)
            if job:
                job.enrichment_status = "complete"
                session.commit()
        except (ProviderUnavailableError, ValueError) as e:
            task.error_message = str(e)
            task.status = "failed"
            session.commit()
```

Read the actual service APIs before writing this handler — adapt method names and
signatures to what exists.

### O-A4: UI — enriching badge in `frontend/templates/jobs.html`

Find the job row rendering for shortlisted jobs (look for `queue_state == "shortlist"` or
the shortlist lane in the Jinja template). For jobs with `enrichment_status != "complete"`,
add a small inline spinner or text badge:

```html
{% if job.queue_state == "shortlist" and job.enrichment_status != "complete" %}
<span class="inline-flex items-center gap-1 text-xs text-yellow-600 animate-pulse"
      title="Gathering company intelligence…">
  Enriching…
</span>
{% endif %}
```

Match the style of other badge elements in the file.

---

## Part O-B — ORM Table Wiring

### O-B0: Verify current usage (MANDATORY — do this before writing any code)

Run:

```bash
grep -rn "FactConflict\|EvidenceIndexItem\|FactSheetChangeLog" \
  job_agent/ --include="*.py" | grep -v "__pycache__" | grep -v "models.py"
```

**If output is non-empty:** The tables are already being populated. Document where and skip
O-B1 through O-B3. If only partially populated, document which parts are missing and
implement only those.

**If output is empty:** Proceed with O-B1 through O-B3.

### O-B1: Populate `FactConflict` on intake merge

In `job_agent/services/intake.py`, find the method that merges new answers into the
existing fact sheet (search for: `grep -n "merge\|_apply_answers\|update.*fact" job_agent/services/intake.py`).

When a new answer changes a field that already has a non-empty value, create a conflict record:

```python
from job_agent.models import FactConflict

# Example: merging an experience entry that already exists with different values
conflict = FactConflict(
    candidate_id=candidate_id,
    field_name="experience.role_title",      # dot-path to the conflicting field
    source_a="previous_intake_iteration",
    value_a=old_value,
    source_b=f"iteration_{iteration_number}",
    value_b=new_value,
    resolved=False
)
session.add(conflict)
```

Read `models.py` to confirm the exact column names on `FactConflict` before implementing.

### O-B2: Populate `EvidenceIndexItem` after fact ingestion

In `job_agent/services/fact_ingestion.py`, find the loop that stores `ExperienceFact`,
`EducationFact`, and `ProjectFact` records. After each one is added to the session, create
an `EvidenceIndexItem`:

```python
from job_agent.models import EvidenceIndexItem

# After storing an ExperienceFact:
evidence = EvidenceIndexItem(
    candidate_id=candidate_id,
    fact_type="experience",
    fact_id=str(exp_fact.id),
    summary_text=f"{exp_fact.role_title} at {exp_fact.company}"[:200]
)
session.add(evidence)
```

Read `models.py` to confirm exact column names on `EvidenceIndexItem`.

### O-B3: Populate `FactSheetChangeLog` at end of each intake iteration

In `job_agent/services/intake.py`, find the method that runs one iteration of intake
(search for `start_intake`, `run_iteration`, or the method that saves the updated
`partial_fact_sheet`). At the end of that method, after the session commit, append a log entry:

```python
from job_agent.models import FactSheetChangeLog
import datetime

log_entry = FactSheetChangeLog(
    candidate_id=candidate_id,
    iteration=intake_draft.iteration,
    changed_fields=list(changed_field_names),   # list[str] of dotted field paths
    timestamp=datetime.datetime.utcnow()
)
session.add(log_entry)
session.commit()
```

`changed_field_names` is the set of keys that differ between the fact sheet before and
after this iteration. Compute it by comparing old vs. new fact sheet dicts.

Read `models.py` to confirm exact column names on `FactSheetChangeLog`.

---

## Tests to write

### `tests/test_discovery_quality.py`

```python
"""
Tests for shortlist-gated enrichment (Part O-A).
"""
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session


def test_jobspy_ingest_does_not_create_company_snapshot(db_session):
    """
    Ingesting a job via JobSpy must not trigger company URL resolution
    or create a CompanySnapshot record.
    """
    from job_agent.models import CompanySnapshot
    from job_agent.services.jobspy_service import JobSpyService

    with patch("job_agent.services.jobspy_service.scrape_jobs") as mock_scrape:
        mock_scrape.return_value = [
            {
                "title": "Software Engineer",
                "company": "Acme Corp",
                "location": "Milan, Italy",
                "description": "Python developer role",
                "job_url": "https://linkedin.com/jobs/view/123",
                "source": "linkedin",
                "date_posted": None,
            }
        ]
        service = JobSpyService(db=db_session, settings=MagicMock())
        service.discover()

    snapshots = db_session.query(CompanySnapshot).all()
    assert len(snapshots) == 0, (
        "Discovery must not create CompanySnapshot records — enrichment is shortlist-gated"
    )


def test_shortlist_action_creates_enrich_task(db_session, test_job_post):
    """
    Moving a job to the shortlist queue must create a WorkflowTask with kind='enrich_job'.
    """
    from job_agent.models import WorkflowTask
    from job_agent.routers.job_queue_actions import move_to_shortlist  # adapt import

    # Move the job to shortlist
    # (adapt this call to the actual function signature in job_queue_actions.py)
    # move_to_shortlist(job_id=test_job_post.id, db=db_session)

    tasks = db_session.query(WorkflowTask).filter_by(kind="enrich_job").all()
    assert len(tasks) >= 1, "Shortlisting must create an enrich_job WorkflowTask"
    assert tasks[0].payload.get("job_post_id") == str(test_job_post.id)


def test_enrichment_status_pending_after_ingest(db_session):
    """Jobs must have enrichment_status='pending' immediately after ingest."""
    from job_agent.models import JobPost
    # Create a minimal job post directly
    job = JobPost(
        company="Test Co",
        title="Engineer",
        description="Test",
        source_id=None,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    assert job.enrichment_status in ("pending", None), (
        "Newly ingested jobs must not be pre-enriched"
    )
```

### `tests/test_orm_table_wiring.py`

```python
"""
Tests for ORM table wiring (Part O-B).
Only runs if the tables were not already populated before this spec.
"""
import pytest


def test_fact_conflict_model_importable():
    from job_agent.models import FactConflict
    assert FactConflict is not None


def test_evidence_index_item_model_importable():
    from job_agent.models import EvidenceIndexItem
    assert EvidenceIndexItem is not None


def test_fact_sheet_change_log_model_importable():
    from job_agent.models import FactSheetChangeLog
    assert FactSheetChangeLog is not None


def test_intake_creates_change_log(db_session, test_candidate):
    """
    Running one round of intake must create at least one FactSheetChangeLog entry.
    """
    from job_agent.models import FactSheetChangeLog
    from job_agent.services.intake import FactSheetIntakeService

    service = FactSheetIntakeService(db=db_session)
    # Run a minimal intake iteration
    # (adapt to actual service API after reading intake.py)
    # service.start_intake(candidate_id=test_candidate.id, content="Alice Smith, Python dev")

    # After intake, at least one log entry should exist
    logs = db_session.query(FactSheetChangeLog).filter_by(
        candidate_id=test_candidate.id
    ).all()
    # If O-B3 is implemented, this passes; if the table was already wired, it also passes
    assert isinstance(logs, list)  # existence check — strengthen after reading implementation


def test_fact_ingestion_creates_evidence_index(db_session, test_candidate):
    """
    Running fact ingestion must create EvidenceIndexItem records for each stored fact.
    """
    from job_agent.models import EvidenceIndexItem, ExperienceFact

    # Create a minimal ExperienceFact directly
    exp = ExperienceFact(
        candidate_id=test_candidate.id,
        role_title="Data Engineer",
        company="BigCo",
        verified_core_facts=[],
        tools_and_tech=[]
    )
    db_session.add(exp)
    db_session.commit()

    # If O-B2 is implemented via fact_ingestion.py service:
    # items = db_session.query(EvidenceIndexItem).filter_by(candidate_id=test_candidate.id).all()
    # assert len(items) >= 1
    # For now, verify model is usable
    item = EvidenceIndexItem(
        candidate_id=test_candidate.id,
        fact_type="experience",
        fact_id=str(exp.id),
        summary_text="Data Engineer at BigCo"
    )
    db_session.add(item)
    db_session.commit()
    assert item.id is not None
```

---

## Verification

```bash
conda run -n ML pytest tests/test_discovery_quality.py -v
conda run -n ML pytest tests/test_orm_table_wiring.py -v
conda run -n ML pytest tests/ -x -q 2>&1 | tail -5
```

Adapt any `pass` placeholders in the test file to real implementations after reading the
actual service code. All tests must pass.

---

## Completion Steps (do these in order after all tests pass)

1. **Write a completion report** at `AGENT_SPECS/completed/phase_O_discovery_quality_and_orm_wiring.md`
   using `AGENT_SPECS/completed/REPORT_TEMPLATE.md`. Include:
   - O-A: Where enrichment was removed from discovery (exact file + function)
   - O-A: Where the `enrich_job` task is created and handled
   - O-B: Output of the O-B0 grep (were the tables already populated?)
   - O-B: Which tables were wired (FactConflict / EvidenceIndexItem / FactSheetChangeLog)
   - Any DB migrations added to `db.py`
   - Test result (pass count)
   - Deviations from this spec

2. **Append to log:**
   ```
   phase_O_discovery_quality_and_orm_wiring — 2026-05-XX
   ```
   at the bottom of `completed_agent_specs.txt`.

3. **Move this spec file** from `AGENT_SPECS/pending/claude/` to `AGENT_SPECS/archive/claude/completed/`.
