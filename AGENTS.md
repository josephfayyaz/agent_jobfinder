# Local LLM Job Agent — Agent Guide

This file is the Codex/OpenAI agent equivalent of CLAUDE.md. Both files describe
the same project; keep them in sync when making architectural changes.

## Project Purpose

A **local-first, privacy-respecting job search and CV optimization system**.
Two parallel goals:
1. Find jobs/internships across Italy and the EU (fully customizable per user)
2. Find thesis/traineeship placements abroad via professor/company outreach

Designed to run entirely on a local machine using LM Studio + SQLite.
Cloud providers (OpenAI, Anthropic) are supported via BYOK, while local
providers remain first-class for users who want fully local inference.

## Repository Layout

```
frontend/
  templates/     Jinja page templates and partials
  static/        Shared CSS and page-specific JS

job_agent/
  main.py          FastAPI application, router assembly, lifespan
  config.py        All settings — single source of truth, loaded from .env
  models.py        SQLAlchemy ORM
  schemas.py       Pydantic I/O schemas
  llm.py           LLM router: LM Studio + Ollama + Gemini + Anthropic + OpenAI
  worker.py        Background task processor (polls every N seconds)
  seed.py          Seeded reference data: resume tracks + job sources
  db.py            SQLAlchemy engine + session + schema bootstrap
  routers/         HTTP routes split by domain (jobs, drafts, system, etc.)
  runtime_paths.py Cross-platform runtime data locations
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
config/            Example config templates committed to the repo
examples/          Sample job.json and profile.json for quick testing

Runtime data (SQLite DB, live user settings, generated files, backups) lives in
the OS app-data directory for the current user, not in the repo tree, unless
`JOB_AGENT_HOME` overrides it.
```

## How to Run (any machine)

**Prerequisites:** LM Studio or another local provider, conda `ML` preferred.

```bash
# 1. Copy and fill in settings
cp .env.example .env
# Edit .env: set your LM Studio model names, optional API keys

# 2. Install dependencies
pip install -e ".[dev]"

# 3. Start API (terminal 1)
uvicorn job_agent.main:app --host 127.0.0.1 --port 8000 --reload

# 4. Start Worker (terminal 2)
python -m job_agent.worker

# 5. Verify
curl localhost:8000/health       # {"status":"ok"}
curl localhost:8000/providers    # LM Studio status + configured models
```

## Environment Variables (see .env.example for full list)

All behavior is controlled via `.env`. Key groups:

| Group | Variables | Purpose |
|-------|-----------|---------|
| Database | `DATABASE_URL` | Optional SQLite URL override; default is the local Job Agent data home |
| LM Studio | `LM_STUDIO_BASE_URL`, `LM_STUDIO_*_MODEL` | Local inference server |
| Token limits | `LM_STUDIO_MAX_TOKENS_SMALL`, `LM_STUDIO_MAX_TOKENS_WRITER`, `LM_STUDIO_MAX_TOKENS_MID` | Per-model token budgets |
| Cloud (optional) | `OPENAI_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY` | Optional hosted providers |
| Gmail | `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REDIRECT_BASE_URL` | Gmail OAuth setup |
| CV thresholds | `CV_PASS_SCORE`, `CV_REVISE_SCORE` | Resume scoring gates |
| Worker | `WORKER_POLL_SECONDS` | Background task poll interval |

## Current State

Current mainline behavior includes:

- setup-gated onboarding with five providers: LM Studio, Ollama, OpenAI, Gemini, Anthropic
- single-owner local workspace with runtime data outside the repo by default
- streamlined onboarding flow: provider -> facts -> questions -> review -> search
- PDF intake hardening via `pdfplumber` primary extraction with `pdfminer` fallback
- manual JD scoring, CV draft generation, preview/review, approve/download, and compliance matrix flow
- frontend provider-controller/state/CSS cleanup plus token-usage and fact-table wiring phases `K` through `O` completed and archived under `AGENT_SPECS/archive/claude/completed/`

## Code Conventions

- Python 3.12+, type hints everywhere
- Pydantic v2 for schemas, SQLAlchemy 2.0 ORM for models
- `ruff` for linting (`ruff check job_agent/`)
- `pytest` for tests (`pytest tests/ -v`)
- **Never hardcode personal data** — all candidate-specific data comes from the fact sheet ingested via API
- All LLM calls go through `job_agent/llm.py:LLMRouter` — never call httpx or OpenAI/Anthropic directly from services
- All settings come from `job_agent/config.py:settings` — never read `.env` directly in application code
- Single-user mode only — prefer updating the owner candidate over creating parallel profiles
- Runtime data lives outside the repo in the OS app-data directory unless explicitly overridden via `JOB_AGENT_HOME`

## Agent Handoff Workflow

For large implementation tasks, specs live in `AGENT_SPECS/`:
- Each file is a self-contained implementation brief
- File naming: `phase{N}_{N}_{short_description}.md`
- Format: file path → exact change → before/after code blocks
- Active unimplemented specs live in `AGENT_SPECS/pending/<agent>/`
- Completed or replaced prompts move to `AGENT_SPECS/archive/<agent>/`
- Completion reports live in `AGENT_SPECS/completed/`
- Longer-horizon plans live in `AGENT_SPECS/master_plans/<agent>/`

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
