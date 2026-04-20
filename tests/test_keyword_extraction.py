from __future__ import annotations

from unittest.mock import MagicMock

from job_agent.llm import ProviderUnavailableError
from job_agent.services.prompts import (
    build_keyword_extraction_prompt,
    build_writer_user_prompt,
)
from job_agent.services.workflows import CVWorkflowService, WorkflowContext


def test_build_keyword_extraction_prompt_includes_title_and_description():
    prompt = build_keyword_extraction_prompt(
        {
            "title": "Data Engineer",
            "company": "Acme",
            "description": "Python SQL spark",
        }
    )

    assert "Data Engineer" in prompt
    assert "Python SQL spark" in prompt


def test_generate_draft_passes_keywords_to_writer(db_session, db_job, db_profile, db_track):
    router = MagicMock()
    router.generate.side_effect = [
        {
            "keywords": [
                {"rank": 1, "term": "Python", "tier": "must"},
                {"rank": 2, "term": "Airflow", "tier": "important"},
            ]
        },
        {
            "headline": "Data Engineer",
            "professional_summary": "Experienced data engineer.",
            "selected_experiences": [],
            "selected_projects": [],
            "selected_skills": ["Python", "SQL"],
            "tailoring_notes": [],
        },
    ]

    service = CVWorkflowService(db_session, router=router)
    context = WorkflowContext(profile=db_profile, track=db_track, job=db_job)
    service._generate_draft(context)

    assert router.generate.call_count == 2
    writer_prompt = router.generate.call_args_list[1].kwargs["user_prompt"]
    assert "Must-have: Python" in writer_prompt
    assert "Important: Airflow" in writer_prompt


def test_generate_draft_continues_when_keyword_extraction_fails(
    db_session,
    db_job,
    db_profile,
    db_track,
):
    router = MagicMock()
    router.generate.side_effect = [
        ProviderUnavailableError("LM Studio offline"),
        {
            "headline": "Data Engineer",
            "professional_summary": "Experienced data engineer.",
            "selected_experiences": [],
            "selected_projects": [],
            "selected_skills": ["Python", "SQL"],
            "tailoring_notes": [],
        },
    ]

    service = CVWorkflowService(db_session, router=router)
    context = WorkflowContext(profile=db_profile, track=db_track, job=db_job)
    draft, _, _, _, _ = service._generate_draft(context)

    assert draft["headline"] == "Data Engineer"
    assert router.generate.call_count == 2


def test_build_writer_user_prompt_includes_keywords_when_provided():
    prompt = build_writer_user_prompt(
        profile={},
        track={},
        job={},
        ranked_keywords=[{"rank": 1, "term": "Python", "tier": "must"}],
    )

    assert "Must-have: Python" in prompt


def test_build_writer_user_prompt_works_without_keywords():
    prompt = build_writer_user_prompt(
        profile={},
        track={},
        job={},
        ranked_keywords=None,
    )

    assert isinstance(prompt, str)
    assert prompt


def test_generate_draft_returns_ranked_keywords(db_session, db_job, db_profile, db_track):
    """ranked_keywords must be returned as 5th element so run_cv_workflow can store them."""
    router = MagicMock()
    kw_list = [{"rank": 1, "term": "Kubernetes", "tier": "must"}]
    router.generate.side_effect = [
        {"keywords": kw_list},
        {
            "headline": "MLOps Engineer",
            "professional_summary": "Cloud MLOps engineer.",
            "selected_experiences": [],
            "selected_projects": [],
            "selected_skills": ["Kubernetes"],
            "tailoring_notes": [],
        },
    ]

    service = CVWorkflowService(db_session, router=router)
    context = WorkflowContext(profile=db_profile, track=db_track, job=db_job)
    _, _, _, _, keywords = service._generate_draft(context)

    assert keywords == kw_list


def test_generate_draft_returns_none_keywords_when_extraction_fails(
    db_session, db_job, db_profile, db_track
):
    """When keyword extraction fails, 5th return value must be None (not raise)."""
    router = MagicMock()
    router.generate.side_effect = [
        ProviderUnavailableError("offline"),
        {
            "headline": "MLOps Engineer",
            "professional_summary": "s",
            "selected_experiences": [],
            "selected_projects": [],
            "selected_skills": [],
            "tailoring_notes": [],
        },
    ]

    service = CVWorkflowService(db_session, router=router)
    context = WorkflowContext(profile=db_profile, track=db_track, job=db_job)
    _, _, _, _, keywords = service._generate_draft(context)

    assert keywords is None
