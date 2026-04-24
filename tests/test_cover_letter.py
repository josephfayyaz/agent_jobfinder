from __future__ import annotations

from uuid import uuid4

import httpx

from job_agent.models import ResumeDraft


def test_cover_letter_system_prompt_has_spartan_rules():
    from job_agent.services.prompts import build_cover_letter_system_prompt

    prompt = build_cover_letter_system_prompt()
    assert "Spartan" in prompt
    assert "Valid JSON" in prompt
    assert "subject" in prompt
    assert "body" in prompt


def test_cover_letter_user_prompt_contains_company():
    from job_agent.services.prompts import build_cover_letter_user_prompt

    profile = {
        "full_name": "Yousef Fayyaz",
        "brand_summary": "Data engineer",
        "education": [],
        "experiences": [],
    }
    track = {"title": "Data Engineering", "emphasis": "Python, SQL"}
    job = {
        "title": "Data Engineer",
        "company": "Bending Spoons",
        "location": "Milan",
        "description": "Build pipelines.",
        "company_url": "",
    }
    prompt = build_cover_letter_user_prompt(
        profile,
        track,
        job,
        company_context="Bending Spoons builds apps.",
    )
    assert "Bending Spoons" in prompt
    assert "Bending Spoons builds apps." in prompt


def test_fetch_company_context_returns_empty_on_failure(monkeypatch):
    from job_agent.services.cover_letter import fetch_company_context

    def _raise(*_args, **_kwargs):
        raise httpx.RequestError("boom")

    monkeypatch.setattr("job_agent.services.cover_letter.httpx.get", _raise)
    result = fetch_company_context("https://this-domain-does-not-exist-xyz.com")
    assert result == ""


def test_generate_cover_letter_stores_on_draft(monkeypatch, db_session, db_job, db_profile, db_track, tmp_path):
    from job_agent.llm import LLMRouter
    from job_agent.services.cover_letter import CoverLetterService

    monkeypatch.setattr("job_agent.services.documents.settings.artifacts_dir", tmp_path)

    draft = ResumeDraft(
        id=uuid4(),
        job_post_id=db_job.id,
        resume_track_id=db_track.id,
        status="approved",
        score=88,
        provider="test",
    )
    db_session.add(draft)
    db_session.commit()

    monkeypatch.setattr("job_agent.services.cover_letter.fetch_company_context", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(
        LLMRouter,
        "generate",
        lambda self, **_kwargs: {"subject": "Test Subject", "body": "Dear Team,\n\nTest body.\n\nBest,\nYousef"},
    )

    svc = CoverLetterService(db_session)
    result = svc.generate_cover_letter(draft.id, company_url=None)

    assert result.cover_letter_text is not None
    assert len(result.cover_letter_text) > 10
    assert result.cover_letter_subject == "Test Subject"
    generated_files = list(tmp_path.glob("*_cover.txt"))
    assert generated_files, "Cover letter text file should be saved"


def test_heuristic_cover_letter_fallback():
    from unittest.mock import MagicMock

    from job_agent.services.cover_letter import CoverLetterService

    svc = CoverLetterService(MagicMock())
    body = svc._heuristic_cover_letter(
        {"full_name": "Test User"},
        {"title": "Data Engineer", "company": "TestCo"},
    )
    assert len(body) > 100
    assert "Test User" in body
    assert "TestCo" in body
