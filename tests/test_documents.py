"""Tests for LaTeX rendering."""
from __future__ import annotations

import os

from job_agent.services.documents import render_resume_tex


def test_render_creates_tex_file(tmp_path, monkeypatch, sample_profile):
    """render_resume_tex should create a .tex file with content."""
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
    with open(tex_path, encoding="utf-8") as handle:
        tex_content = handle.read()
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
    with open(tex_path, encoding="utf-8") as handle:
        tex_content = handle.read()
    assert "\\&" in tex_content or "&" not in tex_content.split("\\begin")[1]
