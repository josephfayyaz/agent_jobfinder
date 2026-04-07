# Local LLM Job Agent

This project is a local-first scaffold for a multi-role job search assistant.

It is built around:

- `LM Studio` running on the Mac host for local models
- `Postgres` in Docker for durable state
- `FastAPI` for orchestration
- a background worker for CV generation and review workflows

## What this first cut does

- seeds four active resume tracks:
  - junior data engineer / analytics engineer
  - junior data analyst / BI / product data analyst
  - junior AI / machine learning engineer
  - junior cloud ML engineer / MLOps / AI platform
- stores a structured master profile
- ingests a fact sheet into normalized Postgres tables
- stores job descriptions and extracted metadata
- stores compliant public job-source registry entries for Italy + EU
- stores application and communication tracking events
- exports the current job/application state to CSV on disk
- creates CV workflow tasks
- drafts a tailored CV with a local provider when available
- reviews the draft with OpenAI when configured, otherwise falls back to heuristic review
- escalates low-scoring drafts for a stronger rewrite when configured
- renders a `.tex` artifact for each draft

## Stack layout

- `LM Studio` stays on the host so it can use Apple-native inference paths.
- Docker runs:
  - `db`
  - `api`
  - `worker`

## Quick start

1. Start the stack:

```bash
docker compose up --build -d
```

2. Check health:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/providers
```

3. Read the seeded resume tracks:

```bash
curl http://localhost:8000/tracks
curl http://localhost:8000/job-sources
```

4. Ingest the fact sheet as the source of truth:

```bash
jq -Rs --arg source_path "/absolute/path/to/master_fact_sheet.txt" \
  '{source_path:$source_path, content:.}' /absolute/path/to/master_fact_sheet.txt \
  | curl -X POST http://localhost:8000/fact-sources/ingest \
      -H 'Content-Type: application/json' \
      --data-binary @-
```

5. Inspect the imported profile:

```bash
curl http://localhost:8000/profile
curl http://localhost:8000/fact-sources/latest
```

6. Update the master profile manually only if needed:

```bash
curl -X PUT http://localhost:8000/profile \
  -H 'Content-Type: application/json' \
  -d @examples/profile.example.json
```

7. Create a job:

```bash
curl -X POST http://localhost:8000/jobs \
  -H 'Content-Type: application/json' \
  -d @examples/job.example.json
```

You can also inspect the automatic role recommendation for any saved job:

```bash
curl http://localhost:8000/jobs/<JOB_ID>/track-fit
```

8. Create an application record and track emails:

```bash
curl -X POST http://localhost:8000/applications \
  -H 'Content-Type: application/json' \
  -d '{"job_post_id":"<JOB_ID>","resume_track_slug":"data-engineering-analytics","status":"shortlisted","next_action":"Tailor resume and submit"}'

curl -X POST http://localhost:8000/applications/<APPLICATION_ID>/communications \
  -H 'Content-Type: application/json' \
  -d '{"sender_name":"Recruiting Team","sender_email":"jobs@example.com","subject":"Application received","snippet":"We received your application."}'
```

9. Export the tracked job state to CSV:

```bash
curl -X POST http://localhost:8000/exports/jobs-csv
curl http://localhost:8000/exports
```

10. Queue a CV workflow task:

```bash
curl -X POST http://localhost:8000/tasks/cv-workflow \
  -H 'Content-Type: application/json' \
  -d '{"job_post_id":"<JOB_ID>","resume_track_slug":"ai-ml-engineering","force_cloud_review":true}'
```

11. Poll the task:

```bash
curl http://localhost:8000/tasks/<TASK_ID>
```

## LM Studio setup

Install and run `LM Studio`, then load:

- one smaller model for control and revisions
- one larger writer model such as `Qwen3.5-27B`

After loading them, set in `.env`:

- `LM_STUDIO_SMALL_MODEL`
- `LM_STUDIO_WRITER_MODEL`

Then enable the local server. The default host URL in this project is:

- `http://host.docker.internal:1234/v1`

## OpenAI setup

If you want cloud review and escalation:

- set `OPENAI_API_KEY`
- keep `USE_OPENAI_REVIEW=true`
- optionally set `USE_OPENAI_ESCALATION=true`

The default models are:

- review: `gpt-5.4`
- escalation: `gpt-5.3-codex`

## Current scope

This is an implementation foundation, not the full finished system yet.

Still pending:

- live job board connectors that pull postings into `job_posts`
- email sync
- LinkedIn and GitHub content workflows
- browser submission via Playwright
- PDF compilation from the TeX artifacts
