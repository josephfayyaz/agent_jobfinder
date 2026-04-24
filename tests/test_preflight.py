from __future__ import annotations

import pytest

from job_agent.preflight import _is_importable, check_and_install_packages


def test_is_importable_known_package():
    assert _is_importable("sys") is True


def test_is_importable_fake_package():
    assert _is_importable("_this_does_not_exist_xyz_abc") is False


def test_check_passes_when_all_packages_present(monkeypatch):
    """When all packages are importable, check_and_install_packages returns silently."""
    monkeypatch.setattr("job_agent.preflight.REQUIRED_PACKAGES", [("sys", "sys")])
    check_and_install_packages()


def test_check_exits_when_offline_and_missing(monkeypatch, tmp_path):
    """When a package is missing and network is offline, exits with code 1."""
    monkeypatch.setattr(
        "job_agent.preflight.REQUIRED_PACKAGES",
        [("_nonexistent_module_xyz", "nonexistent-package")],
    )
    monkeypatch.setattr("job_agent.preflight._check_network", lambda: False)
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    with pytest.raises(SystemExit) as exc_info:
        check_and_install_packages(project_root=tmp_path)
    assert exc_info.value.code == 1
