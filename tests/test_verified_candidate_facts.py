"""Regression coverage for the verified profile-memory layer."""

from __future__ import annotations

from unittest.mock import patch


def test_create_verified_fact_does_not_modify_master_profile(client, db_session, db_profile):
    original_skills = list(db_profile.global_skills)

    response = client.post(
        "/verified-facts",
        json={
            "gap_label": "Kubernetes",
            "evidence": "Deployed k8s cluster on GKE during internship, 6 months.",
            "fact_type": "tool",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["gap_label"] == "Kubernetes"
    assert data["fact_type"] == "tool"
    assert data["is_active"] is True
    db_session.refresh(db_profile)
    assert db_profile.global_skills == original_skills


def test_create_verified_fact_deduplicates_active_rows(client, db_session):
    payload = {
        "gap_label": "Kubernetes",
        "evidence": "Deployed k8s cluster on GKE during internship, 6 months.",
    }

    first = client.post("/verified-facts", json=payload)
    second = client.post("/verified-facts", json=payload)

    assert first.status_code == 201
    assert second.status_code == 200
    from job_agent.models import VerifiedCandidateFact

    assert db_session.query(VerifiedCandidateFact).count() == 1


def test_create_verified_fact_deduplicates_global_fact_after_candidate_is_set(client, db_session):
    import job_agent.config as cfg
    from job_agent.models import Candidate, VerifiedCandidateFact

    global_fact = VerifiedCandidateFact(
        candidate_id=None,
        gap_label="Kubernetes",
        evidence="Deployed k8s cluster on GKE during internship, 6 months.",
    )
    candidate = Candidate(id="candidate-1", full_name="Test User")
    db_session.add_all([global_fact, candidate])
    db_session.commit()
    object.__setattr__(cfg.settings, "default_candidate_id", candidate.id)

    response = client.post(
        "/verified-facts",
        json={
            "gap_label": "Kubernetes",
            "evidence": "Deployed k8s cluster on GKE during internship, 6 months.",
        },
    )

    assert response.status_code == 200
    assert db_session.query(VerifiedCandidateFact).count() == 1


def test_create_verified_fact_derives_source_job_from_draft(client, db_session, db_job, db_track):
    from job_agent.models import ResumeDraft

    draft = ResumeDraft(
        job_post_id=db_job.id,
        resume_track_id=db_track.id,
        provider="test",
        status="pass",
        score=90,
        content={},
        review_feedback={},
    )
    db_session.add(draft)
    db_session.commit()

    response = client.post(
        "/verified-facts",
        json={
            "gap_label": "Airflow",
            "evidence": "Built scheduled ETL DAGs with Airflow.",
            "source_draft_id": str(draft.id),
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["source_draft_id"] == str(draft.id)
    assert data["source_job_id"] == str(db_job.id)


def test_list_verified_facts_excludes_deactivated(client, db_session):
    from job_agent.models import VerifiedCandidateFact

    active = VerifiedCandidateFact(gap_label="dbt", evidence="Used dbt for 1 year.", is_active=True)
    inactive = VerifiedCandidateFact(gap_label="Spark", evidence="Tutorial only.", is_active=False)
    db_session.add_all([active, inactive])
    db_session.commit()

    response = client.get("/verified-facts")

    assert response.status_code == 200
    labels = [fact["gap_label"] for fact in response.json()]
    assert "dbt" in labels
    assert "Spark" not in labels


def test_deactivate_verified_fact(client, db_session):
    from job_agent.models import VerifiedCandidateFact

    fact = VerifiedCandidateFact(gap_label="Airflow", evidence="Used Airflow at work.", is_active=True)
    db_session.add(fact)
    db_session.commit()

    response = client.delete(f"/verified-facts/{fact.id}")

    assert response.status_code == 204
    db_session.refresh(fact)
    assert fact.is_active is False


def test_generate_draft_passes_verified_facts_to_prompt_builder(db_session, db_job, db_track, db_profile):
    from job_agent.models import VerifiedCandidateFact
    from job_agent.services.workflows import CVWorkflowService

    fact = VerifiedCandidateFact(
        gap_label="Kubernetes",
        evidence="Deployed k8s cluster on GKE during internship.",
        fact_type="tool",
        is_active=True,
    )
    inactive = VerifiedCandidateFact(
        gap_label="Spark",
        evidence="Tutorial only, no production use.",
        fact_type="skill",
        is_active=False,
    )
    db_session.add_all([fact, inactive])
    db_session.commit()

    captured_kwargs: dict = {}
    import job_agent.services.prompts as prompts_mod

    real_build = prompts_mod.build_writer_user_prompt

    def spy_build_writer(*args, **kwargs):
        captured_kwargs.update(kwargs)
        return real_build(*args, **kwargs)

    dummy_draft = {
        "summary": "ok",
        "experiences": [],
        "projects": [],
        "skills": [],
        "education": [],
    }
    dummy_review = {
        "score": 90,
        "decision": "pass",
        "hard_blocker_count": 0,
        "soft_blocker_count": 0,
        "overall_risk": "low",
        "recommendation": "Apply",
        "gaps": [],
        "matched": [],
    }

    svc = CVWorkflowService(db_session)
    with (
        patch.object(
            svc.router,
            "generate",
            side_effect=[
                {"keywords": []},
                dummy_draft,
                dummy_review,
            ],
        ),
        patch("job_agent.services.workflows.build_writer_user_prompt", side_effect=spy_build_writer),
        patch("job_agent.services.workflows.render_resume_tex", return_value="/tmp/t.tex"),
    ):
        svc.run_cv_workflow({"job_post_id": str(db_job.id), "resume_track_slug": db_track.slug})

    verified_facts = captured_kwargs.get("verified_facts")
    assert verified_facts == [
        {
            "gap_label": "Kubernetes",
            "evidence": "Deployed k8s cluster on GKE during internship.",
            "fact_type": "tool",
        }
    ]


def test_writer_prompt_contains_verified_facts_block():
    from job_agent.services.prompts import build_writer_user_prompt

    prompt = build_writer_user_prompt(
        profile={"full_name": "Test User"},
        track={"title": "Data", "target_keywords": []},
        job={"title": "Data Engineer", "company": "Acme"},
        verified_facts=[
            {
                "gap_label": "Kubernetes",
                "evidence": "Deployed k8s cluster on GKE during internship.",
                "fact_type": "tool",
            }
        ],
    )

    assert "VERIFIED CANDIDATE FACTS" in prompt
    assert "Kubernetes" in prompt
    assert "Deployed k8s cluster" in prompt


def test_draft_detail_shows_confirmed_facts_profile_memory_cta(client, db_session, db_job, db_track):
    from job_agent.models import ResumeDraft

    draft = ResumeDraft(
        job_post_id=db_job.id,
        resume_track_id=db_track.id,
        provider="test",
        status="pass",
        score=90,
        content={},
        review_feedback={
            "confirmed_facts": [
                {
                    "gap": "Kubernetes",
                    "question_id": "q0",
                    "answer": "I deployed k8s on GKE for 6 months.",
                    "confirmed": True,
                }
            ]
        },
    )
    db_session.add(draft)
    db_session.commit()

    response = client.get(f"/ui/drafts/{draft.id}")

    assert response.status_code == 200
    assert "Answers from This Application" in response.text
    assert "Save to profile memory" in response.text


def test_ui_verified_facts_page_renders(client):
    response = client.get("/ui/verified-facts")

    assert response.status_code == 200
    assert "Verified Profile Memory" in response.text
