from __future__ import annotations

import logging
import time

from job_agent.config import reload_settings_from_sources, settings
from job_agent.db import SessionLocal, prepare_database
from job_agent.models import WorkflowTask
from job_agent.seed import seed_reference_data
from job_agent.services.career_scanner import CareerPageScanner
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
_last_career_scan = 0.0
_last_jobspy_discover = 0.0
_ENRICHMENT_INTERVAL = 3600
_CAREER_SCAN_INTERVAL = 86400


def _run_one_iteration(session=None) -> None:
    global _last_gmail_sync, _last_enrichment, _last_career_scan, _last_jobspy_discover

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
    if settings.gmail_auto_sync and (now - _last_gmail_sync) >= settings.gmail_sync_interval_minutes * 60:
        synced_posts = GmailService().sync_jobs(session)
        _last_gmail_sync = now
        if synced_posts:
            logger.info("Worker Gmail sync created %d jobs", len(synced_posts))
    if now - _last_enrichment >= _ENRICHMENT_INTERVAL:
        enriched = JobFetcher().enrich_pending_parallel(session, limit=10)
        _last_enrichment = now
        if enriched:
            logger.info("Worker LinkedIn enrichment updated %d jobs", enriched)
    if now - _last_career_scan >= _CAREER_SCAN_INTERVAL:
        scanner = CareerPageScanner()
        new_jobs = scanner.scan_all_parallel(session)
        _last_career_scan = now
        if new_jobs:
            logger.info("Worker career page scan created %d jobs", new_jobs)
        spikes = scanner.check_velocity_spikes(session) or []
        for spike in spikes:
            logger.warning(
                "VELOCITY SPIKE: %s added %d new jobs at %s - apply soon!",
                spike.get("company", "unknown"),
                spike.get("new_jobs", 0),
                spike.get("scanned_at", ""),
            )
    if (
        settings.use_jobspy
        and settings.jobspy_discover_interval_hours > 0
        and (now - _last_jobspy_discover) >= settings.jobspy_discover_interval_hours * 3600
    ):
        from job_agent.services.jobspy_service import JobSpyService

        total_new = 0
        for query in settings.jobspy_discover_queries:
            new = JobSpyService().discover(
                query=query,
                location=settings.jobspy_discover_location,
                session=session,
                limit=settings.jobspy_default_limit,
            )
            total_new += new
        _last_jobspy_discover = now
        if total_new:
            logger.info("Worker JobSpy discovery added %d new jobs", total_new)
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
