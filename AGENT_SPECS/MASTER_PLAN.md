# Master Implementation Plan — Post E1/E2

**Updated:** 2026-04-17  
**Status:** 223 tests passing · F1 specced · start_apply urgent

---

## Current State

All original phases (A1–E2) complete. The system has:
- FastAPI :8000 · 82 endpoints · 28 ORM models · PostgreSQL
- Role-adaptive CV writer · reviewer with scoring + gaps + comp + legitimacy
- Fact sheet ingestion · candidate unification (E1) · JobSpy scheduler (E2)
- Career page scanner · company URL resolver · Gmail sync · application tracker UI

---

## Immediate Priority — start_apply CLI (Urgent)

**Spec:** `AGENT_SPECS/codex_prompts/prompt_start_apply.txt`

Standalone CLI tool that does not depend on the running FastAPI server.  
User pastes messy job info → score → 3 clarifying questions → final CV file.  
This runs before anything else so Yousef can begin applying now.

---

## Phase F — CV Workflow Improvements

| Phase | Spec file | What | Depends on |
|---|---|---|---|
| F1 | `prompt_F1_bullet_clarify_rewrite.txt` | Human-in-loop bullet rewrite (interactive) | — |
| F2 | `prompt_F2_keyword_extraction.txt` | ATS keyword extraction pre-step in writer | — |
| F3 | `prompt_F3_rejection_analytics.txt` | Rejection pattern analytics endpoint | — |

**Run order:** F1 → F2 → F3 (each independent, this order preferred)

---

## Phase G — Discovery & Intelligence Improvements

| Phase | Spec file | What | Depends on |
|---|---|---|---|
| F5+G5 | `prompt_F5_G5_ats_discovery_velocity.txt` | Zero-token ATS APIs + velocity alerting | — |
| G1 | `prompt_G1_compliance_matrix.txt` | Semantic ATS compliance matrix per draft | F2 (for keyword logic context) |
| G6 | `prompt_G6_rejection_prediction.txt` | Pre-application rejection risk prediction | — |

**Run order:** F5+G5 → G1 → G6 (each mostly independent)

---

## Discovery Strategy (F5 clarification)

Sources in priority order:
1. **LinkedIn** — via JobSpy (already working, keep as primary broad search)
2. **Direct ATS APIs** — Greenhouse / Lever / Ashby / BambooHR for user-registered companies  
   (zero LLM tokens, structured JSON response, faster)
3. **HTML career page scan** — existing `CareerPageScanner` for companies without ATS API
4. **Gmail notifications** — existing `GmailService` for alerts from recruiters

Users add companies via `POST /career-pages` (already works). F5 extends this by:
- Adding `ats_type` + `ats_slug` columns to `CareerPageSource`
- When `ats_type` is set, using the direct API instead of Playwright scraping

---

## UI Roadmap (modern web UI for tracking)

Inspired by career-ops TUI, implement as web pages inside the existing Jinja2 UI:

| Screen | Route | What it does |
|---|---|---|
| Pipeline table | `/ui/pipeline` | All jobs, filter by status/score/track, sort, bulk actions |
| Draft viewer | `/ui/drafts/{id}` | Full draft content, compliance matrix, clarify button |
| Analytics dashboard | `/ui/analytics` | Funnel, score histogram, conversion rates, velocity chart |
| Company watchlist | `/ui/companies` | Add/remove watched companies, ATS type, last scan |

These are HTMX-enhanced Jinja2 pages — no React needed, keeps the stack uniform.  
**Not included in any current Codex spec** — implement after F/G phases are stable.

---

## Skipped / Deferred

| Feature | Reason |
|---|---|
| G2 (salary intelligence) | Not relevant at junior level in Italian market |
| G7 (multi-persona strategy) | Risks lowering acceptance rate; revisit later |
| F6 (interview prep) | Out of scope for this phase |
| TUI dashboard (Go) | Replace with web UI instead |

---

## Conventions Codex Must Never Break

- No Alembic. Schema = `prepare_database()` in `db.py`.
- Always conda ML. Never create venvs.
- Starlette TemplateResponse: keyword args only.
- No shared DB sessions across threads.
- Real ORM field names: `role_title`, `verified_core_facts`, `tools_and_tech`, `project_name`, `short_resume_line`, `review_feedback`.
- After every phase: run `pytest --tb=short -q`, run `ruff check`, write report to `AGENT_SPECS/completed/`, append to `completed_agent_specs.txt`.
- Graphify rebuild: `python -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"` (may fail in Codex env — ok).
