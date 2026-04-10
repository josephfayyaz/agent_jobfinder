"""Tests for the CV workflow service."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from job_agent.llm import ProviderUnavailableError
from job_agent.models import ResumeDraft
from job_agent.services.workflows import CVWorkflowService


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
    router.generate.side_effect = [writer_draft, reviewer_result]

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
    router.generate.side_effect = [writer_draft, low_score_review, revised_draft]

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
