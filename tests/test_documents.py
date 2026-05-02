"""Tests for LaTeX rendering."""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from job_agent.services.documents import build_artifact_stem, render_resume_tex


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
    assert "Professional Experience" in tex_content
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


def test_render_omits_empty_experience_section(tmp_path, monkeypatch, sample_profile):
    monkeypatch.setattr("job_agent.services.documents.settings.artifacts_dir", tmp_path)

    tex_path = render_resume_tex(
        profile=sample_profile,
        job={"title": "Engineer", "company": "Co"},
        track={"title": "Engineering", "role_family": "engineering"},
        content={
            "professional_summary": "Summary",
            "selected_experiences": [],
            "selected_projects": [],
            "selected_skills": ["Python"],
            "tailoring_notes": [],
        },
        draft_id="test-empty-001",
    )

    tex_content = Path(tex_path).read_text(encoding="utf-8")
    assert "\\section{Professional Experience}" not in tex_content
    assert "\\begin{itemize}\n\n\\end{itemize}" not in tex_content


def test_render_renames_profile_note_projects_to_relevant_evidence(tmp_path, monkeypatch, sample_profile):
    monkeypatch.setattr("job_agent.services.documents.settings.artifacts_dir", tmp_path)

    tex_path = render_resume_tex(
        profile=sample_profile,
        job={"title": "Accountant", "company": "Co"},
        track={"title": "Finance", "role_family": "finance"},
        content={
            "professional_summary": "Summary",
            "selected_experiences": [],
            "selected_projects": [
                {
                    "name": "Profile note evidence",
                    "description": "Handled reconciliations during internship.",
                    "bullets": ["Handled reconciliations during internship."],
                }
            ],
            "selected_skills": ["Excel"],
            "tailoring_notes": [],
        },
        draft_id="test-evidence-001",
    )

    tex_content = Path(tex_path).read_text(encoding="utf-8")
    assert "\\section{Relevant Evidence}" in tex_content
    assert "\\section{Projects}" not in tex_content


def test_render_does_not_print_internal_tailoring_sections(tmp_path, monkeypatch, sample_profile):
    monkeypatch.setattr("job_agent.services.documents.settings.artifacts_dir", tmp_path)

    tex_path = render_resume_tex(
        profile=sample_profile,
        job={"title": "Engineer", "company": "Co"},
        track={"title": "Engineering", "role_family": "engineering", "baseline_summary": "Base summary"},
        content={
            "headline": "Platform Engineer",
            "professional_summary": "Strong summary.",
            "selected_experiences": [],
            "selected_projects": [],
            "selected_skills": ["Python"],
            "tailoring_notes": ["This should stay internal."],
        },
        draft_id="test-tailoring-001",
    )

    tex_content = Path(tex_path).read_text(encoding="utf-8")
    assert "Tailoring Notes" not in tex_content
    assert "Target Role" not in tex_content
    assert "This should stay internal." not in tex_content


def test_render_sanitizes_emoji_for_pdflatex(tmp_path, monkeypatch, sample_profile):
    monkeypatch.setattr("job_agent.services.documents.settings.artifacts_dir", tmp_path)

    tex_path = render_resume_tex(
        profile=sample_profile,
        job={"title": "Engineer", "company": "Co"},
        track={"title": "Engineering", "role_family": "engineering"},
        content={
            "headline": "Platform Engineer 🚀",
            "professional_summary": "Built reliable pipelines ✅ and improved quality.",
            "selected_experiences": [],
            "selected_projects": [],
            "selected_skills": ["Python", "SQL"],
            "tailoring_notes": [],
        },
        draft_id="test-emoji-001",
    )

    tex_content = Path(tex_path).read_text(encoding="utf-8")
    assert "🚀" not in tex_content
    assert "✅" not in tex_content


def test_render_junior_limits_bullets_and_projects(tmp_path, monkeypatch, sample_profile):
    monkeypatch.setattr("job_agent.services.documents.settings.artifacts_dir", tmp_path)
    monkeypatch.setattr("job_agent.services.documents.settings.target_job_seniority", "junior")

    many_experiences = []
    for index in range(6):
        many_experiences.append(
            {
                "title": f"Role {index}",
                "company": "Co",
                "location": "Rome",
                "bullets": [f"Bullet {index}-a", f"Bullet {index}-b", f"Bullet {index}-c"],
            }
        )
    many_projects = [{"name": f"Project {i}", "bullets": ["One", "Two", "Three"]} for i in range(3)]

    tex_path = render_resume_tex(
        profile=sample_profile,
        job={"title": "Junior Engineer", "company": "Co"},
        track={"title": "Engineering", "role_family": "engineering"},
        content={
            "headline": "Junior Engineer",
            "professional_summary": " ".join(["summary"] * 80),
            "selected_experiences": many_experiences,
            "selected_projects": many_projects,
            "selected_skills": [f"Skill-{i}" for i in range(20)],
            "tailoring_notes": [],
        },
        draft_id="test-junior-limits-001",
    )

    tex_content = Path(tex_path).read_text(encoding="utf-8")
    assert tex_content.count("\\item Bullet") <= 6
    assert tex_content.count("\\section{Projects}") <= 1
    assert "Skill-10" not in tex_content


def test_build_artifact_stem_uses_date_company_and_candidate():
    stem = build_artifact_stem("ACME S.p.A.", "Test User", "1234567890abcdef")

    assert stem.startswith(date.today().strftime("%Y-%m-%d"))
    assert "ACME_SpA" in stem
    assert "Test_User" in stem
    assert stem.endswith("12345678")


def test_render_includes_languages_section_when_present(tmp_path, monkeypatch, sample_profile):
    monkeypatch.setattr("job_agent.services.documents.settings.artifacts_dir", tmp_path)
    profile = dict(sample_profile)
    profile["languages"] = [
        {"name": "English", "level": "C1"},
        {"name": "Italian", "level": "B1"},
    ]

    tex_path = render_resume_tex(
        profile=profile,
        job={"title": "Analyst", "company": "Co"},
        track={"title": "Analytics", "role_family": "analytics"},
        content={
            "headline": "Analyst",
            "professional_summary": "Summary",
            "selected_experiences": [],
            "selected_projects": [],
            "selected_skills": ["Excel"],
            "tailoring_notes": [],
        },
        draft_id="test-languages-001",
    )

    tex_content = Path(tex_path).read_text(encoding="utf-8")
    assert "\\section{Languages}" in tex_content
    assert "English (C1)" in tex_content


def test_compile_pdf_repairs_old_tex_without_optional_packages(tmp_path, monkeypatch):
    from job_agent.services.documents import compile_pdf

    monkeypatch.setenv("JOB_AGENT_HOME", str(tmp_path / "home"))
    tex_path = tmp_path / "legacy.tex"
    tex_path.write_text(
        r"""
\documentclass{article}
\usepackage[sfdefault,light]{roboto}
\usepackage{enumitem}
\setlist[itemize]{noitemsep, topsep=2pt, leftmargin=*}
\begin{document}
\begin{itemize}
\end{itemize}
Hello
\end{document}
""".strip(),
        encoding="utf-8",
    )

    pdf_path = compile_pdf(str(tex_path))
    assert Path(pdf_path).exists()
