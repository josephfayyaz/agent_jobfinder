from __future__ import annotations

from copy import deepcopy

from job_agent.services.fact_sheet_json import FactSheetJsonIngestionService
from job_agent.services.fact_sheet_renderer import render_fact_sheet_text
from job_agent.services.resource_loader import load_render_template

_RENDER_SAMPLE = {
    "person": {
        "full_name": "Jane Doe",
        "preferred_name": "Jane",
        "headline": "Data engineer focused on ETL and analytics.",
        "current_location": {"city": "Turin", "country": "Italy"},
        "contact": {
            "email": "jane@example.com",
            "phone": "+39 000 000 0000",
            "linkedin_url": "https://linkedin.com/in/janedoe",
            "github_url": "https://github.com/janedoe",
        },
    },
    "match_profile": {
        "target_roles": ["Data Engineer"],
        "excluded_roles": ["Sales"],
        "preferred_industries": ["Data Platform"],
        "location_preferences": {
            "preferred_countries": ["Italy", "Germany"],
            "remote_preference": "hybrid",
        },
        "work_authorization": "EU",
        "availability": {"status": "available", "earliest_start_date": "2026-06-01"},
        "employment_preferences": {"full_time": True, "internship": True},
        "seniority_estimate": {"target": "junior"},
    },
    "education": [
        {
            "degree": "BSc Computer Science",
            "field": "Computer Science",
            "institution": "University of Turin",
            "location": "Turin, Italy",
            "start_date": "2018-09",
            "end_date": "2022-07",
            "status": "completed",
            "notes": "Final thesis on data systems",
        }
    ],
    "experience": [
        {
            "role_title": "Data Engineer",
            "organization": "ACME Corp",
            "location": "Turin, Italy",
            "start_date": "2022-01",
            "end_date": None,
            "current": True,
            "role_family": "Data Engineering",
            "responsibilities": ["built ETL pipelines", "wrote Python scripts"],
            "tools": ["Python", "Airflow"],
            "achievements": ["Reduced latency by 30%"],
            "evidence_refs": ["EV-001"],
            "verification_status": "verified",
        }
    ],
    "projects": [
        {
            "name": "Analytics Dashboard",
            "summary": "Real-time metrics board.",
            "tools": ["Superset", "PostgreSQL"],
            "link": "https://example.com/dashboard",
        }
    ],
    "skills": {
        "programming_languages": ["Python", "SQL"],
        "frameworks_and_platforms": ["FastAPI", "Airflow"],
        "cloud_and_infra": ["Docker", "AWS S3"],
        "data_and_analytics": ["dbt", "Spark"],
        "business_tools": ["Excel"],
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
    "missing_information": ["LinkedIn profile URL"],
    "conflicts": [
        {
            "field": "location",
            "source_a": "CV says Turin",
            "source_b": "Form says Milan",
            "note": "needs user confirmation",
        }
    ],
    "evidence_index": [
        {
            "id": "EV-001",
            "source_type": "resume",
            "source_name": "cv.pdf",
            "quote_or_summary": "Built ETL pipelines.",
        }
    ],
    "change_log": ["Initial intake 2026-04-13"],
}

_ROUNDTRIP_SAMPLE = {
    "person": {"full_name": "Test User", "contact": {"email": "test@example.com"}},
    "match_profile": {
        "target_roles": ["Data Engineer"],
        "work_authorization": "EU",
        "location_preferences": {
            "preferred_countries": ["Italy", "Germany"],
            "remote_preference": "hybrid",
        },
        "availability": {"status": "available", "earliest_start_date": "2026-06-01"},
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
    "languages": [{"name": "English", "level": "C1"}],
    "completion_status": "usable_with_gaps",
    "confidence_summary": {
        "overall_confidence": "high",
        "notes": ["CV cross-referenced with LinkedIn"],
    },
    "missing_information": ["GitHub URL"],
    "conflicts": [],
    "evidence_index": [
        {
            "id": "EV-001",
            "source_type": "resume",
            "source_name": "cv.pdf",
            "quote_or_summary": "Built ETL pipelines.",
        }
    ],
    "projects": [
        {
            "name": "Analytics Dashboard",
            "summary": "Real-time metrics board built with Superset",
            "tools": ["Superset", "PostgreSQL"],
        }
    ],
    "change_log": ["Initial JSON ingest"],
}


def test_renderer_outputs_stable_section_order():
    text = render_fact_sheet_text(_RENDER_SAMPLE)
    sections = [
        "SECTION: CORE PROFILE",
        "SECTION: MATCH PROFILE",
        "SECTION: EDUCATION",
        "SECTION: EXPERIENCE",
        "SECTION: PROJECTS",
        "SECTION: SKILLS",
        "SECTION: LANGUAGES",
        "SECTION: MISSING INFORMATION",
        "SECTION: CONFLICTS",
        "SECTION: CONFIDENCE SUMMARY",
        "SECTION: EVIDENCE INDEX",
        "SECTION: CHANGE LOG",
    ]
    positions = [text.find(section) for section in sections]
    assert all(position >= 0 for position in positions)
    assert positions == sorted(positions), list(zip(sections, positions, strict=False))


def test_renderer_omits_null_fields_by_default():
    sample = deepcopy(_RENDER_SAMPLE)
    sample["person"]["preferred_name"] = None
    sample["person"]["contact"]["phone"] = None
    sample["person"]["contact"]["github_url"] = None

    text = render_fact_sheet_text(sample)

    assert "PREFERRED_NAME:" not in text
    assert "PHONE:" not in text
    assert "GITHUB:" not in text


def test_renderer_preserves_conflicts_and_missing_info():
    sample = deepcopy(_RENDER_SAMPLE)
    sample["missing_information"] = ["Phone number", "GitHub URL"]
    sample["conflicts"] = [
        {"field": "title", "source_a": "CV", "source_b": "LI", "note": ""},
        {"field": "location", "source_a": "CV", "source_b": "Form", "note": "confirm"},
    ]

    text = render_fact_sheet_text(sample)

    assert "SECTION: CONFLICTS" in text
    assert "FIELD: title" in text
    assert "FIELD: location" in text
    assert "Phone number" in text
    assert "GitHub URL" in text
    assert "None detected." not in text


def test_renderer_handles_empty_change_log_gracefully():
    sample = deepcopy(_RENDER_SAMPLE)
    sample["change_log"] = []

    text = render_fact_sheet_text(sample)

    assert "SECTION: CHANGE LOG" not in text
    assert "SECTION: MISSING INFORMATION" in text
    assert "SECTION: CONFLICTS" in text


def test_renderer_matches_master_template_shape():
    template = load_render_template()
    text = render_fact_sheet_text(_RENDER_SAMPLE)

    expected_labels = (
        "MASTER FACT SHEET",
        "SECTION: CORE PROFILE",
        "SECTION: MATCH PROFILE",
        "SECTION: EDUCATION",
        "SECTION: EXPERIENCE",
        "SECTION: PROJECTS",
        "SECTION: SKILLS",
        "SECTION: LANGUAGES",
        "SECTION: MISSING INFORMATION",
        "SECTION: CONFLICTS",
        "SECTION: CONFIDENCE SUMMARY",
        "SECTION: EVIDENCE INDEX",
        "SECTION: CHANGE LOG",
    )
    for label in expected_labels:
        assert label in template
        assert label in text


def test_roundtrip_ingest_render_reingest_is_stable(db_session):
    service = FactSheetJsonIngestionService(db_session)

    result1 = service.ingest_json(None, _ROUNDTRIP_SAMPLE)
    exported1 = service.export_json(result1.candidate_id)
    rendered1 = service.export_text(result1.candidate_id)

    result2 = service.ingest_json(result1.candidate_id, exported1)
    exported2 = service.export_json(result2.candidate_id)
    rendered2 = service.export_text(result2.candidate_id)

    assert exported1["experience"] == exported2["experience"]
    assert exported1["education"] == exported2["education"]
    assert exported1["person"] == exported2["person"]
    assert rendered1 == rendered2
