from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from job_agent.models import BulletClarification, ResumeDraft
from job_agent.services.bullet_clarify import BulletClarifyService


def _create_draft(db_session, db_job, db_track) -> ResumeDraft:
    draft = ResumeDraft(
        id=uuid4(),
        job_post_id=db_job.id,
        resume_track_id=db_track.id,
        provider="test",
        status="drafted",
        score=80.0,
        content={
            "selected_experiences": [
                {
                    "title": "Data Engineer",
                    "company": "Acme",
                    "bullets": ["Built ETL jobs with Python."],
                },
                {
                    "title": "Analyst",
                    "company": "Beta",
                    "bullets": ["Created reports."],
                },
            ],
            "selected_projects": [
                {
                    "name": "Pipeline Project",
                    "bullets": ["Automated daily pipeline runs."],
                }
            ],
        },
        review_feedback={},
        tex_path="fake.tex",
    )
    db_session.add(draft)
    db_session.commit()
    db_session.refresh(draft)
    return draft


def test_start_clarification_returns_questions_when_gaps_exist(
    db_session,
    db_job,
    db_profile,
    db_track,
    monkeypatch,
):
    del db_profile
    monkeypatch.setattr("job_agent.services.workflows.settings.default_candidate_id", "")
    draft = _create_draft(db_session, db_job, db_track)
    router = MagicMock()
    router.generate.side_effect = [
        {
            "language_map": [
                {"rank": 1, "jd_term": "dbt", "matched_bullet": None, "match_quality": "gap"},
                {"rank": 2, "jd_term": "airflow", "matched_bullet": "Built ETL jobs", "match_quality": "partial"},
            ],
            "gap_count": 2,
            "summary": "Some important gaps found.",
        },
        {
            "questions": [
                {"id": "q1", "question": "Have you used dbt in production?", "context": "Core stack"},
                {"id": "q2", "question": "Did you run Airflow DAGs with SLA targets?", "context": "Ops quality"},
            ]
        },
    ]
    svc = BulletClarifyService(db_session, router=router)

    clarification = svc.start_clarification(draft.id)

    assert clarification.status == "pending_questions"
    assert len(clarification.questions) == 2


def test_start_clarification_skips_questions_when_no_gaps(
    db_session,
    db_job,
    db_profile,
    db_track,
    monkeypatch,
):
    del db_profile
    monkeypatch.setattr("job_agent.services.workflows.settings.default_candidate_id", "")
    draft = _create_draft(db_session, db_job, db_track)
    router = MagicMock()
    router.generate.side_effect = [
        {
            "language_map": [
                {
                    "rank": 1,
                    "jd_term": "Python",
                    "matched_bullet": "Built ETL jobs with Python.",
                    "match_quality": "strong",
                }
            ],
            "gap_count": 0,
            "summary": "Good match.",
        },
        {
            "experiences": [
                {"original_title": "Data Engineer", "bullets": ["Built Python ETL pipelines reducing latency by 40%."]}
            ],
            "projects": [],
            "unchanged_count": 0,
            "rewrite_notes": "Improved specificity",
        },
    ]
    svc = BulletClarifyService(db_session, router=router)

    clarification = svc.start_clarification(draft.id)
    db_session.refresh(draft)

    assert clarification.status == "complete"
    assert draft.content["selected_experiences"][0]["bullets"][0].startswith("Built Python ETL pipelines")


def test_submit_answers_runs_rewrite_with_confirmed_facts(
    db_session,
    db_job,
    db_profile,
    db_track,
    monkeypatch,
):
    del db_profile
    monkeypatch.setattr("job_agent.services.workflows.settings.default_candidate_id", "")
    draft = _create_draft(db_session, db_job, db_track)
    clarification = BulletClarification(
        draft_id=draft.id,
        language_map={"map": [{"jd_term": "dbt", "match_quality": "gap"}], "gap_count": 1},
        questions=[{"id": "q1", "gap_term": "dbt"}, {"id": "q2", "gap_term": "kafka"}],
        status="pending_questions",
    )
    db_session.add(clarification)
    db_session.commit()
    db_session.refresh(clarification)

    captured: dict[str, object] = {}

    def _fake_prompt(language_map, answers, draft_content, job_dict, word_limit):
        captured["answers"] = answers
        del language_map, draft_content, job_dict, word_limit
        return "rewrite"

    monkeypatch.setattr("job_agent.services.bullet_clarify.build_bullet_rewrite_prompt", _fake_prompt)
    router = MagicMock()
    router.generate.return_value = {
        "experiences": [{"original_title": "Data Engineer", "bullets": ["Implemented dbt models improving quality by 25%."]}],
        "projects": [],
        "unchanged_count": 0,
        "rewrite_notes": "Used confirmed facts only.",
    }
    svc = BulletClarifyService(db_session, router=router)
    answers = [
        {"question_id": "q1", "answer": "Yes, built dbt models with tests.", "confirmed": True},
        {"question_id": "q2", "answer": "No", "confirmed": False},
    ]

    updated = svc.submit_answers(clarification.id, answers)

    assert captured["answers"] == answers
    assert updated.status == "complete"


def test_submit_answers_rejects_non_pending_clarification(db_session, db_job, db_track):
    draft = _create_draft(db_session, db_job, db_track)
    clarification = BulletClarification(
        draft_id=draft.id,
        language_map={},
        questions=[],
        status="complete",
    )
    db_session.add(clarification)
    db_session.commit()
    db_session.refresh(clarification)
    svc = BulletClarifyService(db_session, router=MagicMock())

    with pytest.raises(ValueError):
        svc.submit_answers(clarification.id, [])


def test_enforce_word_limit_truncates_long_bullets(db_session):
    svc = BulletClarifyService(db_session, router=MagicMock())
    long_bullet = " ".join(f"word{i}" for i in range(1, 31))
    rewrite = {"experiences": [{"original_title": "Data Engineer", "bullets": [long_bullet]}], "projects": []}

    out = svc._enforce_word_limit(rewrite, 22)
    words = out["experiences"][0]["bullets"][0].split()

    assert len(words) <= 22
    assert words[-1] == "word22"


def test_merge_rewritten_bullets_updates_matching_experiences(db_session):
    svc = BulletClarifyService(db_session, router=MagicMock())
    draft_content = {
        "selected_experiences": [
            {"title": "Data Engineer", "bullets": ["Old data bullet"]},
            {"title": "Analyst", "bullets": ["Old analyst bullet"]},
        ],
        "selected_projects": [{"name": "Pipeline Project", "bullets": ["Old project bullet"]}],
    }
    rewritten = {
        "experiences": [{"original_title": "Data Engineer", "bullets": ["New data bullet"]}],
        "projects": [],
    }

    merged = svc._merge_rewritten_bullets(draft_content, rewritten)

    assert merged["selected_experiences"][0]["bullets"] == ["New data bullet"]
    assert merged["selected_experiences"][1]["bullets"] == ["Old analyst bullet"]


def test_start_clarification_404_for_missing_draft(db_session):
    svc = BulletClarifyService(db_session, router=MagicMock())

    with pytest.raises(ValueError):
        svc.start_clarification(uuid4())


def test_api_start_clarify_endpoint_returns_200(client, db_session, db_job, db_track, monkeypatch):
    draft = _create_draft(db_session, db_job, db_track)
    fake = SimpleNamespace(
        id=uuid4(),
        status="pending_questions",
        language_map={"map": [], "gap_count": 1},
        questions=[{"id": "q1", "question": "Test?"}],
    )
    monkeypatch.setattr(
        "job_agent.services.bullet_clarify.BulletClarifyService.start_clarification",
        lambda self, draft_id: fake,
    )

    response = client.post(f"/drafts/{draft.id}/clarify")

    assert response.status_code == 200
    body = response.json()
    assert {"clarification_id", "status", "language_map", "questions"} <= body.keys()
