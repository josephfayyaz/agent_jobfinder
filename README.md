# Job Agent

Local-first, single-user job search and CV workflow software.

The app is built for one person running their own private workspace on their own machine. Runtime data lives outside the repo, SQLite is the default database, LM Studio is the preferred local provider, and OpenAI or Anthropic can be used as optional cloud fallbacks.

## What it does

- guides first-run onboarding so the workspace is useful before the user lands in the dashboard
- ingests a candidate fact sheet from uploaded files or notes
- discovers jobs and career pages, with language-aware filtering
- scores jobs against active resume tracks
- runs an interactive apply flow: paste JD -> score -> clarifying questions -> draft
- generates CV drafts, cover letters, role-readiness maps, and analytics
- saves verified profile memory for reusable user-confirmed evidence
- integrates Gmail job-alert ingestion via Gmail OAuth, with IMAP fallback kept only for transition cases

## Architecture

- `job_agent/`: backend application, routers, services, models, worker, CLI
- `frontend/`: templates, CSS, and browser-side JavaScript
- `config/`: committed examples and templates
- runtime workspace: OS app-data directory for the current user, or `JOB_AGENT_HOME` if set

Runtime defaults:

- SQLite database: `<app-data>/job_agent.db`
- user settings: `<app-data>/config/user_settings.yml`
- generated artifacts: `<app-data>/generated/`
- backups: `<app-data>/backups/`

## Quick start

```bash
cp .env.example .env
pip install -e ".[dev]"
uvicorn job_agent.main:app --host 127.0.0.1 --port 8000 --reload
python -m job_agent.worker
```

Health checks:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/providers
```

You can also start the stack from the CLI:

```bash
job-agent start
```

## First-run flow

Open:

- [http://127.0.0.1:8000/ui](http://127.0.0.1:8000/ui)

The app keeps core workflow pages gated until setup is complete:

1. create the owner profile
2. connect an AI provider
3. ingest profile or fact-sheet material
4. answer missing questions
5. choose target roles, countries, and job-description languages

That prevents the empty-workspace problem where a user reaches the middle of the app before the system has enough truth to be useful.

## Frontend collaboration

Frontend work lives in `frontend/`.

- templates: `frontend/templates/`
- shared CSS: `frontend/static/app.css`
- page logic: `frontend/static/*.js`

If you are changing page behavior, prefer moving or extending JavaScript in `frontend/static/` instead of growing large inline template scripts.

See `frontend/README.md` for the frontend map.

## Key backend areas

- `job_agent/main.py`: app startup and router assembly
- `job_agent/routers/`: HTTP routes split by domain
- `job_agent/services/workflows.py`: draft generation pipeline
- `job_agent/services/prompts.py`: writer, reviewer, reviser, and enhancement prompts
- `job_agent/config.py`: settings and overlay loading
- `job_agent/db.py`: SQLite engine, schema preparation, additive migrations
- `job_agent/runtime_paths.py`: cross-platform workspace locations

## Current product shape

- single-owner workspace with setup gating before core actions unlock
- cloud BYOK onboarding with OpenAI recommended, Claude supported, and local providers available as advanced options
- Gmail OAuth setup for LinkedIn alert ingestion
- review-first jobs queue with discovery health, freshness, and legitimacy signals
- application package checks before CV drafting
- career tools including Story Bank, Opportunity Snapshot, and Offer Compass

## Development checks

```bash
python -m pytest --tb=short -q
ruff check
```

## Packaging note

The runtime serves templates and static assets from the top-level `frontend/` directory. Wheel builds explicitly include that directory, so installed builds still have the UI assets available.
