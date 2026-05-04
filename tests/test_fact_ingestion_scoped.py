"""Tests that FactSheetIngestionService only deletes facts for the ingested source."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from job_agent.db import Base
from job_agent.models import (
    EducationFact,
    ExperienceFact,
    FactSource,
    ProjectFact,
)
from job_agent.services.fact_ingestion import FactSheetIngestionService


@pytest.fixture
def db_session(tmp_path):
    db_file = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = Session()
    yield session
    session.close()
    engine.dispose()


_MINIMAL_FACT_SHEET = """
SECTION: CORE PROFILE
FULL_NAME: Test User
PRIMARY_EMAIL: test@example.com
PHONE: +39 000 000 0000
CURRENT_LOCATION: Turin, Italy
CURRENT_POSITIONING: Data Engineer

SECTION: PROFESSIONAL EXPERIENCE
ITEM_ID: exp-1
ROLE_TITLE: Data Engineer
ORGANIZATION: ACME Corp
START_DATE: 2022-01
END_DATE: 2023-12
VERIFIED_CORE_FACTS:
- Built ETL pipelines using Python and Airflow
TOOLS_AND_TECH:
- Python
- Airflow

SECTION: EDUCATION
ITEM_ID: edu-1
INSTITUTION: Example University
DEGREE: MSc Computer Engineering
START_DATE: 2023-09
END_DATE: 2026-06

SECTION: PROJECTS
ITEM_ID: proj-1
PROJECT_NAME: Job Agent
SHORT_RESUME_LINE: Local LLM job search assistant
TOOLS_AND_TECH:
- Python
- FastAPI
"""


def test_second_ingest_does_not_delete_unrelated_source_facts(db_session):
    """Ingesting source B must not delete facts that belong to source A."""
    svc = FactSheetIngestionService(db_session)

    # Ingest source A.
    svc.ingest(content=_MINIMAL_FACT_SHEET, source_path="source_a.txt")
    source_a = db_session.query(FactSource).filter_by(source_path="source_a.txt").first()
    assert source_a is not None

    a_edu_count = db_session.query(EducationFact).filter_by(
        fact_source_id=source_a.id
    ).count()
    a_exp_count = db_session.query(ExperienceFact).filter_by(
        fact_source_id=source_a.id
    ).count()
    a_proj_count = db_session.query(ProjectFact).filter_by(
        fact_source_id=source_a.id
    ).count()
    assert a_edu_count > 0
    assert a_exp_count > 0
    assert a_proj_count > 0

    # Ingest source B (different path, different item IDs to avoid global unique collisions).
    source_b_sheet = (
        _MINIMAL_FACT_SHEET.replace("exp-1", "exp-2")
        .replace("edu-1", "edu-2")
        .replace("proj-1", "proj-2")
    )
    svc.ingest(content=source_b_sheet, source_path="source_b.txt")

    # Source A's facts must still exist.
    assert (
        db_session.query(EducationFact).filter_by(fact_source_id=source_a.id).count()
        == a_edu_count
    )
    assert (
        db_session.query(ExperienceFact).filter_by(fact_source_id=source_a.id).count()
        == a_exp_count
    )
    assert (
        db_session.query(ProjectFact).filter_by(fact_source_id=source_a.id).count()
        == a_proj_count
    )


def test_re_ingest_same_source_replaces_own_facts(db_session):
    """Re-ingesting the same source must clear and rewrite its own facts."""
    svc = FactSheetIngestionService(db_session)

    svc.ingest(content=_MINIMAL_FACT_SHEET, source_path="source_a.txt")
    source_a = db_session.query(FactSource).filter_by(source_path="source_a.txt").first()
    assert source_a is not None

    count_before = db_session.query(EducationFact).filter_by(
        fact_source_id=source_a.id
    ).count()
    assert count_before > 0

    svc.ingest(content=_MINIMAL_FACT_SHEET, source_path="source_a.txt")
    count_after = db_session.query(EducationFact).filter_by(
        fact_source_id=source_a.id
    ).count()
    assert count_after == count_before
