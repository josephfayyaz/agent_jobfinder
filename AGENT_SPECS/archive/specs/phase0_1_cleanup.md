# Phase 0.1 — Cleanup: FastAPI Lifespan, Parallel Worker Test, Seed Tests

## Goal

Three small housekeeping items that eliminate deprecation warnings and fill test gaps
identified during previous phases. Bundle into a single commit.

## Item 1 — Migrate `main.py` startup to FastAPI lifespan handler

**Problem**: `@app.on_event("startup")` is deprecated in FastAPI ≥0.93 and spams test output.

**Location**: `job_agent/main.py` — the `@app.on_event("startup")` decorator (currently at
approximately line 309 based on the current codebase).

**Change**: Replace with the `lifespan` context manager pattern:

```python
# REMOVE:
@app.on_event("startup")
async def startup_event():
    ...existing startup body...

# ADD (at the top of main.py, before app = FastAPI(...)):
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    ...existing startup body (copied verbatim, no logic changes)...
    yield
    # --- shutdown (if any) ---

# CHANGE:
app = FastAPI(
    title="Job Agent",
    ...existing kwargs...,
    lifespan=lifespan,    # <-- add this
)
```

No logic changes to the startup body — only the wrapping mechanism changes.

This is the fix that was already applied in commit `40a283b` ("fix: migrate FastAPI startup
to lifespan handler, remove on_event deprecation"). Verify it is in place; if not, apply it.

## Item 2 — Add `test_worker_calls_scan_all_parallel_after_interval`

**Pre-requisite**: Phase 3.5 (parallel ingestion spec) must be implemented first.
This test validates the parallel code path introduced by that spec.

**File**: `tests/test_worker.py` (add to existing file)

```python
def test_worker_calls_scan_all_parallel_after_interval(monkeypatch):
    """
    After the parallel ingestion spec lands, the worker must call
    scan_all_parallel() instead of scan_all().
    """
    from job_agent import worker as w
    from job_agent.services.career_scanner import CareerPageScanner

    calls = []
    monkeypatch.setattr(CareerPageScanner, "scan_all_parallel", lambda self, db: calls.append("parallel"))
    monkeypatch.setattr(CareerPageScanner, "scan_all", lambda self, db: calls.append("serial"))

    # Trigger one worker cycle
    import asyncio
    from unittest.mock import patch, MagicMock

    with patch("job_agent.worker.should_run_scan", return_value=True), \
         patch("job_agent.worker.get_db_session", return_value=MagicMock()):
        asyncio.get_event_loop().run_until_complete(w.run_once())

    assert "parallel" in calls, "Worker must call scan_all_parallel, not serial scan_all"
    assert "serial" not in calls
```

Note: adjust `run_once` / `should_run_scan` / `get_db_session` to match the actual names
used in `job_agent/worker.py` once Phase 3.5 is implemented.

## Item 3 — Create `tests/test_seed.py`

Cover `job_agent/seed.py` — the resume-track and job-source seeding logic.

```python
"""Tests for job_agent/seed.py — resume-track and job-source seeding."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from job_agent.models import Base, ResumeTrack, JobSource


@pytest.fixture
def seed_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_seed_creates_four_resume_tracks(seed_session):
    from job_agent.seed import seed_resume_tracks
    seed_resume_tracks(seed_session)
    tracks = seed_session.query(ResumeTrack).all()
    assert len(tracks) == 4


def test_seed_resume_tracks_have_expected_slugs(seed_session):
    from job_agent.seed import seed_resume_tracks
    seed_resume_tracks(seed_session)
    slugs = {t.slug for t in seed_session.query(ResumeTrack).all()}
    expected = {
        "data-engineering-analytics",
        "data-analyst-bi-product",
        "ai-ml-engineering",
        "cloud-mlops-ai-platform",
    }
    assert expected.issubset(slugs)


def test_seed_is_idempotent(seed_session):
    """Running seed twice must not create duplicate tracks."""
    from job_agent.seed import seed_resume_tracks
    seed_resume_tracks(seed_session)
    seed_resume_tracks(seed_session)
    tracks = seed_session.query(ResumeTrack).all()
    assert len(tracks) == 4


def test_seed_creates_job_sources(seed_session):
    from job_agent.seed import seed_job_sources
    seed_job_sources(seed_session)
    sources = seed_session.query(JobSource).all()
    assert len(sources) >= 2


def test_seed_job_sources_include_linkedin(seed_session):
    from job_agent.seed import seed_job_sources
    seed_job_sources(seed_session)
    names = [s.name.lower() for s in seed_session.query(JobSource).all()]
    assert any("linkedin" in n for n in names)


def test_seed_resume_tracks_have_target_keywords(seed_session):
    from job_agent.seed import seed_resume_tracks
    seed_resume_tracks(seed_session)
    tracks = seed_session.query(ResumeTrack).all()
    for track in tracks:
        assert track.target_keywords, f"Track {track.slug} has no target_keywords"
```

## Commit Message
```
chore: FastAPI lifespan migration, seed tests, and parallel-worker test (Phase 0.1 cleanup)
```
