from pathlib import Path


INTAKE_JS = Path("frontend/static/onboarding/intake.js")
SEARCH_JS = Path("frontend/static/onboarding/search.js")
APPLY_JS = Path("frontend/static/apply.js")


def test_intake_js_has_null_guard_on_full_name():
    content = INTAKE_JS.read_text()
    assert 'getElementById("full-name")?.value' in content, (
        "intake.js must use optional chaining on full-name element"
    )


def test_intake_js_has_null_guard_on_email():
    content = INTAKE_JS.read_text()
    assert 'getElementById("email")?.value' in content, (
        "intake.js must use optional chaining on email element"
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
