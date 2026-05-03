"""Tests for job_agent/seed.py — resume-track and job-source seeding."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from job_agent.db import Base
from job_agent.models import JobSource, ResumeTrack
from job_agent.seed import seed_reference_data


@pytest.fixture
def seed_session():
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


def test_seed_creates_eight_resume_tracks(seed_session):
    seed_reference_data(seed_session)
    tracks = seed_session.query(ResumeTrack).filter(ResumeTrack.active.is_(True)).all()
    assert len(tracks) == 8


def test_seed_resume_tracks_have_expected_slugs(seed_session):
    seed_reference_data(seed_session)
    slugs = {track.slug for track in seed_session.query(ResumeTrack).filter(ResumeTrack.active.is_(True)).all()}
    expected = {
        "data-engineering-analytics",
        "data-analyst-bi-product",
        "consulting-strategy-operations",
        "finance-fpa-accounting",
        "sales-business-development",
        "operations-process-improvement",
        "ai-ml-engineering",
        "cloud-mlops-ai-platform",
    }
    assert expected.issubset(slugs)


def test_seed_is_idempotent(seed_session):
    seed_reference_data(seed_session)
    seed_reference_data(seed_session)
    tracks = seed_session.query(ResumeTrack).filter(ResumeTrack.active.is_(True)).all()
    assert len(tracks) == 8


def test_seed_creates_job_sources(seed_session):
    seed_reference_data(seed_session)
    sources = seed_session.query(JobSource).all()
    assert len(sources) >= 2


def test_seed_job_sources_include_linkedin(seed_session):
    seed_reference_data(seed_session)
    names = [source.name.lower() for source in seed_session.query(JobSource).all()]
    assert any("linkedin" in name for name in names)


def test_seed_resume_tracks_have_target_keywords(seed_session):
    seed_reference_data(seed_session)
    tracks = seed_session.query(ResumeTrack).filter(ResumeTrack.active.is_(True)).all()
    for track in tracks:
        assert track.target_keywords, f"Track {track.slug} has no target_keywords"
