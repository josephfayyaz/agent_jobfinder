# Job Agent — Three Improvements Design Spec
**Date:** 2026-05-03  
**Status:** Approved

---

## 1. Bug Fix: Fetch-once for Application Snapshot & Readiness

### Problem
Both toggle buttons (Application Snapshot and Readiness) carry both an `onclick` handler (toggle row visibility) and an `hx-get` (fire HTMX request). Every click — including to *close* — fires an LLM call to the server, wasting tokens and causing confusing double-loads.

### Solution
Add Alpine.js per-group state on the `<tbody id="job-group-*">` in `job_group.html`:

```
x-data="{ snapLoaded: false, readyLoaded: false }"
```

Replace the `onclick` + always-on `hx-get` buttons with Alpine `@click` handlers:
- If `snapLoaded` is false: show row + call `htmx.ajax(...)` → on HTMX success set `snapLoaded = true`
- If `snapLoaded` is true: just toggle row visibility, no re-fetch

When a queue-state action (Shortlist/Save/Pass) replaces the entire `<tbody>` via outerHTML swap, Alpine state resets automatically because the DOM node is destroyed and recreated.

### Files
- `frontend/templates/partials/job_group.html` — add `x-data`
- `frontend/templates/partials/job_row.html` — replace Snapshot and Readiness button logic

---

## 2. Skeleton Loaders

### 2a. Discovery Panel (Priority)

**Problem:** During a 30–60 second discovery scan, the 14 summary count boxes show meaningless zeros and the queue table below is stale.

**Solution — Count box skeletons:**  
In `jobs.js`, modify `renderTask()`. When `!discoveryTerminal(task)` (scan still running), set `els.summary.innerHTML` to 14 animate-pulse skeleton boxes instead of real data:
```html
<div class="h-9 rounded-xl bg-slate-100 animate-pulse"></div>
```
When the task is terminal, render the real count rows as before.

**Solution — Queue table skeleton:**  
When a scan starts (`createDiscoveryController` fires), inject a `#queue-skeleton` section below `#job-discovery-panel` containing 4 pulsing job-row skeletons (columns: company bar, role bar, score circle, badge bar, actions bar — all gray animate-pulse blocks). When scan completes and "Refresh Queue" appears, the skeleton hides. Clicking Refresh Queue removes the skeleton and triggers HTMX reload.

### 2b. Onboarding Intake (Secondary)

**Problem:** After clicking Analyze, the user sees only "Analysing your profile…" for 20–40 seconds with no visual indication of what's being built.

**Solution:**  
In `step_facts.html`, add a hidden `#intake-skeleton` block containing 3 pulsing profile field placeholders (name bar, two experience blocks, skills bar). In `intake.js`, show this block when `intake/start` is fired and hide it when the response arrives (success or error).

### Files
- `frontend/static/jobs.js` — `renderTask()` + scan-start/scan-end skeleton injection
- `frontend/templates/partials/onboarding/step_facts.html` — add `#intake-skeleton`
- `frontend/static/onboarding/intake.js` — toggle skeleton visibility

---

## 3. LLM-Driven Role Suggestion

### 3a. Data Model Changes (no Alembic)

Add two columns to `resume_tracks` table via `prepare_database()` in `db.py`:
```sql
ALTER TABLE resume_tracks ADD COLUMN IF NOT EXISTS is_custom BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE resume_tracks ADD COLUMN IF NOT EXISTS candidate_id TEXT REFERENCES candidates(id) ON DELETE SET NULL;
```

Add fields to `ResumeTrack` model in `models.py`:
```python
is_custom: Mapped[bool] = mapped_column(Boolean, default=False)
candidate_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("candidates.id", ondelete="SET NULL"), nullable=True)
```

### 3b. Backend — `POST /candidates/{id}/suggest-tracks`

Located in `candidates.py`. Flow:
1. Load all `CandidateSourceFile` rows for the candidate, concatenate `extracted_text` (raw uploaded CV text, per user preference)
2. Truncate to ~6000 chars to stay within context
3. Build a prompt asking LLM to return exactly 4 job role titles as a JSON array
4. Call `LLMRouter(role="small").generate(...)` — fast 9b model
5. Parse JSON array from response
6. Return `{"suggested_roles": ["Data Engineer", ...]}`
7. Catch both `ProviderUnavailableError` and `ValueError` — return empty list gracefully, do not 500

### 3c. Backend — `POST /candidates/{id}/generate-tracks`

Located in `candidates.py`. Accepts `{"roles": ["Data Engineer", ...]}`. Flow:
1. For each role:
   a. Compute a slug from the role name (`role.lower().replace(" ", "-")`)
   b. Check if any existing static seed track slug contains or fuzzy-matches this role — if yes, skip LLM generation, mark that track active (no duplicate)
   c. If no match: call LLM to generate `baseline_summary` (1–2 sentences), `target_keywords` (list of 10–15 strings), `emphasis` dict (`{experiences, projects, skills}`)
   d. Upsert `ResumeTrack` row with `is_custom=True`, `candidate_id=candidate_id`
2. Return `{"generated": N, "reused_seeds": M}`
3. Catch both LLM exception types — partial success is OK, report what was generated

**Synchronous** — caller waits for all 4 LLM calls. Typical duration ~20s. Done screen shown after completion.

### 3d. Frontend — Onboarding Step 6 Enhancement

In `onboarding/search.js`, extend `hydrateSearchFocus()`:
1. After existing `/search/preferences/recommendations` call succeeds, fire `POST /candidates/{id}/suggest-tracks`
2. While that request is in-flight, show skeleton chips in `#suggested-roles-list` (3 animate-pulse gray bars)
3. On success, call `app.renderSuggestedRoles(data.suggested_roles)` — replaces rule-based suggestions with LLM suggestions
4. On failure (provider down), fall back to existing rule-based suggestions silently

In `saveSearchFocus()`:
1. Save settings (as now)
2. Then call `POST /candidates/{id}/generate-tracks` with the confirmed roles
3. Show "Building role tracks…" status on the done panel during the wait
4. On completion show "Setup complete" — tracks ready

### 3e. Settings — Regenerate Tracks

In `partials/settings/discovery_section.html`, add a "Role Tracks" subsection:
- Shows count of current custom tracks (from a new `GET /candidates/{id}/tracks` endpoint)
- A **Regenerate Role Tracks** button that POSTs to `generate-tracks` with current `jobspy_discover_queries` roles
- HTMX `hx-post`, `hx-swap="none"`, `hx-on::after-request="if(event.detail.successful) showToast('Role tracks updated', 'success')"`

New endpoint `GET /candidates/{id}/tracks` returns:
```json
{"tracks": [{"slug": "...", "title": "...", "is_custom": true}], "total": 4}
```

---

## Accepted Recommendations
1. Track generation is **synchronous** in onboarding — user waits on done screen while 4 tracks generate
2. `generate-tracks` skips LLM for roles that match existing static seed track slugs — reuses seed, no duplicate
3. `suggest-tracks` reads raw `extracted_text` from `CandidateSourceFile` (per user preference) — cleaned MatchProfile summary intentionally NOT used; to be revisited after testing

## Out of Scope
- PDF upload bug fix (deferred by user)
- Dynamic track re-scoring of existing jobs (separate task)
- Sibling row bug (already fixed in a prior commit)
