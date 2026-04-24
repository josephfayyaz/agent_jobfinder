from __future__ import annotations

import uuid


def _draft(db_session, db_job, db_track, *, missing: list[str], status: str | None = None):
    from job_agent.models import Application, ResumeDraft

    draft = ResumeDraft(
        id=uuid.uuid4(),
        job_post_id=db_job.id,
        resume_track_id=db_track.id,
        provider="test",
        status="drafted",
        content={},
        review_feedback={"missing_keywords": missing},
    )
    db_session.add(draft)
    db_session.commit()
    db_session.refresh(draft)

    if status is not None:
        db_session.add(
            Application(
                job_post_id=db_job.id,
                resume_track_id=db_track.id,
                resume_draft_id=draft.id,
                status=status,
            )
        )
        db_session.commit()

    return draft


def test_skill_gap_returns_empty_with_no_drafts(db_session):
    from job_agent.services.skill_gap_analytics import SkillGapAnalyticsService

    svc = SkillGapAnalyticsService(session=db_session)
    result = svc.compute(candidate_id="nonexistent", top_n=20)
    assert result["top_gaps"] == []
    assert result["total_drafts_analyzed"] == 0


def test_skill_gap_aggregates_missing_keywords(db_session, db_job, db_track):
    from job_agent.services.skill_gap_analytics import SkillGapAnalyticsService

    candidate_id = str(uuid.uuid4())
    for _ in range(3):
        _draft(db_session, db_job, db_track, missing=["dbt", "spark"])
    _draft(db_session, db_job, db_track, missing=["dbt"])

    svc = SkillGapAnalyticsService(session=db_session)
    result = svc.compute(candidate_id=candidate_id, top_n=5)
    skills = {gap["skill"].casefold(): gap["count"] for gap in result["top_gaps"]}
    assert skills["dbt"] == 4
    assert skills["spark"] == 3
    assert result["total_drafts_analyzed"] == 4


def test_skill_gap_skips_archived_drafts(db_session, db_job, db_track):
    from job_agent.services.skill_gap_analytics import SkillGapAnalyticsService

    candidate_id = str(uuid.uuid4())
    _draft(db_session, db_job, db_track, missing=["python"], status="archived")

    svc = SkillGapAnalyticsService(session=db_session)
    result = svc.compute(candidate_id=candidate_id, top_n=5)
    assert result["top_gaps"] == []
    assert result["total_drafts_analyzed"] == 0


def test_analytics_skill_gaps_endpoint(client):
    resp = client.get("/analytics/skill-gaps")
    assert resp.status_code == 200
    data = resp.json()
    assert "top_gaps" in data
    assert "total_drafts_analyzed" in data
    assert "unique_missing_skills" in data


def test_analytics_skill_gaps_htmx_partial(client):
    resp = client.get("/analytics/skill-gaps", headers={"HX-Request": "true"})
    assert resp.status_code == 200
    assert "Market Skill Gaps" in resp.text


def test_workflow_computes_missing_keywords(db_session, sample_profile):
    from job_agent.services.workflows import CVWorkflowService

    service = CVWorkflowService(db_session)
    missing = service._compute_missing_keywords(
        profile_dict={**sample_profile, "global_skills": ["Python", "SQL"]},
        ranked_keywords=[
            {"term": "Python"},
            {"term": "dbt"},
            {"term": "Spark"},
            {"keyword": "SQL"},
        ],
    )
    assert missing == ["dbt", "Spark"]
