# Local LLM Job Agent

Local-first job search + CV optimization for a single local user.
Goals: (1) jobs/internships in Italy + EU, (2) thesis/traineeship outreach.

## Architecture

```
LM Studio :1234  qwen3.5-9b-mlx (small/reviewer), qwen3.5-27b-...-distilled-mlx (writer),
                 openai/gpt-oss-20b (mid), text-embedding-nomic-embed-text-v1.5
FastAPI   :8000  router-based app assembly — conda ML — job_agent/main.py
Worker           background process — job_agent/worker.py
SQLite            embedded DB in the local Job Agent data home
Claude API       optional final polish — USE_CLAUDE_FINAL_REVIEW=true
frontend/        templates + static JS/CSS served by FastAPI
```

LLM calls go through `LLMRouter` (`llm.py`): `role="small"` → 9b, `role="writer"` → 27b, `role="mid"` → 20b, `role="cloud"` → Anthropic.

## How to Run

```bash
conda activate ML
uvicorn job_agent.main:app --host 127.0.0.1 --port 8000 --reload   # terminal 1
python -m job_agent.worker                                         # terminal 2
curl localhost:8000/health   # → {"status":"ok"}
```

Use the active `python` from the configured `ML` environment for one-offs.

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

## Current State — 2026-05-07

Current branch state is green on the full test suite and `ruff check`. The app is
now a single-owner local workspace with:

- setup-gated onboarding so users cannot fall into half-configured screens
- provider-aware AI routing with cloud BYOK onboarding and local advanced options (5 providers: LM Studio, Ollama, OpenAI, Anthropic, Gemini)
- Gmail OAuth ingestion for LinkedIn alerts
- review-first job discovery with freshness, legitimacy, and discovery-health signals
- shortlist-centric apply flow with package checks before drafting
- reusable verified profile memory plus Story Bank, Opportunity Snapshot, and Offer Compass
- 5-step streamlined onboarding (candidate shell auto-created; no manual profile entry step)
- pdfplumber + pdfminer dual-engine PDF extraction with text normalization before intake

ORM schema: **35 tables** across candidates, jobs, drafts, facts, applications, stories, offers, and outreach.

Implemented work now spans:

| Done | What |
|------|------|
| A1 | Role-adaptive writer — junior/mid/senior presentation modes via `resolve_presentation_mode()` |
| B0–B4 | Fact sheet JSON schema, Candidate model, renderer, intake, reviewer upgrade |
| C1–C2 | Company URL discovery, parallel scanner |
| C3–C8 | Discovery hub, shortlist-first queueing, Story Bank, Opportunity Snapshot, and Offer Compass |
| D | FastAPI lifespan migration |
| E1–E2 | Candidate unification, JobSpy scheduler |
| F1 | Human-in-the-loop bullet rewrite — `BulletClarifyService`, `BulletClarification` model |
| F2 | ATS keyword extraction in `_generate_draft()`, stored in `review_feedback` |
| F3 | Rejection analytics — `RejectionAnalyticsService`, `GET /analytics/rejection-patterns` |
| F5+G5 | Zero-token ATS APIs (Greenhouse/Lever/Ashby) + velocity spike alerting with 2h time filter |
| G1 | Compliance matrix per draft — `ComplianceMatrixService`, stored in `review_feedback["compliance_matrix"]` |
| G1-pdf | PDF intake hardening — pdfplumber primary + pdfminer fallback, `_normalize_extracted_text()` in `services/file_extraction.py` |
| G6 | Rejection risk prediction — `RejectionPredictionService`, stored in `extracted_metadata["rejection_risks"]` |
| start_apply | Standalone CLI: paste job → score → questions → CV file |
| UI1 | `/ui/drafts/{id}` — full draft viewer, compliance matrix badge, approve/reject |
| UI2 | `/ui/analytics` — funnel, score buckets, skill gaps, weekly activity, velocity |
| UI3 | `/ui/companies` — watched companies, ATS type, toggle active, add form |
| UX1 | YAML user config layer — user settings file overlays `.env`; `job_agent/user_config.py`; `POST /settings/save`; `POST /settings/reload`; `GET /settings/current` |
| UX2–UX5 | Guided onboarding, CLI helpers, `job-agent` CLI suite, and `/ui/settings` web editor |
| I1 | HITL bullet rewrite buttons in `draft_detail.html`; `GET /drafts/{id}/clarifications`; promote to profile |
| I2 | Seeded company discovery set and search focus scaffolding |
| I3 | SQLite-only backend — embedded local SQLite DB, no Docker preflight, WAL mode |
| I4 | `artifacts_dir` setting; `Company_YYYY-MM-DD_DraftID[:8]` filename convention |
| I5 | Gmail setup wizard in `/ui/settings`, now centered on Gmail OAuth |
| I6 | `preflight.py` auto-installs packages on first run; clear offline error |
| I7 | `/ui/apply` — paste JD → score → questions → draft; `confirmed_facts` flows to writer; XSS fixed |
| I8 | Market Skill Gaps dashboard — aggregates missing ATS keywords from non-archived drafts |
| I9 | Hiring velocity signal — ⚡ badge for companies with new roles in 2+ recent scans |
| I10 | Role Readiness Map — FitGapService compares JD requirements against fact-sheet evidence before drafting |
| I11 | Verified profile memory — save confirmed answers as reusable candidate evidence |
| P1 | Single-owner workspace — app-data home outside repo, full backup download, GitHub share card, typed reset/delete controls |
| P2a–P2b | Gmail OAuth setup plus enrichment hardening and draft gating |
| P3–P5 | Multi-provider routing, Ollama support, provider onboarding, and resilience/error UX |
| Release 01–05 | Worker resilience, startup hardening, JS null guards + polling error handling, LLM truncation + API-key safety, Gemini provider, cache-busting, skeleton loader accessibility |

## What Comes Next

Active Codex specs in `AGENT_SPECS/pending/claude/` (phases K–O):

- **K** — Frontend provider controller deduplication (extract shared JS module)
- **L** — Onboarding state modularization (per-step state namespaces)
- **M** — CSS isolation, label standardization, dead-code cleanup
- **N** — Provider cost UX: token-usage tracking + pipeline budget guardrail
- **O** — Discovery quality (shortlist-gated enrichment) + ORM table wiring

Longer horizon:

- packaging/distribution refinements for public release

## New Files from UX1 (already implemented)

- `job_agent/user_config.py` — read/write helper for the single-user settings file
- `config/user_settings.example.yml` — committed template (user copies to `user_settings.yml`)
- local user settings file — stored in the OS app-data home, overlays `.env` at runtime
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
`routers/` · `runtime_paths.py` · `services/workflows.py` · `services/prompts.py`
`services/fact_ingestion.py` · `services/fact_sheet_renderer.py` · `services/intake.py`
`services/resource_loader.py` · `services/experience_selection.py` · `services/gmail.py`
`services/company_resolver.py` · `services/career_scanner.py` · `services/jobspy_service.py`
`frontend/templates/` · `frontend/static/`
`job_agent/resources/fact_sheet/fact_sheet_schema.json` (canonical schema, 596 lines)
`config/user_settings.example.yml` · local user settings file in app-data home

## Architecture Notes

If you need architecture context, inspect the live routers, services, and models directly.
Do not rely on generated local graph artifacts being present in the repository.

## Claude ↔ Codex Relay

Active specs in `AGENT_SPECS/pending/` · archived prompts in `AGENT_SPECS/archive/` · reports in `AGENT_SPECS/completed/` · log in `completed_agent_specs.txt`.
Every Codex prompt ON COMPLETION: append to log and write the report.
