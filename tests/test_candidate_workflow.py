from __future__ import annotations

from unittest.mock import MagicMock

from job_agent.models import Candidate, ExperienceFact, FactSource, ProjectFact, ResumeDraft
from job_agent.services.workflows import CVWorkflowService


def test_load_context_uses_master_profile_when_no_default_candidate_id(
    db_session,
    db_job,
    db_profile,
    db_track,
    monkeypatch,
):
    monkeypatch.setattr("job_agent.services.workflows.settings.default_candidate_id", "")
    service = CVWorkflowService(db_session)

    context = service._load_context(str(db_job.id), db_track.slug)

    assert context.profile is not None
    assert context.candidate is None


def test_load_context_uses_candidate_when_default_candidate_id_set(
    db_session,
    db_job,
    db_track,
    monkeypatch,
):
    candidate = Candidate(full_name="Candidate User", email="candidate@example.com")
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)
    monkeypatch.setattr("job_agent.services.workflows.settings.default_candidate_id", candidate.id)

    service = CVWorkflowService(db_session)
    context = service._load_context(str(db_job.id), db_track.slug)

    assert context.candidate is not None
    assert context.profile is None


def test_candidate_profile_dict_builds_correct_shape(db_session):
    candidate = Candidate(full_name="Candidate User", email="candidate@example.com")
    source = FactSource(
        candidate_id=candidate.id,
        source_path="candidate_source.txt",
        source_hash="hash-candidate",
        raw_content="raw",
    )
    db_session.add(candidate)
    db_session.add(source)
    db_session.flush()
    db_session.add(
        ExperienceFact(
            candidate_id=candidate.id,
            fact_source_id=source.id,
            item_id="exp-1",
            section_name="Experience",
            role_title="Data Engineer",
            organization="Acme",
            verified_core_facts=["Built ETL jobs."],
            tools_and_tech=["Python", "SQL"],
        )
    )
    db_session.add(
        ProjectFact(
            candidate_id=candidate.id,
            fact_source_id=source.id,
            item_id="proj-1",
            project_name="ETL Platform",
            short_resume_line="Pipeline automation",
            tools_and_tech=["Python"],
        )
    )
    db_session.commit()

    service = CVWorkflowService(db_session)
    profile_data = service._candidate_profile_dict(candidate)

    assert profile_data["full_name"] == "Candidate User"
    assert profile_data["experiences"][0]["role_title"] == "Data Engineer"
    assert profile_data["projects"][0]["name"] == "ETL Platform"


def test_run_cv_workflow_uses_candidate_dict_when_candidate_set(
    db_session,
    db_job,
    db_track,
    tmp_path,
    monkeypatch,
):
    candidate = Candidate(full_name="Candidate User", email="candidate@example.com")
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)
    monkeypatch.setattr("job_agent.services.workflows.settings.default_candidate_id", candidate.id)
    monkeypatch.setattr("job_agent.services.documents.settings.artifacts_dir", tmp_path)

    writer_draft = {
        "headline": "Data Engineer",
        "professional_summary": "Candidate-focused summary.",
        "selected_experiences": [],
        "selected_projects": [],
        "selected_skills": ["Python"],
        "tailoring_notes": [],
    }
    review = {
        "score": 90,
        "decision": "pass",
        "strengths": [],
        "gaps": [],
        "must_fix": [],
        "keyword_coverage": ["python"],
        "revised_summary": "Candidate-focused summary.",
    }
    router = MagicMock()
    router.generate.side_effect = [{"keywords": []}, writer_draft, review]

    service = CVWorkflowService(db_session, router=router)
    payload = {"job_post_id": str(db_job.id), "resume_track_slug": db_track.slug}
    result = service.run_cv_workflow(payload)

    draft = db_session.query(ResumeDraft).filter_by(job_post_id=db_job.id).first()
    assert draft is not None
    assert result["draft_id"] == str(draft.id)
