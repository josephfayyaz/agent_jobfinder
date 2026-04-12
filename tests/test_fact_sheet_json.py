from __future__ import annotations

import pytest

from job_agent.models import (
    Candidate,
    EvidenceIndexItem,
    ExperienceFact,
    FactConflict,
    MatchProfile,
    MasterProfile,
)
from job_agent.services.fact_sheet_json import FactSheetJsonIngestionService

_MINIMAL_FACT_SHEET = {
    "person": {
        "full_name": "Test User",
        "contact": {"email": "test@example.com"},
    },
    "match_profile": {
        "target_roles": ["Data Engineer"],
        "work_authorization": "EU",
        "location_preferences": {
            "preferred_countries": ["Italy", "Germany"],
            "remote_preference": "hybrid",
        },
        "availability": {
            "status": "available",
            "earliest_start_date": "2026-06-01",
        },
        "employment_preferences": {"full_time": True, "internship": True},
    },
    "experience": [
        {
            "role_title": "Data Engineer",
            "organization": "ACME Corp",
            "start_date": "2022-01",
            "end_date": None,
            "responsibilities": ["built ETL pipelines", "wrote Python scripts"],
            "tools": ["python", "airflow"],
            "achievements": [],
            "verification_status": "verified",
        }
    ],
    "education": [
        {
            "degree": "MSc Computer Engineering",
            "institution": "Politecnico di Torino",
            "start_date": "2023-09",
            "end_date": None,
            "status": "in_progress",
        }
    ],
    "skills": {
        "programming_languages": ["Python", "SQL"],
        "frameworks_and_platforms": ["FastAPI", "Airflow"],
        "cloud_and_infra": ["Docker", "AWS S3"],
        "data_and_analytics": ["dbt", "Spark"],
        "business_tools": [],
        "methods": ["Agile"],
    },
    "languages": [
        {"name": "English", "level": "C1"},
        {"name": "Italian", "level": "B2"},
    ],
    "completion_status": "usable_with_gaps",
    "confidence_summary": {
        "overall_confidence": "high",
        "notes": ["CV cross-referenced with LinkedIn"],
    },
    "missing_information": ["GitHub URL"],
    "conflicts": [],
    "evidence_index": [],
    "projects": [
        {
            "name": "Analytics Dashboard",
            "summary": "Real-time metrics board built with Superset",
            "tools": ["Superset", "PostgreSQL"],
        }
    ],
}


def test_ingest_json_creates_candidate_and_match_profile(db_session):
    service = FactSheetJsonIngestionService(db_session)

    result = service.ingest_json(candidate_id=None, fact_sheet=_MINIMAL_FACT_SHEET)

    assert result.candidate_id
    candidate = db_session.get(Candidate, result.candidate_id)
    assert candidate is not None
    assert candidate.full_name == "Test User"
    match_profile = db_session.query(MatchProfile).filter_by(candidate_id=result.candidate_id).first()
    assert match_profile is not None
    assert match_profile.target_roles == ["Data Engineer"]
    assert match_profile.work_authorization == "EU"


def test_ingest_json_preserves_conflicts_and_evidence(db_session):
    service = FactSheetJsonIngestionService(db_session)
    fact_sheet = {
        **_MINIMAL_FACT_SHEET,
        "conflicts": [{"field": "title", "source_a": "CV", "source_b": "LinkedIn", "note": ""}],
        "evidence_index": [{"source_type": "CV", "source_name": "cv.pdf", "quote_or_summary": "..."}],
    }

    result = service.ingest_json(candidate_id=None, fact_sheet=fact_sheet)

    assert db_session.query(FactConflict).filter_by(candidate_id=result.candidate_id).count() == 1
    assert db_session.query(EvidenceIndexItem).filter_by(candidate_id=result.candidate_id).count() == 1


def test_ingest_json_is_idempotent(db_session):
    service = FactSheetJsonIngestionService(db_session)

    result = service.ingest_json(candidate_id=None, fact_sheet=_MINIMAL_FACT_SHEET)
    service.ingest_json(candidate_id=result.candidate_id, fact_sheet=_MINIMAL_FACT_SHEET)

    count = db_session.query(ExperienceFact).filter_by(candidate_id=result.candidate_id).count()
    assert count == 1


def test_export_json_roundtrip(db_session):
    service = FactSheetJsonIngestionService(db_session)

    result = service.ingest_json(candidate_id=None, fact_sheet=_MINIMAL_FACT_SHEET)
    exported = service.export_json(result.candidate_id)

    assert exported["person"]["full_name"] == "Test User"
    assert exported["person"]["contact"]["email"] == "test@example.com"
    assert exported["experience"][0]["role_title"] == "Data Engineer"
    assert "built ETL pipelines" in exported["experience"][0]["responsibilities"]
    assert exported["match_profile"]["target_roles"] == ["Data Engineer"]
    for key in (
        "person",
        "match_profile",
        "experience",
        "education",
        "skills",
        "languages",
        "completion_status",
        "confidence_summary",
        "missing_information",
        "conflicts",
        "evidence_index",
    ):
        assert key in exported


def test_legacy_profile_endpoint_still_works_after_migration(client, db_session):
    db_session.add(MasterProfile(id=1, full_name="Legacy User"))
    db_session.commit()

    response = client.get("/profile")

    assert response.status_code == 200
    assert response.json()["full_name"] == "Legacy User"


def test_invalid_json_rejected_with_jsonschema_error(db_session):
    service = FactSheetJsonIngestionService(db_session)

    with pytest.raises(Exception) as excinfo:
        service.ingest_json(None, {"totally": "wrong"})
    assert excinfo.value.__class__.__name__ == "ValidationError"

    with pytest.raises(Exception) as excinfo:
        service.ingest_json(None, {"person": {"full_name": "X"}})
    assert excinfo.value.__class__.__name__ == "ValidationError"
