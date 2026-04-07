from __future__ import annotations

import time

from job_agent.config import settings
from job_agent.db import SessionLocal, prepare_database
from job_agent.seed import seed_reference_data
from job_agent.services.workflows import CVWorkflowService


def main() -> None:
    prepare_database()
    while True:
        with SessionLocal() as session:
            seed_reference_data(session)
            service = CVWorkflowService(session)
            service.process_next_task()
        time.sleep(settings.worker_poll_seconds)


if __name__ == "__main__":
    main()
