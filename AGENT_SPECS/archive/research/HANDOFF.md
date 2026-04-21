# Session Handoff

**Date:** 2026-04-15  
**Status:** System fully operational. Two Codex tasks remain to close all known gaps.

---

## What Is Done

All phases complete. 213 tests passing. Ruff clean.

| Phase | What Was Built |
|-------|---------------|
| A1 | Role-adaptive CV writer (junior/mid/senior modes) |
| B0–B3 | Fact sheet JSON schema, ingestion, renderer, intake flow |
| B4 | Reviewer: comp sanity check + legitimacy signals |
| C1 | Company URL resolver + auto-resolve on job creation |
| C2 | Parallel career page scanner (ThreadPoolExecutor) |
| D | FastAPI lifespan, seed tests, parallel-worker test |
| hotfix | Onboarding intake: 500 → 503 on cold LM Studio model |

UI pages all working: `/dashboard`, `/ui/applications`, `/ui/thesis`, `/ui/onboarding`, `/drafts`.

---

## Two Tasks Left for Codex

### E1 — CV Workflow + Candidate Unification  
**File:** `AGENT_SPECS/codex_prompts/prompt_E1_candidate_unification.txt`  
**Why:** The multi-candidate `Candidate` model (Phase B1) is built but never used in the CV writer. `_load_context()` in `workflows.py` hardcodes `MasterProfile(id=1)`. This phase wires `DEFAULT_CANDIDATE_ID` → Candidate facts into the writer while keeping the legacy `MasterProfile` fallback intact.  
**Scope:** ~80 lines changed in `workflows.py`. 4 new tests in `tests/test_candidate_workflow.py`.

### E2 — JobSpy Scheduled Discovery  
**File:** `AGENT_SPECS/codex_prompts/prompt_E2_jobspy_scheduler.txt`  
**Why:** `POST /jobs/discover` works but must be called manually. The worker already runs Gmail sync and career scans on intervals. This adds the same pattern for JobSpy: `JOBSPY_DISCOVER_INTERVAL_HOURS` (default 6) + `JOBSPY_DISCOVER_QUERIES` (default 5 queries).  
**Scope:** ~30 lines in `worker.py` + 3 new config fields. 6 new tests in `tests/test_jobspy_scheduler.py`.

---

## How to Run Each Task

1. Copy the full content of the `.txt` prompt file
2. Paste it into Codex
3. Codex implements, runs tests + ruff, writes `AGENT_SPECS/completed/phase_EX_report.md`
4. Paste the report back to Claude Code for review

**Recommended order:** E1 first (more impactful), then E2.

---

## After Both Tasks Are Done

The system will be feature-complete. Final steps:

1. **End-to-end test with real LM Studio:**
   - Set `DEFAULT_CANDIDATE_ID` to a real Candidate ID in `.env`
   - Run onboarding at `http://localhost:8000/ui/onboarding`
   - Generate a CV for a real job
   - Confirm PDF is produced and score ≥ 60

2. **Activate JobSpy:**
   - Set `USE_JOBSPY=true` in `.env`
   - Set `JOBSPY_DISCOVER_INTERVAL_HOURS=6`
   - Restart the worker — it will auto-discover jobs every 6 hours

3. **Optionally activate Claude final review:**
   - Set `ANTHROPIC_API_KEY=sk-ant-...` and `USE_CLAUDE_FINAL_REVIEW=true`
   - Run CV workflow with `force_cloud_review=true` for top-priority jobs

4. **Re-ingest fact sheet** if `master_fact_sheet.txt` has been updated:
   ```bash
   FACT_PATH="/Users/youseffayyaz/Polito/Resume-CV/fact_sheet/master_fact_sheet.txt"
   jq -Rs --arg p "$FACT_PATH" '{source_path:$p,content:.}' "$FACT_PATH" \
     | curl -sX POST localhost:8000/fact-sources/ingest -H 'Content-Type: application/json' -d @-
   ```

---

## Critical Conventions (Do Not Break)

- **No Alembic.** Schema only via `prepare_database()` in `db.py`.
- **Always conda ML.** `conda activate ML`. Never create venvs.
- **Starlette 1.0.0 TemplateResponse:** must use keyword args `(request=request, name="x.html", context={...})`.
- **No shared DB sessions across threads.** Each `ThreadPoolExecutor` worker gets its own `SessionLocal()`.
- **Real ORM field names:** `ExperienceFact.role_title`, `.verified_core_facts`, `.tools_and_tech`; `ProjectFact.project_name`, `.short_resume_line`; `ResumeDraft.review_feedback` (not `.review_notes`).
- **Graphify rebuild** after any code change:
  ```bash
  /Users/youseffayyaz/miniforge3/envs/ML/bin/python -c \
    "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"
  ```

---

## Key Files to Know

```
job_agent/main.py              — 82 endpoints
job_agent/models.py            — 28 ORM models
job_agent/db.py                — prepare_database() — all schema changes go here
job_agent/services/workflows.py — CVWorkflowService — E1 target
job_agent/worker.py            — background loop — E2 target
job_agent/config.py            — all settings
job_agent/resources/fact_sheet/fact_sheet_schema.json — canonical schema
AGENT_SPECS/codex_prompts/     — Codex prompt files
AGENT_SPECS/completed/         — Codex completion reports
completed_agent_specs.txt      — completion log
```
