# Spec: Phase 4.3 — Write Unit Tests
Status: pending

## Context
Zero tests exist. Add tests for the three pure-logic modules that don't need
a running database or LM Studio. Use pytest (already in dev dependencies).

## Step 0: Create test infrastructure

### File: `tests/__init__.py`
Create an empty file:
```python
```
(just an empty file — makes `tests/` a Python package)

### File: `tests/conftest.py`
Create with this content:
```python
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
```

## Changes

### File: `tests/test_matching.py`
Create with this content:
```python
"""Tests for job-to-track matching algorithm."""
from __future__ import annotations
import pytest
from job_agent.services.matching import score_tracks_for_job


def test_score_zero_match_is_low(sample_track):
    """A job with zero keyword matches should score below 30."""
    job = {"title": "Marketing Manager", "description": "Manage campaigns and social media."}
    results = score_tracks_for_job(job, [sample_track])
    assert results[0]["score"] < 30, "Zero-match job should score < 30 with new formula"


def test_score_strong_match_above_threshold(sample_track):
    """A clearly relevant job should score above the 60 revise threshold."""
    job = {
        "title": "Data Engineer",
        "description": "Strong Python, SQL, dbt, Airflow, PostgreSQL, ETL experience required.",
    }
    results = score_tracks_for_job(job, [sample_track])
    assert results[0]["score"] >= 60, "Strong match job should score >= 60"


def test_matched_keywords_returned(sample_track):
    """matched_keywords should list which track keywords appeared in the job."""
    job = {"title": "Data Engineer", "description": "python and sql experience required"}
    results = score_tracks_for_job(job, [sample_track])
    assert "python" in results[0]["matched_keywords"]
    assert "sql" in results[0]["matched_keywords"]


def test_score_capped_at_100(sample_track):
    """Score should never exceed 100."""
    job = {
        "title": "python sql dbt airflow etl warehouse postgresql data engineer",
        "description": " ".join(["python sql dbt airflow postgresql etl warehouse"] * 10),
    }
    results = score_tracks_for_job(job, [sample_track])
    assert results[0]["score"] <= 100


def test_multiple_tracks_sorted(sample_track):
    """Results should be sorted descending by score."""
    class WeakTrack:
        slug = "cloud-mlops"
        title = "Cloud MLOps"
        role_family = "cloud"
        target_keywords = ["kubernetes", "docker", "mlops"]
        baseline_summary = ""
        emphasis = {}
    job = {"title": "Data Engineer", "description": "python sql dbt airflow etl"}
    results = score_tracks_for_job(job, [sample_track, WeakTrack()])
    assert results[0]["score"] >= results[1]["score"], "Results should be sorted descending"
```

### File: `tests/test_prompts.py`
Create with this content:
```python
"""Tests for prompt builders — check structure and key content."""
from __future__ import annotations
import json
from job_agent.services.prompts import (
    build_writer_system_prompt,
    build_writer_user_prompt,
    build_reviewer_system_prompt,
    build_reviewer_user_prompt,
    build_revision_prompt,
)


def test_writer_system_prompt_contains_json_instruction():
    prompt = build_writer_system_prompt()
    assert "valid JSON only" in prompt
    assert "XYZ" in prompt
    assert "ATS" in prompt


def test_reviewer_system_prompt_contains_rubric():
    prompt = build_reviewer_system_prompt()
    assert "Role Fit" in prompt
    assert "Evidence" in prompt
    assert "Keyword" in prompt
    assert "25" in prompt  # rubric weights
    assert "pass" in prompt
    assert "revise" in prompt
    assert "rewrite" in prompt


def test_writer_user_prompt_contains_candidate_name(sample_profile, sample_track):
    job = {"title": "Data Engineer", "company": "TestCo", "description": "Python and SQL."}
    track_dict = {
        "title": sample_track.title,
        "role_family": sample_track.role_family,
        "baseline_summary": sample_track.baseline_summary,
        "emphasis": sample_track.emphasis,
        "target_keywords": sample_track.target_keywords,
    }
    prompt = build_writer_user_prompt(sample_profile, track_dict, job)
    assert "Test User" in prompt
    assert "TestCo" in prompt
    assert "Data Engineer" in prompt
    # Experiences should be formatted as text, not raw dict repr
    assert "dict_keys" not in prompt
    assert "[Data Engineer" in prompt  # formatted experience header


def test_writer_user_prompt_no_raw_dict_repr(sample_profile, sample_track):
    """Profile data must be formatted as readable text, not Python dict repr."""
    job = {"title": "Engineer", "company": "Co", "description": "test"}
    track_dict = {
        "title": sample_track.title,
        "role_family": sample_track.role_family,
        "baseline_summary": sample_track.baseline_summary,
        "emphasis": sample_track.emphasis,
        "target_keywords": sample_track.target_keywords,
    }
    prompt = build_writer_user_prompt(sample_profile, track_dict, job)
    assert "dict_keys" not in prompt
    assert "object at 0x" not in prompt


def test_revision_prompt_includes_must_fix():
    job = {"title": "Engineer", "company": "Co", "description": "Python required."}
    draft = {"headline": "Engineer", "professional_summary": "I do stuff."}
    feedback = {
        "score": 55,
        "decision": "rewrite",
        "must_fix": ["Add quantified metrics to experience bullets."],
        "gaps": ["Missing Python keyword."],
        "revised_summary": "Experienced engineer specialising in Python systems.",
    }
    prompt = build_revision_prompt(job, draft, feedback)
    assert "quantified metrics" in prompt
    assert "Experienced engineer" in prompt
```

### File: `tests/test_documents.py`
Create with this content:
```python
"""Tests for LaTeX rendering."""
from __future__ import annotations
import os
import pytest
from job_agent.services.documents import render_resume_tex


def test_render_creates_tex_file(tmp_path, monkeypatch, sample_profile):
    """render_resume_tex should create a .tex file with content."""
    # Redirect artifacts dir to a temp directory
    monkeypatch.setattr("job_agent.services.documents.settings.artifacts_dir", tmp_path)

    content = {
        "headline": "Data Engineer",
        "professional_summary": "Test summary.",
        "selected_experiences": [
            {"title": "DE", "company": "Acme", "location": "Milan", "bullets": ["Built pipelines."]}
        ],
        "selected_projects": [
            {"name": "Pipeline", "repo_url": "", "bullets": ["Processed data."]}
        ],
        "selected_skills": ["Python", "SQL"],
        "tailoring_notes": ["Tailored for data engineering roles."],
    }
    job = {"title": "Data Engineer", "company": "TestCo"}
    track = {"title": "Data Engineering", "role_family": "data"}

    tex_path = render_resume_tex(
        profile=sample_profile,
        job=job,
        track=track,
        content=content,
        draft_id="test-draft-001",
    )

    assert os.path.exists(tex_path), "TeX file should be created"
    tex_content = open(tex_path).read()
    assert "Data Engineer" in tex_content
    assert "Test User" in tex_content
    assert len(tex_content) > 100, "TeX file should have substantial content"


def test_render_escapes_special_chars(tmp_path, monkeypatch, sample_profile):
    """Special LaTeX characters in content should be escaped."""
    monkeypatch.setattr("job_agent.services.documents.settings.artifacts_dir", tmp_path)

    content = {
        "headline": "Engineer & Developer",
        "professional_summary": "Expert in C++ & Python. 100% reliable.",
        "selected_experiences": [],
        "selected_projects": [],
        "selected_skills": ["C++", "Python"],
        "tailoring_notes": [],
    }
    tex_path = render_resume_tex(
        profile=sample_profile,
        job={"title": "Engineer", "company": "Co"},
        track={"title": "Engineering", "role_family": "engineering"},
        content=content,
        draft_id="test-escape-001",
    )
    tex_content = open(tex_path).read()
    # Raw & and % should not appear unescaped outside of LaTeX commands
    assert "\\&" in tex_content or "&" not in tex_content.split("\\begin")[1]
```

## Running Tests
```bash
cd /Users/youseffayyaz/Local_LLM
/Users/youseffayyaz/miniforge3/bin/conda run -n ML python -m pytest tests/ -v
```
Expected output: all tests pass. Fix any failures before committing.

## Lint
```bash
/Users/youseffayyaz/miniforge3/bin/conda run -n ML python -m ruff check job_agent/ tests/
```

## Git
```bash
git add tests/
git commit -m "test: add unit tests for matching, prompts, and document rendering

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```
