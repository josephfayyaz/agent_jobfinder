"""Tests that SQLite pragmas are correctly set on new connections."""

from __future__ import annotations

from sqlalchemy import text


def test_sqlite_wal_and_busy_timeout_pragmas(tmp_path):
    """SQLite connections must have WAL mode, foreign keys, busy_timeout, synchronous=NORMAL."""
    from job_agent.db import _make_engine

    db_path = tmp_path / "test_pragmas.db"
    engine = _make_engine(f"sqlite:///{db_path}")

    with engine.connect() as conn:
        journal_mode = conn.execute(text("PRAGMA journal_mode")).scalar()
        fk = conn.execute(text("PRAGMA foreign_keys")).scalar()
        busy_timeout = conn.execute(text("PRAGMA busy_timeout")).scalar()
        synchronous = conn.execute(text("PRAGMA synchronous")).scalar()

    assert journal_mode == "wal"
    assert fk == 1
    assert busy_timeout == 10000
    # synchronous=NORMAL is encoded as 1.
    assert synchronous == 1

    engine.dispose()
