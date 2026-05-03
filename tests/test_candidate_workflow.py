from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

from job_agent.models import Candidate, EducationFact, ExperienceFact, FactSource, ProjectFact, ResumeDraft
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


def test_load_context_uses_explicit_candidate_id_over_changed_default(
    db_session,
    db_job,
    db_track,
    monkeypatch,
):
    original_candidate = Candidate(full_name="Original Candidate", email="original@example.com")
    switched_candidate = Candidate(full_name="Switched Candidate", email="switched@example.com")
    db_session.add_all([original_candidate, switched_candidate])
    db_session.commit()
    db_session.refresh(original_candidate)
    db_session.refresh(switched_candidate)
    monkeypatch.setattr("job_agent.services.workflows.settings.default_candidate_id", switched_candidate.id)

    service = CVWorkflowService(db_session)
    context = service._load_context(
        str(db_job.id),
        db_track.slug,
        candidate_id=original_candidate.id,
    )

    assert context.candidate is not None
    assert context.candidate.id == original_candidate.id


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
    candidate = Candidate(
        full_name="Candidate User",
        email="candidate@example.com",
        skills_json={"programming_languages": ["Python", "SQL"], "methods": ["ETL", "Analytics"]},
    )
    source = FactSource(
        candidate_id=candidate.id,
        source_path="candidate_source.txt",
        source_hash="hash-candidate-2",
        raw_content="raw",
    )
    db_session.add(candidate)
    db_session.add(source)
    db_session.flush()
    db_session.add(
        ProjectFact(
            candidate_id=candidate.id,
            fact_source_id=source.id,
            item_id="proj-1",
            project_name="Warehouse rollout",
            short_resume_line="Built ETL jobs in Python and SQL for analytics reporting.",
            verified_core_facts=["Built ETL jobs in Python and SQL for analytics reporting."],
        )
    )
    db_session.add(
        EducationFact(
            candidate_id=candidate.id,
            fact_source_id=source.id,
            item_id="edu-1",
            degree="MSc Data Engineering",
            institution="Example University",
            status="completed",
        )
    )
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
    router.generate.side_effect = [{"keywords": []}, writer_draft, review, writer_draft]

    service = CVWorkflowService(db_session, router=router)
    payload = {"job_post_id": str(db_job.id), "resume_track_slug": db_track.slug}
    result = service.run_cv_workflow(payload)

    draft = db_session.query(ResumeDraft).filter_by(job_post_id=db_job.id).first()
    assert draft is not None
    assert result["draft_id"] == str(draft.id)
    assert draft.candidate_id == candidate.id


def test_queue_cv_workflow_persists_candidate_id_snapshot(
    db_session,
    db_job,
    db_track,
    monkeypatch,
):
    candidate = Candidate(full_name="Queued Candidate", email="queued@example.com")
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)
    monkeypatch.setattr("job_agent.services.workflows.settings.default_candidate_id", candidate.id)

    service = CVWorkflowService(db_session)
    task = service.queue_cv_workflow(
        job_post_id=db_job.id,
        resume_track_slug=db_track.slug,
    )

    assert task.payload["candidate_id"] == candidate.id


def test_run_cv_workflow_sanitizes_sparse_candidate_hallucinations(
    db_session,
    db_job,
    db_track,
    tmp_path,
    monkeypatch,
):
    candidate = Candidate(
        full_name="Farah Lodi",
        email="farah@example.test",
        skills_json={"business_tools": ["Excel", "SAP"], "methods": ["Reconciliation", "Month-end close"]},
    )
    source = FactSource(
        candidate_id=candidate.id,
        source_path="farah_source.txt",
        source_hash="hash-farah",
        raw_content="raw",
    )
    db_session.add(candidate)
    db_session.add(source)
    db_session.flush()
    db_session.add(
        EducationFact(
            id=uuid4(),
            candidate_id=candidate.id,
            fact_source_id=source.id,
            item_id="edu-1",
            degree="BSc Accounting",
            institution="Uni Test",
            status="completed",
        )
    )
    db_session.add(
        ProjectFact(
            id=uuid4(),
            candidate_id=candidate.id,
            fact_source_id=source.id,
            item_id="proj-1",
            project_name="Profile note evidence",
            short_resume_line="Handled reconciliations, invoice checks, and month-end support during internship.",
        )
    )
    db_session.commit()
    db_session.refresh(candidate)

    monkeypatch.setattr("job_agent.services.workflows.settings.default_candidate_id", candidate.id)
    monkeypatch.setattr("job_agent.services.documents.settings.artifacts_dir", tmp_path)

    writer_draft = {
        "headline": "Trainee Accounts Receivable Specialist",
        "professional_summary": "Seasoned accounting professional with 3+ years of experience and 98% accuracy.",
        "selected_experiences": [
            {
                "title": "Accounts Receivable Specialist",
                "company": "Invented Corp",
                "location": "Milan, Italy",
                "dates": "2022-2024",
                "bullets": ["Reconciled 200+ customer accounts and reduced balances by 12%."],
            }
        ],
        "selected_projects": [],
        "selected_skills": ["Excel", "SAP", "Reconciliation"],
        "tailoring_notes": [],
    }
    review = {
        "score": 58,
        "decision": "rewrite",
        "strengths": [],
        "gaps": [],
        "must_fix": [],
        "keyword_coverage": [],
        "revised_summary": "ok",
    }
    router = MagicMock()
    router.generate.side_effect = [{"keywords": []}, writer_draft, review, writer_draft]

    service = CVWorkflowService(db_session, router=router)
    result = service.run_cv_workflow({"job_post_id": str(db_job.id), "resume_track_slug": db_track.slug})

    draft = db_session.query(ResumeDraft).filter_by(job_post_id=db_job.id).first()
    assert draft is not None
    assert result["draft_id"] == str(draft.id)
    assert "3+ years of experience" not in draft.content["professional_summary"]
    assert all(item.get("company") != "Invented Corp" for item in draft.content["selected_experiences"])
    assert draft.content["selected_projects"][0]["bullets"] == [
        "Handled reconciliations, invoice checks, and month-end support during internship."
    ]


def test_run_cv_workflow_tops_up_thin_draft_with_existing_profile_evidence(
    db_session,
    db_job,
    db_track,
    tmp_path,
    monkeypatch,
):
    candidate = Candidate(
        full_name="Evidence Rich User",
        email="evidence@example.test",
        skills_json={"programming_languages": ["Python", "SQL"], "business_tools": ["Excel"]},
    )
    source = FactSource(
        candidate_id=candidate.id,
        source_path="evidence_source.txt",
        source_hash="hash-evidence",
        raw_content="raw",
    )
    db_session.add(candidate)
    db_session.add(source)
    db_session.flush()
    db_session.add_all(
        [
            ExperienceFact(
                candidate_id=candidate.id,
                fact_source_id=source.id,
                item_id="exp-1",
                section_name="Experience",
                role_title="Data Engineer Intern",
                organization="Example Data Lab",
                verified_core_facts=["Built SQL checks for recurring ETL jobs."],
                tools_and_tech=["Python", "SQL"],
            ),
            ExperienceFact(
                candidate_id=candidate.id,
                fact_source_id=source.id,
                item_id="exp-2",
                section_name="Experience",
                role_title="Reporting Analyst",
                organization="Finance Ops Team",
                enriched_description_bank=["Prepared weekly Excel reporting packs and reconciled source data."],
                tools_and_tech=["Excel"],
            ),
            ProjectFact(
                candidate_id=candidate.id,
                fact_source_id=source.id,
                item_id="proj-1",
                project_name="Warehouse QA",
                short_resume_line="Automated validation rules for staged warehouse tables.",
                verified_core_facts=["Automated validation rules for staged warehouse tables."],
            ),
            EducationFact(
                candidate_id=candidate.id,
                fact_source_id=source.id,
                item_id="edu-1",
                degree="BSc Information Systems",
                institution="Example University",
                status="completed",
            ),
        ]
    )
    db_session.commit()
    db_session.refresh(candidate)

    monkeypatch.setattr("job_agent.services.workflows.settings.default_candidate_id", candidate.id)
    monkeypatch.setattr("job_agent.services.documents.settings.artifacts_dir", tmp_path)

    writer_draft = {
        "headline": "Junior Data Engineer",
        "professional_summary": "Built reliable reporting workflows.",
        "selected_experiences": [
            {
                "title": "Data Engineer Intern",
                "company": "Example Data Lab",
                "location": "Bologna",
                "dates": "2024",
                "bullets": ["Built SQL checks for recurring ETL jobs."],
            }
        ],
        "selected_projects": [],
        "selected_skills": ["Python"],
        "tailoring_notes": [],
    }
    review = {
        "score": 84,
        "decision": "pass",
        "strengths": [],
        "gaps": [],
        "must_fix": [],
        "keyword_coverage": [],
        "revised_summary": writer_draft["professional_summary"],
    }
    router = MagicMock()
    router.generate.side_effect = [{"keywords": []}, writer_draft, review, writer_draft]

    service = CVWorkflowService(db_session, router=router)
    service.run_cv_workflow({"job_post_id": str(db_job.id), "resume_track_slug": db_track.slug})

    draft = db_session.query(ResumeDraft).filter_by(job_post_id=db_job.id).first()
    assert draft is not None
    assert len(draft.content["selected_experiences"]) >= 2
    assert any(
        item.get("title") == "Reporting Analyst"
        and "Prepared weekly Excel reporting packs and reconciled source data." in (item.get("bullets") or [])
        for item in draft.content["selected_experiences"]
    )
    assert draft.content["selected_projects"]
