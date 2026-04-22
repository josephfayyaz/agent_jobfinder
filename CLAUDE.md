# Local LLM Job Agent

Local-first job search + CV optimization for Yousef Fayyaz.
Goals: (1) jobs/internships in Italy + EU, (2) thesis/traineeship outreach.

## Architecture

```
LM Studio :1234  qwen3.5-9b-mlx (small/reviewer), qwen3.5-27b-...-distilled-mlx (writer),
                 openai/gpt-oss-20b (mid), text-embedding-nomic-embed-text-v1.5
FastAPI   :8000  82 endpoints — conda ML — job_agent/main.py
Worker           background process — job_agent/worker.py
SQLite            embedded DB at <project_root>/job_agent.db
Claude API       optional final polish — USE_CLAUDE_FINAL_REVIEW=true
```

LLM calls go through `LLMRouter` (`llm.py`): `role="small"` → 9b, `role="writer"` → 27b, `role="mid"` → 20b, `role="cloud"` → Anthropic.

## How to Run

```bash
conda activate ML
uvicorn job_agent.main:app --host 0.0.0.0 --port 8000 --reload   # terminal 1
python -m job_agent.worker                                         # terminal 2
curl localhost:8000/health   # → {"status":"ok"}
```

Use direct Python for one-offs: `/Users/youseffayyaz/miniforge3/envs/ML/bin/python`

## Hard Rules (Never Break)

- **No Alembic.** Schema = `prepare_database()` in `db.py` via `Base.metadata.create_all()` + `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`.
- **Always conda ML.** Never create venvs.
- **Starlette 1.0.0 TemplateResponse** requires keyword args: `TemplateResponse(request=request, name="x.html", context={...})` — positional args crash with `unhashable type: 'dict'`.
- **Never share a DB session across threads.** Each `ThreadPoolExecutor` worker gets its own `SessionLocal()`.

## Real ORM Field Names

Codex gets these wrong — always check:

| Model | Correct field | Wrong (ignore specs that say this) |
|-------|--------------|-------------------------------------|
| `ExperienceFact` | `.role_title` | ~~`.title`~~ |
| `ExperienceFact` | `.verified_core_facts` | ~~`.bullets`~~ |
| `ExperienceFact` | `.tools_and_tech` | ~~`.tech_stack`~~ |
| `ProjectFact` | `.project_name` | ~~`.name`~~ |
| `ProjectFact` | `.short_resume_line` | ~~`.summary`~~ |
| `ResumeDraft` | `.review_feedback` (JSONB) | ~~`.review_notes`~~ |

Fact sheet JSON: `person.contact.email` (not `person.email`), `experience[].role_title`, `experience[].responsibilities`. `completion_status` enum: `"complete"` | `"usable_with_gaps"` | `"incomplete"`.

## Current State — 2026-04-22

343 tests passing · 0 failing · ruff clean · 28 ORM models · 90+ endpoints

All F/G/UI/UX phases complete. I1–I6 specs written and ready.

| Done | What |
|------|------|
| A1 | Role-adaptive writer — junior/mid/senior presentation modes via `resolve_presentation_mode()` |
| B0–B4 | Fact sheet JSON schema, Candidate model, renderer, intake, reviewer upgrade |
| C1–C2 | Company URL discovery, parallel scanner |
| D | FastAPI lifespan migration |
| E1–E2 | Candidate unification, JobSpy scheduler |
| F1 | Human-in-the-loop bullet rewrite — `BulletClarifyService`, `BulletClarification` model |
| F2 | ATS keyword extraction in `_generate_draft()`, stored in `review_feedback` |
| F3 | Rejection analytics — `RejectionAnalyticsService`, `GET /analytics/rejection-patterns` |
| F5+G5 | Zero-token ATS APIs (Greenhouse/Lever/Ashby) + velocity spike alerting with 2h time filter |
| G1 | Compliance matrix per draft — `ComplianceMatrixService`, stored in `review_feedback["compliance_matrix"]` |
| G6 | Rejection risk prediction — `RejectionPredictionService`, stored in `extracted_metadata["rejection_risks"]` |
| start_apply | Standalone CLI: paste job → score → questions → CV file |
| UI1 | `/ui/drafts/{id}` — full draft viewer, compliance matrix badge, approve/reject |
| UI2 | `/ui/analytics` — funnel, score buckets, skill gaps, weekly activity, velocity |
| UI3 | `/ui/companies` — watched companies, ATS type, toggle active, add form |
| UX1 | YAML user config layer — `config/user_settings.yml` overlays `.env`; `job_agent/user_config.py`; `POST /settings/save`; `POST /settings/reload`; `GET /settings/current` |
| UX2–UX5 | 6-step CLI onboarding; `python -m job_agent.cli start` + `run.sh`; `job-agent` CLI suite; `/ui/settings` web editor |
| I3 | SQLite-only backend — embedded `job_agent.db`, no Docker preflight, SQLite health reporting, shared SQLite test shims |

## What Comes Next (I-phases — specs in `AGENT_SPECS/codex_prompts/`)

Send to Codex in this order:

| Step | Spec | What |
|------|------|------|
| 1a | `prompt_I2_seed_italy_companies.txt` | 54 Italy companies seed + 5-role limit |
| 1b | `prompt_I6_first_run_installer.txt` | Auto-install packages on first run |
| 2a | `prompt_I1_hitl_bullet_rewrite_ui.txt` | HITL bullet rewrite in web UI |
| 2b | `prompt_I4_cv_output_folder.txt` | CV output folder + Company/Date naming |
| 2c | `prompt_I5_gmail_setup_wizard.txt` | Gmail web setup wizard |
| 2d | `prompt_I7_web_apply_flow.txt` | Web interactive apply: `/ui/apply` — paste JD → score → questions → draft |
| 3a | `prompt_I8_market_skill_gap.txt` | Market Skill Gap Dashboard in `/ui/analytics` |
| 3b | `prompt_I9_hiring_velocity.txt` | ⚡ Hiring velocity badge on `/ui/companies` |
| 3c | `prompt_I10_role_readiness_map.txt` | Role Readiness Map on job detail + draft detail |

## New Files from UX1 (already implemented)

- `job_agent/user_config.py` — read/write helper for `config/user_settings.yml`
- `config/user_settings.example.yml` — committed template (user copies to `user_settings.yml`)
- `config/user_settings.yml` — gitignored user config (overlays `.env` at runtime)
- `tests/test_user_settings.py` — tests for YAML overlay and settings endpoints

## Services in `job_agent/services/`

ats_scanner · bullet_clarify · career_scanner · company_resolver · compliance_matrix ·
cover_letter · documents · experience_selection · exporters · fact_ingestion ·
fact_sheet_json · fact_sheet_renderer · file_extraction · gmail · intake · job_fetcher ·
jobspy_service · matching · prompts · rejection_analytics · rejection_prediction ·
resource_loader · thesis_outreach · workflows

## LLMRouter Error Handling (IMPORTANT for Codex)

`LLMRouter.generate()` raises TWO exception types — services MUST catch BOTH:
- `ProviderUnavailableError` — LM Studio is down or model not configured
- `ValueError` — model returned malformed/non-JSON response (`_extract_json` failed)

All G-phase service specs include `except ProviderUnavailableError` but may miss `ValueError`.
Codex MUST catch both when implementing any service that calls `self.router.generate()`.

## Key Files

`main.py` · `models.py` · `db.py` · `llm.py` · `worker.py` · `seed.py` · `config.py` · `user_config.py`
`services/workflows.py` · `services/prompts.py` · `services/fact_ingestion.py`
`services/fact_sheet_renderer.py` · `services/intake.py` · `services/resource_loader.py`
`services/experience_selection.py` · `services/gmail.py` · `services/company_resolver.py`
`services/career_scanner.py` · `services/jobspy_service.py`
`job_agent/resources/fact_sheet/fact_sheet_schema.json` (canonical schema, 596 lines)
`config/user_settings.example.yml` · `config/user_settings.yml` (gitignored, user-created)

## graphify

Graph at `graphify-out/` — 985 nodes · 3461 edges · 58 communities. God nodes: `JobPost`(127) · `ResumeTrack`(110) · `CVWorkflowService`(84).

Read `graphify-out/GRAPH_REPORT.md` before architecture questions. Rebuild after editing:
```bash
/Users/youseffayyaz/miniforge3/envs/ML/bin/python -c \
  "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"
```

## Claude ↔ Codex Relay

Specs in `AGENT_SPECS/codex_prompts/` · reports in `AGENT_SPECS/completed/` · log in `completed_agent_specs.txt`.
Every Codex prompt ON COMPLETION: append to log, write report, run graphify rebuild.
