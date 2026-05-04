"""apply.js polling error-handling test.

A full browser/DOM test for startPolling() requires Playwright with a running
server, which is not wired into this test suite. The content-assertion test in
test_frontend_null_guards.py covers the correctness of the source code instead.
"""
import pytest


@pytest.mark.skip(
    reason=(
        "apply.js polling behaviour requires a live browser + running server. "
        "Source-level assertions are in tests/test_frontend_null_guards.py."
    )
)
def test_apply_js_polling_stops_after_three_failures():
    pass
