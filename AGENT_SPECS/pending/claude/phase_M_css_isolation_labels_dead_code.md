# Phase M — CSS Isolation, Label Standardization, and Dead-Code Cleanup

## Priority
LOW-MEDIUM — implement after phases K and L. Depends on K having shipped the
`ProviderController.labels` map (used in M2).

## Purpose

Three independent housekeeping tasks:

1. **CSS isolation** — onboarding-specific styles live in the global `app.css` and are
   sent to every page. Moving them to an `onboarding.css` file reduces non-onboarding page
   weight and isolates visual regressions.

2. **Label standardization** — provider display names ("LM Studio (Local)", "OpenAI", etc.)
   appear as hardcoded strings in multiple templates. After phase K ships `PROVIDER_LABELS`
   in `provider_controller.js`, templates that still have hardcoded strings should be
   identified and documented (client-side rendering already uses the JS constant; this task
   audits server-rendered occurrences).

3. **Dead-code cleanup** — stale comments, unreferenced functions, and the confirmed-deleted
   `step_profile.html` should be absent; verify and clean up any remaining traces.

---

## Global Constraints (READ THESE FIRST)

1. **Python environment:** `conda run -n ML` for all test/ruff runs.
2. **No backend changes.** Touch only `frontend/` files.
3. **No build step.** CSS is plain; `tailwind.css` is compiled separately (gitignored). Edit
   only `app.css` (the custom design-system file) and create `onboarding.css`.
4. **Verify before moving CSS.** A class moved out of `app.css` but still referenced in a
   non-onboarding template will break that template. Grep every class name before removing it.
5. **`step_profile.html` was deleted in a prior cleanup.** If it still exists, delete it now.
   If it is already gone, note that in the report — do not recreate it.
6. **Phase K must be complete** before running M2. If phase K has not shipped, skip M2 and
   note the dependency in the report.

---

## Task M1 — CSS Isolation

### Step M1-1: Identify onboarding-exclusive CSS classes

Run:

```bash
# Find CSS rules in app.css whose selectors contain onboarding-specific prefixes
grep -n "\.setup-\|\.onboarding-\|#onboarding\|#setup" frontend/static/app.css
```

Also search manually for classes that appear only inside onboarding templates:

```bash
# List class names from onboarding templates
grep -oh 'class="[^"]*"' frontend/templates/onboarding.html \
  frontend/templates/partials/onboarding/*.html | \
  grep -oh '[a-z][a-z0-9_-]*' | sort -u
```

For each class found, check whether it is also used in non-onboarding templates:

```bash
# Example: check if class 'setup-hero' appears outside onboarding
grep -rn "setup-hero" frontend/templates/ --include="*.html" | \
  grep -v "onboarding"
```

Only move a CSS rule to `onboarding.css` if the selector is **not** used in any
non-onboarding template.

### Step M1-2: Create `frontend/static/onboarding.css`

Create the file. Move the identified onboarding-exclusive CSS blocks from `app.css` into it,
preserving exact rule content. Remove those rules from `app.css`.

### Step M1-3: Update `frontend/templates/onboarding.html`

Find the `<link>` tag that loads `app.css`. Add a second `<link>` for `onboarding.css`
directly after it:

```html
<!-- BEFORE -->
<link rel="stylesheet" href="/static/app.css?v=...">

<!-- AFTER -->
<link rel="stylesheet" href="/static/app.css?v=...">
<link rel="stylesheet" href="/static/onboarding.css?v=1">
```

Do NOT add this link to `base.html` — it belongs only in `onboarding.html`.

---

## Task M2 — Provider Label Audit (requires phase K)

### Step M2-1: Grep for hardcoded provider labels in templates

```bash
grep -rn "LM Studio\|Ollama\|OpenAI\|Anthropic\|Google Gemini\|Claude (Anth" \
  frontend/templates/ --include="*.html"
```

### Step M2-2: Classify each occurrence

For each match, determine:
- **Client-side rendered** (inside `{{ }}`, `x-text`, or set by JS) → already using the
  JS constant after phase K; no action needed.
- **Server-side hardcoded** (plain text in HTML, Jinja `if` branch, `<option>` value text,
  tooltip, `aria-label`) → document in the completion report as "remaining server-side labels".

Do NOT change server-side labels in this spec — that requires a backend settings context
refactor. Just document them.

### Step M2-3: Standardize any JS files that still hardcode labels

```bash
grep -rn '"LM Studio"\|"OpenAI"\|"Ollama"\|"Anthropic"\|"Gemini"' \
  frontend/static/ --include="*.js" | grep -v provider_controller.js
```

For any JS file still hardcoding a provider label string (not calling
`ProviderController.getLabel()`), replace the hardcoded string with the controller call.

---

## Task M3 — Dead-Code Cleanup

### Step M3-1: Verify step_profile.html is gone

```bash
test -f frontend/templates/partials/onboarding/step_profile.html && \
  echo "EXISTS — delete it" || echo "Already deleted — OK"
```

If the file still exists, delete it:

```bash
rm frontend/templates/partials/onboarding/step_profile.html
```

### Step M3-2: Grep for references to the deleted step

```bash
grep -rn "step_profile\|step-profile\|createProfile\b" \
  frontend/ --include="*.html" --include="*.js"
```

Remove any `<script>` includes, Jinja `include` tags, or JS function calls that reference
the deleted profile step.

### Step M3-3: Grep onboarding JS for stale comments and TODO blocks

```bash
grep -n "// TODO\|// OLD\|// DEPRECATED\|// REMOVE\|// FIXME" \
  frontend/static/onboarding/*.js \
  frontend/static/settings/*.js
```

Remove stale comment blocks (lines or multi-line commented-out code). Preserve comments
that explain non-obvious behaviour (WHY comments).

### Step M3-4: Audit `done_panel.html` for references to the deleted profile step

```bash
grep -n "profile\|step 2\|step-2\|create.*profile\|name.*email" \
  frontend/templates/partials/onboarding/done_panel.html
```

Remove or reword any copy that references the old "create your profile" step.

---

## Tests to write

Create `tests/test_frontend_css_isolation.py`:

```python
"""
Structural tests for CSS isolation, label standardization, and dead-code cleanup.
"""
from pathlib import Path

STATIC    = Path("frontend/static")
TEMPLATES = Path("frontend/templates")
APP_CSS          = STATIC / "app.css"
ONBOARDING_CSS   = STATIC / "onboarding.css"
ONBOARDING_HTML  = TEMPLATES / "onboarding.html"
STEP_PROFILE     = TEMPLATES / "partials/onboarding/step_profile.html"
DONE_PANEL       = TEMPLATES / "partials/onboarding/done_panel.html"


def test_onboarding_css_created():
    assert ONBOARDING_CSS.exists(), (
        "frontend/static/onboarding.css must exist after M1"
    )
    assert ONBOARDING_CSS.stat().st_size > 0, (
        "onboarding.css must not be empty"
    )


def test_onboarding_html_links_onboarding_css():
    html = ONBOARDING_HTML.read_text()
    assert "onboarding.css" in html, (
        "onboarding.html must include a <link> to onboarding.css"
    )


def test_onboarding_html_still_links_app_css():
    html = ONBOARDING_HTML.read_text()
    assert "app.css" in html, (
        "onboarding.html must still include app.css (base styles)"
    )


def test_step_profile_deleted():
    assert not STEP_PROFILE.exists(), (
        "step_profile.html must not exist — it was removed in the onboarding refactor"
    )


def test_no_reference_to_step_profile_in_onboarding_html():
    html = ONBOARDING_HTML.read_text()
    assert "step_profile" not in html, (
        "onboarding.html must not reference step_profile"
    )


def test_no_create_profile_in_js():
    """createProfile() was removed with the profile step — must not reappear."""
    for js_file in (STATIC / "onboarding").glob("*.js"):
        content = js_file.read_text()
        assert "createProfile()" not in content, (
            f"{js_file.name} must not define or call createProfile() — that step was removed"
        )


def test_base_html_does_not_link_onboarding_css():
    """onboarding.css must not be loaded on every page."""
    base = TEMPLATES / "base.html"
    if base.exists():
        assert "onboarding.css" not in base.read_text(), (
            "base.html must not include onboarding.css — it is onboarding-page only"
        )
```

---

## Verification

```bash
conda run -n ML pytest tests/test_frontend_css_isolation.py -v
```

All 7 tests must pass. Then run the full suite:

```bash
conda run -n ML pytest tests/ -x -q 2>&1 | tail -5
```

---

## Completion Steps (do these in order after all tests pass)

1. **Write a completion report** at `AGENT_SPECS/completed/phase_M_css_isolation_labels_dead_code.md`
   using `AGENT_SPECS/completed/REPORT_TEMPLATE.md`. Include:
   - How many CSS rules were moved and which selectors
   - List of server-side hardcoded provider labels found (M2 audit results)
   - Which dead-code items were removed and which were already gone
   - Test result (pass count)
   - Deviations from this spec

2. **Append to log:**
   ```
   phase_M_css_isolation_labels_dead_code — 2026-05-XX
   ```
   at the bottom of `completed_agent_specs.txt`.

3. **Move this spec file** from `AGENT_SPECS/pending/claude/` to `AGENT_SPECS/archive/claude/completed/`.
