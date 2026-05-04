from __future__ import annotations

from datetime import datetime, timezone
import uuid

from job_agent.models import (
    CareerPageSource,
    DiscoveryEvent,
    JobPost,
    JobTrackScore,
    OfferDecision,
    ResumeDraft,
    VerifiedCandidateFact,
)


def test_discovery_health_partial_renders(client, db_session):
    job = JobPost(
        id=uuid.uuid4(),
        company="SignalCo",
        title="Platform Engineer",
        description="Long enough description " * 40,
        source_name="career_page",
        source_url="https://signal.example/jobs/1",
        canonical_apply_url="https://signal.example/jobs/1",
        created_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    db_session.add(job)
    db_session.flush()
    db_session.add_all(
        [
            DiscoveryEvent(
                source_name="career_page",
                acquisition_path="company_scan",
                outcome="ingested",
                reason="new_import",
                source_url=job.source_url,
                canonical_key="signalco|platformengineer|italy",
                job_post_id=job.id,
            ),
            DiscoveryEvent(
                source_name="linkedin_email_alert",
                acquisition_path="gmail_alert",
                outcome="duplicate",
                reason="canonical_apply_url",
                source_url=job.source_url,
                canonical_key="signalco|platformengineer|italy",
                job_post_id=job.id,
            ),
        ]
    )
    db_session.commit()

    response = client.get("/analytics/discovery-health", headers={"HX-Request": "true"})

    assert response.status_code == 200
    assert "Discovery Health" in response.text
    assert "company scan" in response.text.lower()


def test_story_bank_rebuild_and_page_render(client, db_session, db_job, db_track):
    fact = VerifiedCandidateFact(
        gap_label="Kubernetes",
        evidence="Led a GKE rollout and documented the migration path.",
        fact_type="tool",
        is_active=True,
    )
    draft = ResumeDraft(
        job_post_id=db_job.id,
        resume_track_id=db_track.id,
        provider="test",
        status="pass",
        score=91,
        approved=True,
        content={
            "selected_experiences": [
                {
                    "title": "Software Engineer",
                    "company": "Acme",
                    "bullets": [
                        "Built deployment tooling for multiple services.",
                        "Cut release friction across the team.",
                    ],
                }
            ]
        },
        review_feedback={},
    )
    db_session.add_all([fact, draft])
    db_session.commit()

    rebuild = client.post("/ui/story-bank/rebuild")
    page = client.get("/ui/story-bank")

    assert rebuild.status_code == 204
    assert page.status_code == 200
    assert "Story Bank" in page.text
    assert "Kubernetes" in page.text
    assert "Software Engineer at Acme" in page.text


def test_offer_compass_add_and_render(client, db_session):
    response = client.post(
        "/ui/offers/add",
        data={
            "company": "Northwind",
            "title": "Product Analyst",
            "salary_text": "€55k",
            "location": "Milan",
            "remote_policy": "Hybrid",
            "growth_notes": "Strong mentorship path",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Offer Compass" in response.text
    assert "Northwind" in response.text

    offers = db_session.query(OfferDecision).all()
    assert len(offers) == 1


def test_package_check_partial_renders(client, db_session, db_job, db_track):
    db_session.add(
        JobTrackScore(
            job_post_id=db_job.id,
            resume_track_id=db_track.id,
            score=72,
            matched_keywords=["python"],
        )
    )
    db_session.commit()

    response = client.get(f"/ui/jobs/{db_job.id}/package-check")

    assert response.status_code == 200
    assert "Application Snapshot" in response.text
    assert "Confirm and Queue Package" in response.text
    assert f'hx-target="#job-group-{db_job.id}"' in response.text
    assert "Add to Shortlist First" in response.text


def test_snapshot_partial_renders_for_shortlisted_job(client, db_session, db_job, monkeypatch):
    job = db_session.get(JobPost, db_job.id)
    job.queue_state = "shortlisted"
    db_session.add(job)
    db_session.commit()

    monkeypatch.setattr(
        "job_agent.services.company_snapshot.CompanySnapshotService._build_snapshot_content",
        lambda self, current_job: (
            {
                "headline": f"{current_job.company} snapshot",
                "mission_product": "Mission",
                "team_context": "Team",
                "hiring_clues": ["Fresh listing"],
                "talking_points": ["Point A"],
                "open_questions": ["Question A"],
            },
            "heuristic",
        ),
    )

    response = client.get(f"/ui/jobs/{db_job.id}/snapshot")

    assert response.status_code == 200
    assert "Opportunity Snapshot" in response.text
    assert "Mission" in response.text


def test_career_scanner_records_source_trail_and_discovery_event(monkeypatch, db_session, db_track):
    from job_agent.services.career_scanner import CareerPageScanner

    class _Response:
        def __init__(self, text: str):
            self.text = text
            self.status_code = 200
            self.is_success = True

    source = CareerPageSource(company="Bending Spoons", career_url="https://example.com/careers")
    db_session.add(source)
    db_session.commit()

    monkeypatch.setattr(
        "job_agent.services.career_scanner.httpx.get",
        lambda *_args, **_kwargs: _Response('<a href="/jobs/data-engineer">Data Engineer</a>'),
    )

    count = CareerPageScanner().scan_all(db_session)
    post = db_session.query(JobPost).one()

    assert count == 1
    assert post.extracted_metadata["source_trail"]["path"] == "company_scan"
    assert db_session.query(DiscoveryEvent).count() == 1


def test_gmail_upsert_stamps_source_trail_and_event(db_session, db_track):
    from job_agent.services.gmail import GmailService

    service = GmailService()
    tracks = [db_track]
    post = service._upsert_job_post(
        {
            "title": "Data Engineer",
            "company": "Acme",
            "location": "Italy",
            "url": "https://www.linkedin.com/jobs/view/12345",
        },
        db_session,
        tracks,
    )
    db_session.commit()

    assert post is not None
    assert post.extracted_metadata["source_trail"]["path"] == "gmail_alert"
    assert db_session.query(DiscoveryEvent).count() == 1


def test_enrich_pending_prioritizes_shortlist_then_review(monkeypatch, db_session):
    from job_agent.services.job_fetcher import JobFetcher

    now = datetime.now(timezone.utc)
    jobs = [
        JobPost(
            id=uuid.uuid4(),
            company="SavedCo",
            title="Saved",
            description="",
            source_url="https://example.com/saved",
            canonical_apply_url="https://example.com/saved",
            queue_state="saved",
            created_at=now,
            last_seen_at=now,
        ),
        JobPost(
            id=uuid.uuid4(),
            company="ReviewCo",
            title="Review",
            description="",
            source_url="https://example.com/review",
            canonical_apply_url="https://example.com/review",
            queue_state="new",
            created_at=now,
            last_seen_at=now,
        ),
        JobPost(
            id=uuid.uuid4(),
            company="ShortlistCo",
            title="Shortlist",
            description="",
            source_url="https://example.com/shortlist",
            canonical_apply_url="https://example.com/shortlist",
            queue_state="shortlisted",
            created_at=now,
            last_seen_at=now,
        ),
    ]
    db_session.add_all(jobs)
    db_session.commit()

    seen: list[str] = []

    def fake_enrich(self, job, session):
        del session
        seen.append(job.company)
        job.description = "Full description " * 40
        job.enrichment_status = "ok"
        return True

    monkeypatch.setattr(JobFetcher, "enrich_job", fake_enrich)

    count = JobFetcher().enrich_pending(db_session, limit=3)

    assert count == 3
    assert seen[:2] == ["ShortlistCo", "ReviewCo"]
