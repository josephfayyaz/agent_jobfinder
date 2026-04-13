from __future__ import annotations

from job_agent.services.prompts import build_reviewer_system_prompt


def test_reviewer_flags_below_market_italian_salary():
    prompt = build_reviewer_system_prompt()
    assert "Italy" in prompt or "IT" in prompt
    assert "28,000" in prompt or "28000" in prompt


def test_reviewer_flags_unpaid_internship_as_red_flag():
    prompt = build_reviewer_system_prompt()
    assert "unpaid" in prompt


def test_reviewer_flags_missing_company_url_as_red_flag():
    prompt = build_reviewer_system_prompt()
    assert "no_company_url" in prompt or "company_url" in prompt


def test_legitimacy_score_default_is_100_for_clean_job():
    prompt = build_reviewer_system_prompt()
    assert "legitimacy_score" in prompt
    assert "100" in prompt


def test_comp_assessment_not_listed_when_no_salary_in_description():
    prompt = build_reviewer_system_prompt()
    assert "not_listed" in prompt
    assert "comp_assessment" in prompt


def test_reviewer_system_prompt_includes_block_d_and_g_sections():
    prompt = build_reviewer_system_prompt()
    assert "COMPENSATION SANITY CHECK" in prompt or "Block D" in prompt
    assert "LEGITIMACY SIGNALS" in prompt or "Block G" in prompt
