from __future__ import annotations

from job_agent.services.draft_preview import build_preview_annotations
from job_agent.services.job_target_profile import build_cv_target_fit, build_job_target_profile
from job_agent.services.profile_readiness import (
    READINESS_BLOCK,
    READINESS_READY,
    READINESS_WARN,
    evaluate_profile_readiness,
)


def test_profile_readiness_blocks_without_grounded_evidence():
    readiness = evaluate_profile_readiness(
        {
            "person": {"full_name": "Test User", "contact": {"email": "test@example.com"}},
            "education": [],
            "experience": [],
            "projects": [],
            "skills": {},
            "languages": [],
        }
    )

    assert readiness["status"] == READINESS_BLOCK
    assert "experience_or_evidence" in readiness["missing_sections"]


def test_profile_readiness_warns_for_thin_but_usable_profile():
    readiness = evaluate_profile_readiness(
        {
            "person": {"full_name": "Test User", "contact": {"email": "test@example.com"}},
            "education": [{"degree": "BSc", "institution": "Uni", "status": "completed"}],
            "projects": [{"name": "Capstone", "summary": "Built a reporting dashboard."}],
            "skills": {"business_tools": ["Excel", "Power BI", "SQL", "Reporting"]},
            "languages": [{"name": "English", "level": "C1"}],
        }
    )

    assert readiness["status"] == READINESS_WARN
    assert readiness["ready_for_final_cv"] is True


def test_profile_readiness_marks_rich_profile_ready():
    readiness = evaluate_profile_readiness(
        {
            "person": {"full_name": "Test User", "contact": {"email": "test@example.com"}},
            "education": [{"degree": "MSc", "institution": "Uni", "status": "completed"}],
            "experience": [
                {
                    "role_title": "Financial Analyst",
                    "organization": "Acme",
                    "start_date": "2023-01",
                    "end_date": "2024-12",
                    "responsibilities": ["Built variance reports and monthly forecasts."],
                }
            ],
            "projects": [{"name": "Planning pack", "summary": "Prepared KPI dashboards for leadership."}],
            "skills": {"business_tools": ["Excel", "Power BI", "SAP", "Forecasting"]},
            "languages": [{"name": "English", "level": "C1"}],
        }
    )

    assert readiness["status"] == READINESS_READY


def test_job_target_profile_and_fit_map_produce_structured_output():
    job_profile = build_job_target_profile(
        title="Junior Accountant",
        company="Acme",
        location="Turin, Italy",
        country="Italy",
        description=(
            "Required: Excel and reconciliations. "
            "You will support month-end close and prepare reporting packs. "
            "Nice to have: SAP."
        ),
    )
    fit_map = build_cv_target_fit(
        job_profile=job_profile,
        profile_data={
            "experiences": [
                {"bullets": ["Supported month-end close and reconciliations in Excel."]},
            ],
            "projects": [{"summary": "Prepared weekly reporting packs for finance leads.", "bullets": []}],
            "global_skills": ["Excel", "Reporting", "SAP"],
        },
    )

    assert job_profile["requirements"]
    assert fit_map["rows"]
    assert fit_map["scores"]["overall_match_score"] >= 0
    assert len(fit_map["recommended_improvements"]) <= 5


def test_preview_annotations_flag_unsupported_claims():
    annotations = build_preview_annotations(
        draft_content={
            "professional_summary": "Led multilingual FP&A programs with ten years of ownership.",
            "selected_experiences": [{"bullets": ["Built monthly forecasts in Excel and Power BI."]}],
            "selected_projects": [],
        },
        profile_data={
            "experiences": [{"bullets": ["Built monthly forecasts in Excel and Power BI."]}],
            "projects": [],
            "global_skills": ["Excel", "Power BI"],
        },
        accepted_item_ids=[],
    )

    item_map = {item["item_id"]: item for item in annotations["items"]}
    assert item_map["summary"]["tag"] in {"adjacent_inference", "needs_user_confirmation"}
    assert item_map["selected_experiences:0:0"]["tag"] in {"direct_fact", "safe_paraphrase"}
    assert annotations["pending_confirmation_count"] >= 1
