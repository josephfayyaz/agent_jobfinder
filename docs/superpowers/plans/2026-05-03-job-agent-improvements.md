# Job Agent Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver three improvements to the job agent: (1) fix the Application Snapshot/Readiness double-fetch bug with Alpine.js fetch-once state, (2) add skeleton loaders for the discovery scan panel and onboarding intake, and (3) add LLM-driven role suggestion with new backend endpoints and frontend wiring.

**Architecture:** Tasks 1 and 2 are purely frontend changes. Task 3 adds two migration columns and three new API endpoints in `candidates.py`. Task 4 wires the new endpoints into onboarding and settings. All LLM calls go through `LLMRouter` and must catch both `ProviderUnavailableError` and `ValueError`.

**Tech Stack:** FastAPI + Jinja2 + HTMX 2.0 + Alpine.js 3.x, SQLite (no Alembic — use `_safe_add_column`), LLMRouter (`role="small"`).

---

## File Map

| File | Change |
|------|--------|
| `frontend/templates/partials/job_group.html` | Add Alpine `x-data` for fetch-once state |
| `frontend/templates/partials/job_row.html` | Replace onclick+hx-get with Alpine @click on Snapshot, Readiness, Application Snapshot buttons |
| `frontend/static/jobs.js` | `renderTask()` skeleton summary + `startRun()` queue skeleton injection + terminal cleanup |
| `frontend/templates/partials/onboarding/step_facts.html` | Add hidden `#intake-skeleton` block |
| `frontend/static/onboarding/intake.js` | Show/hide intake skeleton around `intake/start` call |
| `job_agent/db.py` | Two `_safe_add_column` calls for `resume_tracks` |
| `job_agent/models.py` | Add `is_custom` + `candidate_id` to `ResumeTrack` |
| `job_agent/routers/candidates.py` | Three new routes: `suggest-tracks`, `generate-tracks`, `tracks` |
| `frontend/templates/partials/onboarding/step_search.html` | Add `#llm-suggest-status` span and skeleton chips container |
| `frontend/templates/partials/onboarding/done_panel.html` | Add `#tracks-status` paragraph shown during track generation |
| `frontend/static/onboarding/search.js` | Extend `hydrateSearchFocus()` + rewrite `saveSearchFocus()` |
| `frontend/templates/partials/settings/discovery_section.html` | Append Role Tracks subsection |

---

## Task 1: Alpine Fetch-Once Bug Fix

**Files:**
- Modify: `frontend/templates/partials/job_group.html`
- Modify: `frontend/templates/partials/job_row.html`

### Problem

The Application Snapshot, Readiness, and Snapshot buttons each carry both an `onclick` handler (toggle row) **and** `hx-get` (fire LLM call). Every click including close fires a new server request.

### Solution

Add Alpine `x-data` to the `<tbody>` so each row group tracks whether content has been fetched. On first click: show row + call `htmx.ajax`. On subsequent clicks: just toggle row visibility.

- [ ] **Step 1: Add Alpine x-data to job_group.html**

Replace:
```html
<tbody id="job-group-{{ job.id }}" data-job-group="{{ job.id }}">
```
With:
```html
<tbody id="job-group-{{ job.id }}" data-job-group="{{ job.id }}" x-data="{ snapLoaded: false, readyLoaded: false, pkgLoaded: false }">
```

- [ ] **Step 2: Fix the Application Snapshot (package-check) button in job_row.html**

Find the block (lines 169–179 in current file):
```html
      <button
        type="button"
        {% if not drafting_locked and not low_fit %}
        onclick="document.getElementById('package-check-row-{{ job.id }}')?.classList.toggle('hidden')"
        hx-get="/ui/jobs/{{ job.id }}/package-check"
        hx-target="#package-check-{{ job.id }}"
        hx-swap="innerHTML"
        {% endif %}
        class="px-2 py-1 text-xs rounded {% if drafting_locked or low_fit %}bg-slate-100 text-slate-500{% else %}bg-indigo-100 text-indigo-700 hover:bg-indigo-200{% endif %}"
        title="Application Snapshot — review fit, trust, and drafting readiness before spending tokens."
      >{{ 'Low fit' if low_fit else ('Needs JD' if drafting_locked else 'Application Snapshot') }}</button>
```

Replace with:
```html
      <button
        type="button"
        {% if not drafting_locked and not low_fit %}
        @click="if (!pkgLoaded) { document.getElementById('package-check-row-{{ job.id }}').classList.remove('hidden'); htmx.ajax('GET', '/ui/jobs/{{ job.id }}/package-check', {target: '#package-check-{{ job.id }}', swap: 'innerHTML'}); pkgLoaded = true; } else { document.getElementById('package-check-row-{{ job.id }}').classList.toggle('hidden'); }"
        {% endif %}
        class="px-2 py-1 text-xs rounded {% if drafting_locked or low_fit %}bg-slate-100 text-slate-500{% else %}bg-indigo-100 text-indigo-700 hover:bg-indigo-200{% endif %}"
        title="Application Snapshot — review fit, trust, and drafting readiness before spending tokens."
      >{{ 'Low fit' if low_fit else ('Needs JD' if drafting_locked else 'Application Snapshot') }}</button>
```

- [ ] **Step 3: Fix the Readiness button in job_row.html**

Find (lines 198–207 in current file):
```html
      <button
        type="button"
        title="Role Readiness Map — compares this job's requirements against your fact sheet before you generate a CV. Reveals skill gaps and strength matches."
        onclick="document.getElementById('fit-gap-row-{{ job.id }}')?.classList.toggle('hidden')"
        hx-get="/ui/jobs/{{ job.id }}/fit-gaps"
        hx-target="#fit-gaps-{{ job.id }}"
        hx-swap="innerHTML"
        hx-disabled-elt="this"
        class="flex items-center gap-1 px-2 py-1 text-xs bg-orange-100 text-orange-700 rounded hover:bg-orange-200"
      ><span class="htmx-indicator w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin"></span>Readiness</button>
```

Replace with:
```html
      <button
        type="button"
        title="Role Readiness Map — compares this job's requirements against your fact sheet before you generate a CV. Reveals skill gaps and strength matches."
        @click="if (!readyLoaded) { document.getElementById('fit-gap-row-{{ job.id }}').classList.remove('hidden'); htmx.ajax('GET', '/ui/jobs/{{ job.id }}/fit-gaps', {target: '#fit-gaps-{{ job.id }}', swap: 'innerHTML'}); readyLoaded = true; } else { document.getElementById('fit-gap-row-{{ job.id }}').classList.toggle('hidden'); }"
        class="flex items-center gap-1 px-2 py-1 text-xs bg-orange-100 text-orange-700 rounded hover:bg-orange-200"
      >Readiness</button>
```

- [ ] **Step 4: Fix the Snapshot (opportunity snapshot) button in job_row.html**

Find (lines 208–218 in current file):
```html
      <button
        type="button"
        {% if job.snapshot_unlocked %}
        onclick="document.getElementById('snapshot-row-{{ job.id }}')?.classList.toggle('hidden')"
        hx-get="/ui/jobs/{{ job.id }}/snapshot"
        hx-target="#snapshot-{{ job.id }}"
        hx-swap="innerHTML"
        {% endif %}
        class="px-2 py-1 text-xs rounded {% if job.snapshot_unlocked %}bg-sky-100 text-sky-700 hover:bg-sky-200{% else %}bg-slate-100 text-slate-400 cursor-not-allowed{% endif %}"
        title="{% if job.snapshot_unlocked %}Opportunity Snapshot — quick company and role research for shortlisted or high-fit jobs.{% else %}Unlock by shortlisting this job or reaching a high fit score.{% endif %}"
      >Snapshot</button>
```

Replace with:
```html
      <button
        type="button"
        {% if job.snapshot_unlocked %}
        @click="if (!snapLoaded) { document.getElementById('snapshot-row-{{ job.id }}').classList.remove('hidden'); htmx.ajax('GET', '/ui/jobs/{{ job.id }}/snapshot', {target: '#snapshot-{{ job.id }}', swap: 'innerHTML'}); snapLoaded = true; } else { document.getElementById('snapshot-row-{{ job.id }}').classList.toggle('hidden'); }"
        {% endif %}
        class="px-2 py-1 text-xs rounded {% if job.snapshot_unlocked %}bg-sky-100 text-sky-700 hover:bg-sky-200{% else %}bg-slate-100 text-slate-400 cursor-not-allowed{% endif %}"
        title="{% if job.snapshot_unlocked %}Opportunity Snapshot — quick company and role research for shortlisted or high-fit jobs.{% else %}Unlock by shortlisting this job or reaching a high fit score.{% endif %}"
      >Snapshot</button>
```

- [ ] **Step 5: Verify Alpine is loaded on the jobs page**

`base.html` already includes:
```html
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
```
No change needed — Alpine is available on all pages that extend `base.html`, which includes the jobs page.

- [ ] **Step 6: Write failing tests**

In `tests/test_ui_jobs_alpine.py` (new file):
```python
"""Verify the job_row template no longer carries onclick+hx-get on expansion buttons."""
from pathlib import Path


def _row_src():
    return Path("frontend/templates/partials/job_row.html").read_text()


def _group_src():
    return Path("frontend/templates/partials/job_group.html").read_text()


def test_readiness_button_has_no_onclick():
    assert 'onclick="document.getElementById(\'fit-gap-row' not in _row_src()


def test_readiness_button_has_no_hx_get():
    src = _row_src()
    # The hx-get for fit-gaps should not exist as a standalone HTMX attribute
    assert 'hx-get="/ui/jobs/{{ job.id }}/fit-gaps"' not in src


def test_snapshot_button_has_no_onclick():
    assert 'onclick="document.getElementById(\'snapshot-row' not in _row_src()


def test_snapshot_button_has_no_hx_get():
    assert 'hx-get="/ui/jobs/{{ job.id }}/snapshot"' not in _row_src()


def test_pkg_button_has_no_onclick():
    assert 'onclick="document.getElementById(\'package-check-row' not in _row_src()


def test_pkg_button_has_no_hx_get():
    assert 'hx-get="/ui/jobs/{{ job.id }}/package-check"' not in _row_src()


def test_job_group_has_alpine_x_data():
    assert 'x-data="{ snapLoaded: false, readyLoaded: false, pkgLoaded: false }"' in _group_src()


def test_job_group_has_alpine_at_click_for_pkg():
    assert "@click" in _row_src()
    assert "pkgLoaded" in _row_src()


def test_job_group_has_alpine_at_click_for_readiness():
    assert "readyLoaded" in _row_src()


def test_job_group_has_alpine_at_click_for_snapshot():
    assert "snapLoaded" in _row_src()
```

- [ ] **Step 7: Run tests to confirm they fail**

```bash
conda run -n ML pytest tests/test_ui_jobs_alpine.py -v
```
Expected: all 10 tests FAIL (template not yet updated).

- [ ] **Step 8: Apply the template changes from Steps 1–4**

- [ ] **Step 9: Run tests to confirm they pass**

```bash
conda run -n ML pytest tests/test_ui_jobs_alpine.py -v
```
Expected: all 10 PASS.

- [ ] **Step 10: Run full suite to check for regressions**

```bash
conda run -n ML pytest tests/ -x -q
```
Expected: green.

- [ ] **Step 11: Commit**

```bash
git add frontend/templates/partials/job_group.html frontend/templates/partials/job_row.html tests/test_ui_jobs_alpine.py
git commit -m "fix: fetch-once Alpine state for expansion buttons in job queue"
```

---

## Task 2: Skeleton Loaders

### 2a: Discovery Panel Skeleton

**Files:**
- Modify: `frontend/static/jobs.js`

#### Changes

**`renderTask()` — skeleton summary boxes when scan is running:**

In `renderTask()`, find the summary block (around line 162):
```js
    if (els.summary) {
      els.summary.innerHTML = discoverySummaryRows(task)
        .map((row) => `<div class="rounded-xl border border-slate-100 bg-slate-50 px-3 py-2">${row}</div>`)
        .join("");
    }
```

Replace with:
```js
    if (els.summary) {
      if (discoveryTerminal(task)) {
        els.summary.innerHTML = discoverySummaryRows(task)
          .map((row) => `<div class="rounded-xl border border-slate-100 bg-slate-50 px-3 py-2">${row}</div>`)
          .join("");
      } else {
        els.summary.innerHTML = Array.from({length: 14})
          .map(() => `<div class="h-9 rounded-xl bg-slate-100 animate-pulse"></div>`)
          .join("");
      }
    }
```

**Queue table skeleton — add helper functions before `createDiscoveryController()`:**

Add these two functions before the `createDiscoveryController()` function definition (around line 126):
```js
function injectQueueSkeleton() {
  if (document.getElementById("queue-skeleton")) {
    return;
  }
  const panel = document.getElementById("job-discovery-panel");
  if (!panel) {
    return;
  }
  const skeleton = document.createElement("div");
  skeleton.id = "queue-skeleton";
  skeleton.className = "mt-4 space-y-2";
  skeleton.innerHTML = Array.from({length: 4}).map(() => `
    <div class="flex items-center gap-3 rounded-xl border border-slate-100 bg-white px-4 py-3">
      <div class="h-4 w-32 rounded bg-slate-100 animate-pulse"></div>
      <div class="h-4 w-48 rounded bg-slate-100 animate-pulse flex-1"></div>
      <div class="h-8 w-8 rounded-full bg-slate-100 animate-pulse"></div>
      <div class="h-4 w-24 rounded bg-slate-100 animate-pulse"></div>
      <div class="flex gap-2">
        <div class="h-6 w-16 rounded bg-slate-100 animate-pulse"></div>
        <div class="h-6 w-16 rounded bg-slate-100 animate-pulse"></div>
      </div>
    </div>
  `).join("");
  panel.insertAdjacentElement("afterend", skeleton);
}

function removeQueueSkeleton() {
  const skeleton = document.getElementById("queue-skeleton");
  if (skeleton) {
    skeleton.remove();
  }
}
```

**`startRun()` — inject skeleton at start:**

In `startRun()`, after `renderTask({ status: "running", ... })` call (around line 247), add:
```js
    injectQueueSkeleton();
```

**`bind()` — remove skeleton when refresh is clicked:**

In the `bind()` function, find:
```js
    if (els.refresh) {
      els.refresh.addEventListener("click", () => window.location.reload());
    }
```

Replace with:
```js
    if (els.refresh) {
      els.refresh.addEventListener("click", () => {
        removeQueueSkeleton();
        window.location.reload();
      });
    }
```

Also in `renderTask()`, after `els.refresh.classList.toggle("hidden", !discoveryTerminal(task))`, add:
```js
    if (discoveryTerminal(task)) {
      removeQueueSkeleton();
    }
```

- [ ] **Step 1: Write failing tests for skeleton behavior in jobs.js**

In `tests/test_jobs_js_skeleton.py` (new file):
```python
"""Verify skeleton logic strings are present in jobs.js."""
from pathlib import Path


def _src():
    return Path("frontend/static/jobs.js").read_text()


def test_summary_skeleton_on_running():
    src = _src()
    assert "animate-pulse" in src
    assert "Array.from({length: 14})" in src


def test_summary_real_data_on_terminal():
    src = _src()
    assert "discoveryTerminal(task)" in src


def test_inject_queue_skeleton_function_exists():
    assert "function injectQueueSkeleton()" in _src()


def test_remove_queue_skeleton_function_exists():
    assert "function removeQueueSkeleton()" in _src()


def test_queue_skeleton_injected_on_start():
    src = _src()
    assert "injectQueueSkeleton()" in src


def test_queue_skeleton_removed_on_terminal():
    assert "removeQueueSkeleton()" in _src()
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
conda run -n ML pytest tests/test_jobs_js_skeleton.py -v
```
Expected: all FAIL.

- [ ] **Step 3: Apply jobs.js changes from the Changes section above**

- [ ] **Step 4: Run tests to confirm they pass**

```bash
conda run -n ML pytest tests/test_jobs_js_skeleton.py -v
```
Expected: all PASS.

### 2b: Onboarding Intake Skeleton

**Files:**
- Modify: `frontend/templates/partials/onboarding/step_facts.html`
- Modify: `frontend/static/onboarding/intake.js`

#### Changes

**`step_facts.html` — add skeleton block before the buttons row:**

Find the buttons div (currently the last element in the panel body):
```html
    <div class="flex items-center gap-3">
      <button type="button" onclick="goToStep(2)" class="app-button app-button--ghost">Back</button>
      <button type="button" onclick="runIntake()" class="app-button app-button--primary">Analyse my profile</button>
    </div>
```

Insert the skeleton block immediately before it:
```html
    <div id="intake-skeleton" class="hidden space-y-3">
      <div class="h-5 w-48 rounded-lg bg-slate-100 animate-pulse"></div>
      <div class="h-4 w-full rounded-lg bg-slate-100 animate-pulse"></div>
      <div class="h-4 w-3/4 rounded-lg bg-slate-100 animate-pulse"></div>
      <div class="h-4 w-full rounded-lg bg-slate-100 animate-pulse"></div>
      <div class="h-4 w-2/3 rounded-lg bg-slate-100 animate-pulse"></div>
    </div>
    <div class="flex items-center gap-3">
```

**`intake.js` — show/hide skeleton:**

In `app.runIntake`, find:
```js
    app.setStatus("Analysing your profile...");
```

Immediately after that line add:
```js
    const intakeSkeleton = document.getElementById("intake-skeleton");
    if (intakeSkeleton) {
      intakeSkeleton.classList.remove("hidden");
    }
```

Find where the function returns on error or success (there are multiple early-return paths after the intake response). Before every `return` statement that comes *after* the skeleton was shown, and before the final `goToStep` calls, add the hide call. The cleanest approach is a `finally`-like cleanup. Restructure the intake response handling block:

Find this block:
```js
    const intakeResponse = await fetch(`/candidates/${app.state.candidateId}/intake/start`, {
      method: "POST",
      headers: {"Content-Type": "application/x-www-form-urlencoded"},
      body: new URLSearchParams({profile_notes: notes}),
    });
    if (!intakeResponse.ok) {
      let errMsg = "The AI provider could not complete intake. Check your provider key in Settings.";
      try {
        const errData = await intakeResponse.json();
        if (errData.detail) {
          errMsg = errData.detail;
        }
      } catch (_error) {
        // Keep the generic status message when the response body is not JSON.
      }
      app.setStatus(errMsg, true);
      return;
    }
    const data = await intakeResponse.json();
    if (data.status === "questions_needed" && (data.questions || []).length) {
      app.state.questions = data.questions || [];
      app.renderQuestions();
      app.goToStep(4);
    } else {
      const setupReady = await app.ensureFactSheetReady();
      if (!setupReady) {
        app.goToStep(3);
        return;
      }
      await app.loadProfileReview();
      app.goToStep(5);
    }
```

Replace with:
```js
    let intakeData = null;
    try {
      const intakeResponse = await fetch(`/candidates/${app.state.candidateId}/intake/start`, {
        method: "POST",
        headers: {"Content-Type": "application/x-www-form-urlencoded"},
        body: new URLSearchParams({profile_notes: notes}),
      });
      if (!intakeResponse.ok) {
        let errMsg = "The AI provider could not complete intake. Check your provider key in Settings.";
        try {
          const errData = await intakeResponse.json();
          if (errData.detail) {
            errMsg = errData.detail;
          }
        } catch (_error) {
          // Keep the generic status message when the response body is not JSON.
        }
        app.setStatus(errMsg, true);
        return;
      }
      intakeData = await intakeResponse.json();
    } finally {
      if (intakeSkeleton) {
        intakeSkeleton.classList.add("hidden");
      }
    }
    if (intakeData.status === "questions_needed" && (intakeData.questions || []).length) {
      app.state.questions = intakeData.questions || [];
      app.renderQuestions();
      app.goToStep(4);
    } else {
      const setupReady = await app.ensureFactSheetReady();
      if (!setupReady) {
        app.goToStep(3);
        return;
      }
      await app.loadProfileReview();
      app.goToStep(5);
    }
```

- [ ] **Step 5: Write failing tests for skeleton elements**

In `tests/test_onboarding_skeleton.py` (new file):
```python
"""Verify intake skeleton HTML and JS toggle logic are present."""
from pathlib import Path


def test_intake_skeleton_block_in_template():
    src = Path("frontend/templates/partials/onboarding/step_facts.html").read_text()
    assert 'id="intake-skeleton"' in src
    assert "animate-pulse" in src
    assert 'class="hidden' in src


def test_intake_skeleton_show_in_js():
    src = Path("frontend/static/onboarding/intake.js").read_text()
    assert "intake-skeleton" in src
    assert 'classList.remove("hidden")' in src


def test_intake_skeleton_hide_in_js():
    src = Path("frontend/static/onboarding/intake.js").read_text()
    assert 'classList.add("hidden")' in src
```

- [ ] **Step 6: Run tests to confirm they fail**

```bash
conda run -n ML pytest tests/test_onboarding_skeleton.py -v
```
Expected: all FAIL.

- [ ] **Step 7: Apply step_facts.html and intake.js changes from the Changes section above**

- [ ] **Step 8: Run tests to confirm they pass**

```bash
conda run -n ML pytest tests/test_onboarding_skeleton.py -v
```
Expected: all PASS.

- [ ] **Step 9: Run full suite**

```bash
conda run -n ML pytest tests/ -x -q
```
Expected: green.

- [ ] **Step 10: Commit**

```bash
git add frontend/static/jobs.js frontend/templates/partials/onboarding/step_facts.html frontend/static/onboarding/intake.js tests/test_jobs_js_skeleton.py tests/test_onboarding_skeleton.py
git commit -m "feat: skeleton loaders for discovery panel and onboarding intake"
```

---

## Task 3: LLM Role Suggestion — Backend

**Files:**
- Modify: `job_agent/db.py`
- Modify: `job_agent/models.py`
- Modify: `job_agent/routers/candidates.py`

### 3a: Schema + Model Changes

- [ ] **Step 1: Write failing tests for new model fields**

In `tests/test_resume_track_model.py` (new file):
```python
"""Verify ResumeTrack has the new is_custom and candidate_id fields."""
import inspect
from job_agent.models import ResumeTrack


def test_resume_track_has_is_custom():
    cols = {col.key for col in ResumeTrack.__table__.columns}
    assert "is_custom" in cols


def test_resume_track_has_candidate_id():
    cols = {col.key for col in ResumeTrack.__table__.columns}
    assert "candidate_id" in cols


def test_is_custom_default_false():
    track = ResumeTrack(
        slug="test-slug",
        title="Test",
        role_family="data",
        baseline_summary="summary",
    )
    assert track.is_custom is False


def test_candidate_id_nullable():
    track = ResumeTrack(
        slug="test-slug2",
        title="Test2",
        role_family="data",
        baseline_summary="summary",
    )
    assert track.candidate_id is None
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
conda run -n ML pytest tests/test_resume_track_model.py -v
```
Expected: `ImportError` or `AttributeError` — field not present.

- [ ] **Step 3: Add columns to db.py**

In `job_agent/db.py`, inside `prepare_database()`, find:
```python
        _safe_add_column(conn, "resume_tracks", "active", "INTEGER DEFAULT 1")
```

Add two lines immediately after:
```python
        _safe_add_column(conn, "resume_tracks", "is_custom", "INTEGER NOT NULL DEFAULT 0")
        _safe_add_column(conn, "resume_tracks", "candidate_id", "VARCHAR(36)")
```

- [ ] **Step 4: Add fields to models.py**

In `job_agent/models.py`, find the `ResumeTrack` class. After the `active` field:
```python
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
```

Replace with:
```python
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False)
    candidate_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
```

- [ ] **Step 5: Run model tests to confirm they pass**

```bash
conda run -n ML pytest tests/test_resume_track_model.py -v
```
Expected: all PASS.

### 3b: New API Endpoints

- [ ] **Step 6: Write failing tests for new endpoints**

In `tests/test_suggest_generate_tracks.py` (new file):
```python
"""Tests for suggest-tracks, generate-tracks, and GET tracks endpoints."""
from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from job_agent.main import app
from job_agent.db import SessionLocal, prepare_database
from job_agent.models import Candidate, CandidateSourceFile, ResumeTrack


@pytest.fixture(autouse=True)
def setup_db():
    prepare_database()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def candidate(tmp_path):
    db = SessionLocal()
    try:
        cand = Candidate(
            id=str(uuid4()),
            full_name="Test User",
            email="test@example.com",
        )
        db.add(cand)
        db.commit()
        db.refresh(cand)
        return cand
    finally:
        db.close()


def test_suggest_tracks_returns_empty_on_no_source_files(client, candidate):
    resp = client.post(f"/candidates/{candidate.id}/suggest-tracks")
    assert resp.status_code == 200
    data = resp.json()
    assert "suggested_roles" in data
    assert isinstance(data["suggested_roles"], list)


def test_suggest_tracks_returns_roles_when_llm_succeeds(client, candidate):
    db = SessionLocal()
    try:
        src = CandidateSourceFile(
            id=str(uuid4()),
            candidate_id=candidate.id,
            original_name="cv.txt",
            extracted_text="Data Engineer with Python and SQL experience.",
            mime_type="text/plain",
        )
        db.add(src)
        db.commit()
    finally:
        db.close()

    mock_router = MagicMock()
    mock_router.generate.return_value = {"content": '["Data Engineer", "Analytics Engineer", "ML Engineer", "Data Analyst"]'}
    with patch("job_agent.routers.candidates.LLMRouter", return_value=mock_router):
        resp = client.post(f"/candidates/{candidate.id}/suggest-tracks")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["suggested_roles"]) == 4


def test_suggest_tracks_returns_empty_on_provider_unavailable(client, candidate):
    from job_agent.llm import ProviderUnavailableError
    mock_router = MagicMock()
    mock_router.generate.side_effect = ProviderUnavailableError("down")
    with patch("job_agent.routers.candidates.LLMRouter", return_value=mock_router):
        resp = client.post(f"/candidates/{candidate.id}/suggest-tracks")
    assert resp.status_code == 200
    assert resp.json()["suggested_roles"] == []


def test_suggest_tracks_returns_empty_on_value_error(client, candidate):
    mock_router = MagicMock()
    mock_router.generate.side_effect = ValueError("bad json")
    with patch("job_agent.routers.candidates.LLMRouter", return_value=mock_router):
        resp = client.post(f"/candidates/{candidate.id}/suggest-tracks")
    assert resp.status_code == 200
    assert resp.json()["suggested_roles"] == []


def test_generate_tracks_creates_custom_track(client, candidate):
    mock_router = MagicMock()
    mock_router.generate.return_value = {
        "content": '{"baseline_summary": "ML engineer focused on model deployment.", "target_keywords": ["python", "mlflow", "kubernetes"], "emphasis": {"experiences": ["deployment"], "projects": ["pipelines"], "skills": ["python"]}}'
    }
    with patch("job_agent.routers.candidates.LLMRouter", return_value=mock_router):
        resp = client.post(
            f"/candidates/{candidate.id}/generate-tracks",
            json={"roles": ["Machine Learning Engineer"]},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["generated"] + data["reused_seeds"] >= 1


def test_generate_tracks_reuses_seed_for_matching_role(client, candidate):
    resp = client.post(
        f"/candidates/{candidate.id}/generate-tracks",
        json={"roles": ["data engineer"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["reused_seeds"] >= 1
    assert data["generated"] == 0


def test_get_tracks_returns_list(client):
    resp = client.get("/candidates/any-id/tracks")
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        data = resp.json()
        assert "tracks" in data
        assert "total" in data
```

- [ ] **Step 7: Run tests to confirm they fail**

```bash
conda run -n ML pytest tests/test_suggest_generate_tracks.py -v
```
Expected: 404 / attribute errors — endpoints don't exist.

- [ ] **Step 8: Add the three endpoints to candidates.py**

Update the existing imports in `candidates.py`. The file already has:
```python
from sqlalchemy import func
from job_agent.models import (
    Candidate,
    CandidateIntakeDraft,
    JobPost,
    MasterProfile,
    VerifiedCandidateFact,
)
```

Change them to:
```python
from sqlalchemy import func, select
from job_agent.models import (
    Candidate,
    CandidateIntakeDraft,
    CandidateSourceFile,
    JobPost,
    MasterProfile,
    ResumeTrack,
    VerifiedCandidateFact,
)
```

Then add these three endpoints at the bottom of the router, before any existing `@router.get("/ui/...")` blocks:

```python
@router.post("/candidates/{candidate_id}/suggest-tracks")
async def suggest_tracks(candidate_id: str, db: Session = Depends(get_db)):
    """Read raw extracted_text from uploaded source files and ask the small LLM for 4 role titles."""
    sources = db.scalars(
        select(CandidateSourceFile).where(CandidateSourceFile.candidate_id == candidate_id)
    ).all()
    if not sources:
        return {"suggested_roles": []}

    combined = "\n\n".join(
        (s.extracted_text or "").strip() for s in sources if s.extracted_text
    )
    combined = combined[:6000]
    if not combined:
        return {"suggested_roles": []}

    system_prompt = (
        "You are a career advisor. Given a candidate's CV text, return exactly 4 job role titles "
        "as a JSON array of strings. Example: [\"Data Engineer\", \"Analytics Engineer\", "
        "\"ML Engineer\", \"Data Analyst\"]. Return ONLY the JSON array, no other text."
    )
    user_prompt = f"CV text:\n{combined}"

    try:
        result = LLMRouter(role="small").generate(
            role="small",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
        )
        raw = (result.get("content") or "").strip()
        import json as _json
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start == -1 or end == 0:
            return {"suggested_roles": []}
        roles = _json.loads(raw[start:end])
        if not isinstance(roles, list):
            return {"suggested_roles": []}
        return {"suggested_roles": [str(r) for r in roles if r][:4]}
    except (ProviderUnavailableError, ValueError):
        return {"suggested_roles": []}


@router.post("/candidates/{candidate_id}/generate-tracks")
async def generate_tracks(candidate_id: str, body: dict = Body(...), db: Session = Depends(get_db)):
    """For each role in the request, reuse a matching seed track or generate a custom one via LLM."""
    import json as _json
    import re as _re

    roles = body.get("roles") or []
    if not roles:
        return {"generated": 0, "reused_seeds": 0}

    existing_tracks = db.scalars(select(ResumeTrack)).all()
    existing_slugs = {t.slug for t in existing_tracks}

    generated = 0
    reused_seeds = 0

    for role in roles[:4]:
        role_slug = _re.sub(r"[^a-z0-9]+", "-", role.lower().strip()).strip("-")

        # Check if any existing seed slug contains or fuzzy-matches this role
        matched_seed = None
        role_lower = role.lower()
        for track in existing_tracks:
            if not track.is_custom and (
                role_lower in track.slug.replace("-", " ")
                or role_lower in track.title.lower()
                or track.slug in role_slug
                or any(role_lower in kw for kw in (track.target_keywords or []))
            ):
                matched_seed = track
                break

        if matched_seed:
            if not matched_seed.active:
                matched_seed.active = True
                db.commit()
            reused_seeds += 1
            continue

        # No seed match — generate via LLM
        if role_slug in existing_slugs:
            reused_seeds += 1
            continue

        system_prompt = (
            "You are a career coach. Given a job role title, return a JSON object with exactly "
            "three keys: \"baseline_summary\" (1-2 sentences describing what to emphasize for this role), "
            "\"target_keywords\" (list of 10-15 relevant skill/tool strings), "
            "\"emphasis\" (object with keys \"experiences\", \"projects\", \"skills\", each a list of strings). "
            "Return ONLY the JSON object."
        )
        user_prompt = f"Job role: {role}"

        try:
            result = LLMRouter(role="small").generate(
                role="small",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
            )
            raw = (result.get("content") or "").strip()
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start == -1 or end == 0:
                continue
            track_data = _json.loads(raw[start:end])

            new_track = ResumeTrack(
                slug=role_slug,
                title=role,
                role_family=role_slug.split("-")[0],
                baseline_summary=str(track_data.get("baseline_summary", "")),
                target_keywords=track_data.get("target_keywords") or [],
                emphasis=track_data.get("emphasis") or {},
                is_custom=True,
                candidate_id=candidate_id,
                active=True,
            )
            db.add(new_track)
            db.commit()
            existing_slugs.add(role_slug)
            generated += 1
        except (ProviderUnavailableError, ValueError):
            continue

    return {"generated": generated, "reused_seeds": reused_seeds}


@router.get("/candidates/{candidate_id}/tracks")
async def get_candidate_tracks(candidate_id: str, db: Session = Depends(get_db)):
    """Return all tracks relevant to this candidate (seeds + custom tracks for this candidate)."""
    tracks = db.scalars(
        select(ResumeTrack).where(
            (ResumeTrack.is_custom == False) | (ResumeTrack.candidate_id == candidate_id)  # noqa: E712
        )
    ).all()
    return {
        "tracks": [
            {"slug": t.slug, "title": t.title, "is_custom": t.is_custom}
            for t in tracks
        ],
        "total": len(tracks),
    }
```

- [ ] **Step 9: Run backend tests to confirm they pass**

```bash
conda run -n ML pytest tests/test_suggest_generate_tracks.py -v
```
Expected: all PASS.

- [ ] **Step 10: Run full suite**

```bash
conda run -n ML pytest tests/ -x -q
```
Expected: green.

- [ ] **Step 11: Commit**

```bash
git add job_agent/db.py job_agent/models.py job_agent/routers/candidates.py tests/test_resume_track_model.py tests/test_suggest_generate_tracks.py
git commit -m "feat: LLM-driven role suggestion backend — suggest-tracks, generate-tracks, GET tracks"
```

---

## Task 4: LLM Role Suggestion — Frontend

**Files:**
- Modify: `frontend/templates/partials/onboarding/step_search.html`
- Modify: `frontend/templates/partials/onboarding/done_panel.html`
- Modify: `frontend/static/onboarding/search.js`
- Modify: `frontend/templates/partials/settings/discovery_section.html`

### Changes

**`step_search.html` — add status span and skeleton chips:**

Find the `#suggested-roles` div:
```html
    <div id="suggested-roles" class="hidden rounded-xl border border-indigo-100 bg-indigo-50 px-4 py-3">
      <p class="text-xs font-medium uppercase tracking-wide text-indigo-600">Detected role suggestions</p>
      <div id="suggested-roles-list" class="mt-2 flex flex-wrap gap-2"></div>
    </div>
```

Replace with:
```html
    <div id="suggested-roles" class="hidden rounded-xl border border-indigo-100 bg-indigo-50 px-4 py-3">
      <div class="flex items-center justify-between gap-2">
        <p class="text-xs font-medium uppercase tracking-wide text-indigo-600">Detected role suggestions</p>
        <span id="llm-suggest-status" class="text-xs text-slate-400"></span>
      </div>
      <div id="suggested-roles-list" class="mt-2 flex flex-wrap gap-2">
        <div id="suggest-skeletons" class="hidden flex flex-wrap gap-2">
          <div class="h-7 w-24 rounded-full bg-indigo-100 animate-pulse"></div>
          <div class="h-7 w-32 rounded-full bg-indigo-100 animate-pulse"></div>
          <div class="h-7 w-28 rounded-full bg-indigo-100 animate-pulse"></div>
        </div>
      </div>
    </div>
```

**`done_panel.html` — add tracks-status paragraph:**

Find:
```html
    <p class="text-sm text-slate-600">You can now review jobs, apply interactively, generate drafts, and save verified profile memory.</p>
```

Add below it:
```html
    <p id="tracks-status" class="hidden text-sm text-indigo-600 animate-pulse">Building role tracks…</p>
```

**`search.js` — extend hydrateSearchFocus and rewrite saveSearchFocus:**

Replace the entire contents of `frontend/static/onboarding/search.js` with:
```js
/*
 * Search focus stage.
 *
 * This stage translates the reviewed profile into search roles, one-country
 * targeting, and language preferences used by discovery.
 */

(() => {
  const app = window.OnboardingApp;

  app.hydrateSearchFocus = async function hydrateSearchFocus(force = false) {
    if (!app.state.candidateId || (app.state.searchRecommendationsLoaded && !force)) {
      return;
    }
    try {
      const response = await fetch(`/search/preferences/recommendations?candidate_id=${encodeURIComponent(app.state.candidateId)}`);
      if (!response.ok) {
        return;
      }
      const data = await response.json();
      app.state.languageOptions = Array.isArray(data.language_options) && data.language_options.length
        ? data.language_options
        : app.state.languageOptions;
      app.state.levelOptions = Array.isArray(data.level_options) && data.level_options.length
        ? data.level_options
        : app.state.levelOptions;

      const countriesEl = document.getElementById("search-countries");
      if (countriesEl && !countriesEl.dataset.userEdited) {
        const country = (data.countries || ["Italy"])[0] || "Italy";
        countriesEl.value = country;
      }

      const rolesEl = document.getElementById("target-roles");
      if (rolesEl && !rolesEl.dataset.userEdited && (data.suggested_roles || []).length) {
        rolesEl.value = data.suggested_roles.slice(0, 4).join("\n");
      }
      if (!app.state.languagesTouched) {
        app.renderOnboardingLanguageRows(data.selected_languages || [], {markTouched: false});
      }

      app.renderSuggestedRoles(data.suggested_roles || []);
      app.renderRecommendedSources(data.recommended_sources || []);
      app.state.searchRecommendationsLoaded = true;
    } catch (_error) {
      app.renderRecommendedSources([]);
    }

    // LLM-driven role suggestions (runs after rule-based suggestions are shown)
    if (!app.state.candidateId) {
      return;
    }
    const suggestSkeletons = document.getElementById("suggest-skeletons");
    const suggestStatus = document.getElementById("llm-suggest-status");
    const suggestedPanel = document.getElementById("suggested-roles");
    if (suggestSkeletons) {
      suggestSkeletons.classList.remove("hidden");
    }
    if (suggestedPanel) {
      suggestedPanel.classList.remove("hidden");
    }
    if (suggestStatus) {
      suggestStatus.textContent = "Refining with AI…";
    }
    try {
      const suggestResp = await fetch(`/candidates/${encodeURIComponent(app.state.candidateId)}/suggest-tracks`, {
        method: "POST",
      });
      if (suggestResp.ok) {
        const suggestData = await suggestResp.json();
        if (Array.isArray(suggestData.suggested_roles) && suggestData.suggested_roles.length) {
          app.renderSuggestedRoles(suggestData.suggested_roles);
          const rolesEl = document.getElementById("target-roles");
          if (rolesEl && !rolesEl.dataset.userEdited) {
            rolesEl.value = suggestData.suggested_roles.slice(0, 4).join("\n");
          }
        }
      }
    } catch (_error) {
      // Provider down — rule-based suggestions remain visible
    } finally {
      if (suggestSkeletons) {
        suggestSkeletons.classList.add("hidden");
      }
      if (suggestStatus) {
        suggestStatus.textContent = "";
      }
    }
  };

  app.saveSearchFocus = async function saveSearchFocus() {
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
    const country = countries[0] || "Italy";
    const languages = app.readOnboardingLanguageRows();
    if (!roles.length) {
      app.setStatus("Add at least one target role.", true);
      return;
    }
    const payload = {
      jobspy_discover_queries: roles,
      job_search_countries: [country],
      jobspy_discover_location: country,
      target_job_seniority: document.getElementById("target-seniority").value,
      job_search_languages: languages,
    };
    const response = await fetch("/settings/save", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      app.setStatus(await response.text(), true);
      return;
    }

    // Show done panel first, then generate tracks in the background
    document.querySelectorAll(".setup-step").forEach((section) => section.classList.add("hidden"));
    document.getElementById("done-panel").classList.remove("hidden");
    app.setStatus("");

    if (app.state.candidateId && roles.length) {
      const tracksStatus = document.getElementById("tracks-status");
      if (tracksStatus) {
        tracksStatus.classList.remove("hidden");
      }
      try {
        await fetch(`/candidates/${encodeURIComponent(app.state.candidateId)}/generate-tracks`, {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({roles}),
        });
      } catch (_error) {
        // Silent — tracks can be regenerated from settings
      } finally {
        if (tracksStatus) {
          tracksStatus.textContent = "Role tracks ready.";
          window.setTimeout(() => tracksStatus.classList.add("hidden"), 3000);
        }
      }
    }
  };

  window.saveSearchFocus = app.saveSearchFocus;
})();
```

**`discovery_section.html` — append Role Tracks subsection:**

At the end of the file, immediately before the closing `</details>` tag, add:

```html
  <section class="rounded-2xl border border-[var(--border)] bg-[rgba(15,27,46,0.4)] px-4 py-4 mt-6">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <p class="field-label">Role Tracks</p>
        <p class="mt-1 text-sm text-[var(--text-muted)]">
          Custom tracks built from your search roles. Regenerate after changing your desired roles above.
        </p>
      </div>
      <button
        type="button"
        hx-post="/candidates/{{ ui_candidate_id }}/generate-tracks"
        hx-vals='js:{"roles": (document.getElementById("jobspy_discover_queries")?.value || "").split("\n").filter(r => r.trim()).slice(0, 4)}'
        hx-swap="none"
        hx-on::after-request="if(event.detail.successful) { window.showToast('Role tracks updated', 'success'); } else { window.showToast('Track generation failed', 'error'); }"
        class="app-button app-button--sm"
      >Regenerate Role Tracks</button>
    </div>
  </section>
```

Note: `ui_candidate_id` is already available in the settings page context (from `_ui_context()`). If the candidate is not configured, the button will POST to `/candidates/None/generate-tracks` which the endpoint handles by returning empty. No error shown to the user.

- [ ] **Step 1: Write failing tests for frontend changes**

In `tests/test_role_suggestion_frontend.py` (new file):
```python
"""Verify role suggestion frontend wiring is present in templates and JS."""
from pathlib import Path


def test_suggest_skeletons_in_step_search():
    src = Path("frontend/templates/partials/onboarding/step_search.html").read_text()
    assert 'id="suggest-skeletons"' in src
    assert "animate-pulse" in src


def test_llm_suggest_status_in_step_search():
    src = Path("frontend/templates/partials/onboarding/step_search.html").read_text()
    assert 'id="llm-suggest-status"' in src


def test_tracks_status_in_done_panel():
    src = Path("frontend/templates/partials/onboarding/done_panel.html").read_text()
    assert 'id="tracks-status"' in src
    assert "Building role tracks" in src


def test_search_js_calls_suggest_tracks():
    src = Path("frontend/static/onboarding/search.js").read_text()
    assert "suggest-tracks" in src


def test_search_js_calls_generate_tracks():
    src = Path("frontend/static/onboarding/search.js").read_text()
    assert "generate-tracks" in src


def test_search_js_hides_skeleton_in_finally():
    src = Path("frontend/static/onboarding/search.js").read_text()
    assert "finally" in src
    assert "suggest-skeletons" in src


def test_discovery_section_has_regenerate_button():
    src = Path("frontend/templates/partials/settings/discovery_section.html").read_text()
    assert "generate-tracks" in src
    assert "Regenerate Role Tracks" in src
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
conda run -n ML pytest tests/test_role_suggestion_frontend.py -v
```
Expected: all FAIL.

- [ ] **Step 3: Apply all four file changes from the Changes section above**

- [ ] **Step 4: Run tests to confirm they pass**

```bash
conda run -n ML pytest tests/test_role_suggestion_frontend.py -v
```
Expected: all PASS.

- [ ] **Step 5: Run full suite**

```bash
conda run -n ML pytest tests/ -x -q
```
Expected: green.

- [ ] **Step 6: Commit**

```bash
git add frontend/templates/partials/onboarding/step_search.html \
        frontend/templates/partials/onboarding/done_panel.html \
        frontend/static/onboarding/search.js \
        frontend/templates/partials/settings/discovery_section.html \
        tests/test_role_suggestion_frontend.py
git commit -m "feat: LLM role suggestion wired into onboarding step 6 and settings"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] Bug fix — Application Snapshot & Readiness double-fetch → Task 1
- [x] Discovery panel skeleton (priority) → Task 2a
- [x] Onboarding intake skeleton (secondary) → Task 2b
- [x] `is_custom` / `candidate_id` columns → Task 3 Step 3–4
- [x] `POST /candidates/{id}/suggest-tracks` → Task 3 Step 8
- [x] `POST /candidates/{id}/generate-tracks` → Task 3 Step 8 (skips duplicate seeds, synchronous)
- [x] `GET /candidates/{id}/tracks` → Task 3 Step 8
- [x] `suggest-tracks` reads `extracted_text` from `CandidateSourceFile` (not MatchProfile) → Task 3 Step 8
- [x] Onboarding step 6 — skeleton chips + LLM suggest call → Task 4
- [x] `saveSearchFocus` calls `generate-tracks` after settings save → Task 4
- [x] Settings "Regenerate Role Tracks" button → Task 4
- [x] Both `ProviderUnavailableError` and `ValueError` caught on all LLM calls → Task 3 Step 8
- [x] No Alembic — `_safe_add_column` only → Task 3 Step 3
- [x] No new venvs — all commands use `conda run -n ML` → throughout

**Type consistency:**
- `CandidateSourceFile.extracted_text` — confirmed field at models.py:111; `original_name` (not `original_filename`), `mime_type` (not `content_type`)
- `ResumeTrack.is_custom` / `ResumeTrack.candidate_id` — defined in Task 3 Step 4, used in Task 3 Step 8 endpoint
- `LLMRouter(role="small").generate(role=..., system_prompt=..., user_prompt=..., temperature=...)` — confirmed signature from llm.py
- `TemplateResponse(request=request, name=..., context=...)` — no new TemplateResponse calls added; all new endpoints return JSON dicts
