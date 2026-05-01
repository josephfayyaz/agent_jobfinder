from __future__ import annotations

from job_agent.services.job_description_quality import evaluate_job_description


def test_job_description_quality_marks_missing_when_empty():
    quality = evaluate_job_description(
        description="",
        source_name="jobspy_linkedin",
        source_url="https://www.linkedin.com/jobs/view/1",
        company_url=None,
    )

    assert quality["label"] == "missing"
    assert quality["ready_for_provider_scoring"] is False


def test_job_description_quality_marks_short_linkedin_snippet_as_thin():
    quality = evaluate_job_description(
        description="Junior accountant role helping with invoices and reports.",
        source_name="jobspy_linkedin",
        source_url="https://www.linkedin.com/jobs/view/2",
        company_url=None,
    )

    assert quality["label"] == "thin"
    assert quality["ready_for_provider_scoring"] is False
    assert quality["source_kind"] == "linkedin_snippet"


def test_job_description_quality_accepts_strong_ats_description():
    description = """
    Responsibilities:
    - Build monthly close reporting and variance analysis.
    - Support budgeting, forecasting, and stakeholder reviews.

    Requirements:
    - Degree in finance or accounting.
    - 2+ years of FP&A or controlling experience.
    - Strong Excel and Power BI skills.
    """
    quality = evaluate_job_description(
        description=description * 6,
        source_name="greenhouse",
        source_url="https://boards.greenhouse.io/acme/jobs/123",
        company_url="https://boards.greenhouse.io/acme/jobs/123",
    )

    assert quality["ready_for_provider_scoring"] is True
    assert quality["label"] in {"usable", "strong"}
    assert quality["source_kind"] == "ats_structured"
