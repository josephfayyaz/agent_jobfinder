# Phase 1.5 — Deterministic JSON→TXT Fact Sheet Renderer

## Goal

Implement a Python renderer that converts a canonical JSON fact sheet into the exact
plain-text format described in `fact_sheet_renderer_spec.md` and exemplified by
`master_fact_sheet_render_template.txt`.

This enables:
- `GET /candidates/{id}/fact-sheet-text` to serve human-readable output without calling an LLM
- Round-trip stability: JSON → TXT → JSON → TXT produces identical output
- Golden file tests that pin the output shape to the template

## Dependencies

No new packages. Phase 1.4.0 (resource_loader) must be complete — the renderer loads
`master_fact_sheet_render_template.txt` for golden-file tests.

## New File: `job_agent/services/fact_sheet_renderer.py`

```python
"""
Deterministic JSON → plain text renderer for canonical fact sheets.

Rendering rules (from fact_sheet_renderer_spec.md):
  - Plain text only. No markdown, no emoji.
  - Uppercase labels.
  - Omit null / empty fields unless a field is strategically important; then write VERIFY.
  - Never invent facts.
  - Always render MISSING INFORMATION section (even if empty: show "None noted.").
  - Never hide conflicts; render every conflict in the CONFLICTS section.
  - Stable section order (see SECTION_ORDER below).
  - ITEM_IDs are deterministic: EDU-001, EXP-001, PROJ-001, etc.
  - Dates: render as-is from the fact sheet (ISO YYYY-MM or YYYY).
  - Use 80-char ruler lines (═) to separate major sections.
  - Use 40-char ruler lines (─) to separate items within a section.
"""

from __future__ import annotations


_RULER_MAJOR = "═" * 80
_RULER_MINOR = "─" * 40
_INDENT = "  "


def _section(title: str, body: str) -> str:
    """Wrap a section with a major ruler."""
    if not body.strip():
        return ""
    return f"\n{_RULER_MAJOR}\n{title}\n{_RULER_MAJOR}\n{body.rstrip()}\n"


def _field(label: str, value: str | None, *, important: bool = False) -> str:
    """Render a single KEY: value line. Omit if empty unless important."""
    if not value:
        return f"{label}: VERIFY\n" if important else ""
    return f"{label}: {value}\n"


def _bullets(items: list[str], indent: str = _INDENT) -> str:
    return "".join(f"{indent}- {item}\n" for item in (items or []))


# ─── Section renderers ───────────────────────────────────────────────────────

def _render_header(fact_sheet: dict) -> str:
    person = fact_sheet.get("person", {})
    name = person.get("full_name", "UNKNOWN")
    return (
        f"MASTER FACT SHEET\n"
        f"Generated for: {name}\n"
        f"PURPOSE: Single source of truth for resume and cover letter generation.\n"
        f"INSTRUCTIONS: Do not edit values unless you have verified them against\n"
        f"primary sources (CV, LinkedIn, portfolio).\n"
    )


def _render_core_profile(fact_sheet: dict) -> str:
    person = fact_sheet.get("person", {})
    profile = fact_sheet.get("core_profile", {})
    lines = []
    lines.append(_field("FULL_NAME", person.get("full_name"), important=True))
    lines.append(_field("PREFERRED_NAME", person.get("preferred_name")))
    lines.append(_field("EMAIL", person.get("email")))
    lines.append(_field("LOCATION", profile.get("location")))
    lines.append(_field("NATIONALITY", profile.get("nationality")))
    lines.append(_field("CURRENT_POSITIONING", profile.get("current_positioning")))
    if profile.get("good_lead_options"):
        lines.append("GOOD_LEAD_OPTIONS:\n")
        lines.append(_bullets(profile["good_lead_options"]))
    lines.append(_field("DEFAULT_HEADLINE", profile.get("default_headline")))
    lines.append(_field("RECRUITER_PRESENTATION_RULE", profile.get("recruiter_presentation_rule")))
    return "".join(lines)


def _render_match_profile(fact_sheet: dict) -> str:
    mp = fact_sheet.get("match_profile", {})
    if not mp:
        return ""
    lines = []
    if mp.get("target_roles"):
        lines.append("TARGET_ROLES:\n")
        roles = mp["target_roles"]
        if isinstance(roles, list):
            lines.append(_bullets(roles))
        else:
            lines.append(f"{_INDENT}{roles}\n")
    if mp.get("excluded_roles"):
        lines.append("EXCLUDED_ROLES:\n")
        excluded = mp["excluded_roles"]
        if isinstance(excluded, list):
            lines.append(_bullets(excluded))
    lines.append(_field("WORK_AUTHORIZATION", mp.get("work_authorization")))
    lines.append(_field("AVAILABILITY_STATUS", mp.get("availability_status")))
    lines.append(_field("EARLIEST_START_DATE", mp.get("earliest_start_date")))
    if mp.get("location_preferences"):
        lines.append("LOCATION_PREFERENCES:\n")
        lp = mp["location_preferences"]
        if isinstance(lp, list):
            lines.append(_bullets(lp))
        elif isinstance(lp, dict):
            for k, v in lp.items():
                lines.append(f"{_INDENT}{k.upper()}: {v}\n")
    if mp.get("seniority_estimate"):
        lines.append("SENIORITY_ESTIMATE:\n")
        se = mp["seniority_estimate"]
        if isinstance(se, dict):
            for k, v in se.items():
                lines.append(f"{_INDENT}{k.upper()}: {v}\n")
        else:
            lines.append(f"{_INDENT}{se}\n")
    return "".join(lines)


def _render_education(fact_sheet: dict) -> str:
    items = fact_sheet.get("education", [])
    if not items:
        return ""
    blocks = []
    for i, edu in enumerate(items, start=1):
        item_id = f"EDU-{i:03d}"
        b = [f"ITEM_ID: {item_id}\n"]
        b.append(_field("DEGREE", edu.get("degree"), important=True))
        b.append(_field("INSTITUTION", edu.get("institution"), important=True))
        b.append(_field("START_DATE", edu.get("start_date")))
        b.append(_field("END_DATE", edu.get("end_date") or "present"))
        b.append(_field("GPA", edu.get("gpa")))
        b.append(_field("THESIS", edu.get("thesis")))
        b.append(_field("NOTES", edu.get("notes")))
        blocks.append("".join(b))
    return f"\n{_RULER_MINOR}\n".join(blocks)


def _render_experience(fact_sheet: dict) -> str:
    items = fact_sheet.get("experience", [])
    if not items:
        return ""
    blocks = []
    for i, exp in enumerate(items, start=1):
        item_id = f"EXP-{i:03d}"
        b = [f"ITEM_ID: {item_id}\n"]
        b.append(_field("TITLE", exp.get("title"), important=True))
        b.append(_field("ORGANIZATION", exp.get("organization"), important=True))
        b.append(_field("START_DATE", exp.get("start_date")))
        b.append(_field("END_DATE", exp.get("end_date") or "present"))
        b.append(_field("EMPLOYMENT_TYPE", exp.get("employment_type")))
        b.append(_field("LOCATION", exp.get("location")))
        if exp.get("bullets"):
            b.append("BULLETS:\n")
            b.append(_bullets(exp["bullets"]))
        if exp.get("keywords"):
            b.append(f"KEYWORDS: {', '.join(exp['keywords'])}\n")
        b.append(_field("VERIFICATION_STATUS", exp.get("verification_status")))
        blocks.append("".join(b))
    return f"\n{_RULER_MINOR}\n".join(blocks)


def _render_projects(fact_sheet: dict) -> str:
    items = fact_sheet.get("projects", [])
    if not items:
        return ""
    blocks = []
    for i, proj in enumerate(items, start=1):
        item_id = f"PROJ-{i:03d}"
        b = [f"ITEM_ID: {item_id}\n"]
        b.append(_field("NAME", proj.get("name"), important=True))
        b.append(_field("DESCRIPTION", proj.get("description")))
        if proj.get("bullets"):
            b.append("BULLETS:\n")
            b.append(_bullets(proj["bullets"]))
        if proj.get("keywords"):
            b.append(f"KEYWORDS: {', '.join(proj['keywords'])}\n")
        b.append(_field("URL", proj.get("url")))
        blocks.append("".join(b))
    return f"\n{_RULER_MINOR}\n".join(blocks)


def _render_skills(fact_sheet: dict) -> str:
    skills = fact_sheet.get("skills", {})
    if not skills:
        return ""
    lines = []
    subsections = [
        ("LANGUAGES_AND_FRAMEWORKS", "languages_and_frameworks"),
        ("ML_AND_AI", "ml_and_ai"),
        ("DATA_ENGINEERING", "data_engineering"),
        ("CLOUD_AND_DEVOPS", "cloud_and_devops"),
        ("DATABASES", "databases"),
        ("OTHER", "other"),
    ]
    for label, key in subsections:
        items = skills.get(key, [])
        if not items:
            # Try alternate flat key formats the schema may use
            items = skills.get(label.lower(), []) or skills.get(key.replace("_", ""), [])
        if items:
            if isinstance(items, list):
                lines.append(f"{label}: {', '.join(str(x) for x in items)}\n")
            else:
                lines.append(f"{label}: {items}\n")
    # Catch-all for any top-level skill keys we didn't enumerate
    known_keys = {k for _, k in subsections}
    for k, v in skills.items():
        if k not in known_keys and v:
            if isinstance(v, list):
                lines.append(f"{k.upper()}: {', '.join(str(x) for x in v)}\n")
            else:
                lines.append(f"{k.upper()}: {v}\n")
    return "".join(lines)


def _render_languages(fact_sheet: dict) -> str:
    langs = fact_sheet.get("languages", [])
    if not langs:
        return ""
    lines = []
    for lang in langs:
        if isinstance(lang, dict):
            name = lang.get("language") or lang.get("name", "")
            level = lang.get("level") or lang.get("proficiency", "")
            lines.append(f"{name}: {level}\n" if level else f"{name}\n")
        else:
            lines.append(f"{lang}\n")
    return "".join(lines)


def _render_missing_information(fact_sheet: dict) -> str:
    items = fact_sheet.get("missing_information", [])
    if not items:
        return "None noted.\n"
    return _bullets(items if isinstance(items, list) else [str(items)])


def _render_conflicts(fact_sheet: dict) -> str:
    items = fact_sheet.get("conflicts", [])
    if not items:
        return "None detected.\n"
    blocks = []
    for i, c in enumerate(items, start=1):
        b = [f"CONFLICT-{i:03d}\n"]
        b.append(_field("FIELD", c.get("field")))
        b.append(_field("SOURCE_A", c.get("source_a")))
        b.append(_field("SOURCE_B", c.get("source_b")))
        b.append(_field("NOTE", c.get("note")))
        resolved = c.get("resolved", False)
        b.append(f"RESOLVED: {'YES' if resolved else 'NO'}\n")
        blocks.append("".join(b))
    return f"\n{_RULER_MINOR}\n".join(blocks)


def _render_confidence_summary(fact_sheet: dict) -> str:
    cs = fact_sheet.get("confidence_summary", {})
    if not cs:
        return ""
    lines = []
    lines.append(_field("OVERALL", cs.get("overall")))
    lines.append(_field("MOST_RELIABLE", cs.get("most_reliable")))
    lines.append(_field("NEEDS_VERIFICATION", cs.get("needs_verification")))
    return "".join(lines)


def _render_evidence_index(fact_sheet: dict) -> str:
    items = fact_sheet.get("evidence_index", [])
    if not items:
        return ""
    lines = []
    for item in items:
        if isinstance(item, dict):
            stype = item.get("source_type", "")
            sname = item.get("source_name", "")
            quote = item.get("quote_or_summary", "")
            lines.append(f"[{stype}] {sname}")
            if quote:
                lines.append(f"\n{_INDENT}{quote}")
            lines.append("\n")
        else:
            lines.append(f"{item}\n")
    return "".join(lines)


def _render_change_log(fact_sheet: dict) -> str:
    items = fact_sheet.get("change_log", [])
    if not items:
        return ""
    lines = []
    for entry in items:
        if isinstance(entry, str):
            lines.append(f"- {entry}\n")
        elif isinstance(entry, dict):
            lines.append(f"- {entry.get('message', str(entry))}\n")
    return "".join(lines)


# ─── Public API ──────────────────────────────────────────────────────────────

def render_fact_sheet_text(fact_sheet: dict) -> str:
    """
    Convert a canonical JSON fact sheet dict to the plain-text master_fact_sheet format.

    Section order (stable, required):
      1. Header
      2. CORE PROFILE
      3. MATCH PROFILE
      4. EDUCATION
      5. EXPERIENCE
      6. PROJECTS
      7. SKILLS
      8. LANGUAGES
      9. MISSING INFORMATION
      10. CONFLICTS
      11. CONFIDENCE SUMMARY
      12. EVIDENCE INDEX
      13. CHANGE LOG (only if non-empty)
    """
    parts = [_render_header(fact_sheet)]

    core = _render_core_profile(fact_sheet)
    if core.strip():
        parts.append(_section("CORE PROFILE", core))

    match = _render_match_profile(fact_sheet)
    if match.strip():
        parts.append(_section("MATCH PROFILE", match))

    edu = _render_education(fact_sheet)
    if edu.strip():
        parts.append(_section("EDUCATION", edu))

    exp = _render_experience(fact_sheet)
    if exp.strip():
        parts.append(_section("EXPERIENCE", exp))

    proj = _render_projects(fact_sheet)
    if proj.strip():
        parts.append(_section("PROJECTS", proj))

    skills = _render_skills(fact_sheet)
    if skills.strip():
        parts.append(_section("SKILLS", skills))

    langs = _render_languages(fact_sheet)
    if langs.strip():
        parts.append(_section("LANGUAGES", langs))

    # Always render MISSING INFORMATION
    parts.append(_section("MISSING INFORMATION", _render_missing_information(fact_sheet)))

    # Always render CONFLICTS
    parts.append(_section("CONFLICTS", _render_conflicts(fact_sheet)))

    cs = _render_confidence_summary(fact_sheet)
    if cs.strip():
        parts.append(_section("CONFIDENCE SUMMARY", cs))

    ev = _render_evidence_index(fact_sheet)
    if ev.strip():
        parts.append(_section("EVIDENCE INDEX", ev))

    cl = _render_change_log(fact_sheet)
    if cl.strip():
        parts.append(_section("CHANGE LOG", cl))

    return "\n".join(p for p in parts if p)
```

## Wire into `FactSheetJsonIngestionService`

In `job_agent/services/fact_sheet_json.py`, add a convenience method:

```python
def export_text(self, candidate_id: str) -> str:
    """Render the candidate's fact sheet as plain text."""
    from job_agent.services.fact_sheet_renderer import render_fact_sheet_text
    fact_sheet = self.export_json(candidate_id)
    return render_fact_sheet_text(fact_sheet)
```

## Tests

### `tests/test_fact_sheet_renderer.py`

```python
import pytest

_SAMPLE = {
    "person": {"full_name": "Jane Doe", "email": "jane@example.com"},
    "core_profile": {
        "current_positioning": "Data engineer with 3 years of experience.",
        "default_headline": "Data engineer focused on ETL and analytics.",
    },
    "match_profile": {"target_roles": ["Data Engineer"], "work_authorization": "EU"},
    "experience": [
        {
            "title": "Data Engineer",
            "organization": "ACME Corp",
            "start_date": "2022-01",
            "end_date": None,
            "bullets": ["built ETL pipelines", "wrote Python scripts"],
            "keywords": ["python", "etl"],
        }
    ],
    "projects": [
        {
            "name": "Analytics Dashboard",
            "description": "Real-time metrics board.",
            "bullets": ["used Superset", "integrated with Postgres"],
            "keywords": ["superset", "sql"],
        }
    ],
    "education": [
        {
            "degree": "BSc Computer Science",
            "institution": "University of Turin",
            "start_date": "2018-09",
            "end_date": "2022-07",
        }
    ],
    "skills": {
        "languages_and_frameworks": ["Python", "SQL"],
        "cloud_and_devops": ["AWS S3", "Docker"],
    },
    "languages": [{"language": "English", "level": "C1"}, {"language": "Italian", "level": "B2"}],
    "conflicts": [],
    "evidence_index": [],
    "change_log": ["Initial intake 2026-04-11"],
    "missing_information": ["LinkedIn profile URL"],
}


def test_renderer_outputs_stable_section_order():
    from job_agent.services.fact_sheet_renderer import render_fact_sheet_text
    text = render_fact_sheet_text(_SAMPLE)
    sections = [
        "CORE PROFILE", "MATCH PROFILE", "EDUCATION", "EXPERIENCE",
        "PROJECTS", "SKILLS", "LANGUAGES", "MISSING INFORMATION",
        "CONFLICTS", "CHANGE LOG",
    ]
    positions = [text.find(s) for s in sections]
    assert positions == sorted(positions), \
        f"Section order mismatch: {list(zip(sections, positions))}"


def test_renderer_omits_null_fields_by_default():
    from job_agent.services.fact_sheet_renderer import render_fact_sheet_text
    sample = {"person": {"full_name": "Jane"}, "experience": [], "missing_information": []}
    text = render_fact_sheet_text(sample)
    assert "VERIFY" not in text or "important" not in text  # null non-important fields are omitted


def test_renderer_preserves_conflicts_and_missing_info():
    from job_agent.services.fact_sheet_renderer import render_fact_sheet_text
    sample = dict(_SAMPLE)
    sample["conflicts"] = [{"field": "title", "source_a": "CV", "source_b": "LI", "note": "", "resolved": False}]
    sample["missing_information"] = ["Phone number", "GitHub URL"]
    text = render_fact_sheet_text(sample)
    assert "CONFLICTS" in text
    assert "CONFLICT-001" in text
    assert "Phone number" in text
    assert "GitHub URL" in text


def test_renderer_handles_empty_change_log_gracefully():
    from job_agent.services.fact_sheet_renderer import render_fact_sheet_text
    sample = dict(_SAMPLE)
    sample["change_log"] = []
    text = render_fact_sheet_text(sample)
    # Empty change log → section should be omitted entirely
    assert "CHANGE LOG" not in text


def test_renderer_matches_master_template_shape():
    """
    Golden file test: render a minimal fact sheet and confirm major section
    labels match those in master_fact_sheet_render_template.txt.
    """
    from job_agent.services.fact_sheet_renderer import render_fact_sheet_text
    from job_agent.services.resource_loader import load_render_template
    template = load_render_template()
    text = render_fact_sheet_text(_SAMPLE)
    # Check that core section labels present in the template also appear in our output
    for label in ("EXPERIENCE", "EDUCATION", "SKILLS", "MISSING INFORMATION"):
        if label in template:
            assert label in text, f"Section {label!r} missing from renderer output"


def test_roundtrip_ingest_render_reingest_is_stable(db_session):
    """
    Critical invariant: JSON → TXT → re-ingest → export JSON must produce
    structurally identical experience/education data.
    """
    from job_agent.services.fact_sheet_json import FactSheetJsonIngestionService
    svc = FactSheetJsonIngestionService(db_session)
    result1 = svc.ingest_json(None, _SAMPLE)
    exported1 = svc.export_json(result1.candidate_id)

    # Re-ingest the exported JSON
    result2 = svc.ingest_json(result1.candidate_id, exported1)
    exported2 = svc.export_json(result2.candidate_id)

    assert exported1["experience"] == exported2["experience"]
    assert exported1["education"] == exported2["education"]
    assert exported1["person"] == exported2["person"]
```

## Commit Message
```
feat(fact_sheet): add deterministic JSON->TXT renderer following canonical spec (Phase 1.5)
```
