from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from job_agent.models import Candidate

_RULER_MAJOR = "═" * 80
_RULER_MINOR = "─" * 40
_INDENT = "  "
_SECTION_ORDER = (
    "CORE PROFILE",
    "MATCH PROFILE",
    "EDUCATION",
    "EXPERIENCE",
    "PROJECTS",
    "SKILLS",
    "LANGUAGES",
    "MISSING INFORMATION",
    "CONFLICTS",
    "CONFIDENCE SUMMARY",
    "EVIDENCE INDEX",
    "CHANGE LOG",
)


def _section(title: str, body: str, *, always: bool = False) -> str:
    if not body.strip() and not always:
        return ""
    return f"{_RULER_MAJOR}\nSECTION: {title}\n{_RULER_MAJOR}\n{body.rstrip()}\n"


def _field(label: str, value: str | None, *, important: bool = False) -> str:
    if value in (None, ""):
        return f"{label}: VERIFY\n" if important else ""
    return f"{label}: {value}\n"


def _bullets(items: list[str]) -> str:
    return "".join(f"- {item}\n" for item in items if item)


def _list_block(label: str, items: list[str]) -> str:
    if not items:
        return ""
    return f"{label}:\n{_bullets(items)}"


def _join_location(value: dict | None) -> str | None:
    if not isinstance(value, dict):
        return None
    parts = [value.get("city"), value.get("country")]
    joined = ", ".join(part for part in parts if part)
    return joined or None


def _truthy_labels(value: dict | None) -> list[str]:
    if not isinstance(value, dict):
        return []
    labels: list[str] = []
    for key, item in value.items():
        if item is True:
            labels.append(key.upper())
        elif isinstance(item, str) and item:
            labels.append(f"{key.upper()}: {item}")
    return labels


def _location_preferences_lines(value: dict | None) -> list[str]:
    if not isinstance(value, dict):
        return []
    lines: list[str] = []
    for key, item in value.items():
        if item in (None, "", [], {}):
            continue
        if isinstance(item, list):
            lines.append(f"{key.upper()}: {', '.join(str(part) for part in item)}")
        else:
            lines.append(f"{key.upper()}: {item}")
    return lines


def _confidence_lines(fact_sheet: dict) -> list[str]:
    confidence = fact_sheet.get("confidence_summary", {}) or {}
    lines = []
    completion_status = fact_sheet.get("completion_status")
    if completion_status:
        lines.append(f"COMPLETION_STATUS: {completion_status}\n")
    overall = confidence.get("overall_confidence")
    if overall:
        lines.append(f"OVERALL_CONFIDENCE: {overall}\n")
    notes = confidence.get("notes", [])
    if notes:
        lines.append("NOTES:\n")
        lines.append(_bullets([str(item) for item in notes]))
    return lines


def _minor_join(blocks: list[str]) -> str:
    content = [block.rstrip() for block in blocks if block.strip()]
    return f"\n{_RULER_MINOR}\n".join(content)


def _render_header(fact_sheet: dict) -> str:
    person = fact_sheet.get("person", {})
    name = person.get("full_name", "UNKNOWN")
    return (
        "MASTER FACT SHEET\n\n"
        "PURPOSE:\n"
        "This file is the source of truth for job matching, resume generation, "
        "cover letters, and profile updates.\n"
        "It stores verified facts first, then missing information, conflicts, "
        "and evidence references.\n"
        f"CANDIDATE: {name}\n"
    )


def _render_core_profile(fact_sheet: dict) -> str:
    person = fact_sheet.get("person", {}) or {}
    contact = person.get("contact", {}) or {}
    lines = [
        _field("FULL_NAME", person.get("full_name"), important=True),
        _field("PREFERRED_NAME", person.get("preferred_name")),
        _field("CURRENT_LOCATION", _join_location(person.get("current_location"))),
        _field("PRIMARY_EMAIL", contact.get("email")),
        _field("PHONE", contact.get("phone")),
        _field("LINKEDIN", contact.get("linkedin_url")),
        _field("GITHUB", contact.get("github_url")),
        _field("PORTFOLIO_WEBSITE", contact.get("portfolio_url")),
        _field("HEADLINE", person.get("headline")),
    ]
    return "".join(line for line in lines if line)


def _render_match_profile(fact_sheet: dict) -> str:
    match_profile = fact_sheet.get("match_profile", {}) or {}
    availability = match_profile.get("availability", {}) or {}
    blocks = [
        _list_block("TARGET_ROLES", [str(item) for item in match_profile.get("target_roles", [])]),
        _list_block("EXCLUDED_ROLES", [str(item) for item in match_profile.get("excluded_roles", [])]),
        _list_block(
            "PREFERRED_INDUSTRIES",
            [str(item) for item in match_profile.get("preferred_industries", [])],
        ),
    ]

    location_preferences = _location_preferences_lines(match_profile.get("location_preferences"))
    if location_preferences:
        blocks.append(_list_block("LOCATION_PREFERENCES", location_preferences))

    if match_profile.get("work_authorization"):
        blocks.append(f"WORK_AUTHORIZATION: {match_profile['work_authorization']}\n")

    availability_bits = []
    if availability.get("status"):
        availability_bits.append(str(availability["status"]))
    if availability.get("earliest_start_date"):
        availability_bits.append(f"earliest_start_date={availability['earliest_start_date']}")
    if availability.get("notes"):
        availability_bits.append(f"notes={availability['notes']}")
    if availability_bits:
        blocks.append(f"AVAILABILITY: {'; '.join(availability_bits)}\n")

    employment_preferences = _truthy_labels(match_profile.get("employment_preferences"))
    if employment_preferences:
        blocks.append(_list_block("EMPLOYMENT_PREFERENCES", employment_preferences))

    seniority = match_profile.get("seniority_estimate", {})
    if isinstance(seniority, dict) and seniority:
        lines = []
        for key, value in seniority.items():
            if value in (None, "", [], {}):
                continue
            lines.append(f"{key.upper()}: {value}")
        if lines:
            blocks.append(_list_block("SENIORITY_ESTIMATE", lines))
    elif seniority:
        blocks.append(f"SENIORITY_ESTIMATE: {seniority}\n")

    return "".join(block for block in blocks if block)


def _render_education(fact_sheet: dict) -> str:
    blocks = []
    for index, item in enumerate(fact_sheet.get("education", []), start=1):
        notes = item.get("notes")
        if isinstance(notes, str):
            note_items = [notes] if notes else []
        else:
            note_items = [str(entry) for entry in notes or []]
        lines = [
            f"ITEM_ID: EDU-{index:03d}\n",
            _field("DEGREE", item.get("degree"), important=True),
            _field("FIELD", item.get("field")),
            _field("INSTITUTION", item.get("institution"), important=True),
            _field("LOCATION", item.get("location")),
            _field("START_DATE", item.get("start_date")),
            _field("END_DATE", item.get("end_date")),
            _field("STATUS", item.get("status")),
        ]
        if note_items:
            lines.append("NOTES:\n")
            lines.append(_bullets(note_items))
        blocks.append("".join(line for line in lines if line))
    return _minor_join(blocks)


def _render_experience(fact_sheet: dict) -> str:
    blocks = []
    for index, item in enumerate(fact_sheet.get("experience", []), start=1):
        responsibilities = [str(entry) for entry in item.get("responsibilities", [])]
        achievements = [str(entry) for entry in item.get("achievements", [])]
        tools = [str(entry) for entry in item.get("tools", [])]
        evidence_refs = [str(entry) for entry in item.get("evidence_refs", [])]
        current = item.get("current")
        lines = [
            f"ITEM_ID: EXP-{index:03d}\n",
            _field("ROLE_TITLE", item.get("role_title"), important=True),
            _field("ORGANIZATION", item.get("organization"), important=True),
            _field("LOCATION", item.get("location")),
            _field("START_DATE", item.get("start_date")),
            _field("END_DATE", item.get("end_date") or ("PRESENT" if current else None)),
            _field("CURRENT", "Yes" if current is True else "No" if current is False else None),
            _field("ROLE_FAMILY", item.get("role_family")),
            _field("VERIFICATION_STATUS", item.get("verification_status")),
        ]
        if responsibilities:
            lines.append("RESPONSIBILITIES:\n")
            lines.append(_bullets(responsibilities))
        if achievements:
            lines.append("ACHIEVEMENTS:\n")
            lines.append(_bullets(achievements))
        if tools:
            lines.append("TOOLS:\n")
            lines.append(_bullets(tools))
        if evidence_refs:
            lines.append("EVIDENCE_REFS:\n")
            lines.append(_bullets(evidence_refs))
        blocks.append("".join(line for line in lines if line))
    return _minor_join(blocks)


def _render_projects(fact_sheet: dict) -> str:
    blocks = []
    for index, item in enumerate(fact_sheet.get("projects", []), start=1):
        summary = item.get("summary")
        summary_items = [summary] if isinstance(summary, str) and summary else [str(entry) for entry in summary or []]
        tools = [str(entry) for entry in item.get("tools", [])]
        lines = [
            f"ITEM_ID: PROJ-{index:03d}\n",
            _field("NAME", item.get("name"), important=True),
        ]
        if summary_items:
            lines.append("SUMMARY:\n")
            lines.append(_bullets(summary_items))
        if tools:
            lines.append("TOOLS:\n")
            lines.append(_bullets(tools))
        lines.append(_field("LINK", item.get("link")))
        blocks.append("".join(line for line in lines if line))
    return _minor_join(blocks)


def _render_skills(fact_sheet: dict) -> str:
    skills = fact_sheet.get("skills", {}) or {}
    labels = (
        ("PROGRAMMING_LANGUAGES", "programming_languages"),
        ("FRAMEWORKS_AND_PLATFORMS", "frameworks_and_platforms"),
        ("CLOUD_AND_INFRA", "cloud_and_infra"),
        ("DATA_AND_ANALYTICS", "data_and_analytics"),
        ("BUSINESS_TOOLS", "business_tools"),
        ("METHODS", "methods"),
    )
    blocks = []
    for label, key in labels:
        items = [str(entry) for entry in skills.get(key, [])]
        if items:
            blocks.append(_list_block(label, items))
    return "".join(blocks)


def _render_languages(fact_sheet: dict) -> str:
    lines = []
    for item in fact_sheet.get("languages", []):
        if isinstance(item, dict):
            name = item.get("name") or item.get("language")
            level = item.get("level") or item.get("proficiency")
            if name and level:
                lines.append(f"- {name}: {level}\n")
            elif name:
                lines.append(f"- {name}\n")
        elif item:
            lines.append(f"- {item}\n")
    return "".join(lines)


def _render_missing_information(fact_sheet: dict) -> str:
    items = [str(item) for item in fact_sheet.get("missing_information", [])]
    return _bullets(items) if items else "None noted.\n"


def _render_conflicts(fact_sheet: dict) -> str:
    conflicts = fact_sheet.get("conflicts", [])
    if not conflicts:
        return "None detected.\n"

    blocks = []
    for item in conflicts:
        lines = []
        if item.get("field"):
            lines.append(f"- FIELD: {item['field']}\n")
        else:
            lines.append("- FIELD: VERIFY\n")
        if item.get("source_a"):
            lines.append(f"{_INDENT}SOURCE_A: {item['source_a']}\n")
        if item.get("source_b"):
            lines.append(f"{_INDENT}SOURCE_B: {item['source_b']}\n")
        if item.get("note") not in (None, ""):
            lines.append(f"{_INDENT}NOTE: {item['note']}\n")
        blocks.append("".join(lines))
    return _minor_join(blocks)


def _render_confidence_summary(fact_sheet: dict) -> str:
    return "".join(_confidence_lines(fact_sheet))


def _render_evidence_index(fact_sheet: dict) -> str:
    evidence_items = fact_sheet.get("evidence_index", [])
    blocks = []
    for item in evidence_items:
        identifier = item.get("id")
        lines = [f"- ID: {identifier}\n"] if identifier else []
        if item.get("source_type"):
            lines.append(f"{_INDENT}SOURCE_TYPE: {item['source_type']}\n")
        if item.get("source_name"):
            lines.append(f"{_INDENT}SOURCE_NAME: {item['source_name']}\n")
        if item.get("quote_or_summary"):
            lines.append(f"{_INDENT}SUMMARY: {item['quote_or_summary']}\n")
        blocks.append("".join(lines))
    return _minor_join(blocks)


def _render_change_log(fact_sheet: dict) -> str:
    entries = fact_sheet.get("change_log", [])
    if not entries:
        return ""
    rendered = []
    for entry in entries:
        if isinstance(entry, str):
            rendered.append(f"- {entry}\n")
        elif isinstance(entry, dict) and entry.get("message"):
            rendered.append(f"- {entry['message']}\n")
    return "".join(rendered)


def render_fact_sheet_text(fact_sheet: dict) -> str:
    parts = [_render_header(fact_sheet)]

    sections = (
        ("CORE PROFILE", _render_core_profile(fact_sheet), False),
        ("MATCH PROFILE", _render_match_profile(fact_sheet), False),
        ("EDUCATION", _render_education(fact_sheet), False),
        ("EXPERIENCE", _render_experience(fact_sheet), False),
        ("PROJECTS", _render_projects(fact_sheet), False),
        ("SKILLS", _render_skills(fact_sheet), False),
        ("LANGUAGES", _render_languages(fact_sheet), False),
        ("MISSING INFORMATION", _render_missing_information(fact_sheet), True),
        ("CONFLICTS", _render_conflicts(fact_sheet), True),
        ("CONFIDENCE SUMMARY", _render_confidence_summary(fact_sheet), False),
        ("EVIDENCE INDEX", _render_evidence_index(fact_sheet), False),
        ("CHANGE LOG", _render_change_log(fact_sheet), False),
    )
    for title, body, always in sections:
        if title not in _SECTION_ORDER:
            continue
        rendered = _section(title, body, always=always)
        if rendered:
            parts.append(rendered)
    return "\n".join(part.rstrip() for part in parts if part).rstrip() + "\n"


class FactSheetRenderer:
    """Small DB-backed renderer helpers for prompt-sized fact summaries."""

    def __init__(self, session: "Session | None" = None) -> None:
        self.session = session

    def render_short_summary(self, candidate: "Candidate") -> str:
        """Return a compact, evidence-focused summary for fit-gap prompts."""
        lines: list[str] = []

        if candidate.full_name:
            lines.append(f"Candidate: {candidate.full_name}")
        if candidate.skills_json:
            skill_items: list[str] = []
            if isinstance(candidate.skills_json, dict):
                for value in candidate.skills_json.values():
                    if isinstance(value, list):
                        skill_items.extend(str(item) for item in value if item)
                    elif isinstance(value, str) and value:
                        skill_items.append(value)
            elif isinstance(candidate.skills_json, list):
                skill_items.extend(str(item) for item in candidate.skills_json if item)
            if skill_items:
                lines.append("Skills: " + ", ".join(dict.fromkeys(skill_items[:25])))

        if self.session is not None:
            from job_agent.models import EducationFact, ExperienceFact, ProjectFact, VerifiedCandidateFact

            experiences = (
                self.session.query(ExperienceFact)
                .filter(ExperienceFact.candidate_id == str(candidate.id))
                .limit(5)
                .all()
            )
            for exp in experiences:
                bits = [exp.role_title, exp.organization]
                heading = " at ".join(bit for bit in bits if bit)
                evidence = list(exp.verified_core_facts or [])[:3]
                tools = list(exp.tools_and_tech or [])[:8]
                if heading:
                    lines.append(f"Experience: {heading}")
                if evidence:
                    lines.append("Experience evidence: " + "; ".join(str(item) for item in evidence))
                if tools:
                    lines.append("Experience tools: " + ", ".join(str(item) for item in tools))

            projects = (
                self.session.query(ProjectFact)
                .filter(ProjectFact.candidate_id == str(candidate.id))
                .limit(5)
                .all()
            )
            for project in projects:
                evidence = list(project.verified_core_facts or project.key_results or [])[:3]
                tools = list(project.tools_and_tech or [])[:8]
                if project.project_name:
                    lines.append(f"Project: {project.project_name}")
                if project.short_resume_line:
                    lines.append(f"Project summary: {project.short_resume_line}")
                if evidence:
                    lines.append("Project evidence: " + "; ".join(str(item) for item in evidence))
                if tools:
                    lines.append("Project tools: " + ", ".join(str(item) for item in tools))

            education = (
                self.session.query(EducationFact)
                .filter(EducationFact.candidate_id == str(candidate.id))
                .limit(3)
                .all()
            )
            for item in education:
                label = " ".join(part for part in (item.degree, item.field, item.institution) if part)
                if label:
                    lines.append(f"Education: {label}")

            verified = (
                self.session.query(VerifiedCandidateFact)
                .filter(
                    VerifiedCandidateFact.is_active.is_(True),
                    (VerifiedCandidateFact.candidate_id == str(candidate.id))
                    | (VerifiedCandidateFact.candidate_id.is_(None)),
                )
                .order_by(VerifiedCandidateFact.created_at.desc())
                .limit(10)
                .all()
            )
            for fact in verified:
                lines.append(f"Verified memory: {fact.gap_label} — {fact.evidence}")

        return "\n".join(lines[:80]) or "No fact sheet available."
