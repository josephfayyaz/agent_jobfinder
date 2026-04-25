from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

from job_agent.config import Settings
from job_agent.llm import ProviderUnavailableError
from job_agent.models import ResumeDraft
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
            "selected_experiences": [{"title": "Data Engineer", "bullets": ["Built ETL jobs."]}],
            "selected_projects": [{"name": "Pipeline Project", "bullets": ["Automated runs."]}],
        },
        review_feedback={},
        tex_path="fake.tex",
    )
    db_session.add(draft)
    db_session.commit()
    db_session.refresh(draft)
    return draft


def test_startup_warning_logged_when_candidate_id_unset(monkeypatch):
    from job_agent import main

    mock_warning = MagicMock()
    monkeypatch.setattr(main.settings, "default_candidate_id", "")
    monkeypatch.setattr(main.logger, "warning", mock_warning)

    main._log_startup_config_warning()

    mock_warning.assert_called_once()
    assert "DEFAULT_CANDIDATE_ID is not set" in mock_warning.call_args[0][0]


def test_default_jobspy_queries_are_empty_until_user_sets_roles(monkeypatch):
    monkeypatch.delenv("JOBSPY_DISCOVER_QUERIES", raising=False)
    cfg = Settings()
    assert cfg.jobspy_discover_queries == []


def test_bullet_clarify_handles_provider_error_gracefully(
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
    router.generate.side_effect = ProviderUnavailableError("LM unavailable")
    svc = BulletClarifyService(db_session, router=router)

    clarification = svc.start_clarification(draft.id)

    assert clarification.status == "complete"
    assert clarification.questions == []
    assert clarification.rewritten_bullets == {}


def test_bullet_clarify_handles_json_error_gracefully(
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
    router.generate.side_effect = ValueError("Could not extract valid JSON...")
    svc = BulletClarifyService(db_session, router=router)

    clarification = svc.start_clarification(draft.id)

    assert clarification.status == "complete"
    assert clarification.questions == []
    assert clarification.rewritten_bullets == {}
