"""Smoke-check that accessibility attributes are present in HTML and JS files."""
from pathlib import Path


STEP_FACTS = Path("frontend/templates/partials/onboarding/step_facts.html")
JOBS_JS = Path("frontend/static/jobs.js")
BASE_HTML = Path("frontend/templates/base.html")
ONBOARDING_HTML = Path("frontend/templates/onboarding.html")


def test_intake_skeleton_has_aria_busy():
    content = STEP_FACTS.read_text()
    assert 'aria-busy="true"' in content, (
        "intake-skeleton container must have aria-busy='true'"
    )


def test_intake_skeleton_pulse_divs_have_aria_hidden():
    content = STEP_FACTS.read_text()
    import re
    pulse_divs = re.findall(r'<div[^>]*animate-pulse[^>]*>', content)
    for div in pulse_divs:
        assert 'aria-hidden="true"' in div, (
            f"animate-pulse div in step_facts.html missing aria-hidden='true': {div}"
        )


def test_base_html_has_versioned_app_css():
    content = BASE_HTML.read_text()
    assert "/static/app.css?v=" in content, (
        "base.html must have ?v= cache-busting on app.css"
    )


def test_base_html_has_versioned_tailwind_css():
    content = BASE_HTML.read_text()
    assert "/static/tailwind.css?v=" in content, (
        "base.html must have ?v= cache-busting on tailwind.css"
    )


def test_base_html_has_versioned_app_js():
    content = BASE_HTML.read_text()
    assert "/static/app.js?v=" in content, (
        "base.html must have ?v= cache-busting on app.js"
    )


def test_onboarding_html_has_versioned_css_assets():
    content = ONBOARDING_HTML.read_text()
    assert "/static/tailwind.css?v=" in content, (
        "onboarding.html must have ?v= cache-busting on tailwind.css"
    )
    assert "/static/app.css?v=" in content, (
        "onboarding.html must have ?v= cache-busting on app.css"
    )


def test_jobs_js_skeleton_divs_have_aria_hidden():
    content = JOBS_JS.read_text()
    if "animate-pulse" in content:
        import re
        pulse_divs = re.findall(r'<div[^>]*animate-pulse[^>]*>', content)
        for div in pulse_divs:
            assert 'aria-hidden' in div, (
                f"animate-pulse div in jobs.js missing aria-hidden: {div}"
            )
