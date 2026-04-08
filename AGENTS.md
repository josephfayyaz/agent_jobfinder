# Local LLM Job Agent — Agent Guide

This file is the Codex/OpenAI agent equivalent of CLAUDE.md. Both files describe
the same project; keep them in sync when making architectural changes.

## Project Purpose

A **local-first, privacy-respecting job search and CV optimization system**.
Two parallel goals:
1. Find jobs/internships across Italy and the EU (fully customizable per user)
2. Find thesis/traineeship placements abroad via professor/company outreach

Designed to run entirely on a local machine using LM Studio + PostgreSQL.
Cloud APIs (Anthropic, OpenAI) are **optional** fallback/escalation only.

## Repository Layout

```
job_agent/
  main.py          FastAPI application, all REST endpoints
  config.py        All settings — single source of truth, loaded from .env
  models.py        SQLAlchemy ORM (18 models)
  schemas.py       Pydantic I/O schemas
  llm.py           LLM router: LM Studio + Anthropic + OpenAI
  worker.py        Background task processor (polls every N seconds)
  seed.py          Seeded reference data: resume tracks + job sources
  db.py            SQLAlchemy engine + session + schema bootstrap
  parsers/
    fact_sheet.py  Parses structured .txt fact sheet into profile data
  services/
    workflows.py   CV generation pipeline (draft → review → revise → polish)
    prompts.py     All LLM prompts (writer, reviewer, reviser, enhancer)
    matching.py    Job-to-resume-track scoring
    documents.py   LaTeX resume rendering + PDF compilation
    fact_ingestion.py  Stores parsed fact sheet into DB
    exporters.py   CSV snapshot export

AGENT_SPECS/       Precise implementation specs for agent handoff
generated/         Output artifacts (.tex, .pdf, CSV exports) — gitignored
examples/          Sample job.json and profile.json for quick testing
```

## How to Run (any machine)

**Prerequisites:** Docker Desktop, LM Studio (any OpenAI-compatible server works), conda or venv.

```bash
# 1. Copy and fill in settings
cp .env.example .env
# Edit .env: set your LM Studio model names, optional API keys

# 2. Start PostgreSQL
docker compose up -d db

# 3. Install dependencies (conda ML recommended; any Python 3.12+ env works)
pip install -e ".[dev]"

# 4. Start API (terminal 1)
uvicorn job_agent.main:app --host 0.0.0.0 --port 8000 --reload

# 5. Start Worker (terminal 2)
python -m job_agent.worker

# 6. Verify
curl localhost:8000/health       # {"status":"ok"}
curl localhost:8000/providers    # LM Studio status + configured models
```

## Environment Variables (see .env.example for full list)

All behavior is controlled via `.env`. Key groups:

| Group | Variables | Purpose |
|-------|-----------|---------|
| Database | `DATABASE_URL` | PostgreSQL connection string |
| LM Studio | `LM_STUDIO_BASE_URL`, `LM_STUDIO_*_MODEL` | Local inference server |
| Token limits | `LM_STUDIO_MAX_TOKENS_SMALL`, `LM_STUDIO_MAX_TOKENS_WRITER`, `LM_STUDIO_MAX_TOKENS_MID` | Per-model token budgets |
| Cloud (optional) | `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` | Optional escalation |
| CV thresholds | `CV_PASS_SCORE`, `CV_REVISE_SCORE` | Resume scoring gates |
| Worker | `WORKER_POLL_SECONDS` | Background task poll interval |

## Code Conventions

- Python 3.12+, type hints everywhere
- Pydantic v2 for schemas, SQLAlchemy 2.0 ORM for models
- `ruff` for linting (`ruff check job_agent/`)
- `pytest` for tests (`pytest tests/ -v`)
- **Never hardcode personal data** — all candidate-specific data comes from the fact sheet ingested via API
- All LLM calls go through `job_agent/llm.py:LLMRouter` — never call httpx or OpenAI/Anthropic directly from services
- All settings come from `job_agent/config.py:settings` — never read `.env` directly in application code

## Agent Handoff Workflow

For large implementation tasks, specs live in `AGENT_SPECS/`:
- Each file is a self-contained implementation brief
- File naming: `phase{N}_{N}_{short_description}.md`
- Format: file path → exact change → before/after code blocks

Read the spec file fully before implementing. Follow it exactly unless a clear bug exists, in which case note it and fix it.

## Key Endpoints Quick Reference

| Method | Path | What it does |
|--------|------|-------------|
| GET | `/health` | Liveness check |
| GET | `/providers` | LM Studio + cloud provider status |
| GET/PUT | `/profile` | Candidate master profile |
| POST | `/fact-sources/ingest` | Ingest/update fact sheet |
| POST | `/jobs` | Create job posting (auto-scores tracks) |
| GET | `/jobs/{id}/track-fit` | Get track match scores for a job |
| POST | `/tasks/cv-workflow` | Queue resume generation task |
| GET | `/tasks/{id}` | Poll task status |
| GET | `/drafts/{id}` | Get generated resume draft |
| POST | `/drafts/{id}/approve` | Approve draft for submission |
| POST | `/exports/jobs-csv` | Export jobs + applications to CSV |

## DO NOT

- Hardcode any name, email, phone, or personal URL — use the fact sheet
- Call LLM providers directly — always use `LLMRouter`
- Read `.env` in application code — always use `settings` from `config.py`
- Create Python venvs — use conda `ML` env or the user's preferred env
- Commit `.env` — it is gitignored, `.env.example` is the template
- Commit `generated/` — these are runtime artifacts
