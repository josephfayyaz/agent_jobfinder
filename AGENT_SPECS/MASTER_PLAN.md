# Master Implementation Plan

**Updated:** 2026-04-22  
**Status:** 335 tests · All F/G/UI/UX phases DONE · I-phase specs written (I1–I10)

---

## Current State

| Metric | Value |
|--------|-------|
| Tests | 335 passing · 0 failing |
| Endpoints | 90+ |
| Templates | 11+ |
| ORM Models | 28 |
| Ruff | Clean |
| Phases done | A1, B0–B4, C1–C2, D, E1, E2, F1, F2, F3, F5+G5, G1, G6, start_apply, UI1, UI2, UI3, UX1–UX5 |
| Next phases | I1–I10 (specs in `AGENT_SPECS/codex_prompts/`) |

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

**All F/G/UI/UX phases complete.** Next: I-phases (polish + first-run UX).

### I-Phase Order (send to Codex in this sequence)

| Step | Spec | What | Notes |
|------|------|------|-------|
| 1 | `prompt_I3_sqlite_only.txt` | SQLite-ONLY DB — delete PostgreSQL path entirely, absolute path, WAL mode | Do first — changes DB foundation |
| 2a | `prompt_I2_seed_italy_companies.txt` | 50 Italy tech companies seed + 5-role limit | After I3 (needs DB) |
| 2b | `prompt_I6_first_run_installer.txt` | Package auto-install on first run | Parallel with I2 |
| 3a | `prompt_I1_hitl_bullet_rewrite_ui.txt` | HITL bullet rewrite in web UI | After I3 |
| 3b | `prompt_I4_cv_output_folder.txt` | CV output folder + Company/Date naming | Parallel with I1 |
| 3c | `prompt_I5_gmail_setup_wizard.txt` | Gmail web setup wizard in settings | Parallel with I1 |
| 3d | `prompt_I7_web_apply_flow.txt` | Web interactive apply: paste JD → score → questions → draft | Parallel with I1 |
| 4a | `prompt_I8_market_skill_gap.txt` | Market Skill Gap Dashboard in `/ui/analytics` | After I3 |
| 4b | `prompt_I9_hiring_velocity.txt` | ⚡ Hiring velocity badge on `/ui/companies` | After I3 |
| 4c | `prompt_I10_role_readiness_map.txt` | Role Readiness Map on job detail + draft detail | After I3 |

See `AGENT_SPECS/PRODUCT_ROADMAP.md` for full context.

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

## UX Roadmap (Public-Readiness + CLI)

Web UI exists. These phases make the system usable by a non-expert without editing config files.

| Phase | Spec | Route/Command | What | Status |
|-------|------|---------------|------|--------|
| UX1 | `prompt_UX1_settings_persistence.txt` | `/settings/save`, `/settings/reload` | YAML user config layer over `.env` | ✅ DONE |
| UX2 | `prompt_UX2_onboarding_wizard.txt` | `python -m job_agent.onboard` | 6-step guided setup, model detection, fact sheet ingest | ✅ DONE |
| UX3 | `prompt_UX3_unified_entry.txt` | `python -m job_agent.cli start`, `run.sh` | Unified entry: boots DB+API+worker, opens browser | ✅ DONE |
| UX4 | `prompt_UX4_cli_commands.txt` | `job-agent apply/companies/settings` | Full CLI suite via click+rich | ✅ DONE |
| UX5 | `prompt_UX5_settings_web_ui.txt` | `/ui/settings` | Settings web editor: provider switcher, model dropdowns | ✅ DONE |

---

## I-Phase Roadmap (Polish + First-Run UX)

These phases make the system usable on a brand-new machine with zero manual config.

| Phase | Spec | What | Status |
|-------|------|------|--------|
| I1 | `prompt_I1_hitl_bullet_rewrite_ui.txt` | HITL bullet rewrite buttons in draft_detail.html; `GET /drafts/{id}/clarifications`; `POST /drafts/clarifications/{id}/accept` | Spec ready |
| I2 | `prompt_I2_seed_italy_companies.txt` | 50 Italy tech companies seeded on startup (idempotent); 5-role discovery limit | Spec ready |
| I3 | `prompt_I3_sqlite_only.txt` | SQLite-ONLY (Option A): delete PostgreSQL path, absolute DB path, WAL, move @compiles to db.py, rewrite prepare_database() for SQLite syntax | Spec ready (revised) |
| I4 | `prompt_I4_cv_output_folder.txt` | `artifacts_dir` setting; Company_Date_DraftID[:8] filename convention; onboarding step | Spec ready |
| I5 | `prompt_I5_gmail_setup_wizard.txt` | Gmail web setup wizard in settings; IMAP test endpoint; password masked | Spec ready |
| I6 | `prompt_I6_first_run_installer.txt` | `preflight.py` auto-installs missing packages; clear error if offline; never silent fail | Spec ready |
| I7 | `prompt_I7_web_apply_flow.txt` | Web interactive apply: `/ui/apply` — paste JD → score → 0–3 questions → generate draft (mirrors start_apply CLI) | Spec ready |
| I8 | `prompt_I8_market_skill_gap.txt` | Market Skill Gap Dashboard: aggregate missing ATS keywords across applied drafts; bar chart in `/ui/analytics` | Spec ready |
| I9 | `prompt_I9_hiring_velocity.txt` | Hiring Velocity Signal: ⚡ badge on companies that posted in 2+ consecutive scans; `/career-pages/{id}/velocity` + bulk endpoint | Spec ready |
| I10 | `prompt_I10_role_readiness_map.txt` | Role Readiness Map: FitGapService, lazy-computed on job detail, 5-column table (Fit Level / What They Ask For / What You Have / Best Next Move / Draft Readiness), cached in `extracted_metadata["fit_gaps"]` | Spec ready |

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
