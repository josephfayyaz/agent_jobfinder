# Local LLM Job Agent

Local-first job search + CV optimization for Yousef Fayyaz.
Goals: (1) jobs/internships in Italy + EU, (2) thesis/traineeship outreach.

## Architecture

```
LM Studio :1234  qwen3.5-9b-mlx (small/reviewer), qwen3.5-27b-...-distilled-mlx (writer),
                 openai/gpt-oss-20b (mid), text-embedding-nomic-embed-text-v1.5
FastAPI   :8000  82 endpoints — conda ML — job_agent/main.py
Worker           background process — job_agent/worker.py
PostgreSQL:5432  Docker only, named volume (persists restarts)
Claude API       optional final polish — USE_CLAUDE_FINAL_REVIEW=true
```

LLM calls go through `LLMRouter` (`llm.py`): `role="small"` → 9b, `role="writer"` → 27b, `role="mid"` → 20b, `role="cloud"` → Anthropic.

## How to Run

```bash
docker compose up -d db
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

## Current State — All Phases Complete

213 tests passing · 0 failing · ruff clean · 28 ORM models · 82 endpoints

| Done | What |
|------|------|
| A1 | Role-adaptive writer — junior/mid/senior presentation modes via `resolve_presentation_mode()` |
| B0–B1 | Fact sheet JSON schema vendored; `Candidate` model + `FactSheetJsonIngestionService` |
| B2 | `FactSheetRenderer` — deterministic JSON→TXT in 12-section stable order |
| B3 | `FactSheetIntakeService` — file upload + LLM iterative Q&A (3 max iterations) |
| B4 | Reviewer upgraded: comp sanity check (Block D, 9 country baselines) + legitimacy signals (Block G) stored in `review_feedback` JSONB |
| C1 | `find_company_url()` + `POST /jobs/{id}/resolve-company-url`; auto-resolves on job creation |
| C2 | `scan_all_parallel()` with `ThreadPoolExecutor`, `scanner_max_workers` config |
| D | FastAPI lifespan migration; seed tests; parallel-worker test |

## Known Gaps (What Comes Next)

- **E1 — CV + Candidate unification** — `_load_context()` hardcodes `MasterProfile(id=1)`; `DEFAULT_CANDIDATE_ID` + `Candidate` facts not wired. → `prompt_E1_candidate_unification.txt`
- **E2 — JobSpy scheduler** — no `JOBSPY_DISCOVER_INTERVAL_HOURS` config, no worker loop call; discovery is manual only. → `prompt_E2_jobspy_scheduler.txt`
- ~~Application tracker~~ — done: `applications.html` + `/ui/applications` + `/ui/applications/{id}/advance` all wired
- ~~Thesis UI~~ — done: `thesis.html` + `/ui/thesis` wired
- ~~Cover letter~~ — done: `POST /drafts/{draft_id}/cover-letter` wired
- ~~Onboarding crash~~ — fixed: `start_intake` / `answer_questions` return HTTP 503 on `ProviderUnavailableError`

## Key Files

`main.py` · `models.py` · `db.py` · `llm.py` · `worker.py` · `seed.py`
`services/workflows.py` · `services/prompts.py` · `services/fact_ingestion.py`
`services/fact_sheet_renderer.py` · `services/intake.py` · `services/resource_loader.py`
`services/experience_selection.py` · `services/gmail.py` · `services/company_resolver.py`
`services/career_scanner.py` · `services/jobspy_service.py`
`job_agent/resources/fact_sheet/fact_sheet_schema.json` (canonical schema, 596 lines)

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
