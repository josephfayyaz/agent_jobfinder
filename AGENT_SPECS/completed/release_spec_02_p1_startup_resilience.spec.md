# Release Spec 02 — P1 Startup Resilience (Lifespan + Runtime Dirs + SQLite Locks)

## Priority: HIGH — implement after spec 01 is fully complete.

---

## Purpose

This spec fixes three startup-time failures that produce cryptic or no error messages for new users:

1. **Lifespan errors are silent** — `prepare_database()` and `seed_reference_data()` failures print a raw Python traceback with no actionable guidance.
2. **Directory creation fails with PermissionError** — `ensure_runtime_dirs()` crashes with an OS error and no hint of what variable to set to fix it.
3. **SQLite deadlocks on dual-process setup** — running `uvicorn` and `worker.py` simultaneously (the documented setup) can hit "database is locked" errors because `busy_timeout` and `synchronous` are not configured.

---

## Global Constraints (READ THESE FIRST)

1. **Python environment:** Only `conda run -n ML <command>`. Never create a virtualenv.
2. **No Alembic.** Schema changes only in `db.py:prepare_database()` via `_safe_add_column()`.
3. **Starlette TemplateResponse** uses keyword-only args: `TemplateResponse(request=request, name="...", context={...})`.
4. **LLMRouter.generate()** — always catch BOTH `ProviderUnavailableError` AND `ValueError`.
5. After completing this spec: write report, append to `completed_agent_specs.txt`, move spec file.
6. Run full test suite after ALL changes. All tests must pass.

---

## Fix 1 of 3: Lifespan startup error handling

### File to modify
`/Users/youseffayyaz/Local_LLM/job_agent/main.py`

### Problem
In `lifespan()` (lines 51–63), `prepare_database()` and `seed_reference_data()` are called with no error handling. Any failure raises a raw traceback. New users with unusual home directory configs or permission issues get no actionable message.

### Exact change required

**Find this block (lines 51–63):**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    del app
    prepare_database()
    if not _onboarding_complete():
        logger.warning(
            "%s not found. "
            "Run 'python -m job_agent.onboard' to configure the system.",
            _user_settings_file(),
        )
    _log_startup_config_warning()
    with next(get_db()) as db:
        seed_reference_data(db)
    yield
```

**Replace with:**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    del app
    try:
        prepare_database()
    except Exception as exc:
        logger.critical(
            "Database setup failed: %s. "
            "Check that the app data directory is writable. "
            "Set the JOB_AGENT_HOME environment variable to a writable path if needed.",
            exc,
        )
        raise
    if not _onboarding_complete():
        logger.warning(
            "%s not found. "
            "Run 'python -m job_agent.onboard' to configure the system.",
            _user_settings_file(),
        )
    _log_startup_config_warning()
    try:
        with next(get_db()) as db:
            seed_reference_data(db)
    except Exception as exc:
        logger.warning("Seed data setup failed (non-fatal): %s", exc)
    yield
```

**Note:** `prepare_database()` failure is fatal (re-raise). `seed_reference_data()` failure is non-fatal (log warning, continue startup) because seed data is reference data only and the app can run without it temporarily.

### Test to write
Create file: `tests/test_lifespan_resilience.py`

```python
"""Tests that lifespan handles startup failures gracefully."""
import pytest
from unittest.mock import patch, MagicMock
from contextlib import asynccontextmanager


def test_lifespan_raises_when_prepare_database_fails():
    """If prepare_database() raises, lifespan must re-raise (not swallow)."""
    import asyncio
    from job_agent.main import lifespan

    async def _run():
        fake_app = MagicMock()
        with patch("job_agent.main.prepare_database", side_effect=RuntimeError("disk full")):
            with patch("job_agent.main._onboarding_complete", return_value=True):
                async with lifespan(fake_app):
                    pass  # pragma: no cover

    with pytest.raises(RuntimeError, match="disk full"):
        asyncio.get_event_loop().run_until_complete(_run())


def test_lifespan_continues_when_seed_fails(caplog):
    """If seed_reference_data() raises, lifespan must log a warning but not crash."""
    import asyncio
    import logging
    from job_agent.main import lifespan

    async def _run():
        fake_app = MagicMock()
        with patch("job_agent.main.prepare_database"):
            with patch("job_agent.main._onboarding_complete", return_value=True):
                with patch("job_agent.main.seed_reference_data", side_effect=Exception("seed failed")):
                    with patch("job_agent.main.get_db") as mock_get_db:
                        mock_session = MagicMock()
                        mock_get_db.return_value = iter([mock_session])
                        async with lifespan(fake_app):
                            pass  # lifespan must reach yield without raising

    with caplog.at_level(logging.WARNING, logger="job_agent.main"):
        asyncio.get_event_loop().run_until_complete(_run())

    assert any("seed" in rec.message.lower() for rec in caplog.records), (
        "Expected a warning about seed failure in logs"
    )
```

### Run test
```bash
conda run -n ML pytest tests/test_lifespan_resilience.py -v
```
Expected: both tests PASS.

---

## Fix 2 of 3: runtime_paths PermissionError handling

### File to modify
`/Users/youseffayyaz/Local_LLM/job_agent/runtime_paths.py`

### Problem
`ensure_runtime_dirs()` at lines 90–93 calls `mkdir()` on three paths. If any call fails (PermissionError, read-only filesystem), it raises the raw OS error with no hint about what the user can do to fix it.

### Current code (lines 90–93):
```python
def ensure_runtime_dirs() -> None:
    app_home().mkdir(parents=True, exist_ok=True)
    config_dir().mkdir(parents=True, exist_ok=True)
    backups_dir().mkdir(parents=True, exist_ok=True)
```

### Replace with:
```python
def ensure_runtime_dirs() -> None:
    for path in [app_home(), config_dir(), backups_dir()]:
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise RuntimeError(
                f"Cannot create app data directory at {path}: {exc}. "
                f"Set the JOB_AGENT_HOME environment variable to a writable directory "
                f"and restart the application."
            ) from exc
```

### Test to write
Create file: `tests/test_runtime_paths_resilience.py`

```python
"""Tests that ensure_runtime_dirs() gives a clear error on permission failure."""
import pytest
from pathlib import Path
from unittest.mock import patch


def test_ensure_runtime_dirs_raises_runtime_error_on_permission_denied():
    """OSError during mkdir must become a RuntimeError with a helpful message."""
    from job_agent.runtime_paths import ensure_runtime_dirs

    def _raising_mkdir(self, parents=False, exist_ok=False):
        raise PermissionError(13, "Permission denied")

    with patch.object(Path, "mkdir", _raising_mkdir):
        with pytest.raises(RuntimeError) as exc_info:
            ensure_runtime_dirs()

    assert "JOB_AGENT_HOME" in str(exc_info.value), (
        "Error message must mention JOB_AGENT_HOME so the user knows how to fix it"
    )
    assert "writable" in str(exc_info.value).lower(), (
        "Error message must mention 'writable'"
    )


def test_ensure_runtime_dirs_succeeds_with_valid_path(tmp_path):
    """ensure_runtime_dirs() must work normally when paths are writable."""
    from job_agent import runtime_paths

    with patch.object(runtime_paths, "app_home", return_value=tmp_path / "app"):
        with patch.object(runtime_paths, "config_dir", return_value=tmp_path / "app" / "config"):
            with patch.object(runtime_paths, "backups_dir", return_value=tmp_path / "app" / "backups"):
                ensure_runtime_dirs()  # must not raise

    assert (tmp_path / "app").exists()
    assert (tmp_path / "app" / "config").exists()
    assert (tmp_path / "app" / "backups").exists()
```

### Run test
```bash
conda run -n ML pytest tests/test_runtime_paths_resilience.py -v
```
Expected: both tests PASS.

---

## Fix 3 of 3: SQLite busy_timeout + synchronous pragma + connection timeout

### File to modify
`/Users/youseffayyaz/Local_LLM/job_agent/db.py`

### Problem
The documented production setup runs `uvicorn` and `worker.py` as two separate processes sharing one SQLite file. Without `busy_timeout`, the second process immediately raises `OperationalError: database is locked` instead of waiting. Without `timeout=10` in `connect_args`, the Python sqlite3 driver also does not retry.

### Change A — add `"timeout": 10` to connect_args (line 45)

**Find:**
```python
        engine_kwargs["connect_args"] = {"check_same_thread": False}
```

**Replace with:**
```python
        engine_kwargs["connect_args"] = {"check_same_thread": False, "timeout": 10}
```

### Change B — add two pragmas in `_set_pragmas` (lines 51–55)

**Find:**
```python
        @event.listens_for(engine, "connect")
        def _set_pragmas(dbapi_conn, _record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
```

**Replace with:**
```python
        @event.listens_for(engine, "connect")
        def _set_pragmas(dbapi_conn, _record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=10000")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()
```

**Why `synchronous=NORMAL`:** Safe with WAL mode. Reduces fsync overhead on each write without risking data loss on power failure (WAL checkpointing handles durability).

### Test to write
Create file: `tests/test_db_sqlite_pragmas.py`

```python
"""Tests that SQLite pragmas are correctly set on new connections."""
import pytest
from sqlalchemy import create_engine, text


def test_sqlite_wal_and_busy_timeout_pragmas(tmp_path):
    """New SQLite connections must have WAL mode, foreign keys ON, and 10s busy_timeout."""
    from job_agent.db import _make_engine

    db_path = tmp_path / "test_pragmas.db"
    engine = _make_engine(f"sqlite:///{db_path}")

    with engine.connect() as conn:
        journal_mode = conn.execute(text("PRAGMA journal_mode")).scalar()
        fk = conn.execute(text("PRAGMA foreign_keys")).scalar()
        busy_timeout = conn.execute(text("PRAGMA busy_timeout")).scalar()
        synchronous = conn.execute(text("PRAGMA synchronous")).scalar()

    assert journal_mode == "wal", f"Expected WAL, got {journal_mode}"
    assert fk == 1, f"Expected foreign_keys=1, got {fk}"
    assert busy_timeout == 10000, f"Expected busy_timeout=10000, got {busy_timeout}"
    # synchronous=NORMAL is value 1
    assert synchronous == 1, f"Expected synchronous=NORMAL (1), got {synchronous}"

    engine.dispose()
```

### Run test
```bash
conda run -n ML pytest tests/test_db_sqlite_pragmas.py -v
```
Expected: test PASSES.

---

## Verification

Run the full suite:
```bash
conda run -n ML pytest tests/ -x -q
```
All tests must pass.

Run linter:
```bash
conda run -n ML ruff check job_agent/main.py job_agent/runtime_paths.py job_agent/db.py
```
No errors allowed.

---

## Completion Steps (do these in order after all tests pass)

1. **Write a report** at `AGENT_SPECS/completed/release_spec_02_p1_startup_resilience.md` describing:
   - What you changed in each file (exact lines)
   - Test results (pass count)
   - Any issues encountered and how you resolved them
   - Any suggestions for improvement

2. **Append to log:**
   ```
   release_spec_02_p1_startup_resilience.md — COMPLETE — <ISO timestamp>
   ```
   Append to `/Users/youseffayyaz/Local_LLM/completed_agent_specs.txt`.

3. **Move this spec file** from `AGENT_SPECS/pending/claude/release_spec_02_p1_startup_resilience.md` to `AGENT_SPECS/completed/release_spec_02_p1_startup_resilience.md`.
