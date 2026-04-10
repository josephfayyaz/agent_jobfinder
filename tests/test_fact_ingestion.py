"""Tests for fact sheet ingestion deduplication and replacement."""

from __future__ import annotations

from job_agent.models import EducationFact, ExperienceFact, FactSource, ProjectFact
from job_agent.services.fact_ingestion import FactSheetIngestionService

SAMPLE_FACT_SHEET = """
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
- Reduced query latency by 30% via index optimization
TOOLS_AND_TECH:
- Python
- Airflow

SECTION: EDUCATION
ITEM_ID: edu-1
INSTITUTION: Politecnico di Torino
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
- PostgreSQL
"""


def test_ingest_creates_fact_source(db_session, tmp_path):
    """Ingestion creates a FactSource record with content hash."""
    svc = FactSheetIngestionService(db_session)
    fact_file = tmp_path / "fact_sheet.txt"
    fact_file.write_text(SAMPLE_FACT_SHEET, encoding="utf-8")

    svc.ingest(str(fact_file), SAMPLE_FACT_SHEET)

    source = db_session.query(FactSource).first()
    assert source is not None
    assert source.source_hash is not None


def test_ingest_creates_experience_fact(db_session, tmp_path):
    """Ingestion parses experience content into ExperienceFact records."""
    svc = FactSheetIngestionService(db_session)
    fact_file = tmp_path / "fact_sheet.txt"
    fact_file.write_text(SAMPLE_FACT_SHEET, encoding="utf-8")

    svc.ingest(str(fact_file), SAMPLE_FACT_SHEET)

    exp = db_session.query(ExperienceFact).filter_by(organization="ACME Corp").first()
    assert exp is not None
    assert exp.role_title == "Data Engineer"
    assert len(exp.verified_core_facts or []) >= 1


def test_ingest_creates_education_and_project_facts(db_session, tmp_path):
    """Ingestion populates education and project facts from the parsed sections."""
    svc = FactSheetIngestionService(db_session)
    fact_file = tmp_path / "fact_sheet.txt"
    fact_file.write_text(SAMPLE_FACT_SHEET, encoding="utf-8")

    svc.ingest(str(fact_file), SAMPLE_FACT_SHEET)

    edu = db_session.query(EducationFact).filter_by(institution="Politecnico di Torino").first()
    proj = db_session.query(ProjectFact).filter_by(project_name="Job Agent").first()
    assert edu is not None
    assert proj is not None


def test_ingest_deduplicate_by_hash(db_session, tmp_path):
    """Ingesting the same content twice does not create duplicate records."""
    svc = FactSheetIngestionService(db_session)
    fact_file = tmp_path / "fact_sheet.txt"
    fact_file.write_text(SAMPLE_FACT_SHEET, encoding="utf-8")

    svc.ingest(str(fact_file), SAMPLE_FACT_SHEET)
    svc.ingest(str(fact_file), SAMPLE_FACT_SHEET)

    count = db_session.query(FactSource).count()
    assert count == 1


def test_ingest_replaces_old_facts_on_update(db_session, tmp_path):
    """Ingesting updated content clears old facts and replaces them with new ones."""
    svc = FactSheetIngestionService(db_session)
    fact_file = tmp_path / "fact_sheet.txt"
    fact_file.write_text(SAMPLE_FACT_SHEET, encoding="utf-8")
    svc.ingest(str(fact_file), SAMPLE_FACT_SHEET)

    updated_sheet = SAMPLE_FACT_SHEET.replace("ACME Corp", "NewCo")
    fact_file.write_text(updated_sheet, encoding="utf-8")
    svc.ingest(str(fact_file), updated_sheet)

    old_exp = db_session.query(ExperienceFact).filter_by(organization="ACME Corp").first()
    new_exp = db_session.query(ExperienceFact).filter_by(organization="NewCo").first()
    assert old_exp is None
    assert new_exp is not None
