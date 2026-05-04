"""Tests that ensure_runtime_dirs() gives a clear error on permission failure."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest


def test_ensure_runtime_dirs_raises_runtime_error_on_permission_denied():
    """OSError during mkdir must become RuntimeError with a helpful message."""
    from job_agent.runtime_paths import ensure_runtime_dirs

    def _raising_mkdir(self, parents=False, exist_ok=False):
        del self, parents, exist_ok
        raise PermissionError(13, "Permission denied")

    with patch.object(Path, "mkdir", _raising_mkdir):
        with pytest.raises(RuntimeError) as exc_info:
            ensure_runtime_dirs()

    assert "JOB_AGENT_HOME" in str(exc_info.value)
    assert "writable" in str(exc_info.value).lower()


def test_ensure_runtime_dirs_succeeds_with_valid_path(tmp_path):
    """ensure_runtime_dirs() must work normally when paths are writable."""
    from job_agent import runtime_paths

    with patch.object(runtime_paths, "app_home", return_value=tmp_path / "app"):
        with patch.object(runtime_paths, "config_dir", return_value=tmp_path / "app" / "config"):
            with patch.object(runtime_paths, "backups_dir", return_value=tmp_path / "app" / "backups"):
                runtime_paths.ensure_runtime_dirs()

    assert (tmp_path / "app").exists()
    assert (tmp_path / "app" / "config").exists()
    assert (tmp_path / "app" / "backups").exists()
