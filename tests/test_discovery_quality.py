from __future__ import annotations

from uuid import uuid4

from job_agent.models import JobPost, JobTrackScore
from job_agent.services.company_snapshot import CompanySnapshotService


def test_company_snapshot_requires_real_enriched_description(db_session):
    job = JobPost(
        id=uuid4(),
        company="Needs Input Co",
        title="Data Analyst",
        description="",
        queue_state="shortlisted",
        enrichment_status="needs_input",
        source_name="manual",
        source_url="https://example.com/job",
    )
    db_session.add(job)
    db_session.commit()

    service = CompanySnapshotService(db_session)

    assert service.eligible(job) is False


def test_company_snapshot_unlocks_for_shortlisted_or_high_fit_jobs(db_session):
    shortlisted = JobPost(
        id=uuid4(),
        company="Shortlist Co",
        title="Analytics Engineer",
        description="Real job description",
        queue_state="shortlisted",
        enrichment_status="ok",
        source_name="manual",
        source_url="https://example.com/shortlist",
    )
    strong_fit = JobPost(
        id=uuid4(),
        company="Strong Fit Co",
        title="ML Engineer",
        description="Real job description",
        queue_state="new",
        enrichment_status="partial",
        source_name="manual",
        source_url="https://example.com/fit",
    )
    db_session.add_all([shortlisted, strong_fit])
    db_session.flush()
    db_session.add(
        JobTrackScore(
            job_post_id=strong_fit.id,
            resume_track_id=uuid4(),
            score=90.0,
            matched_keywords=["python"],
        )
    )
    db_session.commit()

    service = CompanySnapshotService(db_session)

    assert service.eligible(shortlisted) is True
    assert service.eligible(strong_fit) is True
