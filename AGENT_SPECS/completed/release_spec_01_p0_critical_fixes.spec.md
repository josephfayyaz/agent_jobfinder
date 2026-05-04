# Release Spec 01 — P0 Critical Fixes (Worker Crash + Bulk Delete Scope)

## Priority: RELEASE BLOCKER — implement this spec first, before any others.

---

## Purpose

This spec fixes two bugs that will silently corrupt or break the app for any new user who installs it:

1. **Worker crashes permanently** — one bad LLM response or DB lock kills the background worker process with no recovery.
2. **FactSheet ingestion deletes ALL facts** — re-running intake wipes every candidate's facts from the database, not just the current one's.

Both bugs affect new users immediately (on first run) and have no visible error — the app appears to do nothing.

---

## Global Constraints (READ THESE FIRST — never break them)

1. **Python environment:** Only use `conda run -n ML <command>` or activate `conda activate ML`. Never create a virtualenv.
2. **No Alembic.** Schema changes only via `_safe_add_column()` calls in `db.py:prepare_database()`.
3. **Starlette TemplateResponse** requires keyword-only arguments: `TemplateResponse(request=request, name="x.html", context={...})`. Positional args crash with `unhashable type: 'dict'`.
4. **Never share a DB session across threads.** Each worker gets its own `SessionLocal()`.
5. **LLMRouter.generate()** raises TWO exception types. Always catch BOTH: `ProviderUnavailableError` AND `ValueError`.
6. After completing this spec: write a report in `AGENT_SPECS/completed/`, append a completion line to `completed_agent_specs.txt`, then move this spec file from `AGENT_SPECS/pending/claude/` to `AGENT_SPECS/completed/`.
7. Run the full test suite (`conda run -n ML pytest tests/ -x -q`) after ALL changes in this spec. All tests must pass.

---

## Fix 1 of 2: Worker loop crash recovery

### File to modify
`/Users/youseffayyaz/Local_LLM/job_agent/worker.py`

### Problem
`main()` at line 98 has no error handling around `_run_one_iteration()`. Any exception (bad LLM JSON, DB lock, network error) terminates the `while True` loop permanently. The worker process exits silently and the app stops processing all jobs forever.

### Exact change required

**Find this block (lines 98–107):**
```python
def main() -> None:
    prepare_database()
    while True:
        with SessionLocal() as session:
            _run_one_iteration(session)
        time.sleep(settings.worker_poll_seconds)


if __name__ == "__main__":
    main()
```

**Replace with:**
```python
def main() -> None:
    try:
        prepare_database()
    except Exception:
        logger.exception("Worker: database setup failed. Exiting.")
        raise
    while True:
        try:
            with SessionLocal() as session:
                _run_one_iteration(session)
        except Exception:
            logger.exception("Worker iteration crashed — will retry after sleep.")
        time.sleep(settings.worker_poll_seconds)


if __name__ == "__main__":
    main()
```

### Test to write
Create file: `tests/test_worker_resilience.py`

```python
"""Tests that the worker loop recovers from exceptions instead of crashing."""
import time
from unittest.mock import MagicMock, patch

import pytest


def test_worker_loop_continues_after_iteration_exception(monkeypatch):
    """Worker main() must not exit when _run_one_iteration raises."""
    from job_agent import worker

    call_count = 0

    def failing_iteration(_session):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("simulated crash")
        # After first crash, raise SystemExit to break the loop cleanly in test
        raise SystemExit(0)

    monkeypatch.setattr(worker, "_run_one_iteration", failing_iteration)
    monkeypatch.setattr(worker, "prepare_database", lambda: None)
    monkeypatch.setattr(time, "sleep", lambda _: None)

    with pytest.raises(SystemExit):
        worker.main()

    # Confirm the loop ran twice — once raising RuntimeError, once raising SystemExit
    assert call_count == 2, f"Expected 2 iterations, got {call_count}"


def test_worker_loop_exits_when_prepare_database_fails(monkeypatch):
    """Worker must exit (not silently swallow) if prepare_database itself fails."""
    from job_agent import worker

    monkeypatch.setattr(worker, "prepare_database", lambda: (_ for _ in ()).throw(RuntimeError("db setup failed")))

    with pytest.raises(RuntimeError, match="db setup failed"):
        worker.main()
```

### Run test
```bash
conda run -n ML pytest tests/test_worker_resilience.py -v
```
Expected: both tests PASS.

---

## Fix 2 of 2: FactSheetIngestionService scoped deletes

### File to modify
`/Users/youseffayyaz/Local_LLM/job_agent/services/fact_ingestion.py`

### Problem
Lines 43–47 run five `.delete()` calls with NO filter. This deletes ALL rows from those tables across ALL candidates and sources in the database. A user who re-runs intake loses everything previously stored.

### Exact change required

**Find this block (lines 43–47):**
```python
        self.session.query(EducationFact).delete()
        self.session.query(ExperienceFact).delete()
        self.session.query(ProjectFact).delete()
        self.session.query(SummaryVariant).delete()
        self.session.query(KeywordSet).delete()
```

**Step 1:** Remove those 5 lines entirely (delete lines 43–47).

**Step 2:** The `source` object is resolved on line 59 (`else: source = latest`) and on line 57 (`self.session.flush()` after adding a new source). After `flush()`, the new source has an `id`. So `source.id` is available at line 60 onward.

Insert the scoped deletes AFTER line 59 (right after `source = latest` in the else branch) — but because both the `if` branch and the `else` branch converge at what becomes line 60 (the `source.parsed_metadata = {...}` assignment), you must place the scoped deletes after `source` is fully resolved.

**The correct placement:** insert the 5 scoped deletes IMMEDIATELY before the `source.parsed_metadata = {` line (which is currently around line 63). At that point `source.id` is always available whether the source is new (just flushed) or existing.

**Insert these 5 lines right before `source.parsed_metadata = {`:**
```python
        self.session.query(EducationFact).filter(EducationFact.fact_source_id == source.id).delete(synchronize_session=False)
        self.session.query(ExperienceFact).filter(ExperienceFact.fact_source_id == source.id).delete(synchronize_session=False)
        self.session.query(ProjectFact).filter(ProjectFact.fact_source_id == source.id).delete(synchronize_session=False)
        self.session.query(SummaryVariant).filter(SummaryVariant.fact_source_id == source.id).delete(synchronize_session=False)
        self.session.query(KeywordSet).filter(KeywordSet.fact_source_id == source.id).delete(synchronize_session=False)
```

### What the final block looks like after both changes

After removing the 5 lines at 43–47 and inserting the scoped deletes before `source.parsed_metadata`, the relevant section of `ingest()` should read:

```python
        latest = (
            self.session.query(FactSource)
            .filter(FactSource.source_path == source_path)
            .order_by(FactSource.imported_at.desc())
            .first()
        )
        reused_existing_source = bool(latest and latest.source_hash == source_hash)

        # NOTE: no unscoped deletes here any more

        if latest is None:
            source = FactSource(
                source_path=source_path,
                source_hash=source_hash,
                raw_content=content,
                parsed_metadata={},
            )
            self.session.add(source)
            self.session.flush()
        else:
            source = latest
            source.source_hash = source_hash
            source.raw_content = content

        # Scoped deletes — only remove facts belonging to THIS source
        self.session.query(EducationFact).filter(EducationFact.fact_source_id == source.id).delete(synchronize_session=False)
        self.session.query(ExperienceFact).filter(ExperienceFact.fact_source_id == source.id).delete(synchronize_session=False)
        self.session.query(ProjectFact).filter(ProjectFact.fact_source_id == source.id).delete(synchronize_session=False)
        self.session.query(SummaryVariant).filter(SummaryVariant.fact_source_id == source.id).delete(synchronize_session=False)
        self.session.query(KeywordSet).filter(KeywordSet.fact_source_id == source.id).delete(synchronize_session=False)

        source.parsed_metadata = {
            "core_profile": parsed.get("core_profile", {}),
            ...
        }
```

### Test to write
Create file: `tests/test_fact_ingestion_scoped.py`

```python
"""Tests that FactSheetIngestionService only deletes facts for the ingested source."""
import pytest
from job_agent.db import Base
from job_agent.models import EducationFact, ExperienceFact, FactSource, KeywordSet, ProjectFact, SummaryVariant
from job_agent.services.fact_ingestion import FactSheetIngestionService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def db_session(tmp_path):
    db_file = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = Session()
    yield session
    session.close()
    engine.dispose()


_MINIMAL_FACT_SHEET = """
# FACT SHEET
## SUMMARY_BANK
IDENTITY: Test User — Software Engineer
## KEYWORD_SETS
PYTHON: python, fastapi
## EDUCATION_ITEMS
- ITEM_ID: edu1
  institution: Test University
  degree: BSc Computer Science
  year: 2020
"""


def test_second_ingest_does_not_delete_unrelated_source_facts(db_session):
    """Ingesting source B must not delete facts that belong to source A."""
    svc = FactSheetIngestionService(db_session)

    # Ingest source A
    svc.ingest(content=_MINIMAL_FACT_SHEET, source_path="source_a.txt")
    db_session.commit()

    source_a = db_session.query(FactSource).filter_by(source_path="source_a.txt").first()
    assert source_a is not None
    a_edu_count = db_session.query(EducationFact).filter_by(fact_source_id=source_a.id).count()
    assert a_edu_count > 0, "Source A should have education facts"

    # Ingest source B (different path)
    svc.ingest(content=_MINIMAL_FACT_SHEET, source_path="source_b.txt")
    db_session.commit()

    # Source A's facts must still exist
    remaining = db_session.query(EducationFact).filter_by(fact_source_id=source_a.id).count()
    assert remaining == a_edu_count, (
        f"Source A facts were deleted by source B ingestion. Expected {a_edu_count}, got {remaining}."
    )


def test_re_ingest_same_source_replaces_own_facts(db_session):
    """Re-ingesting the same source must clear and rewrite its OWN facts."""
    svc = FactSheetIngestionService(db_session)

    svc.ingest(content=_MINIMAL_FACT_SHEET, source_path="source_a.txt")
    db_session.commit()

    source_a = db_session.query(FactSource).filter_by(source_path="source_a.txt").first()
    count_before = db_session.query(EducationFact).filter_by(fact_source_id=source_a.id).count()

    # Re-ingest same path with same content
    svc.ingest(content=_MINIMAL_FACT_SHEET, source_path="source_a.txt")
    db_session.commit()

    count_after = db_session.query(EducationFact).filter_by(fact_source_id=source_a.id).count()
    assert count_after == count_before, "Re-ingesting same source should produce the same fact count"
```

### Run test
```bash
conda run -n ML pytest tests/test_fact_ingestion_scoped.py -v
```
Expected: both tests PASS.

---

## Verification

After both fixes, run the full suite:
```bash
conda run -n ML pytest tests/ -x -q
```
All tests must pass. Fix any failures before proceeding to the completion steps.

Also run the linter:
```bash
conda run -n ML ruff check job_agent/worker.py job_agent/services/fact_ingestion.py
```
No errors allowed.

---

## Completion Steps (do these in order after all tests pass)

1. **Write a report** at `AGENT_SPECS/completed/release_spec_01_p0_critical_fixes.md` describing:
   - What you changed in each file (exact lines)
   - Test results (pass count)
   - Any issues you encountered and how you resolved them
   - Any suggestions for improvement

2. **Append to log:**
   ```
   release_spec_01_p0_critical_fixes.md — COMPLETE — <ISO timestamp>
   ```
   Append this line to `/Users/youseffayyaz/Local_LLM/completed_agent_specs.txt`.

3. **Move this spec file** from `AGENT_SPECS/pending/claude/release_spec_01_p0_critical_fixes.md` to `AGENT_SPECS/completed/release_spec_01_p0_critical_fixes.md`. Do NOT delete it — move it.

Do NOT start spec 02 until spec 01 is fully complete and verified.
