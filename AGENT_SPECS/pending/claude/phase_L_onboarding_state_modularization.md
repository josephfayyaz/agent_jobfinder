# Phase L — Onboarding State Modularization

## Priority
MEDIUM — implement after phase K. Does not depend on K, but K should ship first so the
`ProviderController` module exists by the time L refactors provider-related state reads.

## Purpose

The onboarding JavaScript uses a single flat state object (or several ad-hoc module-level
variables) shared across all five steps. Any step can accidentally overwrite another step's
data. This causes subtle bugs when the user navigates back or reruns the intake flow.

This spec replaces the flat shared namespace with five small, named state objects — one per
onboarding step — so each step owns only the data it needs.

---

## Global Constraints (READ THESE FIRST)

1. **Python environment:** `conda run -n ML` for all test runs. Never create a venv.
2. **No build step.** Files are served directly. No ES6 `import`/`export`.
3. **No Python backend changes in this spec.** Touch only `frontend/static/onboarding/` files.
4. **Read each JS file fully before editing.** The exact variable names may differ from what
   this spec predicts — adapt the spec's intent to whatever is actually in the file.
5. **Do not break the onboarding flow.** After this change, the full 5-step flow
   (Provider → Facts → Questions → Review → Search) must still work end-to-end.
6. **Preserve all existing function signatures.** Only change internal variable references
   from the flat object to the per-step objects.

---

## Step 1 — Audit the current state structure

Run:

```bash
grep -n "onboardingState\|sharedState\|state\." \
  frontend/static/onboarding/core.js \
  frontend/static/onboarding/intake.js \
  frontend/static/onboarding/hydrate.js \
  frontend/static/onboarding/review.js \
  frontend/static/onboarding/search.js
```

Also grep for module-level variables that act as implicit state:

```bash
grep -n "^var \|^let \|^const " \
  frontend/static/onboarding/core.js \
  frontend/static/onboarding/intake.js \
  frontend/static/onboarding/hydrate.js \
  frontend/static/onboarding/review.js \
  frontend/static/onboarding/search.js
```

Read the output carefully. Map every piece of cross-step state to its correct owner step.

---

## Step 2 — Define the five state objects in `core.js`

In `frontend/static/onboarding/core.js`, **replace** the existing flat state variable(s) with
five named objects. Place them near the top of the file, after any `use strict` or initial
comments, before any function definitions.

The five objects and their canonical fields (adapt field names to match what actually exists
in the code — these are the intended semantics, not rigid names):

```javascript
// Step 1: AI Provider
var providerState = {
  mode:      "",        // e.g. "lm_studio", "openai"
  config:    {},        // provider-specific field values collected from the form
  validated: false      // true after a successful reachability check
};

// Step 2: Fact Sheet Intake
var intakeState = {
  candidateId:       null,  // UUID set after ensure-owner
  filesUploaded:     [],    // list of File objects or filenames
  notesText:         "",    // freeform notes textarea value
  questions:         [],    // questions returned by the backend
  questionsAnswered: false  // true after answers submitted
};

// Step 3: Profile Review
var reviewState = {
  profileData: {},    // raw profile JSON from /candidates/{id}/intake/status
  editedRows:  {},    // user edits keyed by field name
  saved:       false
};

// Step 4: Search Focus
var searchState = {
  roles:     [],         // list of target role strings
  country:   "Italy",
  seniority: "junior",
  languages: []          // [{language, proficiency}]
};

// Navigation (shared across all steps)
var navState = {
  currentStep: 1
};
```

**If the existing code already has named objects** (not a flat one), check whether the field
names match the above semantics. If they do, only rename properties that diverge — do not
rewrite working state management.

---

## Step 3 — Update references in each file

For each file, read it fully, then replace references to the old flat state with the
correct per-step object:

### `frontend/static/onboarding/intake.js`
- References to provider mode / provider config → use `providerState.mode`, `providerState.config`
- References to candidateId, filesUploaded, questions → use `intakeState.*`
- Do NOT reference `reviewState` or `searchState` from intake.js

### `frontend/static/onboarding/hydrate.js`
- Hydration should write directly into the appropriate state object
- Provider mode from server → `providerState.mode`
- Candidate ID → `intakeState.candidateId`
- Existing profile data → `reviewState.profileData`
- Existing search config → `searchState.roles`, `searchState.country`, etc.
- Current step → `navState.currentStep`

### `frontend/static/onboarding/review.js`
- All state reads/writes use `reviewState.*`
- Do NOT read `intakeState` or `providerState` here

### `frontend/static/onboarding/search.js`
- All state reads/writes use `searchState.*`

### `frontend/static/onboarding/core.js`
- `goToStep()` and navigation use `navState.currentStep`
- Remove the old flat state object declaration
- `ensureCandidateShell()` writes `intakeState.candidateId`
- Provider-related helpers (if still in core.js after phase K) read `providerState.*`

---

## Step 4 — Tests to write

Create `tests/test_frontend_state_modularization.py`:

```python
"""
Structural tests that verify onboarding state is split into per-step namespaces.
These are static analysis tests (file content checks), not browser tests.
"""
from pathlib import Path

ONBOARDING = Path("frontend/static/onboarding")
CORE    = ONBOARDING / "core.js"
INTAKE  = ONBOARDING / "intake.js"
HYDRATE = ONBOARDING / "hydrate.js"
REVIEW  = ONBOARDING / "review.js"
SEARCH  = ONBOARDING / "search.js"


def test_per_step_state_objects_declared_in_core():
    content = CORE.read_text()
    for name in ("providerState", "intakeState", "reviewState", "searchState", "navState"):
        assert name in content, (
            f"core.js must declare the '{name}' state object"
        )


def test_no_old_flat_state_in_step_files():
    """
    After modularization, step-specific files must NOT reference a flat
    'onboardingState' global — they must use their own state object.
    """
    for path in (INTAKE, HYDRATE, REVIEW, SEARCH):
        content = path.read_text()
        assert "onboardingState." not in content, (
            f"{path.name} must not reference 'onboardingState.' — use per-step state"
        )


def test_intake_uses_intake_state():
    content = INTAKE.read_text()
    assert "intakeState" in content, "intake.js must reference intakeState"


def test_review_uses_review_state():
    content = REVIEW.read_text()
    assert "reviewState" in content, "review.js must reference reviewState"


def test_search_uses_search_state():
    content = SEARCH.read_text()
    assert "searchState" in content, "search.js must reference searchState"


def test_hydrate_populates_multiple_state_objects():
    content = HYDRATE.read_text()
    # Hydrate touches provider + intake + review + search state
    found = sum(
        1 for name in ("providerState", "intakeState", "reviewState", "searchState")
        if name in content
    )
    assert found >= 2, (
        "hydrate.js must write into at least 2 per-step state objects"
    )


def test_state_objects_initialised_at_module_load():
    """
    State must be initialised at file scope, not inside a function,
    so it is available as soon as the script loads.
    """
    content = CORE.read_text()
    # Each declaration must appear before any function definition that uses it.
    # Simple heuristic: all five state var declarations appear before line 200.
    lines = content.splitlines()
    for name in ("providerState", "intakeState", "reviewState", "searchState", "navState"):
        decl_line = next(
            (i for i, l in enumerate(lines, 1) if name in l and ("var " in l or "let " in l or "const " in l)),
            None
        )
        assert decl_line is not None, f"'{name}' must be declared at module scope in core.js"
        assert decl_line < 200, (
            f"'{name}' declaration (line {decl_line}) must appear before line 200 (module-level init)"
        )
```

---

## Verification

```bash
conda run -n ML pytest tests/test_frontend_state_modularization.py -v
```

All 7 tests must pass. Then run the full suite:

```bash
conda run -n ML pytest tests/ -x -q 2>&1 | tail -5
```

---

## Completion Steps (do these in order after all tests pass)

1. **Write a completion report** at `AGENT_SPECS/completed/phase_L_onboarding_state_modularization.md`
   using `AGENT_SPECS/completed/REPORT_TEMPLATE.md`. Include:
   - Whether a flat `onboardingState` object existed (or a different structure)
   - Which fields were moved to which state object
   - Any cross-step dependencies found (where step A needed step B's data) and how resolved
   - Test result (pass count)
   - Deviations from this spec

2. **Append to log:**
   ```
   phase_L_onboarding_state_modularization — 2026-05-XX
   ```
   at the bottom of `completed_agent_specs.txt`.

3. **Move this spec file** from `AGENT_SPECS/pending/claude/` to `AGENT_SPECS/archive/claude/completed/`.
