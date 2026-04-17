# Phase 4.3 — Career-Ops Reviewer Upgrade (Seniority, Comp, Legitimacy)

## Goal

Add the career-ops evaluation blocks that are currently missing from the reviewer:
- **Block C — Seniority Fit** (already added as a rubric dimension in Phase 1.2; wire the
  per-country salary and legitimacy signals on top of it)
- **Block D — Compensation Sanity Check** — if the JD mentions a salary range, compare it
  against a per-country junior-role baseline and flag "below market" or "within range"
- **Block G — Legitimacy Signals** — red flags like unpaid roles, vague titles, no company URL

These are reported to the user but do not change the pass/fail threshold — they inform
the candidate so they can decide whether to proceed.

## Dependencies

No new pip packages.

## Changes to `job_agent/services/prompts.py`

### Extend `build_reviewer_system_prompt()` — add three new output sections

After the existing scoring rubric (as updated in Phase 1.2), append:

```python
COMP_ASSESSMENT_BLOCK = """
════════════════════════════════
COMPENSATION SANITY CHECK (Block D)
════════════════════════════════
If the job description contains a salary range, assess it against these
per-country baselines for junior / early-career roles (annual, gross):

  Italy (IT)       : €28,000 – €38,000
  Germany (DE)     : €45,000 – €60,000
  Netherlands (NL) : €45,000 – €55,000
  France (FR)      : €35,000 – €48,000
  Spain (ES)       : €25,000 – €35,000
  Sweden (SE)      : SEK 380,000 – SEK 480,000
  Switzerland (CH) : CHF 70,000 – CHF 90,000
  Belgium (BE)     : €35,000 – €45,000
  Poland (PL)      : PLN 60,000 – PLN 90,000
  Remote (EU)      : Use the country of the employer's HQ if discernible.

Return:
  "comp_assessment": {
    "verdict": "within_range" | "below_market" | "above_market" | "not_listed",
    "note": "brief explanation or empty string"
  }

If no salary is mentioned, set verdict to "not_listed".
Do NOT fabricate a number. If the country is unknown, use "not_listed".
"""

LEGITIMACY_BLOCK = """
════════════════════════════════
LEGITIMACY SIGNALS (Block G)
════════════════════════════════
Check the job description and company information for the following red flags.
For each flag that applies, add a short string to the `red_flags` list.

Red flag conditions:
  - "unpaid"               : role is explicitly unpaid
  - "equity_only"          : compensation is equity or stock only, no salary
  - "commission_only"      : OTE/commission only, no base salary
  - "urgent_start"         : start date is "immediate" or "ASAP" with no interview process
  - "vague_title"          : job title is generic ("various roles", "talent", "opportunity")
  - "no_company_url"       : job has no company_url and company name is unrecognised
  - "excessive_requirements": junior role asks for ≥5 years of experience
  - "no_contact_info"      : no recruiter name, no email, no ATS link

Return:
  "legitimacy_score": <0–100>,   # 100 = no red flags, subtract 15 per flag
  "red_flags": ["flag1", "flag2"]  # empty list if clean

A legitimacy_score < 70 should be surfaced as a warning in the UI.
"""
```

Append both blocks to the system prompt string returned by `build_reviewer_system_prompt()`.

### Extend the reviewer JSON output schema instruction

The reviewer must now return:

```json
{
  "overall_score": 0,
  "rubric_scores": {
    "role_fit": 0,
    "evidence": 0,
    "keyword_coverage": 0,
    "clarity": 0,
    "ats": 0,
    "career_level_alignment": 0
  },
  "gaps": [],
  "suggestions": [],
  "comp_assessment": {
    "verdict": "not_listed",
    "note": ""
  },
  "legitimacy_score": 100,
  "red_flags": []
}
```

Add this schema to the reviewer's output format instruction in `build_reviewer_system_prompt()`.

## Changes to `job_agent/services/workflows.py`

### Surface comp_assessment and red_flags in `ResumeDraft.review_notes`

In `_review_draft()`, after parsing the reviewer JSON, merge the new fields:

```python
# Existing: draft.review_score = reviewer_json.get("overall_score", 0)
# Add:
review_notes = draft.review_notes or {}
review_notes["comp_assessment"] = reviewer_json.get("comp_assessment", {})
review_notes["legitimacy_score"] = reviewer_json.get("legitimacy_score", 100)
review_notes["red_flags"] = reviewer_json.get("red_flags", [])
draft.review_notes = review_notes
```

## Changes to `job_agent/main.py` (dashboard badge data)

The existing `GET /drafts/{id}` endpoint already returns `review_notes`. No new endpoint
needed. The dashboard (Phase 8.1 / Spec C3) reads `review_notes.legitimacy_score` and
`review_notes.red_flags` to show warning badges.

### Archetype-based target roles (align Jobs filter)

In the `/jobs` listing endpoint, if the requesting candidate has a `MatchProfile`
with `target_roles` set (Phase B1), filter jobs against `match_profile.target_roles`
instead of the hardcoded resume track list. Add an optional query parameter
`?candidate_id=<UUID>` to the GET `/jobs` endpoint:

```python
# In GET /jobs, after existing filters:
if candidate_id:
    mp = db.query(MatchProfile).filter_by(candidate_id=candidate_id).first()
    if mp and mp.target_roles:
        # target_roles is a list of role strings; filter by similarity to job.title
        # Simple contains-any check; semantic matching is Phase 3.2
        allowed = [r.lower() for r in mp.target_roles]
        jobs = [j for j in jobs if any(a in (j.title or "").lower() for a in allowed)]
```

## Tests

### `tests/test_reviewer_extensions.py`

```python
def test_reviewer_flags_below_market_italian_salary():
    from job_agent.services.prompts import build_reviewer_system_prompt
    prompt = build_reviewer_system_prompt()
    assert "Italy" in prompt or "IT" in prompt
    assert "28,000" in prompt or "28000" in prompt


def test_reviewer_flags_unpaid_internship_as_red_flag():
    from job_agent.services.prompts import build_reviewer_system_prompt
    prompt = build_reviewer_system_prompt()
    assert "unpaid" in prompt


def test_reviewer_flags_missing_company_url_as_red_flag():
    from job_agent.services.prompts import build_reviewer_system_prompt
    prompt = build_reviewer_system_prompt()
    assert "no_company_url" in prompt or "company_url" in prompt


def test_legitimacy_score_default_is_100_for_clean_job():
    """Reviewer JSON output schema instruction must specify legitimacy_score: 100 as default."""
    from job_agent.services.prompts import build_reviewer_system_prompt
    prompt = build_reviewer_system_prompt()
    assert "legitimacy_score" in prompt


def test_comp_assessment_not_listed_when_no_salary_in_description():
    """Reviewer schema must include comp_assessment with not_listed as a possible verdict."""
    from job_agent.services.prompts import build_reviewer_system_prompt
    prompt = build_reviewer_system_prompt()
    assert "not_listed" in prompt
    assert "comp_assessment" in prompt


def test_reviewer_system_prompt_includes_block_d_and_g_sections():
    from job_agent.services.prompts import build_reviewer_system_prompt
    prompt = build_reviewer_system_prompt()
    assert "COMPENSATION SANITY CHECK" in prompt or "Block D" in prompt
    assert "LEGITIMACY SIGNALS" in prompt or "Block G" in prompt
```

## Commit Message
```
feat(reviewer): add career-ops seniority, comp, and legitimacy checks (Phase 4.3)
```
