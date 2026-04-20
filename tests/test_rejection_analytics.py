from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from job_agent.models import Application, ResumeDraft
from job_agent.services.rejection_analytics import RejectionAnalyticsService


def _create_draft(
    db_session,
    *,
    job_post_id,
    resume_track_id,
    score: float | None,
    review_feedback: dict | None = None,
) -> ResumeDraft:
    draft = ResumeDraft(
        id=uuid4(),
        job_post_id=job_post_id,
        resume_track_id=resume_track_id,
        provider="test",
        status="drafted",
        score=score,
        content={},
        review_feedback=review_feedback or {},
        tex_path="fake.tex",
        approved=False,
    )
    db_session.add(draft)
    db_session.commit()
    db_session.refresh(draft)
    return draft


def _create_application(
    db_session,
    *,
    job_post_id,
    resume_track_id,
    resume_draft_id=None,
    status: str = "applied",
    created_at: datetime | None = None,
) -> Application:
    application = Application(
        id=uuid4(),
        job_post_id=job_post_id,
        resume_track_id=resume_track_id,
        resume_draft_id=resume_draft_id,
        status=status,
    )
    if created_at is not None:
        application.created_at = created_at
        application.applied_at = created_at
    db_session.add(application)
    db_session.commit()
    db_session.refresh(application)
    return application


def _seed_scored_application(
    db_session,
    *,
    job_post_id,
    resume_track_id,
    status: str,
    score: float,
    review_feedback: dict | None = None,
    created_at: datetime | None = None,
) -> Application:
    draft = _create_draft(
        db_session,
        job_post_id=job_post_id,
        resume_track_id=resume_track_id,
        score=score,
        review_feedback=review_feedback,
    )
    return _create_application(
        db_session,
        job_post_id=job_post_id,
        resume_track_id=resume_track_id,
        resume_draft_id=draft.id,
        status=status,
        created_at=created_at,
    )


def test_analyse_returns_insufficient_data_when_fewer_than_5_apps(db_session, db_job, db_track):
    for _ in range(3):
        _seed_scored_application(
            db_session,
            job_post_id=db_job.id,
            resume_track_id=db_track.id,
            status="applied",
            score=72.0,
        )

    service = RejectionAnalyticsService(db_session)
    with pytest.raises(ValueError, match="insufficient_data"):
        service.analyse()


def test_analyse_funnel_counts_correctly(db_session, db_job, db_track):
    statuses = ["responded"] * 4 + ["interview"] * 2 + ["offer"] + ["rejected"] * 3
    for index, status in enumerate(statuses):
        _seed_scored_application(
            db_session,
            job_post_id=db_job.id,
            resume_track_id=db_track.id,
            status=status,
            score=70.0 + index,
        )

    result = RejectionAnalyticsService(db_session).analyse()
    funnel = result["funnel"]

    assert funnel["applied"] == 10
    assert funnel["offer"] == 1
    assert funnel["offer_rate_pct"] == 10.0


def test_analyse_score_buckets_group_correctly(db_session, db_job, db_track):
    for score in [55, 70, 80, 90, 95]:
        _seed_scored_application(
            db_session,
            job_post_id=db_job.id,
            resume_track_id=db_track.id,
            status="applied",
            score=score,
        )

    result = RejectionAnalyticsService(db_session).analyse()
    buckets = result["score_analysis"]["buckets"]
    high_bucket = next(bucket for bucket in buckets if bucket["range"] == "85-100")

    assert len(buckets) == 4
    assert high_bucket["count"] == 2


def test_analyse_skill_gaps_aggregates_from_rejected_applications(db_session, db_job, db_track):
    for _ in range(3):
        _seed_scored_application(
            db_session,
            job_post_id=db_job.id,
            resume_track_id=db_track.id,
            status="rejected",
            score=78.0,
            review_feedback={"gaps": ["missing Python", "missing SQL"]},
        )
    for _ in range(2):
        _seed_scored_application(
            db_session,
            job_post_id=db_job.id,
            resume_track_id=db_track.id,
            status="applied",
            score=82.0,
        )

    result = RejectionAnalyticsService(db_session).analyse()
    gaps = {item["gap"]: item["occurrences"] for item in result["skill_gaps"]}

    assert gaps["missing Python"] >= 3


def test_analyse_weekly_activity_covers_last_12_weeks(db_session, db_job, db_track):
    now = datetime.now(timezone.utc)
    week_offsets = [1, 1, 3, 3, 5]
    for offset in week_offsets:
        dt = now - timedelta(weeks=offset)
        _seed_scored_application(
            db_session,
            job_post_id=db_job.id,
            resume_track_id=db_track.id,
            status="applied",
            score=76.0,
            created_at=dt,
        )

    result = RejectionAnalyticsService(db_session).analyse()
    weekly = result["weekly_activity"]
    weekly_map = {row["week"]: row["applied"] for row in weekly}

    assert len(weekly) <= 12
    for offset in {1, 3, 5}:
        dt = now - timedelta(weeks=offset)
        iso = dt.isocalendar()
        key = f"{iso.year}-W{iso.week:02d}"
        assert key in weekly_map


def test_api_endpoint_returns_200_with_data(client, db_session, db_job, db_track):
    for status in ["applied", "responded", "interview", "offer", "rejected"]:
        _seed_scored_application(
            db_session,
            job_post_id=db_job.id,
            resume_track_id=db_track.id,
            status=status,
            score=80.0,
        )

    response = client.get("/analytics/rejection-patterns")

    assert response.status_code == 200
    data = response.json()
    assert "funnel" in data
    assert "score_analysis" in data


def test_api_endpoint_returns_insufficient_data_when_empty(client):
    response = client.get("/analytics/rejection-patterns")

    assert response.status_code == 200
    assert response.json() == {"status": "insufficient_data", "required": 5, "current": 0}
