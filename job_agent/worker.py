from __future__ import annotations

import logging
import time

from job_agent.config import settings
from job_agent.db import SessionLocal, prepare_database
from job_agent.models import WorkflowTask
from job_agent.seed import seed_reference_data
from job_agent.services.gmail import GmailService
from job_agent.services.job_fetcher import JobFetcher
from job_agent.services.workflows import CVWorkflowService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

_last_gmail_sync = 0.0
_last_enrichment = 0.0
_ENRICHMENT_INTERVAL = 3600


def _run_one_iteration(session=None) -> None:
    global _last_gmail_sync, _last_enrichment

    seed_reference_data(session)
    now = time.time()
    if settings.gmail_auto_sync and (now - _last_gmail_sync) >= settings.gmail_sync_interval_minutes * 60:
        synced_posts = GmailService().sync_jobs(session)
        _last_gmail_sync = now
        if synced_posts:
            logger.info("Worker Gmail sync created %d jobs", len(synced_posts))
    if now - _last_enrichment >= _ENRICHMENT_INTERVAL:
        enriched = JobFetcher().enrich_pending(session, limit=10)
        _last_enrichment = now
        if enriched:
            logger.info("Worker LinkedIn enrichment updated %d jobs", enriched)
    service = CVWorkflowService(session)
    pending_task = (
        session.query(WorkflowTask)
        .filter(WorkflowTask.status == "pending")
        .order_by(WorkflowTask.created_at.asc())
        .first()
    )
    if pending_task is None:
        logger.debug("No pending tasks, sleeping %ds", settings.worker_poll_seconds)
    else:
        logger.info("Picked up task %s (kind=%s)", pending_task.id, pending_task.kind)
        task = service.process_next_task()
        if task is not None and task.status == "completed":
            logger.info("Task %s completed | result=%s", task.id, task.result)
        elif task is not None and task.status == "failed":
            logger.error("Task %s failed | error=%s", task.id, task.error_message)


def main() -> None:
    prepare_database()
    while True:
        with SessionLocal() as session:
            _run_one_iteration(session)
        time.sleep(settings.worker_poll_seconds)


if __name__ == "__main__":
    main()
