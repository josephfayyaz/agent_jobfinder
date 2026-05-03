"""Verify role suggestion frontend wiring is present in templates and JS."""
from pathlib import Path


def test_suggest_skeletons_in_step_search():
    src = Path("frontend/templates/partials/onboarding/step_search.html").read_text()
    assert 'id="suggest-skeletons"' in src
    assert "animate-pulse" in src


def test_llm_suggest_status_in_step_search():
    src = Path("frontend/templates/partials/onboarding/step_search.html").read_text()
    assert 'id="llm-suggest-status"' in src


def test_tracks_status_in_done_panel():
    src = Path("frontend/templates/partials/onboarding/done_panel.html").read_text()
    assert 'id="tracks-status"' in src
    assert "Building role tracks" in src


def test_search_js_calls_suggest_tracks():
    src = Path("frontend/static/onboarding/search.js").read_text()
    assert "suggest-tracks" in src


def test_search_js_calls_generate_tracks():
    src = Path("frontend/static/onboarding/search.js").read_text()
    assert "generate-tracks" in src


def test_search_js_hides_skeleton_in_finally():
    src = Path("frontend/static/onboarding/search.js").read_text()
    assert "finally" in src
    assert "suggest-skeletons" in src


def test_discovery_section_has_regenerate_button():
    src = Path("frontend/templates/partials/settings/discovery_section.html").read_text()
    assert "generate-tracks" in src
    assert "Regenerate Role Tracks" in src
