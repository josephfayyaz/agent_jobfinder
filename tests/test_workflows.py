"""Tests for the CV workflow service."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

from job_agent.llm import ProviderUnavailableError
from job_agent.models import JobPost, ResumeDraft
from job_agent.services.workflows import CVWorkflowService


def _create_job_for_role(db_session, *, title: str, description: str, seniority: str) -> JobPost:
    job = JobPost(
        id=uuid4(),
        company="Example Co",
        title=title,
        description=description,
        location="Remote",
        source_name="manual",
        source_url=f"https://example.com/jobs/{uuid4()}",
        canonical_apply_url=f"https://example.com/jobs/{uuid4()}",
        seniority=seniority,
        created_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


def test_queue_cv_workflow_creates_pending_task(db_session, db_job):
    """queue_cv_workflow creates a WorkflowTask with status=pending."""
    svc = CVWorkflowService(db_session)
    task = svc.queue_cv_workflow(db_job.id, "data-engineering-analytics")
    assert task.status == "pending"
    assert task.kind == "cv_workflow"
    assert task.payload["job_post_id"] == str(db_job.id)


def test_process_next_task_runs_pending(db_session, sample_workflow_task):
    """process_next_task picks up the pending task and runs it."""
    svc = CVWorkflowService(db_session)
    with patch.object(svc, "run_cv_workflow") as mock_run:
        mock_run.return_value = {"status": "completed", "draft_id": 1}
        svc.process_next_task()
    mock_run.assert_called_once()


def test_process_next_task_marks_failed_on_exception(db_session, sample_workflow_task):
    """process_next_task sets status=failed if run_cv_workflow raises."""
    svc = CVWorkflowService(db_session)
    with patch.object(svc, "run_cv_workflow", side_effect=RuntimeError("LLM unavailable")):
        svc.process_next_task()

    db_session.refresh(sample_workflow_task)
    assert sample_workflow_task.status == "failed"
    assert "LLM unavailable" in (sample_workflow_task.error_message or "")


def test_run_cv_workflow_generates_draft(db_session, db_job, db_profile, db_track, tmp_path, monkeypatch):
    """Full pipeline: mocked writer/reviewer responses still create a ResumeDraft."""
    writer_draft = {
        "headline": "Data Engineer",
        "professional_summary": "Experienced data engineer.",
        "selected_experiences": [],
        "selected_projects": [],
        "selected_skills": ["Python", "SQL"],
        "tailoring_notes": [],
    }
    reviewer_result = {
        "score": 90,
        "decision": "pass",
        "strengths": [],
        "gaps": [],
        "must_fix": [],
        "keyword_coverage": ["python", "sql"],
        "revised_summary": "Experienced data engineer.",
    }
    monkeypatch.setattr("job_agent.services.documents.settings.artifacts_dir", tmp_path)
    router = MagicMock()
    router.generate.side_effect = [{"keywords": []}, writer_draft, reviewer_result]

    svc = CVWorkflowService(db_session, router=router)
    payload = {"job_post_id": str(db_job.id), "resume_track_slug": db_track.slug}
    result = svc.run_cv_workflow(payload)

    draft = db_session.query(ResumeDraft).filter_by(job_post_id=db_job.id).first()
    assert draft is not None
    assert float(draft.score or 0) >= 0
    assert result["draft_id"] == str(draft.id)


def test_run_cv_workflow_revises_on_low_score(db_session, db_job, db_profile, db_track, tmp_path, monkeypatch):
    """If reviewer returns score < 85, revision step is triggered."""
    writer_draft = {
        "headline": "DE",
        "professional_summary": "...",
        "selected_experiences": [],
        "selected_projects": [],
        "selected_skills": ["Python"],
        "tailoring_notes": [],
    }
    low_score_review = {
        "score": 65,
        "decision": "revise",
        "must_fix": ["Add more keywords"],
        "gaps": [],
        "keyword_coverage": [],
        "revised_summary": "...",
    }
    revised_draft = {
        "headline": "DE Revised",
        "professional_summary": "...",
        "selected_experiences": [],
        "selected_projects": [],
        "selected_skills": ["Python", "SQL"],
        "tailoring_notes": [],
    }
    monkeypatch.setattr("job_agent.services.documents.settings.artifacts_dir", tmp_path)
    router = MagicMock()
    router.generate.side_effect = [{"keywords": []}, writer_draft, low_score_review, revised_draft]

    svc = CVWorkflowService(db_session, router=router)
    payload = {"job_post_id": str(db_job.id), "resume_track_slug": db_track.slug}
    svc.run_cv_workflow(payload)

    assert router.generate.call_count >= 3


def test_heuristic_fallback_when_llm_unavailable(
    db_session,
    db_job,
    db_profile,
    db_track,
    tmp_path,
    monkeypatch,
):
    """When the router is unavailable, heuristic fallback still creates a draft."""
    monkeypatch.setattr("job_agent.services.documents.settings.artifacts_dir", tmp_path)
    router = MagicMock()
    router.generate.side_effect = ProviderUnavailableError("LM Studio offline")

    svc = CVWorkflowService(db_session, router=router)
    payload = {"job_post_id": str(db_job.id), "resume_track_slug": db_track.slug}
    svc.run_cv_workflow(payload)

    draft = db_session.query(ResumeDraft).filter_by(job_post_id=db_job.id).first()
    assert draft is not None


def test_sparse_writer_output_is_backfilled_from_profile(db_session, db_job, db_profile, db_track, tmp_path, monkeypatch):
    monkeypatch.setattr("job_agent.services.documents.settings.artifacts_dir", tmp_path)
    router = MagicMock()
    router.generate.side_effect = [
        {"keywords": []},
        {
            "summary": "Too short.",
            "skills": {"tools": ["Python"]},
            "experience": [],
            "projects": [],
        },
        {
            "score": 90,
            "decision": "pass",
            "strengths": [],
            "gaps": [],
            "must_fix": [],
            "keyword_coverage": ["python"],
            "revised_summary": "ok",
        },
    ]

    svc = CVWorkflowService(db_session, router=router)
    result = svc.run_cv_workflow({"job_post_id": str(db_job.id), "resume_track_slug": db_track.slug})

    draft = db_session.query(ResumeDraft).filter_by(job_post_id=db_job.id).first()
    assert result["draft_id"] == str(draft.id)
    assert draft.content["professional_summary"] == db_profile.public_brand_summary
    assert len(draft.content["selected_experiences"]) == 1
    assert len(draft.content["selected_skills"]) >= 4


@patch("job_agent.services.workflows.render_resume_tex", return_value="/tmp/test.tex")
@patch("job_agent.services.workflows.build_writer_user_prompt", side_effect=lambda *args, **kwargs: "writer prompt")
@patch("job_agent.services.workflows.build_reviewer_user_prompt", side_effect=lambda *args, **kwargs: "reviewer prompt")
@patch("job_agent.services.workflows.build_writer_system_prompt", return_value="writer system")
@patch("job_agent.services.workflows.build_reviewer_system_prompt", return_value="reviewer system")
@patch("job_agent.services.workflows.build_keyword_extraction_prompt", return_value="keyword prompt")
@patch("job_agent.services.workflows.build_keyword_extraction_system_prompt", return_value="keyword system")
@patch("job_agent.services.workflows.select_experiences_for_job", return_value=[])
@patch("job_agent.services.workflows.select_projects_for_job", return_value=[])
@patch("job_agent.services.workflows.resolve_presentation_mode", side_effect=lambda target_seniority, job_seniority=None: job_seniority or target_seniority)
@patch("job_agent.services.workflows.CVWorkflowService._load_verified_facts_for_prompt", return_value=[])
@patch("job_agent.services.workflows.CVWorkflowService._review_draft")
@patch("job_agent.services.workflows.CVWorkflowService._apply_review_decision")
@patch("job_agent.services.workflows.CVWorkflowService._compute_missing_keywords", return_value=[])
def test_run_cv_workflow_handles_diverse_roles_and_seniority(
    mock_missing_keywords,
    mock_apply_review,
    mock_review,
    mock_verified_facts,
    mock_presentation_mode,
    mock_projects,
    mock_experiences,
    mock_keyword_system,
    mock_keyword_prompt,
    mock_reviewer_system,
    mock_writer_system,
    mock_reviewer_prompt,
    mock_writer_prompt,
    mock_render_resume,
    db_session,
    db_profile,
    db_track,
):
    del mock_missing_keywords, mock_verified_facts, mock_presentation_mode
    del mock_projects, mock_experiences, mock_keyword_system, mock_keyword_prompt
    del mock_reviewer_system, mock_writer_system, mock_reviewer_prompt, mock_writer_prompt, mock_render_resume
    del db_profile

    role_cases = [
        ("Junior Accountant", "Support reconciliations, reporting, and month-end close.", "junior"),
        ("Software Developer", "Build backend services, APIs, tests, and release improvements.", "mid"),
        ("Senior Architect", "Lead design reviews, technical planning, and project coordination.", "senior"),
        ("Material Engineer", "Run materials analysis, testing, compliance checks, and documentation.", "mid"),
    ]

    mock_review.side_effect = [
        {
            "score": 88,
            "decision": "pass",
            "strengths": [],
            "gaps": [],
            "must_fix": [],
            "keyword_coverage": [],
            "revised_summary": f"{title} summary",
        }
        for title, _, _ in role_cases
    ]
    mock_apply_review.side_effect = lambda context, draft_content, review: (draft_content, "test-provider")

    router = MagicMock()
    flattened = []
    for title, _, _ in role_cases:
        flattened.append({"keywords": []})
        flattened.append(
            {
                "headline": title,
                "professional_summary": f"Tailored summary for {title}.",
                "selected_experiences": [],
                "selected_projects": [],
                "selected_skills": ["Communication", "Problem Solving"],
                "tailoring_notes": [],
            }
        )
    router.generate.side_effect = flattened

    svc = CVWorkflowService(db_session, router=router)

    for title, description, seniority in role_cases:
        job = _create_job_for_role(
            db_session,
            title=title,
            description=description,
            seniority=seniority,
        )
        result = svc.run_cv_workflow({"job_post_id": str(job.id), "resume_track_slug": db_track.slug})

        draft = db_session.query(ResumeDraft).filter_by(job_post_id=job.id).first()
        assert draft is not None
        assert result["draft_id"] == str(draft.id)
        assert float(draft.score or 0) == 88
        assert draft.content["headline"] == title
