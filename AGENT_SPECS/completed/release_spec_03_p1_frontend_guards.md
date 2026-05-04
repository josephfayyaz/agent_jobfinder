# Release Spec 03 — P1 Frontend Safety Guards (Null Refs + Polling Error Handling)

## Priority: HIGH — implement after spec 02 is fully complete.

---

## Purpose

This spec fixes three JavaScript bugs that crash the UI silently for new users:

1. **`apply.js` polling has no try/catch** — any network error inside `setInterval` is swallowed silently and the spinner freezes forever, with no message to the user.
2. **`intake.js` null dereference** — `document.getElementById("full-name").value` crashes with `TypeError: Cannot read properties of null` if the DOM element is absent (e.g., template rendering differences).
3. **`search.js` null dereference** — `saveSearchFocus()` calls `.value` on `getElementById("target-roles")` and `getElementById("search-countries")` without null guards, crashing the onboarding flow.

---

## Global Constraints (READ THESE FIRST)

1. **Python environment:** `conda run -n ML` only.
2. **JavaScript files** are in `frontend/static/`. Edit them directly — no build step.
3. **Tests for JS** are Playwright/HTMX-stub tests in `tests/`. Follow the existing test patterns there.
4. Do NOT change any Python backend code in this spec.
5. After completing: write report, append to `completed_agent_specs.txt`, move spec file.
6. Run full test suite after ALL changes. All tests must pass.

---

## Fix 1 of 3: apply.js polling try/catch with error counter

### File to modify
`/Users/youseffayyaz/Local_LLM/frontend/static/apply.js`

### Problem
`startPolling()` (lines 145–159) uses `setInterval` with no error handling. If `fetch()` throws (worker not running, network error), the exception propagates silently and the interval keeps firing failed calls. After a page reload the user has no idea what happened.

### Find this entire function (lines 145–159):
```javascript
function startPolling() {
  _pollInterval = setInterval(async () => {
    const response = await fetch(`/apply/status/${_taskId}`);
    const data = await response.json();
    const statusEl = document.getElementById("status-text");
    statusEl.textContent = `Status: ${data.status}`;
    if (data.status === "completed" && data.draft_id) {
      clearInterval(_pollInterval);
      window.location.href = `/ui/drafts/${data.draft_id}`;
    } else if (data.status === "failed") {
      clearInterval(_pollInterval);
      statusEl.textContent = "Generation failed. Check the worker logs.";
    }
  }, 3000);
}
```

### Replace the entire function with:
```javascript
function startPolling() {
  let _errors = 0;
  _pollInterval = setInterval(async () => {
    try {
      const response = await fetch(`/apply/status/${_taskId}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      _errors = 0;
      const statusEl = document.getElementById("status-text");
      if (statusEl) {
        statusEl.textContent = `Status: ${data.status}`;
      }
      if (data.status === "completed" && data.draft_id) {
        clearInterval(_pollInterval);
        window.location.href = `/ui/drafts/${data.draft_id}`;
      } else if (data.status === "failed") {
        clearInterval(_pollInterval);
        if (statusEl) {
          statusEl.textContent = "Generation failed. Check the worker logs.";
        }
      }
    } catch (_err) {
      _errors += 1;
      if (_errors >= 3) {
        clearInterval(_pollInterval);
        const statusEl = document.getElementById("status-text");
        if (statusEl) {
          statusEl.textContent = "Status check failed — is the worker running?";
        }
      }
    }
  }, 3000);
}
```

**What changed:**
- Entire interval body wrapped in `try/catch`
- `_errors` counter stops polling after 3 consecutive failures
- Null-guard on `statusEl` (guards against `getElementById` returning null)
- Non-2xx response treated as an error

---

## Fix 2 of 3: intake.js null guards on form element reads

### File to modify
`/Users/youseffayyaz/Local_LLM/frontend/static/onboarding/intake.js`

### Problem
In `createProfile()` (lines 12–13), `document.getElementById("full-name")` and `document.getElementById("email")` are called without null guards. If these elements are not rendered (e.g., partial template load, onboarding step not shown), this crashes with `TypeError: Cannot read properties of null (reading 'value')`.

### Find these two lines (lines 12–13 inside `createProfile`):
```javascript
    const fullName = document.getElementById("full-name").value.trim();
    const email = document.getElementById("email").value.trim();
```

### Replace with:
```javascript
    const fullName = (document.getElementById("full-name")?.value || "").trim();
    const email = (document.getElementById("email")?.value || "").trim();
```

**That is the only change in this file.** Do not change anything else.

---

## Fix 3 of 3: search.js null guards in saveSearchFocus()

### File to modify
`/Users/youseffayyaz/Local_LLM/frontend/static/onboarding/search.js`

### Problem
`saveSearchFocus()` reads `.value` directly on `getElementById("target-roles")` and `getElementById("search-countries")` (lines 92–101) without null guards. If the onboarding step is rendered before the element exists (e.g., race condition, template partial missing), this crashes with `TypeError: Cannot read properties of null`.

### Find these two expressions inside `saveSearchFocus()`:
```javascript
    const roles = document.getElementById("target-roles").value
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean)
      .slice(0, 4);
    const countries = document.getElementById("search-countries").value
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean)
      .slice(0, 1);
```

### Replace with:
```javascript
    const roles = (document.getElementById("target-roles")?.value || "")
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean)
      .slice(0, 4);
    const countries = (document.getElementById("search-countries")?.value || "")
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean)
      .slice(0, 1);
```

**That is the only change in this file.** Do not change anything else.

---

## Tests to write

### For apply.js (test that polling stops after 3 consecutive fetch failures)

**IMPORTANT:** The apply.js polling test is a browser/DOM test. If your test environment does not have a browser driver (Playwright), write it as a Node.js jsdom test or skip it and add a note in the report. Do NOT break the existing test suite trying to add this test.

If you can write the test, create `tests/test_apply_js_polling.py` using your project's existing browser test patterns. If not, create the file with a single `pytest.mark.skip` test and document the reason.

### For intake.js and search.js null guards

These are DOM safety guards. Write `tests/test_frontend_null_guards.py` that checks the JavaScript for the correct optional chaining syntax using file content assertions:

```python
"""Smoke-check that null guards are present in onboarding JavaScript files."""
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
```

### Run tests
```bash
conda run -n ML pytest tests/test_frontend_null_guards.py -v
```
Expected: all 6 tests PASS.

---

## Verification

Run the full suite:
```bash
conda run -n ML pytest tests/ -x -q
```
All tests must pass.

No Python linting needed for this spec (JS-only changes). But verify no Python syntax errors were introduced by running:
```bash
conda run -n ML ruff check job_agent/
```

---

## Completion Steps (do these in order after all tests pass)

1. **Write a report** at `AGENT_SPECS/completed/release_spec_03_p1_frontend_guards.md` describing:
   - What you changed in each file (exact lines)
   - Test results (pass count)
   - Any issues encountered and how you resolved them
   - Any suggestions for improvement

2. **Append to log:**
   ```
   release_spec_03_p1_frontend_guards.md — COMPLETE — <ISO timestamp>
   ```
   Append to `/Users/youseffayyaz/Local_LLM/completed_agent_specs.txt`.

3. **Move this spec file** from `AGENT_SPECS/pending/claude/release_spec_03_p1_frontend_guards.md` to `AGENT_SPECS/completed/release_spec_03_p1_frontend_guards.md`.
