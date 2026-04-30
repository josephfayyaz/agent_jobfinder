from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from job_agent.llm import ProviderUnavailableError


def _candidate_fit(job, candidate_id: str) -> dict:
    meta = dict(job.extracted_metadata or {})
    fit_map = dict(meta.get("candidate_fit") or {})
    return dict(fit_map.get(candidate_id) or {})


def test_job_fit_scoring_uses_active_provider_and_persists_metadata(db_session, monkeypatch):
    import job_agent.config as cfg
    from job_agent.models import Candidate, JobPost, MatchProfile
    from job_agent.services.job_fit_scoring import JobFitScoringService

    candidate = Candidate(
        id=str(uuid.uuid4()),
        full_name="Test User",
        spoken_languages=[{"name": "English", "level": "C1"}],
        skills_json={"programming_languages": ["Python", "SQL"], "data_and_analytics": ["dbt", "Airflow"]},
    )
    db_session.add(candidate)
    db_session.add(
        MatchProfile(
            id=str(uuid.uuid4()),
            candidate_id=candidate.id,
            target_roles=["Data Engineer"],
            location_preferences={"preferred_countries": ["Italy"]},
        )
    )
    job = JobPost(
        id=uuid.uuid4(),
        company="Acme",
        title="Data Engineer",
        location="Milan, Italy",
        country="Italy",
        description=(
            "We are looking for a data engineer to build Python pipelines, SQL models, "
            "dbt transformations, and Airflow scheduling for analytics workloads."
        ),
        source_name="manual",
        source_url="https://example.com/jobs/1",
        canonical_apply_url="https://example.com/jobs/1",
    )
    db_session.add(job)
    db_session.commit()

    monkeypatch.setattr(cfg.settings, "default_candidate_id", candidate.id, raising=False)
    monkeypatch.setattr(cfg.settings, "llm_provider_mode", "lm_studio", raising=False)
    monkeypatch.setattr(cfg.settings, "jobspy_discover_queries", ["Data Engineer"], raising=False)
    monkeypatch.setattr(cfg.settings, "job_search_countries", ["Italy"], raising=False)
    monkeypatch.setattr(
        cfg.settings,
        "job_search_languages",
        [{"name": "English", "level": "professional"}],
        raising=False,
    )

    router = MagicMock()
    router.generate_with_retry.return_value = {
        "fit_score": 88,
        "matched_evidence": ["Built Python pipelines", "Worked with SQL and dbt"],
        "top_gaps": ["No explicit Kubernetes evidence"],
        "language_assessment": {"label": "good", "reason": "English is configured strongly."},
        "seniority_assessment": {"label": "aligned", "reason": "Role reads as junior or mid-compatible."},
        "short_reason": "Strong fit for a data platform candidate.",
    }

    result = JobFitScoringService(db_session, router=router).score_and_persist(
        job,
        candidate_id=candidate.id,
        force=True,
    )

    assert result["score_source"] == "provider"
    assert result["provider_mode"] == "lm_studio"
    assert result["fit_score"] == 88
    db_session.refresh(job)
    persisted = _candidate_fit(job, candidate.id)
    assert persisted["fit_score"] == 88
    assert persisted["score_source"] == "provider"
    assert persisted["matched_evidence"] == ["Built Python pipelines", "Worked with SQL and dbt"]


def test_job_fit_scoring_falls_back_when_provider_fails(db_session, monkeypatch):
    import job_agent.config as cfg
    from job_agent.models import Candidate, JobPost, MatchProfile, ResumeTrack
    from job_agent.services.job_fit_scoring import JobFitScoringService

    candidate = Candidate(
        id=str(uuid.uuid4()),
        full_name="Fallback User",
        spoken_languages=[{"name": "English", "level": "C1"}],
        skills_json={"programming_languages": ["Python", "SQL"]},
    )
    db_session.add(candidate)
    db_session.add(
        MatchProfile(
            id=str(uuid.uuid4()),
            candidate_id=candidate.id,
            target_roles=["Data Engineer"],
            location_preferences={"preferred_countries": ["Italy"]},
        )
    )
    db_session.add(
        ResumeTrack(
            id=uuid.uuid4(),
            slug="data-engineering",
            title="Data Engineer",
            role_family="data",
            baseline_summary="",
            target_keywords=["python", "sql", "warehouse"],
            emphasis={},
            linkedin_strategy="",
            github_strategy="",
            active=True,
        )
    )
    job = JobPost(
        id=uuid.uuid4(),
        company="Beta",
        title="Data Engineer",
        location="Rome, Italy",
        country="Italy",
        description=(
            "We are hiring a data engineer to build Python ETL jobs and SQL transformations "
            "for the warehouse and BI stack."
        ),
        source_name="manual",
        source_url="https://example.com/jobs/2",
        canonical_apply_url="https://example.com/jobs/2",
    )
    db_session.add(job)
    db_session.commit()

    monkeypatch.setattr(cfg.settings, "llm_provider_mode", "lm_studio", raising=False)
    monkeypatch.setattr(cfg.settings, "jobspy_discover_queries", ["Data Engineer"], raising=False)
    monkeypatch.setattr(cfg.settings, "job_search_countries", ["Italy"], raising=False)
    monkeypatch.setattr(
        cfg.settings,
        "job_search_languages",
        [{"name": "English", "level": "professional"}],
        raising=False,
    )

    router = MagicMock()
    router.generate_with_retry.side_effect = ProviderUnavailableError("provider offline")

    result = JobFitScoringService(db_session, router=router).score_and_persist(
        job,
        candidate_id=candidate.id,
        force=True,
    )

    assert result["score_source"] == "fallback"
    assert result["fit_score"] > 0
    assert "provider" in result["short_reason"].lower()
    db_session.refresh(job)
    assert _candidate_fit(job, candidate.id)["score_source"] == "fallback"


def test_job_fit_scoring_accepts_string_job_id_for_uuid_posts(db_session, monkeypatch):
    import job_agent.config as cfg
    from job_agent.models import Candidate, JobPost, MatchProfile
    from job_agent.services.job_fit_scoring import JobFitScoringService

    candidate = Candidate(
        id=str(uuid.uuid4()),
        full_name="String ID User",
        spoken_languages=[{"name": "English", "level": "C1"}],
    )
    db_session.add(candidate)
    db_session.add(
        MatchProfile(
            id=str(uuid.uuid4()),
            candidate_id=candidate.id,
            target_roles=["Data Engineer"],
            location_preferences={"preferred_countries": ["Italy"]},
        )
    )
    job = JobPost(
        id=uuid.uuid4(),
        company="Gamma",
        title="Data Engineer",
        location="Turin, Italy",
        country="Italy",
        description=(
            "We need a junior data engineer who can build Python ingestion, SQL transformations, "
            "and analytics models for reporting and warehouse operations."
        ),
        source_name="manual",
        source_url="https://example.com/jobs/3",
        canonical_apply_url="https://example.com/jobs/3",
    )
    db_session.add(job)
    db_session.commit()

    monkeypatch.setattr(cfg.settings, "llm_provider_mode", "lm_studio", raising=False)
    monkeypatch.setattr(cfg.settings, "jobspy_discover_queries", ["Data Engineer"], raising=False)
    monkeypatch.setattr(cfg.settings, "job_search_countries", ["Italy"], raising=False)
    monkeypatch.setattr(
        cfg.settings,
        "job_search_languages",
        [{"name": "English", "level": "professional"}],
        raising=False,
    )

    router = MagicMock()
    router.generate_with_retry.return_value = {
        "fit_score": 81,
        "matched_evidence": ["Python and SQL fit"],
        "top_gaps": [],
        "language_assessment": {"label": "good", "reason": "English is configured strongly."},
        "seniority_assessment": {"label": "aligned", "reason": "Role is junior compatible."},
        "short_reason": "Good fit for entry data engineering work.",
    }

    result = JobFitScoringService(db_session, router=router).score_and_persist(
        str(job.id),
        candidate_id=candidate.id,
        force=True,
    )

    assert result["fit_score"] == 81
    db_session.refresh(job)
    assert _candidate_fit(job, candidate.id)["score_source"] == "provider"


def test_job_fit_scoring_normalizes_one_to_ten_provider_scores(db_session, monkeypatch):
    import job_agent.config as cfg
    from job_agent.models import Candidate, JobPost, MatchProfile
    from job_agent.services.job_fit_scoring import JobFitScoringService

    candidate = Candidate(
        id=str(uuid.uuid4()),
        full_name="Scale User",
        spoken_languages=[{"name": "English", "level": "C1"}],
    )
    db_session.add(candidate)
    db_session.add(
        MatchProfile(
            id=str(uuid.uuid4()),
            candidate_id=candidate.id,
            target_roles=["Data Engineer"],
            location_preferences={"preferred_countries": ["Italy"]},
        )
    )
    job = JobPost(
        id=uuid.uuid4(),
        company="Delta",
        title="Warehouse Developer",
        location="Milan, Italy",
        country="Italy",
        description=(
            "We need a junior data engineer who can build Python ingestion, SQL transformations, "
            "and analytics models for warehouse reporting."
        ),
        source_name="manual",
        source_url="https://example.com/jobs/5",
        canonical_apply_url="https://example.com/jobs/5",
    )
    db_session.add(job)
    db_session.commit()

    monkeypatch.setattr(cfg.settings, "llm_provider_mode", "lm_studio", raising=False)
    monkeypatch.setattr(cfg.settings, "jobspy_discover_queries", ["Data Engineer"], raising=False)
    monkeypatch.setattr(cfg.settings, "job_search_countries", ["Italy"], raising=False)
    monkeypatch.setattr(
        cfg.settings,
        "job_search_languages",
        [{"name": "English", "level": "professional"}],
        raising=False,
    )

    router = MagicMock()
    router.generate_with_retry.return_value = {
        "fit_score": 6,
        "matched_evidence": ["Python pipelines", "SQL transformations"],
        "top_gaps": ["No Airflow evidence"],
        "language_assessment": {"label": "good", "reason": "English is configured strongly."},
        "seniority_assessment": {"label": "aligned", "reason": "Role is junior compatible."},
        "short_reason": "Solid junior fit with a few tooling gaps.",
    }

    result = JobFitScoringService(db_session, router=router).score_and_persist(
        job,
        candidate_id=candidate.id,
        force=True,
    )

    assert result["fit_score"] == 60


def test_job_fit_scoring_lifts_exact_junior_role_matches_into_shortlist_range(db_session, monkeypatch):
    import job_agent.config as cfg
    from job_agent.models import Candidate, JobPost, MatchProfile
    from job_agent.services.job_fit_scoring import JobFitScoringService

    candidate = Candidate(
        id=str(uuid.uuid4()),
        full_name="Shortlist User",
        spoken_languages=[{"name": "English", "level": "C1"}],
    )
    db_session.add(candidate)
    db_session.add(
        MatchProfile(
            id=str(uuid.uuid4()),
            candidate_id=candidate.id,
            target_roles=["Junior Data Engineer"],
            location_preferences={"preferred_countries": ["Italy"]},
        )
    )
    job = JobPost(
        id=uuid.uuid4(),
        company="Exact Match Co",
        title="Junior Data Engineer",
        location="Milan, Italy",
        country="Italy",
        description=(
            "We need a junior data engineer who can build Python ETL jobs, SQL transformations, "
            "and analytics pipelines for reporting."
        ),
        source_name="manual",
        source_url="https://example.com/jobs/6",
        canonical_apply_url="https://example.com/jobs/6",
    )
    db_session.add(job)
    db_session.commit()

    monkeypatch.setattr(cfg.settings, "llm_provider_mode", "lm_studio", raising=False)
    monkeypatch.setattr(cfg.settings, "jobspy_discover_queries", ["Junior Data Engineer"], raising=False)
    monkeypatch.setattr(cfg.settings, "job_search_countries", ["Italy"], raising=False)
    monkeypatch.setattr(cfg.settings, "target_job_seniority", "junior", raising=False)
    monkeypatch.setattr(
        cfg.settings,
        "job_search_languages",
        [{"name": "English", "level": "professional"}],
        raising=False,
    )

    router = MagicMock()
    router.generate_with_retry.return_value = {
        "fit_score": 60,
        "matched_evidence": ["Python ETL pipelines", "SQL transformations", "Analytics warehouse project"],
        "top_gaps": ["No explicit Snowflake evidence"],
        "language_assessment": {"label": "good", "reason": "English is configured strongly."},
        "seniority_assessment": {"label": "aligned", "reason": "Role is junior compatible."},
        "short_reason": "Core match is strong but enterprise tooling is limited.",
    }

    result = JobFitScoringService(db_session, router=router).score_and_persist(
        job,
        candidate_id=candidate.id,
        force=True,
    )

    assert result["fit_score"] == 80


def test_discovery_visibility_count_accepts_string_job_ids(db_session):
    from job_agent.models import JobPost
    from job_agent.services.workflows import CVWorkflowService

    candidate_id = str(uuid.uuid4())
    job = JobPost(
        id=uuid.uuid4(),
        company="Visible Co",
        title="Analytics Engineer",
        location="Milan, Italy",
        country="Italy",
        description="dbt and analytics engineering role.",
        source_name="manual",
        source_url="https://example.com/jobs/4",
        canonical_apply_url="https://example.com/jobs/4",
        extracted_metadata={
            "candidate_fit": {
                candidate_id: {
                    "fit_score": 74,
                    "score_source": "provider",
                }
            }
        },
    )
    db_session.add(job)
    db_session.commit()

    visible = CVWorkflowService(db_session)._count_visible_jobs(
        saved_job_ids=[str(job.id)],
        candidate_id=candidate_id,
        threshold=70,
    )

    assert visible == 1


def test_jobs_default_visibility_uses_candidate_fit_threshold_and_cap(client, db_session, monkeypatch):
    import job_agent.config as cfg
    from job_agent.models import Candidate, JobPost

    candidate = Candidate(
        id=str(uuid.uuid4()),
        full_name="Queue User",
        spoken_languages=[{"name": "English", "level": "C1"}],
    )
    db_session.add(candidate)
    db_session.commit()

    monkeypatch.setattr(cfg.settings, "default_candidate_id", candidate.id, raising=False)
    monkeypatch.setattr(cfg.settings, "discovery_min_fit_score", 70, raising=False)
    monkeypatch.setattr(cfg.settings, "discovery_max_visible_jobs", 2, raising=False)

    for index, score in enumerate([91, 83, 76, 65], start=1):
        db_session.add(
            JobPost(
                id=uuid.uuid4(),
                company=f"Company {index}",
                title="Data Engineer",
                location="Italy",
                country="Italy",
                description="Python and SQL role.",
                source_name="manual",
                source_url=f"https://example.com/jobs/{index}",
                canonical_apply_url=f"https://example.com/jobs/{index}",
                extracted_metadata={
                    "candidate_fit": {
                        candidate.id: {
                            "fit_score": score,
                            "score_source": "provider",
                            "provider_mode": "lm_studio",
                            "language_assessment": {"label": "good", "reason": "English fit."},
                            "seniority_assessment": {"label": "aligned", "reason": "Junior fit."},
                            "short_reason": "Synthetic queue fixture.",
                        }
                    }
                },
            )
        )
    db_session.commit()

    response = client.get("/jobs")
    assert response.status_code == 200
    payload = response.json()
    assert [item["company"] for item in payload] == ["Company 1", "Company 2"]

    response_all = client.get("/jobs", params={"show_all": "true"})
    assert response_all.status_code == 200
    assert len(response_all.json()) == 4
