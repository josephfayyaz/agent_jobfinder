"""Shared pytest fixtures."""
from __future__ import annotations

import pytest


@pytest.fixture
def sample_job() -> dict:
    return {
        "title": "Data Engineer",
        "description": (
            "We need strong Python, SQL, dbt, Airflow, and PostgreSQL skills. "
            "Experience with ETL pipelines and data warehousing required."
        ),
    }


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
        slug = "data-engineering-analytics"
        title = "Data Engineer / Analytics Engineer"
        role_family = "data"
        target_keywords = ["python", "sql", "etl", "dbt", "airflow", "postgresql", "warehouse"]
        baseline_summary = "Data engineer focused on pipelines and warehousing."
        emphasis = {"focus": ["etl", "warehousing"]}
        linkedin_strategy = ""
        github_strategy = ""

    return FakeTrack()
