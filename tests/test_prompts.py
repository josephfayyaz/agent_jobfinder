"""Tests for prompt builders — check structure and key content."""
from __future__ import annotations

from job_agent.services.prompts import (
    build_compliance_matrix_system_prompt,
    build_reviewer_system_prompt,
    build_reviewer_user_prompt,
    build_revision_prompt,
    build_writer_system_prompt,
    build_writer_user_prompt,
)
from job_agent.services.resource_loader import load_prompt_resource


def test_prompt_resource_loader_returns_non_empty_text():
    text = load_prompt_resource("writer_system.md")
    assert text.strip()
    assert "HUMAN-IN-THE-LOOP" in text


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
    assert "25" in prompt
    assert "pass" in prompt
    assert "revise" in prompt
    assert "rewrite" in prompt


def test_compliance_system_prompt_contains_ats_marker():
    prompt = build_compliance_matrix_system_prompt()
    assert "ATS compliance analyst" in prompt
    assert "valid JSON only" in prompt


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
    assert "dict_keys" not in prompt
    assert "[Data Engineer" in prompt


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


def test_writer_user_prompt_includes_truth_constraints(sample_profile, sample_track):
    job = {"title": "FP&A Analyst", "company": "AB Parfums", "description": "Budgeting and forecasting."}
    track_dict = {
        "title": sample_track.title,
        "role_family": sample_track.role_family,
        "baseline_summary": sample_track.baseline_summary,
        "emphasis": sample_track.emphasis,
        "target_keywords": sample_track.target_keywords,
    }
    prompt = build_writer_user_prompt(
        sample_profile,
        track_dict,
        job,
        truth_constraints=[
            "Do not invent years of experience.",
            "Use project evidence only.",
        ],
    )
    assert "TRUTHFULNESS CONSTRAINTS" in prompt
    assert "Do not invent years of experience." in prompt


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


def test_reviewer_user_prompt_renders_draft_context(sample_profile, sample_track):
    job = {"title": "Data Engineer", "company": "TestCo", "description": "Python and SQL."}
    track_dict = {
        "title": sample_track.title,
        "role_family": sample_track.role_family,
        "baseline_summary": sample_track.baseline_summary,
        "emphasis": sample_track.emphasis,
        "target_keywords": sample_track.target_keywords,
    }
    draft = {
        "headline": "Data Engineer",
        "professional_summary": "Summary",
        "selected_skills": ["Python", "SQL"],
        "selected_experiences": [{"title": "Data Engineer", "company": "Acme", "bullets": ["Built ETL."]}],
        "selected_projects": [{"name": "Pipeline", "bullets": ["Processed data."]}],
        "tailoring_notes": ["Matched SQL and Python requirements."],
    }
    prompt = build_reviewer_user_prompt(sample_profile, track_dict, job, draft)
    assert "TestCo" in prompt
    assert "Built ETL." in prompt
    assert "Matched SQL and Python requirements." in prompt
