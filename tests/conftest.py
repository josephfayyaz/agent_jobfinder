"""Shared pytest fixtures."""
from __future__ import annotations

from datetime import datetime, timezone
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from job_agent.db import Base


@pytest.fixture(autouse=True)
def _clear_default_candidate_id():
    """Reset runtime settings that should not leak in from the local .env.

    The real .env may set a user-specific candidate UUID and DATABASE_URL that
    do not exist in the test SQLite DB. Clearing them keeps tests hermetic and
    forces workflow tests to fall back to MasterProfile fixtures.
    """
    import job_agent.config as cfg

    original_candidate_id = cfg.settings.default_candidate_id
    original_database_url = cfg.settings.database_url
    original_app_env = cfg.settings.app_env
    original_provider_mode = getattr(cfg.settings, "llm_provider_mode", "local")
    original_job_search_languages = getattr(cfg.settings, "job_search_languages", [])
    original_job_search_countries = getattr(cfg.settings, "job_search_countries", ["Italy"])
    original_job_search_region = getattr(cfg.settings, "job_search_region", "")
    original_jobspy_location = getattr(cfg.settings, "jobspy_discover_location", "Italy")
    object.__setattr__(cfg.settings, "default_candidate_id", "")
    object.__setattr__(cfg.settings, "database_url", "")
    object.__setattr__(cfg.settings, "app_env", "test")
    object.__setattr__(cfg.settings, "llm_provider_mode", "local")
    object.__setattr__(cfg.settings, "job_search_languages", [])
    object.__setattr__(cfg.settings, "job_search_countries", ["Italy"])
    object.__setattr__(cfg.settings, "job_search_region", "")
    object.__setattr__(cfg.settings, "jobspy_discover_location", "Italy")
    yield
    object.__setattr__(cfg.settings, "default_candidate_id", original_candidate_id)
    object.__setattr__(cfg.settings, "database_url", original_database_url)
    object.__setattr__(cfg.settings, "app_env", original_app_env)
    object.__setattr__(cfg.settings, "llm_provider_mode", original_provider_mode)
    object.__setattr__(cfg.settings, "job_search_languages", original_job_search_languages)
    object.__setattr__(cfg.settings, "job_search_countries", original_job_search_countries)
    object.__setattr__(cfg.settings, "job_search_region", original_job_search_region)
    object.__setattr__(cfg.settings, "jobspy_discover_location", original_jobspy_location)


class AttrDict(dict):
    """Dict with attribute access for tests that use dot notation."""

    def __getattr__(self, key: str):
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(key) from exc

    def __setattr__(self, key: str, value):
        self[key] = value

@pytest.fixture
def db_session():
    import job_agent.models  # noqa: F401

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session, monkeypatch):
    from fastapi.testclient import TestClient

    from job_agent.db import get_db
    from job_agent.main import app

    def _override_get_db():
        yield db_session

    monkeypatch.setattr("job_agent.main.prepare_database", lambda: None)
    monkeypatch.setattr("job_agent.main.seed_reference_data", lambda _session: None)
    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def sample_job() -> dict:
    return AttrDict({
        "id": uuid.uuid4(),
        "company": "TestCo",
        "title": "Data Engineer",
        "description": (
            "We need strong Python, SQL, dbt, Airflow, and PostgreSQL skills. "
            "Experience with ETL pipelines and data warehousing required."
        ),
        "location": "Turin, Italy",
    })


@pytest.fixture
def sample_profile() -> dict:
    return {
        "full_name": "Test User",
        "email": "test@example.com",
        "phone": "+1 000 000 0000",
        "location": "Milan, Italy",
        "linkedin_url": "https://linkedin.com/in/testuser",
        "github_url": "https://github.com/testuser",
        "public_brand_summary": "Data engineer with 3 years of experience.",
        "experiences": [
            {
                "title": "Data Engineer",
                "company": "Acme Corp",
                "location": "Milan, Italy",
                "summary": "Built ETL pipelines.",
                "bullets": ["Built ETL pipeline in Python reducing latency by 30%."],
                "skills": ["Python", "SQL", "Airflow"],
                "tags": ["data-engineering"],
            }
        ],
        "projects": [
            {
                "name": "Data Pipeline Project",
                "summary": "End-to-end data pipeline.",
                "bullets": ["Processed 1M records daily using Apache Airflow."],
                "skills": ["Python", "Airflow", "PostgreSQL"],
                "repo_url": "https://github.com/testuser/pipeline",
                "tags": ["data-engineering"],
            }
        ],
        "education": [
            {
                "degree": "Master of Science",
                "field": "Data Science",
                "institution": "Test University",
                "status": "Completed",
                "presentation": "MSc Data Science, Test University",
            }
        ],
        "global_skills": ["Python", "SQL", "dbt", "Airflow", "PostgreSQL"],
        "certifications": [],
        "achievements": [],
        "additional_notes": "",
    }


@pytest.fixture
def sample_track():
    """A minimal resume track object (plain dict, not ORM)."""

    class FakeTrack:
        id = uuid.uuid4()
        slug = "data-engineering-analytics"
        title = "Data Engineer / Analytics Engineer"
        role_family = "data"
        target_keywords = ["python", "sql", "etl", "dbt", "airflow", "postgresql", "warehouse"]
        baseline_summary = "Data engineer focused on pipelines and warehousing."
        emphasis = {"focus": ["etl", "warehousing"]}
        linkedin_strategy = ""
        github_strategy = ""

    return FakeTrack()


@pytest.fixture
def db_profile(db_session, sample_profile):
    from job_agent.models import MasterProfile

    profile = MasterProfile(
        id=1,
        full_name=sample_profile["full_name"],
        email=sample_profile["email"],
        phone=sample_profile["phone"],
        location=sample_profile["location"],
        linkedin_url=sample_profile["linkedin_url"],
        github_url=sample_profile["github_url"],
        public_brand_summary=sample_profile["public_brand_summary"],
        experiences=sample_profile["experiences"],
        projects=sample_profile["projects"],
        education=sample_profile["education"],
        certifications=sample_profile["certifications"],
        achievements=sample_profile["achievements"],
        global_skills=sample_profile["global_skills"],
        additional_notes={"source": "test"},
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile


@pytest.fixture
def db_track(db_session, sample_track):
    from job_agent.models import ResumeTrack

    track = ResumeTrack(
        id=sample_track.id,
        slug=sample_track.slug,
        title=sample_track.title,
        role_family=sample_track.role_family,
        baseline_summary=sample_track.baseline_summary,
        target_keywords=sample_track.target_keywords,
        emphasis=sample_track.emphasis,
        linkedin_strategy=sample_track.linkedin_strategy,
        github_strategy=sample_track.github_strategy,
        active=True,
    )
    db_session.add(track)
    db_session.commit()
    db_session.refresh(track)
    return track


@pytest.fixture
def db_job(db_session, sample_job):
    from job_agent.models import JobPost

    job = JobPost(
        id=sample_job.id,
        company=sample_job.company,
        title=sample_job.title,
        description=sample_job.description,
        location=sample_job.location,
        source_name="manual",
        source_url="https://example.com/jobs/1",
        canonical_apply_url="https://example.com/jobs/1",
        created_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


@pytest.fixture
def sample_workflow_task(db_session, db_job, db_track):
    """A pending WorkflowTask linked to a job and a track slug."""
    from job_agent.models import WorkflowTask

    task = WorkflowTask(
        kind="cv_workflow",
        status="pending",
        payload={"job_post_id": str(db_job.id), "resume_track_slug": db_track.slug},
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task
