from __future__ import annotations

from job_agent.models import EvidenceIndexItem, FactConflict, FactSheetChangeLog
from job_agent.services.fact_sheet_json import FactSheetJsonIngestionService


_BASE_FACT_SHEET = {
    "person": {
        "full_name": "Test User",
        "contact": {"email": "test@example.com"},
    },
    "match_profile": {
        "target_roles": ["Data Engineer"],
        "work_authorization": "EU",
        "location_preferences": {"preferred_countries": ["Italy"]},
        "availability": {"status": "available", "earliest_start_date": "2026-06-01"},
        "employment_preferences": {"full_time": True},
    },
    "experience": [
        {
            "role_title": "Data Engineer",
            "organization": "ACME Corp",
            "responsibilities": ["Built ETL pipelines", "Automated checks"],
            "tools": ["Python"],
            "achievements": [],
            "evidence_refs": [],
        }
    ],
    "projects": [
        {
            "name": "Analytics Dashboard",
            "summary": "Built an internal dashboard for weekly metrics",
            "tools": ["Superset"],
        }
    ],
    "education": [
        {
            "degree": "MSc Computer Engineering",
            "institution": "Example University",
            "status": "completed",
        }
    ],
    "skills": {"business_tools": ["Excel"]},
    "languages": [{"name": "English", "level": "C1"}],
    "completion_status": "usable_with_gaps",
    "confidence_summary": {},
    "missing_information": [],
    "conflicts": [],
    "evidence_index": [],
    "change_log": [],
}


def test_structured_ingestion_derives_evidence_and_change_log_and_conflicts(db_session):
    service = FactSheetJsonIngestionService(db_session)

    first = service.ingest_json(candidate_id=None, fact_sheet=_BASE_FACT_SHEET, source_name="initial_upload")
    replacement_sheet = {
        **_BASE_FACT_SHEET,
        "person": {
            "full_name": "Replacement User",
            "contact": {"email": "replacement@example.com"},
        },
    }

    service.ingest_json(
        candidate_id=first.candidate_id,
        fact_sheet=replacement_sheet,
        source_name="review_save",
    )

    conflicts = db_session.query(FactConflict).filter_by(candidate_id=first.candidate_id).all()
    evidence_rows = db_session.query(EvidenceIndexItem).filter_by(candidate_id=first.candidate_id).all()
    change_rows = db_session.query(FactSheetChangeLog).filter_by(candidate_id=first.candidate_id).all()

    assert any(item.field == "person.full_name" for item in conflicts)
    assert any(item.source_type == "experience" for item in evidence_rows)
    assert any("review_save" in item.message for item in change_rows)
