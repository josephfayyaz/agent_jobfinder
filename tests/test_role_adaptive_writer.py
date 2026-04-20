from __future__ import annotations

from unittest.mock import MagicMock

from job_agent.models import ExperienceFact, FactSource, ProjectFact
from job_agent.services.workflows import CVWorkflowService, WorkflowContext


def test_presentation_mode_resolves_to_junior_for_intern_and_entry():
    from job_agent.services.prompts import resolve_presentation_mode

    assert resolve_presentation_mode("intern") == "junior"
    assert resolve_presentation_mode("entry") == "junior"
    assert resolve_presentation_mode("junior") == "junior"
    assert resolve_presentation_mode("graduate") == "junior"


def test_presentation_mode_resolves_to_senior_for_staff_and_lead():
    from job_agent.services.prompts import resolve_presentation_mode

    assert resolve_presentation_mode("senior") == "senior"
    assert resolve_presentation_mode("staff") == "senior"
    assert resolve_presentation_mode("lead") == "senior"
    assert resolve_presentation_mode("principal") == "senior"


def test_job_seniority_overrides_global_setting():
    from job_agent.services.prompts import resolve_presentation_mode

    assert resolve_presentation_mode("junior", job_seniority="senior") == "senior"
    assert resolve_presentation_mode("senior", job_seniority="junior") == "junior"


def test_writer_system_prompt_does_not_call_candidate_a_student():
    from job_agent.services.prompts import build_writer_system_prompt

    prompt = build_writer_system_prompt()
    assert "NOT a student" in prompt
    assert prompt.lower().count("student") == 1


def test_human_in_the_loop_keyword_rule_present_in_every_mode():
    from job_agent.services.prompts import build_writer_system_prompt

    prompt = build_writer_system_prompt()
    assert "HUMAN-IN-THE-LOOP KEYWORD RULE" in prompt


def test_keyword_rule_describes_tier_1_2_3_explicitly():
    from job_agent.services.prompts import build_writer_system_prompt

    prompt = build_writer_system_prompt()
    assert "TIER 1" in prompt
    assert "TIER 2" in prompt
    assert "TIER 3" in prompt


def test_writer_prompt_injects_junior_presentation_block_when_junior():
    from job_agent.services.prompts import build_writer_user_prompt

    prompt = build_writer_user_prompt(
        profile={},
        track=None,
        job=None,
        presentation_mode="junior",
    )
    assert "PRESENTATION MODE: JUNIOR" in prompt


def test_writer_prompt_injects_senior_presentation_block_when_senior():
    from job_agent.services.prompts import build_writer_user_prompt

    prompt = build_writer_user_prompt(
        profile={},
        track=None,
        job=None,
        presentation_mode="senior",
    )
    assert "PRESENTATION MODE: SENIOR" in prompt


def test_writer_prompt_omits_5_years_phrase_from_junior_headline_instruction():
    from job_agent.services.prompts import build_writer_user_prompt

    prompt = build_writer_user_prompt(
        profile={},
        track=None,
        job=None,
        presentation_mode="junior",
    )
    assert 'do NOT include "5+ years"' in prompt


def test_reviewer_rubric_has_career_level_alignment_dimension():
    from job_agent.services.prompts import build_reviewer_system_prompt

    prompt = build_reviewer_system_prompt()
    assert "Career-Level Alignment" in prompt


def test_presentation_mismatch_gate_triggers_on_5_years_gap_in_junior_mode(
    db_session,
    db_job,
    db_profile,
    db_track,
):
    service = CVWorkflowService(db_session)
    context = WorkflowContext(profile=db_profile, track=db_track, job=db_job)
    review = {"gaps": []}
    draft = {
        "headline": "Data Engineer",
        "professional_summary": "Data engineer with 5+ years of experience in ETL systems.",
        "selected_experiences": [],
        "selected_projects": [],
        "selected_skills": [],
        "tailoring_notes": [],
    }

    updated = service._apply_presentation_mismatch_gate(context, draft, review, "junior")

    assert any("[MISMATCH]" in gap for gap in updated["gaps"])


def test_presentation_mismatch_gate_does_not_trigger_in_senior_mode(
    db_session,
    db_job,
    db_profile,
    db_track,
):
    service = CVWorkflowService(db_session)
    context = WorkflowContext(profile=db_profile, track=db_track, job=db_job)
    review = {"gaps": []}
    draft = {
        "headline": "Senior Data Engineer",
        "professional_summary": "Data engineer with 5+ years of experience in ETL systems.",
        "selected_experiences": [],
        "selected_projects": [],
        "selected_skills": [],
        "tailoring_notes": [],
    }

    updated = service._apply_presentation_mismatch_gate(context, draft, review, "senior")

    assert updated["gaps"] == []


def test_workflows_passes_selected_experiences_and_full_fact_sheet_to_writer(
    db_session,
    db_job,
    db_profile,
    db_track,
    monkeypatch,
):
    source = FactSource(
        source_path="inline_fact_sheet.txt",
        source_hash="abc123",
        raw_content="raw",
    )
    db_session.add(source)
    db_session.flush()
    db_session.add(
        ExperienceFact(
            fact_source_id=source.id,
            item_id="exp-1",
            section_name="Experience",
            role_title="Data Engineer",
            organization="Acme",
            start_date="2023-01",
            end_date="2025-01",
            verified_core_facts=["Built Airflow ETL pipelines."],
            tools_and_tech=["Python", "Airflow"],
            best_bullets_by_track={db_track.slug: ["Built Airflow ETL pipelines."]},
        )
    )
    db_session.add(
        ProjectFact(
            fact_source_id=source.id,
            item_id="proj-1",
            project_name="Pipeline Project",
            short_resume_line="Data pipeline project",
            verified_core_facts=["Built Kafka ingestion flow."],
            tools_and_tech=["Python", "Kafka"],
            best_bullets_by_track={db_track.slug: ["Built Kafka ingestion flow."]},
        )
    )
    db_session.commit()

    captured: dict[str, object] = {}

    def fake_writer_prompt(profile, track, job, **kwargs):
        captured["profile"] = profile
        captured["track"] = track
        captured["job"] = job
        captured.update(kwargs)
        return "writer-user-prompt"

    router = MagicMock()
    router.generate.return_value = {
        "headline": "Data Engineer",
        "professional_summary": "Focused on ETL pipelines.",
        "selected_experiences": [],
        "selected_projects": [],
        "selected_skills": ["Python"],
        "tailoring_notes": [],
    }

    monkeypatch.setattr("job_agent.services.workflows.build_writer_system_prompt", lambda: "system")
    monkeypatch.setattr("job_agent.services.workflows.build_writer_user_prompt", fake_writer_prompt)

    service = CVWorkflowService(db_session, router=router)
    context = WorkflowContext(profile=db_profile, track=db_track, job=db_job)
    _, _, _, inferred, _ = service._generate_draft(context)

    assert inferred == []
    assert isinstance(captured["profile"], dict)
    assert captured["selected_experiences"]
    assert captured["selected_projects"]
