# Spec: Phase 4.1 — Add Structured Logging
Status: pending

## Context
The application runs completely silently. No logs means no visibility into what the
worker is doing, which model was called, what scores were produced, or why a task
failed. Add Python stdlib `logging` throughout.

Important: `llm.py` already has a logger defined (`logger = logging.getLogger(__name__)`).
Do not add a second one there. Only add log calls where they are missing.

## Changes

### File: `job_agent/worker.py`
Read the file first. Add logging setup at the top and log statements for task lifecycle.

After the existing imports, add:
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)
```

Inside the poll loop, before processing a task add:
```python
logger.info("Picked up task %s (kind=%s)", task.id, task.kind)
```
After a task completes (status == "completed"), add:
```python
logger.info("Task %s completed | result=%s", task.id, task.result)
```
After a task fails (status == "failed"), add:
```python
logger.error("Task %s failed | error=%s", task.id, task.error_message)
```
When no tasks are found (idle), add at DEBUG level:
```python
logger.debug("No pending tasks, sleeping %ds", settings.worker_poll_seconds)
```

### File: `job_agent/services/workflows.py`
Read the file first. Add at the top after existing imports:
```python
import logging
logger = logging.getLogger(__name__)
```

In `run_cv_workflow()`, after generating the draft add:
```python
logger.info("Draft generated | provider=%s | job=%s", draft_provider, payload.get("job_post_id"))
```

After reviewing the draft add:
```python
logger.info(
    "Draft reviewed | score=%.0f | decision=%s",
    review.get("score", 0),
    review.get("decision", "unknown"),
)
```

After the final decision (just before creating ResumeDraft) add:
```python
logger.info("Final draft | provider=%s | score=%.0f", final_provider, float(review["score"]))
```

### File: `job_agent/main.py`
Read the file first. Add near the top of the file (after imports, before `app = FastAPI()`):
```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
```

Note: `llm.py` already has `logger = logging.getLogger(__name__)` and log calls —
do NOT change `llm.py`.

## Verification
```bash
# Restart the worker and queue a task — you should see log output in the terminal
python -m job_agent.worker
# Expected: lines like:
# 2026-04-08T14:00:00 [INFO] job_agent.worker: Picked up task abc123 (kind=cv_workflow)
# 2026-04-08T14:03:00 [INFO] job_agent.services.workflows: Draft reviewed | score=91 | decision=pass

/Users/youseffayyaz/miniforge3/bin/conda run -n ML python -m ruff check job_agent/
# Expected: no errors
```

## Git
```bash
git add job_agent/worker.py job_agent/services/workflows.py job_agent/main.py
git commit -m "feat: add structured logging to worker, workflows, and API

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```
