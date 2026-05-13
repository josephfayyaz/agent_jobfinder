from __future__ import annotations

import logging
import time

from job_agent.config import reload_settings_from_sources, settings
from job_agent.db import SessionLocal, prepare_database
from job_agent.models import WorkflowTask
from job_agent.seed import seed_reference_data
from job_agent.services.job_fetcher import JobFetcher
from job_agent.services.workflows import CVWorkflowService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

_last_enrichment = 0.0
_ENRICHMENT_INTERVAL = 3600


def _run_one_iteration(session=None) -> None:
    global _last_enrichment

    reload_settings_from_sources(settings)
    seed_reference_data(session)
    service = CVWorkflowService(session)
    pending_task = (
        session.query(WorkflowTask)
        .filter(WorkflowTask.status == "pending")
        .order_by(WorkflowTask.created_at.asc())
        .first()
    )
    if pending_task is not None:
        logger.info("Picked up task %s (kind=%s)", pending_task.id, pending_task.kind)
        task = service.process_next_task()
        if task is not None and task.status == "completed":
            logger.info("Task %s completed | result=%s", task.id, task.result)
        elif task is not None and task.status == "failed":
            logger.error("Task %s failed | error=%s", task.id, task.error_message)
        return

    now = time.time()
    if now - _last_enrichment >= _ENRICHMENT_INTERVAL:
        enriched = JobFetcher().enrich_pending_parallel(session, limit=10)
        _last_enrichment = now
        if enriched:
            logger.info("Worker LinkedIn enrichment updated %d jobs", enriched)
    logger.debug("No pending tasks, sleeping %ds", settings.worker_poll_seconds)


def main() -> None:
    try:
        prepare_database()
    except Exception:
        logger.exception("Worker: database setup failed. Exiting.")
        raise
    while True:
        try:
            with SessionLocal() as session:
                _run_one_iteration(session)
        except Exception:
            logger.exception("Worker iteration crashed — will retry after sleep.")
        time.sleep(settings.worker_poll_seconds)


if __name__ == "__main__":
    main()
