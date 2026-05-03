"""Verify intake skeleton HTML and JS toggle logic are present."""
from pathlib import Path


def test_intake_skeleton_block_in_template():
    src = Path("frontend/templates/partials/onboarding/step_facts.html").read_text()
    assert 'id="intake-skeleton"' in src
    assert "animate-pulse" in src
    assert 'class="hidden' in src


def test_intake_skeleton_show_in_js():
    src = Path("frontend/static/onboarding/intake.js").read_text()
    assert "intake-skeleton" in src
    assert 'classList.remove("hidden")' in src


def test_intake_skeleton_hide_in_js():
    src = Path("frontend/static/onboarding/intake.js").read_text()
    assert 'classList.add("hidden")' in src
