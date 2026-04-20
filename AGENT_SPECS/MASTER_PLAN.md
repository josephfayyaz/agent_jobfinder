# Master Implementation Plan

**Updated:** 2026-04-21  
**Status:** 292 tests · All F/G phases DONE · UI1/UI2/UI3 DONE

---

## Current State

| Metric | Value |
|--------|-------|
| Tests | 292 passing · 0 failing |
| Endpoints | 88+ |
| Templates | 11 (+ draft_detail, analytics, companies) |
| ORM Models | 28 |
| Ruff | Clean |
| Phases done | A1, B0–B4, C1–C2, D, E1, E2, F1, F2, F3, F5+G5, G1, G6, start_apply, UI1, UI2, UI3 |

Services in `job_agent/services/`: ats_scanner · bullet_clarify · career_scanner · company_resolver · compliance_matrix · cover_letter · documents · experience_selection · exporters · fact_ingestion · fact_sheet_json · fact_sheet_renderer · file_extraction · gmail · intake · job_fetcher · jobspy_service · matching · prompts · rejection_analytics · rejection_prediction · resource_loader · thesis_outreach · workflows

---

## Bug Tracker

| ID | Severity | Status | What | Spec |
|----|----------|--------|------|------|
| B1 | Critical | ✅ DONE (E1) | `_load_context()` hardcoded MasterProfile — fixed via `DEFAULT_CANDIDATE_ID` | — |
| B2 | Critical | ✅ DONE (E2) | JobSpy manual-only — fixed via worker loop + interval config | — |
| B3 | Medium | ✅ DONE | `DEFAULT_CANDIDATE_ID` startup warning; BulletClarify ValueError catch; JobSpy default queries | `bug_B3_startup_config_validation.md` |
| B4 | Architectural | ✅ DONE | G1/G6 catch `(ProviderUnavailableError, ValueError)` — no 500 on malformed JSON | Patched in G1/G6 |
| B5 | Medium | ✅ DONE | `check_velocity_spikes` no time filter — re-alerted historical spikes every cycle | `bug_G5_velocity_spike_time_filter.md` |

---

## Execution Order for Codex (Priority)

**All F/G phases complete.** Next work is the UI roadmap below.

---

## Phase F — CV Workflow Improvements

| Phase | Spec | What | Status |
|-------|------|------|--------|
| start_apply | `prompt_start_apply.txt` | Standalone CLI: paste job info → score → questions → CV file | ✅ DONE |
| F1 | archived | Human-in-loop bullet rewrite: `BulletClarifyService`, `BulletClarification` model | ✅ DONE |
| F2 | `prompt_F2_keyword_extraction.txt` | ATS keyword extraction in `_generate_draft()`, stored in `review_feedback` | ✅ DONE |
| F3 | `prompt_F3_rejection_analytics.txt` | Pure-Python rejection analytics: funnel, score buckets, skill gaps, weekly pipeline | ✅ DONE |

---

## Phase G — Discovery & Intelligence

| Phase | Spec | What | Depends on | Status |
|-------|------|------|------------|--------|
| F5+G5 | `prompt_F5_G5_ats_discovery_velocity.txt` | Zero-token ATS JSON APIs (Greenhouse/Lever/Ashby) + velocity spike alerting | — | ✅ DONE |
| G1 | `prompt_G1_compliance_matrix.txt` | Requirement-by-requirement JD coverage map per draft | F2 | ✅ DONE |
| G6 | `prompt_G6_rejection_prediction.txt` | Pre-application rejection risk prediction stored in JSONB | — | ✅ DONE |

---

## Discovery Strategy (live)

Sources in priority order — already implemented or specced:
1. **LinkedIn** — via JobSpy (`USE_JOBSPY=true`, interval-scheduled in worker)
2. **Direct ATS APIs** — Greenhouse / Lever / Ashby (F5: zero LLM tokens, structured JSON)
3. **HTML career page scan** — existing `CareerPageScanner` for non-ATS companies
4. **Gmail notifications** — `GmailService` for recruiter alerts

Users add companies via `POST /career-pages`. F5 extends with `ats_type` + `ats_slug`.

---

## UI Roadmap

Web UI inside the existing Jinja2 app — HTMX-enhanced, no React.
Pipeline/Kanban already exists at `/ui/applications`. Gaps below.

| Phase | Spec | Route | What | Status |
|-------|------|-------|------|--------|
| UI1 | `prompt_UI1_draft_viewer.txt` | `/ui/drafts/{id}` | Full draft content, compliance matrix badge, approve/reject | ✅ DONE |
| UI2 | `prompt_UI2_analytics_dashboard.txt` | `/ui/analytics` | Funnel, score buckets, skill gaps, weekly activity, velocity | ✅ DONE |
| UI3 | `prompt_UI3_company_watchlist.txt` | `/ui/companies` | Watched companies, ATS type, toggle active, add form | ✅ DONE |

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
