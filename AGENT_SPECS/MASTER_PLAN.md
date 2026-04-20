# Master Implementation Plan

**Updated:** 2026-04-19  
**Status:** 231 tests · F1 DONE · B3 bug-fix specced · start_apply URGENT

---

## Current State

| Metric | Value |
|--------|-------|
| Tests | 231 passing · 0 failing |
| Endpoints | 82+ (main.py 1788 lines) |
| ORM Models | 28 |
| Ruff | Clean |
| Phases done | A1, B0–B4, C1–C2, D, E1, E2, F1 |

Services in `job_agent/services/`: bullet_clarify · career_scanner · company_resolver · cover_letter · documents · experience_selection · exporters · fact_ingestion · fact_sheet_json · fact_sheet_renderer · file_extraction · gmail · intake · job_fetcher · jobspy_service · matching · prompts · resource_loader · thesis_outreach · workflows

---

## Bug Tracker

| ID | Severity | Status | What | Spec |
|----|----------|--------|------|------|
| B1 | Critical | ✅ DONE (E1) | `_load_context()` hardcoded MasterProfile — fixed via `DEFAULT_CANDIDATE_ID` | — |
| B2 | Critical | ✅ DONE (E2) | JobSpy manual-only — fixed via worker loop + interval config | — |
| B3 | Medium | SPECCED | `DEFAULT_CANDIDATE_ID` no startup warning; BulletClarify missing ValueError catch; JobSpy default queries wrong | `bug_B3_startup_config_validation.md` |
| B4 | Architectural | MITIGATED in specs | G1/G6 specs now catch `(ProviderUnavailableError, ValueError)` — no 500 on malformed JSON | Patched in G1/G6 specs |

---

## Execution Order for Codex (Priority)

```
1. bug_B3_startup_config_validation.md     ← fix before anything else (small, ~4 tests)
2. prompt_start_apply.txt                  ← URGENT: user needs to apply NOW
3. prompt_F2_keyword_extraction.txt        ← needed by G1; enhances draft quality
4. prompt_F3_rejection_analytics.txt       ← pure Python, no LLM, simple
5. prompt_F5_G5_ats_discovery_velocity.txt ← ATS APIs + velocity alerting
6. prompt_G1_compliance_matrix.txt         ← after F2 so keywords are available
7. prompt_G6_rejection_prediction.txt      ← after G1 (architectural clarity)
```

**Dependency rules:**
- G1 uses `ranked_keywords` from `review_feedback` populated by F2. Run F2 first.
- G6 is independent but logically after G1.
- B3 should always go first — it fixes BulletClarify (F1) graceful error handling.

---

## Immediate Priority — start_apply CLI (URGENT)

**Spec:** `AGENT_SPECS/codex_prompts/prompt_start_apply.txt`

Standalone CLI tool — no FastAPI server, no DB, no Docker required.  
User pastes messy job info → score → 3 questions → tailored CV file.  
The user is losing application opportunities every day this is not built.

Outputs:
- `start_apply/output/cv_<timestamp>.txt` — formatted CV text
- (Future: compile `.tex` → `.pdf` using `xelatex` if available)

---

## Phase F — CV Workflow Improvements

| Phase | Spec | What | Status |
|-------|------|------|--------|
| F1 | archived | Human-in-loop bullet rewrite: `BulletClarifyService`, `BulletClarification` model | ✅ DONE |
| F2 | `prompt_F2_keyword_extraction.txt` | ATS keyword extraction in `_generate_draft()`, stored in `review_feedback` | pending |
| F3 | `prompt_F3_rejection_analytics.txt` | Pure-Python rejection analytics: funnel, score buckets, skill gaps, weekly pipeline | pending |

---

## Phase G — Discovery & Intelligence

| Phase | Spec | What | Depends on | Status |
|-------|------|------|------------|--------|
| F5+G5 | `prompt_F5_G5_ats_discovery_velocity.txt` | Zero-token ATS JSON APIs (Greenhouse/Lever/Ashby) + velocity spike alerting | — | pending |
| G1 | `prompt_G1_compliance_matrix.txt` | Requirement-by-requirement JD coverage map per draft | F2 | pending |
| G6 | `prompt_G6_rejection_prediction.txt` | Pre-application rejection risk prediction stored in JSONB | — | pending |

---

## Discovery Strategy (live)

Sources in priority order — already implemented or specced:
1. **LinkedIn** — via JobSpy (`USE_JOBSPY=true`, interval-scheduled in worker)
2. **Direct ATS APIs** — Greenhouse / Lever / Ashby (F5: zero LLM tokens, structured JSON)
3. **HTML career page scan** — existing `CareerPageScanner` for non-ATS companies
4. **Gmail notifications** — `GmailService` for recruiter alerts

Users add companies via `POST /career-pages`. F5 extends with `ats_type` + `ats_slug`.

---

## UI Roadmap (after F/G phases stable)

Web UI inside the existing Jinja2 app — HTMX-enhanced, no React:

| Screen | Route | What |
|--------|-------|------|
| Pipeline table | `/ui/pipeline` | All jobs, filter by status/score/track, sort, bulk actions |
| Draft viewer | `/ui/drafts/{id}` | Full draft content, compliance matrix, clarify button |
| Analytics dashboard | `/ui/analytics` | Funnel, score histogram, conversion rates, velocity chart |
| Company watchlist | `/ui/companies` | Add/remove watched companies, ATS type, last scan |

Not in any current Codex spec — implement after G6 is done.

---

## Skipped / Deferred

| Feature | Reason |
|---------|--------|
| G2 (salary intelligence) | Not relevant at junior level in Italian market |
| G7 (multi-persona A/B) | Risks lowering acceptance rate; revisit Q3 2026 |
| F6 (interview prep) | Out of scope for now |
| TUI dashboard | Replaced by web UI plan |

---

## Conventions Codex Must Never Break

- **No Alembic.** Schema = `prepare_database()` in `db.py`.
- **Always conda ML.** Never create venvs.
- **Starlette TemplateResponse:** keyword args only.
- **No shared DB sessions across threads.**
- **LLM error handling:** ALWAYS catch `(ProviderUnavailableError, ValueError)` — not just `ProviderUnavailableError`. `ValueError` is raised by `_extract_json()` on malformed JSON.
- **Real ORM field names:** `role_title`, `verified_core_facts`, `tools_and_tech`, `project_name`, `short_resume_line`, `review_feedback`.
- **After every phase:** run `pytest --tb=short -q`, `ruff check`, write report to `AGENT_SPECS/completed/`, append to `completed_agent_specs.txt`.
