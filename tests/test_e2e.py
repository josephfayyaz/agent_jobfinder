from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from job_agent.models import JobPost, ResumeDraft
from job_agent.services.fact_ingestion import FactSheetIngestionService
from job_agent.services.matching import score_tracks_for_job
from job_agent.services.workflows import CVWorkflowService

SAMPLE_FACT_SHEET = """
SECTION: CORE PROFILE
FULL_NAME: Test User
PRIMARY_EMAIL: test@example.com
PHONE: +39 000 000 0000
CURRENT_LOCATION: Turin, Italy
CURRENT_POSITIONING: Data Engineer

SECTION: PROFESSIONAL EXPERIENCE
ITEM_ID: exp-1
ROLE_TITLE: Data Engineer
ORGANIZATION: ACME Corp
START_DATE: 2022-01
END_DATE: 2023-12
VERIFIED_CORE_FACTS:
- Built ETL pipelines using Python and Airflow
- Reduced query latency by 30 percent
TOOLS_AND_TECH:
- Python
- SQL
- dbt
- Airflow

SECTION: EDUCATION
ITEM_ID: edu-1
INSTITUTION: Politecnico di Torino
DEGREE: MSc Computer Engineering
START_DATE: 2023-09
END_DATE: 2026-06
"""


def _ingest_profile(db_session, tmp_path: Path) -> None:
    fact_file = tmp_path / "fact_sheet.txt"
    fact_file.write_text(SAMPLE_FACT_SHEET, encoding="utf-8")
    FactSheetIngestionService(db_session).ingest(path=str(fact_file), content=SAMPLE_FACT_SHEET)


def _create_job(db_session) -> JobPost:
    job = JobPost(
        id=uuid4(),
        source_name="manual",
        source_url="https://example.com/jobs/123",
        canonical_apply_url="https://example.com/jobs/123",
        company="Acme",
        title="Data Engineer",
        location="Milan, Italy",
        description="Python, SQL, dbt, and Airflow required for analytics pipelines.",
        status="new",
        created_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


def _fake_render_resume(tmp_path: Path):
    def _render(profile, job, track, content, draft_id):
        del profile, job, track, content
        tex_path = tmp_path / f"{draft_id}.tex"
        tex_path.write_text("test tex", encoding="utf-8")
        return str(tex_path)

    return _render


def test_full_pipeline_job_to_approved_cv(db_session, db_track, tmp_path, monkeypatch):
    _ingest_profile(db_session, tmp_path)
    job = _create_job(db_session)

    monkeypatch.setattr("job_agent.services.matching._get_embedding", lambda _text: None)
    scores = score_tracks_for_job(job, [db_track])

    assert scores[0]["slug"] == db_track.slug
    assert scores[0]["score"] > 0

    responses = iter(
        [
            {
                "headline": "Data Engineer",
                "professional_summary": "Data engineer with 3 years building ETL pipelines.",
                "selected_experiences": [
                    {
                        "title": "Data Engineer",
                        "company": "Acme",
                        "bullets": [
                            "Built ETL pipeline reducing latency by 30%.",
                            "Designed dbt data models for 5 business domains.",
                            "Deployed Airflow DAGs processing 1M records daily.",
                        ],
                    }
                ],
                "selected_projects": [],
                "selected_skills": ["Python", "SQL", "dbt", "Airflow"],
                "tailoring_notes": [],
            },
            {
                "score": 88,
                "decision": "pass",
                "strengths": [],
                "gaps": [],
                "must_fix": [],
                "keyword_coverage": ["python", "sql", "dbt", "airflow"],
                "revised_summary": "Data engineer with 3 years building ETL pipelines.",
            },
        ]
    )

    router = object.__new__(__import__("job_agent.llm").llm.LLMRouter)
    monkeypatch.setattr(router, "generate", lambda **kwargs: next(responses))
    monkeypatch.setattr(
        "job_agent.services.workflows.render_resume_tex",
        _fake_render_resume(tmp_path),
    )

    service = CVWorkflowService(db_session, router=router)
    task = service.queue_cv_workflow(job.id, db_track.slug)
    processed = service.process_next_task()

    assert task.id == processed.id
    assert processed.status == "completed"

    draft = db_session.query(ResumeDraft).filter_by(job_post_id=job.id).one()
    assert draft.status == "pass"
    assert float(draft.score or 0) == 88.0
    assert draft.approved is False

    draft.approved = True
    db_session.commit()
    db_session.refresh(draft)
    assert draft.approved is True


def test_pipeline_revises_on_low_score(db_session, db_track, tmp_path, monkeypatch):
    _ingest_profile(db_session, tmp_path)
    job = _create_job(db_session)

    monkeypatch.setattr("job_agent.services.matching._get_embedding", lambda _text: None)
    monkeypatch.setattr("job_agent.services.workflows.settings.use_claude_final_review", False)
    monkeypatch.setattr("job_agent.services.workflows.settings.use_openai_escalation", False)
    responses = iter(
        [
            {
                "headline": "Data Engineer",
                "professional_summary": "Initial draft summary.",
                "selected_experiences": [],
                "selected_projects": [],
                "selected_skills": ["Python"],
                "tailoring_notes": [],
            },
            {
                "score": 65,
                "decision": "revise",
                "strengths": [],
                "gaps": ["Missing stronger SQL evidence"],
                "must_fix": ["Add more SQL evidence"],
                "keyword_coverage": ["python"],
                "revised_summary": "Revised summary with more SQL emphasis.",
            },
            {
                "headline": "Data Engineer",
                "professional_summary": "Revised summary with more SQL emphasis.",
                "selected_experiences": [],
                "selected_projects": [],
                "selected_skills": ["Python", "SQL"],
                "tailoring_notes": ["Add more SQL evidence"],
            },
        ]
    )

    router = object.__new__(__import__("job_agent.llm").llm.LLMRouter)
    monkeypatch.setattr(router, "generate", lambda **kwargs: next(responses))
    monkeypatch.setattr(
        "job_agent.services.workflows.render_resume_tex",
        _fake_render_resume(tmp_path),
    )

    service = CVWorkflowService(db_session, router=router)
    service.queue_cv_workflow(job.id, db_track.slug)
    task = service.process_next_task()

    assert task.status == "completed"

    draft = db_session.query(ResumeDraft).filter_by(job_post_id=job.id).one()
    assert draft.status == "revise"
    assert float(draft.score or 0) == 65.0
    assert draft.provider == "lm_studio_revision"


def test_pipeline_low_score_uses_heuristic_rewrite(db_session, db_track, tmp_path, monkeypatch):
    _ingest_profile(db_session, tmp_path)
    job = _create_job(db_session)

    monkeypatch.setattr("job_agent.services.matching._get_embedding", lambda _text: None)
    monkeypatch.setattr("job_agent.services.workflows.settings.use_claude_final_review", False)
    monkeypatch.setattr("job_agent.services.workflows.settings.use_openai_escalation", False)
    responses = iter(
        [
            {
                "headline": "Data Engineer",
                "professional_summary": "Initial low-quality draft summary.",
                "selected_experiences": [],
                "selected_projects": [],
                "selected_skills": ["Python"],
                "tailoring_notes": [],
            },
            {
                "score": 30,
                "decision": "rewrite",
                "strengths": [],
                "gaps": ["Missing keywords"],
                "must_fix": ["Rewrite for SQL and dbt relevance"],
                "keyword_coverage": [],
                "revised_summary": "Heuristic rewrite summary.",
            },
        ]
    )

    router = object.__new__(__import__("job_agent.llm").llm.LLMRouter)
    monkeypatch.setattr(router, "generate", lambda **kwargs: next(responses))
    monkeypatch.setattr(
        "job_agent.services.workflows.render_resume_tex",
        _fake_render_resume(tmp_path),
    )

    service = CVWorkflowService(db_session, router=router)
    service.queue_cv_workflow(job.id, db_track.slug)
    task = service.process_next_task()

    assert task.status == "completed"

    draft = db_session.query(ResumeDraft).filter_by(job_post_id=job.id).one()
    assert draft.status == "rewrite"
    assert draft.provider == "heuristic_rewrite"
    assert float(draft.score or 0) == 30.0
