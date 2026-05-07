# Phase K — Frontend Provider Controller Deduplication

## Priority
HIGH — implement before phases L and M (L and M depend on the shared module introduced here).

## Purpose

Provider-selection, validation, and persistence logic is copy-pasted across four JavaScript files:

- `frontend/static/onboarding/core.js`
- `frontend/static/onboarding/intake.js`
- `frontend/static/onboarding/hydrate.js`
- `frontend/static/settings/provider.js`

When a provider is added or a config field changes, all four files must be updated in lockstep.
This spec extracts that logic into a single canonical module so there is exactly one place to update.

---

## Global Constraints (READ THESE FIRST)

1. **Python environment:** `conda run -n ML` for all test runs. Never create a venv.
2. **No build step.** JS files are served directly by FastAPI from `frontend/static/`. Do NOT use ES6 `import`/`export`. The module must be a plain global object on `window`.
3. **No Python backend changes in this spec.** Touch only `frontend/` files.
4. **Do NOT rename or remove existing HTML element IDs** — the backend renders them.
5. **Ruff:** Not applicable (JS only). Run `conda run -n ML pytest tests/test_frontend_provider_controller.py -v` to validate.
6. **Template TemplateResponse rule:** You will not be modifying Python templates in this spec, but if you add a `<script>` tag, use a URL path starting with `/static/` (FastAPI static mount).
7. **Read the existing files before editing.** Open each JS file and understand what's there before making changes.

---

## Step 1 — Audit the current duplication

Before writing any code, run the following to understand what's currently duplicated:

```bash
grep -n "validateAndSaveProvider\|saveProviderSettings\|getProviderLabel\|showProviderFields\|clearProvider\|PROVIDER_LABELS\|lm_studio.*ollama\|ollama.*openai" \
  frontend/static/onboarding/core.js \
  frontend/static/onboarding/intake.js \
  frontend/static/onboarding/hydrate.js \
  frontend/static/settings/provider.js
```

Read each file fully. List all functions and constants related to provider logic. You will move these into the new module.

---

## Step 2 — Create `frontend/static/provider_controller.js`

Create a new file at exactly that path. It must define `window.ProviderController` as a plain object (not a class). Use only ES5 syntax (no arrow functions in the top-level object, no `const`/`let` at file scope — use `var` for IE11 compatibility; or if the codebase already uses `const`/`let` consistently, match that style).

The module must expose at minimum:

```javascript
window.ProviderController = (function () {

  // ── Canonical provider metadata ──────────────────────────────────────────
  var PROVIDER_LABELS = {
    lm_studio:  "LM Studio (Local)",
    ollama:     "Ollama (Local)",
    openai:     "OpenAI",
    anthropic:  "Claude (Anthropic)",
    gemini:     "Google Gemini"
  };

  // Fields that must be non-empty before the provider can be saved.
  // Codex: inspect step_provider.html and provider_section.html to find the
  // actual input element IDs, then populate this map accurately.
  var PROVIDER_REQUIRED_FIELDS = {
    lm_studio:  [],                          // base URL has a default
    ollama:     [],
    openai:     ["openai-api-key"],
    anthropic:  ["anthropic-api-key"],
    gemini:     ["gemini-api-key"]
  };

  // ── Public API ────────────────────────────────────────────────────────────

  function getLabel(mode) {
    return PROVIDER_LABELS[mode] || mode;
  }

  // Returns true if all required fields for `mode` have non-empty values.
  // Reads values directly from the DOM input elements.
  function validateRequiredFields(mode) {
    var fields = PROVIDER_REQUIRED_FIELDS[mode] || [];
    for (var i = 0; i < fields.length; i++) {
      var el = document.getElementById(fields[i]);
      if (!el || !el.value.trim()) return false;
    }
    return true;
  }

  // Show only the config block for `mode`; hide all others.
  // Codex: inspect the HTML to find the actual container element IDs/classes
  // (e.g. `[data-provider]` attribute or named divs), then implement correctly.
  function showProviderFields(mode) {
    // TODO: implement based on actual HTML structure — read step_provider.html
    // and provider_section.html before implementing.
  }

  // POST the current provider config to /settings/save, then verify
  // reachability via GET /providers. Returns a Promise<{ok, error}>.
  // Codex: extract the existing implementation from intake.js or core.js
  // rather than writing from scratch — copy and adapt it here.
  function validateAndSave(mode, extraPayload) {
    // TODO: extract from existing code
  }

  // Clear secret-value inputs (API key fields) when switching away from a provider.
  function clearSecretInputs(mode) {
    var fields = PROVIDER_REQUIRED_FIELDS[mode] || [];
    fields.forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.value = "";
    });
  }

  return {
    labels:                PROVIDER_LABELS,
    getLabel:              getLabel,
    validateRequiredFields: validateRequiredFields,
    showProviderFields:    showProviderFields,
    validateAndSave:       validateAndSave,
    clearSecretInputs:     clearSecretInputs
  };
})();
```

**Important:** The `validateAndSave` and `showProviderFields` implementations must be extracted from the existing JS files, not invented. Read intake.js and core.js to find the real implementation, then move it here.

---

## Step 3 — Add script tag to templates

### `frontend/templates/onboarding.html`

Find the block that loads onboarding JS (look for `<script src="/static/onboarding/core.js`). Add the new script tag **before** core.js:

```html
<!-- BEFORE -->
<script src="/static/onboarding/core.js?v=..."></script>

<!-- AFTER -->
<script src="/static/provider_controller.js?v=1"></script>
<script src="/static/onboarding/core.js?v=..."></script>
```

### `frontend/templates/settings.html`

Find the block that loads settings JS (look for `<script src="/static/settings/`). Add the new script tag before the first settings script:

```html
<!-- BEFORE -->
<script src="/static/settings/core.js?v=..."></script>

<!-- AFTER -->
<script src="/static/provider_controller.js?v=1"></script>
<script src="/static/settings/core.js?v=..."></script>
```

---

## Step 4 — Update the four source files

For each file, **read the full file first**, then:

### `frontend/static/onboarding/intake.js`
- Find any function that validates or saves provider settings (e.g. `validateAndSaveProvider`, inline fetch to `/settings/save`)
- Replace the body of that function with a call to `ProviderController.validateAndSave(...)`
- Remove any locally-defined `PROVIDER_LABELS` constant or inline provider label logic

### `frontend/static/onboarding/core.js`
- Find any provider label map, `showProviderFields`, or `clearProviderSecrets` equivalents
- Remove them and replace call sites with `ProviderController.getLabel(...)`, `ProviderController.showProviderFields(...)`, etc.
- Do NOT remove unrelated functions (goToStep, ensureCandidateShell, setInlineStatus, etc.)

### `frontend/static/onboarding/hydrate.js`
- Find any hardcoded provider label strings (e.g. `"LM Studio"`, `"OpenAI"`) and replace with `ProviderController.getLabel(mode)`
- Find any provider field visibility logic and replace with `ProviderController.showProviderFields(mode)`

### `frontend/static/settings/provider.js`
- Find the validate-and-save flow (fetch to `/settings/save` or `/providers`)
- Replace with `ProviderController.validateAndSave(...)` call
- Remove duplicate provider label constants if present

---

## Step 5 — Tests to write

Create `tests/test_frontend_provider_controller.py`:

```python
"""
Structural tests for the provider_controller.js module.
Validates that the shared module exists and that duplication is eliminated.
"""
from pathlib import Path

STATIC = Path("frontend/static")
TEMPLATES = Path("frontend/templates")
CONTROLLER = STATIC / "provider_controller.js"
INTAKE_JS   = STATIC / "onboarding/intake.js"
HYDRATE_JS  = STATIC / "onboarding/hydrate.js"
CORE_JS     = STATIC / "onboarding/core.js"
SETTINGS_PROVIDER_JS = STATIC / "settings/provider.js"
ONBOARDING_HTML = TEMPLATES / "onboarding.html"
SETTINGS_HTML   = TEMPLATES / "settings.html"


def test_provider_controller_file_exists():
    assert CONTROLLER.exists(), "provider_controller.js must exist"
    assert CONTROLLER.stat().st_size > 200, "provider_controller.js must not be empty"


def test_provider_controller_exposes_global():
    content = CONTROLLER.read_text()
    assert "window.ProviderController" in content, (
        "Must assign to window.ProviderController"
    )


def test_provider_labels_has_five_entries():
    content = CONTROLLER.read_text()
    for key in ("lm_studio", "ollama", "openai", "anthropic", "gemini"):
        assert key in content, f"PROVIDER_LABELS must contain key: {key}"


def test_validate_and_save_defined_in_controller():
    content = CONTROLLER.read_text()
    assert "validateAndSave" in content, (
        "validateAndSave must be defined in provider_controller.js"
    )


def test_validate_and_save_not_duplicated_in_intake():
    # After extraction, intake.js should call ProviderController.validateAndSave,
    # not define its own full fetch-to-save-provider implementation.
    intake = INTAKE_JS.read_text()
    # The old implementation fetched directly to /settings/save with a big body.
    # After this spec, it should delegate to the controller.
    assert "ProviderController" in intake, (
        "intake.js must call ProviderController, not duplicate provider logic"
    )


def test_provider_labels_not_duplicated_in_hydrate():
    hydrate = HYDRATE_JS.read_text()
    # After extraction, hardcoded label strings like '"LM Studio (Local)"' should
    # not appear in hydrate.js — getLabel() call replaces them.
    assert "ProviderController.getLabel" in hydrate or "ProviderController" in hydrate, (
        "hydrate.js must use ProviderController for provider labels"
    )


def test_onboarding_html_loads_controller_before_core():
    html = ONBOARDING_HTML.read_text()
    assert "provider_controller.js" in html, (
        "onboarding.html must load provider_controller.js"
    )
    controller_pos = html.index("provider_controller.js")
    core_pos = html.index("onboarding/core.js")
    assert controller_pos < core_pos, (
        "provider_controller.js script tag must appear before core.js"
    )


def test_settings_html_loads_controller():
    html = SETTINGS_HTML.read_text()
    assert "provider_controller.js" in html, (
        "settings.html must load provider_controller.js"
    )
```

---

## Verification

```bash
conda run -n ML pytest tests/test_frontend_provider_controller.py -v
```

All 8 tests must pass. Then run the full suite to confirm no regressions:

```bash
conda run -n ML pytest tests/ -x -q 2>&1 | tail -5
```

---

## Completion Steps (do these in order after all tests pass)

1. **Write a completion report** at `AGENT_SPECS/completed/phase_K_provider_controller_deduplication.md` using the template at `AGENT_SPECS/completed/REPORT_TEMPLATE.md`. Fill every section. Include:
   - Which functions were moved from which files
   - Any provider logic that turned out NOT to be duplicated (and was left in place)
   - Test result (pass count)
   - Any deviations from this spec

2. **Append to log:**
   ```
   phase_K_provider_controller_deduplication — 2026-05-XX
   ```
   at the bottom of `completed_agent_specs.txt`.

3. **Move this spec file** from `AGENT_SPECS/pending/claude/` to `AGENT_SPECS/archive/claude/completed/`.
