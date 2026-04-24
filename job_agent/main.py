from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from job_agent.config import settings
from job_agent.db import get_db, prepare_database
from job_agent.llm import LLMRouter  # noqa: F401 — kept for monkeypatch paths in tests
from job_agent.seed import seed_reference_data
from job_agent.services.career_scanner import CareerPageScanner  # noqa: F401
from job_agent.services.gmail import GmailService  # noqa: F401
from job_agent.services.job_fetcher import JobFetcher  # noqa: F401
from job_agent.services.matching import score_tracks_for_job  # noqa: F401
from job_agent.services.rejection_analytics import RejectionAnalyticsService  # noqa: F401
from job_agent.services.thesis_outreach import ThesisOutreachService  # noqa: F401
from job_agent.services.workflows import CVWorkflowService  # noqa: F401
from job_agent.frontend_paths import frontend_static_dir

from job_agent.routers._deps import _onboarding_complete
from job_agent.routers.setup_state import _user_settings_file
from job_agent.routers import applications, candidates, drafts, jobs, system, thesis

# Re-exports required by tests that import directly from job_agent.main
from job_agent.routers.thesis import (  # noqa: F401
    approve_outreach_draft,
    archive_thesis_target,
    create_thesis_target,
    update_thesis_target,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _log_startup_config_warning() -> None:
    if not settings.default_candidate_id.strip():
        logger.warning(
            "DEFAULT_CANDIDATE_ID is not set. CV workflow will fall back to MasterProfile(id=1). "
            "Set DEFAULT_CANDIDATE_ID=<uuid> in .env to use Candidate-based profiles."
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    del app
    prepare_database()
    if not _onboarding_complete():
        logger.warning(
            "%s not found. "
            "Run 'python -m job_agent.onboard' to configure the system.",
            _user_settings_file(),
        )
    _log_startup_config_warning()
    with next(get_db()) as db:
        seed_reference_data(db)
    yield


app = FastAPI(title="Job Agent API", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(frontend_static_dir())), name="static")

app.include_router(system.router)
app.include_router(jobs.router)
app.include_router(candidates.router)
app.include_router(drafts.router)
app.include_router(applications.router)
app.include_router(thesis.router)
