# Release Spec 05 — P2 Frontend Polish (Cache-Busting + Accessibility)

## Priority: MEDIUM — implement after specs 01–04 are fully complete.

---

## Purpose

This spec fixes two frontend quality issues that affect all users on every page load:

1. **No cache-busting on static assets in `base.html`** — after any app update, users with browser-cached JS/CSS will run stale code against new HTML, causing broken UI. `onboarding.html` and `settings.html` already use `?v=` versioning but `base.html` (used by every other page) does not.

2. **Skeleton loaders have no accessibility attributes** — the `animate-pulse` placeholder divs have no `aria-busy` or `aria-label`, so screen readers give users no information during loading states. (Reported by Gemini project analysis.)

---

## Global Constraints (READ THESE FIRST)

1. **Python environment:** `conda run -n ML` only.
2. **HTML/JS files** are in `frontend/`. Edit them directly — no build step.
3. Do NOT change any Python backend code in this spec.
4. Do NOT change `onboarding.html` or `settings.html` — they already have `?v=` versioning.
5. After completing: write report, append to `completed_agent_specs.txt`, move spec file.
6. Run full test suite after ALL changes. All tests must pass.

---

## Fix 1 of 2: Cache-busting on base.html static assets

### File to modify
`/Users/youseffayyaz/Local_LLM/frontend/templates/base.html`

### Problem
Lines 7, 8, 10 load `tailwind.css`, HTMX (CDN — already versioned), Alpine.js (CDN — already versioned), and `app.css` with no cache-busting. After deploying a new version of these files, browser caches will serve stale versions.

### Find these lines (lines 7–10):
```html
  <link rel="stylesheet" href="/static/tailwind.css">
  <script src="https://unpkg.com/htmx.org@2.0.0/dist/htmx.min.js"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
  <link rel="stylesheet" href="/static/app.css">
```

Note: `app.js` is loaded elsewhere in the body of base.html. Find the `<script>` tag that loads `/static/app.js` and add `?v=1` to it as well.

### Changes required:

1. Add `?v=1` to the local `tailwind.css` link:
   ```html
   <link rel="stylesheet" href="/static/tailwind.css?v=1">
   ```

2. Add `?v=1` to the local `app.css` link:
   ```html
   <link rel="stylesheet" href="/static/app.css?v=1">
   ```

3. Find the `<script>` tag that loads `/static/app.js` in `base.html`. Add `?v=1`:
   ```html
   <script defer src="/static/app.js?v=1"></script>
   ```

   To find the exact line, run:
   ```bash
   grep -n "app.js" /Users/youseffayyaz/Local_LLM/frontend/templates/base.html
   ```

**Do NOT add `?v=` to CDN scripts** (htmx.org or jsdelivr.net). They are already pinned to exact versions in the URL.

**Do NOT change `onboarding.html` or `settings.html`** — they already have versioning.

**Future releases:** When deploying a code update, increment `?v=1` to `?v=2`, etc. in `base.html` to force cache invalidation.

---

## Fix 2 of 2: aria-busy and aria-label on skeleton loader divs

### Files to modify

1. `frontend/templates/partials/onboarding/step_facts.html` — the `#intake-skeleton` div
2. `frontend/static/jobs.js` — the `injectQueueSkeleton()` function (if it exists) and the `renderTask()` function that generates summary skeleton HTML
3. Any other template file that contains `animate-pulse` divs used as loading placeholders

### Finding all skeleton loader locations
Run this to find all animate-pulse locations:
```bash
grep -rn "animate-pulse" /Users/youseffayyaz/Local_LLM/frontend/
```

### Required changes

#### Rule 1: Container element gets `aria-busy="true"`
Every top-level `<div>` that wraps a skeleton (the one that gets `hidden`/shown via JavaScript) must have `aria-busy="true"` added to its HTML attributes AND `aria-label` describing what is loading.

Example — find the `#intake-skeleton` div in `step_facts.html`:
```html
<!-- BEFORE -->
<div id="intake-skeleton" class="hidden space-y-3">

<!-- AFTER -->
<div id="intake-skeleton" class="hidden space-y-3" aria-busy="true" aria-label="Loading profile analysis…">
```

#### Rule 2: Individual `animate-pulse` divs get `aria-hidden="true"`
The individual placeholder bars inside a skeleton should be hidden from screen readers (they are purely visual):
```html
<!-- BEFORE -->
<div class="h-5 w-48 rounded-lg bg-slate-100 animate-pulse"></div>

<!-- AFTER -->
<div class="h-5 w-48 rounded-lg bg-slate-100 animate-pulse" aria-hidden="true"></div>
```

Apply this `aria-hidden="true"` to EVERY individual `animate-pulse` div inside a skeleton container.

#### Rule 3: JavaScript-generated skeleton HTML in jobs.js
In `jobs.js`, if the `injectQueueSkeleton()` function or `renderTask()` generates skeleton HTML strings, update the generated HTML to include `aria-hidden="true"` on each `animate-pulse` div and `aria-busy="true"` on the wrapper:

Find the generated HTML in jobs.js:
```bash
grep -n "animate-pulse" /Users/youseffayyaz/Local_LLM/frontend/static/jobs.js
```

For each generated skeleton block wrapper, add `aria-busy="true"` and an `aria-label`. For each individual `animate-pulse` div in the generated string, add `aria-hidden="true"`.

Example:
```javascript
// BEFORE
'<div class="h-9 rounded-xl bg-slate-100 animate-pulse"></div>'

// AFTER
'<div class="h-9 rounded-xl bg-slate-100 animate-pulse" aria-hidden="true"></div>'
```

For the wrapper of the summary skeletons:
```javascript
// BEFORE
'<div class="grid grid-cols-7 gap-2">' + skeletons.join("") + '</div>'

// AFTER
'<div class="grid grid-cols-7 gap-2" aria-busy="true" aria-label="Loading discovery summary…">' + skeletons.join("") + '</div>'
```

---

## Tests to write

Create file: `tests/test_frontend_accessibility.py`

```python
"""Smoke-check that accessibility attributes are present in HTML and JS files."""
from pathlib import Path


STEP_FACTS = Path("frontend/templates/partials/onboarding/step_facts.html")
JOBS_JS = Path("frontend/static/jobs.js")
BASE_HTML = Path("frontend/templates/base.html")


def test_intake_skeleton_has_aria_busy():
    content = STEP_FACTS.read_text()
    assert 'aria-busy="true"' in content, (
        "intake-skeleton container must have aria-busy='true'"
    )


def test_intake_skeleton_pulse_divs_have_aria_hidden():
    content = STEP_FACTS.read_text()
    # All animate-pulse divs should be aria-hidden
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


def test_jobs_js_skeleton_divs_have_aria_hidden():
    content = JOBS_JS.read_text()
    # If the file contains animate-pulse, those divs should also have aria-hidden
    if "animate-pulse" in content:
        import re
        pulse_divs = re.findall(r'<div[^>]*animate-pulse[^>]*>', content)
        for div in pulse_divs:
            assert 'aria-hidden' in div, (
                f"animate-pulse div in jobs.js missing aria-hidden: {div}"
            )
```

### Run test
```bash
conda run -n ML pytest tests/test_frontend_accessibility.py -v
```
Expected: all tests PASS.

---

## Verification

Run the full suite:
```bash
conda run -n ML pytest tests/ -x -q
```
All tests must pass.

No Python linting needed for this spec. Verify no Python errors:
```bash
conda run -n ML ruff check job_agent/
```

---

## Completion Steps (do these in order after all tests pass)

1. **Write a report** at `AGENT_SPECS/completed/release_spec_05_p2_frontend_polish.md` describing:
   - Which files you changed (exact lines)
   - How many `animate-pulse` divs you found and updated
   - Test results (pass count)
   - Any issues encountered and how you resolved them
   - Any suggestions for improvement

2. **Append to log:**
   ```
   release_spec_05_p2_frontend_polish.md — COMPLETE — <ISO timestamp>
   ```
   Append to `/Users/youseffayyaz/Local_LLM/completed_agent_specs.txt`.

3. **Move this spec file** from `AGENT_SPECS/pending/claude/release_spec_05_p2_frontend_polish.md` to `AGENT_SPECS/completed/release_spec_05_p2_frontend_polish.md`.
