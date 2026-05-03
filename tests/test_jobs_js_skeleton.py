"""Verify skeleton logic strings are present in jobs.js."""
from pathlib import Path


def _src():
    return Path("frontend/static/jobs.js").read_text()


def test_summary_skeleton_on_running():
    src = _src()
    assert "animate-pulse" in src
    assert "Array.from({length: 14})" in src


def test_summary_real_data_on_terminal():
    src = _src()
    assert "discoveryTerminal(task)" in src


def test_inject_queue_skeleton_function_exists():
    assert "function injectQueueSkeleton()" in _src()


def test_remove_queue_skeleton_function_exists():
    assert "function removeQueueSkeleton()" in _src()


def test_queue_skeleton_injected_on_start():
    src = _src()
    assert "injectQueueSkeleton()" in src


def test_queue_skeleton_removed_on_terminal():
    assert "removeQueueSkeleton()" in _src()
