"""Verify the job_row template no longer carries onclick+hx-get on expansion buttons."""
from pathlib import Path


def _row_src():
    return Path("frontend/templates/partials/job_row.html").read_text()


def _group_src():
    return Path("frontend/templates/partials/job_group.html").read_text()


def test_readiness_button_has_no_onclick():
    assert 'onclick="document.getElementById(\'fit-gap-row' not in _row_src()


def test_readiness_button_has_no_hx_get():
    assert 'hx-get="/ui/jobs/{{ job.id }}/fit-gaps"' not in _row_src()


def test_snapshot_button_has_no_onclick():
    assert 'onclick="document.getElementById(\'snapshot-row' not in _row_src()


def test_snapshot_button_has_no_hx_get():
    assert 'hx-get="/ui/jobs/{{ job.id }}/snapshot"' not in _row_src()


def test_pkg_button_has_no_onclick():
    assert 'onclick="document.getElementById(\'package-check-row' not in _row_src()


def test_pkg_button_has_no_hx_get():
    assert 'hx-get="/ui/jobs/{{ job.id }}/package-check"' not in _row_src()


def test_job_group_has_alpine_x_data():
    assert 'x-data="{ snapLoaded: false, readyLoaded: false, pkgLoaded: false }"' in _group_src()


def test_job_group_has_alpine_at_click_for_pkg():
    assert "@click" in _row_src()
    assert "pkgLoaded" in _row_src()


def test_job_group_has_alpine_at_click_for_readiness():
    assert "readyLoaded" in _row_src()


def test_job_group_has_alpine_at_click_for_snapshot():
    assert "snapLoaded" in _row_src()


def test_readiness_button_targets_ui_fit_gap_route():
    assert "/ui/jobs/{{ job.id }}/fit-gaps" in _row_src()
