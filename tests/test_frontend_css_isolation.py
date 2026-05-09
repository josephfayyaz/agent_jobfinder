from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_onboarding_css_exists_and_is_loaded_only_on_onboarding_page():
    assert (ROOT / "frontend/static/onboarding.css").exists()
    onboarding_html = _read("frontend/templates/onboarding.html")
    base_html = _read("frontend/templates/base.html")
    assert "/static/onboarding.css" in onboarding_html
    assert "/static/onboarding.css" not in base_html


def test_dead_profile_step_references_are_gone():
    onboarding_templates = _read("frontend/templates/onboarding.html") + _read(
        "frontend/templates/partials/onboarding/steps_nav.html"
    )
    onboarding_scripts = "\n".join(
        _read(path)
        for path in (
            "frontend/static/onboarding/core.js",
            "frontend/static/onboarding/intake.js",
            "frontend/static/onboarding/review.js",
            "frontend/static/onboarding/search.js",
            "frontend/static/onboarding/hydrate.js",
            "frontend/static/onboarding.js",
        )
    )
    assert "step_profile" not in onboarding_templates
    assert "createProfile(" not in onboarding_scripts
