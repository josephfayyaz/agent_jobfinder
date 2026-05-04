"""Tests that the worker loop recovers from exceptions instead of crashing."""

from __future__ import annotations

import time

import pytest


class _DummySessionContext:
    def __enter__(self):
        return object()

    def __exit__(self, exc_type, exc, tb):
        return False


def test_worker_loop_continues_after_iteration_exception(monkeypatch):
    """Worker main() must not exit when _run_one_iteration raises."""
    from job_agent import worker

    call_count = 0

    def failing_iteration(_session):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("simulated crash")
        # After first crash, raise SystemExit to break the loop cleanly in test.
        raise SystemExit(0)

    monkeypatch.setattr(worker, "_run_one_iteration", failing_iteration)
    monkeypatch.setattr(worker, "prepare_database", lambda: None)
    monkeypatch.setattr(worker, "SessionLocal", lambda: _DummySessionContext())
    monkeypatch.setattr(time, "sleep", lambda _: None)

    with pytest.raises(SystemExit):
        worker.main()

    assert call_count == 2, f"Expected 2 iterations, got {call_count}"


def test_worker_loop_exits_when_prepare_database_fails(monkeypatch):
    """Worker must exit (not silently swallow) if prepare_database itself fails."""
    from job_agent import worker

    monkeypatch.setattr(
        worker,
        "prepare_database",
        lambda: (_ for _ in ()).throw(RuntimeError("db setup failed")),
    )

    with pytest.raises(RuntimeError, match="db setup failed"):
        worker.main()
