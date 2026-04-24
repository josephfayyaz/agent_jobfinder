"""Integration test: confirmed_facts flow through WorkflowTask to writer prompt."""

from __future__ import annotations

from unittest.mock import patch


def test_apply_template_uses_safe_dom_rendering():
    """LLM/parser-provided apply-page text must be inserted with textContent."""
    from pathlib import Path

    template = Path("frontend/templates/apply.html").read_text()
    script = Path("frontend/static/apply.js").read_text()

    assert ".map((s) => `<li>${s}</li>`)" not in template
    assert "container.innerHTML = _questions.map" not in template
    assert "createElement" in script
    assert "textContent" in script


def test_confirmed_facts_reach_writer_prompt(db_session, db_job, db_track, db_profile):
    """run_cv_workflow must pass non-empty confirmed_facts to build_writer_user_prompt."""
    from job_agent.services.workflows import CVWorkflowService

    facts = [
        {
            "gap": "Kubernetes",
            "question_id": "q0",
            "answer": "I deployed k8s on GKE for 6 months",
            "confirmed": True,
        },
        {
            "gap": "dbt",
            "question_id": "q1",
            "answer": "",
            "confirmed": False,
        },
    ]
    payload = {
        "job_post_id": str(db_job.id),
        "resume_track_slug": db_track.slug,
        "confirmed_facts": facts,
    }

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
                {"keywords": [{"term": "python", "priority": "must-have"}]},
                dummy_draft,
                dummy_review,
            ],
        ),
        patch("job_agent.services.workflows.build_writer_user_prompt", side_effect=spy_build_writer),
        patch("job_agent.services.workflows.render_resume_tex", return_value="/tmp/test.tex"),
    ):
        result = svc.run_cv_workflow(payload)

    assert "draft_id" in result

    cf = captured_kwargs.get("confirmed_facts")
    assert cf is not None, "confirmed_facts was not passed to build_writer_user_prompt"
    assert len(cf) == 1, f"Expected 1 fact (filtered), got {len(cf)}: {cf}"
    assert cf[0]["gap"] == "Kubernetes"
    assert cf[0]["answer"] == "I deployed k8s on GKE for 6 months"
