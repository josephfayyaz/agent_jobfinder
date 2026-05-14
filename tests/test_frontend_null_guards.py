"""Smoke-check that null guards are present in onboarding JavaScript files."""
from pathlib import Path


INTAKE_JS = Path("frontend/static/onboarding/intake.js")
REVIEW_JS = Path("frontend/static/onboarding/review.js")
SEARCH_JS = Path("frontend/static/onboarding/search.js")
APPLY_JS = Path("frontend/static/apply.js")


def test_review_js_has_null_guard_on_full_name():
    content = REVIEW_JS.read_text()
    assert 'getElementById("review-full-name")?.value?.trim()' in content, (
        "review.js must use optional chaining on review-full-name element"
    )


def test_review_js_has_null_guard_on_email():
    content = REVIEW_JS.read_text()
    assert 'getElementById("review-email")?.value?.trim()' in content, (
        "review.js must use optional chaining on review-email element"
    )


def test_search_js_has_null_guard_on_target_roles():
    content = SEARCH_JS.read_text()
    assert 'getElementById("target-roles")?.value' in content, (
        "search.js must use optional chaining on target-roles element"
    )


def test_search_js_has_null_guard_on_search_countries():
    content = SEARCH_JS.read_text()
    assert 'getElementById("search-countries")?.value' in content, (
        "search.js must use optional chaining on search-countries element"
    )


def test_apply_js_polling_has_try_catch():
    content = APPLY_JS.read_text()
    assert "try {" in content and "_errors" in content, (
        "apply.js startPolling must have try/catch and an error counter"
    )


def test_apply_js_polling_stops_after_errors():
    content = APPLY_JS.read_text()
    assert "_errors >= 3" in content, (
        "apply.js must stop polling after 3 consecutive errors"
    )
