# Local LLM Job Agent

Local-first job search and CV optimization system for Yousef Fayyaz. Two goals:
1. Find jobs/internships in Italy and across the EU
2. Find thesis/traineeship abroad in EU via outreach

## Architecture

```
LM Studio (port 1234, MLX backend)
  qwen3.5-9b   — always loaded (reviewer, router, scoring)
  qwen3.5-27b  — on-demand only (resume writing)

FastAPI API   — conda ML, port 8000
Worker        — conda ML, background process
PostgreSQL 17 — Docker only (port 5432)
Claude API    — Anthropic, final resume polish (optional)
```

## How to Run

**Prerequisite:** Docker Desktop running, LM Studio running with models loaded.

```bash
# 1. Start PostgreSQL (only container needed)
docker compose up -d db

# 2. Activate conda env
conda activate ML   # uses ~/miniforge3/envs/ML

# 3. Start API (terminal 1)
cd /Users/youseffayyaz/Local_LLM
uvicorn job_agent.main:app --host 0.0.0.0 --port 8000 --reload

# 4. Start Worker (terminal 2)
cd /Users/youseffayyaz/Local_LLM
python -m job_agent.worker
```

**Quick verify:**
```bash
curl localhost:8000/health        # {"status":"ok"}
curl localhost:8000/providers     # shows LM Studio reachable + models
curl localhost:8000/profile       # shows Yousef's master profile
```

## Key Commands

```bash
# Re-ingest fact sheet after updates
FACT_PATH="/Users/youseffayyaz/Polito/Resume-CV/fact_sheet/master_fact_sheet.txt"
jq -Rs --arg p "$FACT_PATH" '{source_path:$p,content:.}' "$FACT_PATH" \
  | curl -sX POST localhost:8000/fact-sources/ingest -H 'Content-Type: application/json' -d @-

# Create a job and queue CV workflow
curl -sX POST localhost:8000/jobs -H 'Content-Type: application/json' -d @examples/job.example.json
curl -sX POST localhost:8000/tasks/cv-workflow -H 'Content-Type: application/json' \
  -d '{"job_post_id":"<ID>","resume_track_slug":"data-engineering-analytics","force_cloud_review":false}'

# Poll task
curl -s localhost:8000/tasks/<TASK_ID>

# Export jobs to CSV
curl -sX POST localhost:8000/exports/jobs-csv

# Lint and test
ruff check job_agent/
pytest tests/ -v
```

## Python Environment

Always use conda env `ML` (miniforge3). Never create venvs.
```bash
/Users/youseffayyaz/miniforge3/bin/conda run -n ML pip install -e ".[dev]"
```

## Configuration

`.env` file (not committed). Key settings:
- `LM_STUDIO_SMALL_MODEL=qwen3.5-9b` — reviewer / router
- `LM_STUDIO_WRITER_MODEL=qwen3.5-27b` — resume writer (on-demand)
- `CV_PASS_SCORE=85` — accept without revision
- `CV_REVISE_SCORE=60` — revise with 9B before escalating
- `USE_CLAUDE_FINAL_REVIEW=false` — set true + add `ANTHROPIC_API_KEY` for Claude final polish
- `USE_OPENAI_REVIEW=false` — keep false (going local-first)

## Resume Tracks (4 active)
- `data-engineering-analytics` — Data Engineer / Analytics Engineer
- `data-analyst-bi-product` — Data Analyst / BI / Product Analytics
- `ai-ml-engineering` — AI / ML Engineer
- `cloud-mlops-ai-platform` — Cloud / MLOps / AI Platform

## Source of Truth
- **Master fact sheet:** `/Users/youseffayyaz/Polito/Resume-CV/fact_sheet/master_fact_sheet.txt`
- **Database:** PostgreSQL `job_agent` (Docker, port 5432, persisted in named volume)
- **Generated resumes:** `generated/` directory (.tex files)

## Key Files
| File | Purpose |
|------|---------|
| `job_agent/main.py` | FastAPI app, all endpoints |
| `job_agent/models.py` | 18 SQLAlchemy ORM models |
| `job_agent/services/workflows.py` | CV generation pipeline |
| `job_agent/services/prompts.py` | LLM prompts (writer + reviewer) |
| `job_agent/services/matching.py` | Job-to-track scoring |
| `job_agent/services/documents.py` | LaTeX rendering |
| `job_agent/llm.py` | LM Studio + Anthropic routing |
| `job_agent/parsers/fact_sheet.py` | Fact sheet parser |
| `job_agent/seed.py` | Resume tracks + job sources |
| `docker-compose.yml` | PostgreSQL only |

## Job Sources (trusted only)
1. LinkedIn — manual search + Gmail alert parsing
2. Company career pages — resolved from LinkedIn listings

## Fact Sheet Updates
Re-run the ingest command above whenever `master_fact_sheet.txt` changes.
Rule of thumb: if only editing values/bullets/dates → re-ingest. If adding new section types → tell Claude Code first (parser may need updating).
