from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
import hashlib
import uuid

from sqlalchemy.orm import Session

from job_agent.config import settings
from job_agent.llm import LLMRouter
from job_agent.models import Candidate, CandidateIntakeDraft, CandidateSourceFile
from job_agent.parsers.fact_sheet import as_list, parse_fact_sheet
from job_agent.runtime_paths import resolve_artifacts_dir
from job_agent.services.fact_sheet_json import FactSheetJsonIngestionService
from job_agent.services.file_extraction import extract_text_auto
from job_agent.services.resource_loader import extract_prompt_section, load_prompt_pack

logger = logging.getLogger(__name__)

_MAX_ITERATIONS = 3
_MAX_INTAKE_DOC_TOTAL_CHARS = 24_000
_MAX_INTAKE_DOC_CHARS_PER_FILE = 12_000
_MAX_QUESTIONS_PER_BATCH = 5

_HIGH_VALUE_QUESTION_HINTS = (
    "target role",
    "job title",
    "work in",
    "location",
    "country",
    "city",
    "visa",
    "work authorization",
    "sponsorship",
    "available",
    "availability",
    "start",
    "remote",
    "hybrid",
    "on-site",
    "onsite",
    "strongest skill",
    "core skill",
    "tools",
    "tech stack",
    "languages can you work",
    "job language",
)

_LOW_VALUE_QUESTION_HINTS = (
    "exact start date",
    "exact end date",
    "month and year",
    "certificate number",
    "serial number",
    "passport number",
    "national id",
)


@dataclass
class UploadedFile:
    filename: str
    content: bytes
    content_type: str | None = None


@dataclass
class IntakeResult:
    status: str
    questions: list[dict] | None = None
    fact_sheet: dict | None = None
    iteration: int = 0


def _parse_llm_response(raw: object) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            import re

            match = re.search(r"\{.*\}", raw, re.S)
            if match:
                return json.loads(match.group(0))
    raise ValueError(f"Intake LLM response is not parseable JSON: {str(raw)[:200]}")


def _build_intake_system_prompt(prompt_pack_text: str) -> str:
    return (
        extract_prompt_section(prompt_pack_text, 1).strip()
        + "\n\nReturn JSON only. Use either "
        + "{\"questions\": [{\"id\": \"...\", \"prompt\": \"...\", \"kind\": \"single_select|multi_select|text\", \"options\": [\"...\"], \"allow_free_text\": true|false}], \"partial_fact_sheet\": {...}} "
        + "or {\"fact_sheet\": {...}}. Prefer structured choice questions whenever the answer can be selected from clear options."
    )


def _build_intake_user_prompt(
    prompt_pack_text: str,
    extracted_texts: list[str],
    profile_notes: str | None = None,
    existing_fact_sheet: dict | None = None,
) -> str:
    prompt_number = 2 if extracted_texts else 3
    base = extract_prompt_section(prompt_pack_text, prompt_number).strip()
    if prompt_number == 2:
        base = base.replace("{{uploaded_files}}", str(len(extracted_texts)))
        base = base.replace("{{profile_notes}}", profile_notes or "")
        base = base.replace(
            "{{existing_fact_sheet_or_null}}",
            json.dumps(existing_fact_sheet, indent=2) if existing_fact_sheet else "null",
        )
        combined = "\n\n---\n\n".join(text for text in extracted_texts if text.strip())
        return f"{base}\n\n=== UPLOADED DOCUMENT TEXT ===\n{combined}"

    note_block = f"\n\nPROFILE NOTES:\n{profile_notes}" if profile_notes else ""
    return f"{base}{note_block}"


def _build_answer_prompt(
    prompt_pack_text: str,
    partial_fact_sheet: dict,
    questions: list[dict],
    answers: dict[str, object],
) -> str:
    base = extract_prompt_section(prompt_pack_text, 4).strip()
    qa_rows: list[str] = []
    for index, raw_question in enumerate(questions):
        question = _normalize_intake_question(raw_question, index)
        if not question:
            continue
        prompt = str(question.get("prompt") or question.get("id") or "").strip()
        key = str(question.get("id") or prompt)
        answer_value = answers.get(key)
        if isinstance(answer_value, list):
            answer_text = ", ".join(str(item).strip() for item in answer_value if str(item).strip())
        else:
            answer_text = str(answer_value or "").strip()
        options = question.get("options") or []
        options_block = ""
        if isinstance(options, list) and options:
            options_block = "\nOptions: " + " | ".join(str(option).strip() for option in options if str(option).strip())
        qa_rows.append(f"Q ({key}): {prompt}{options_block}\nA: {answer_text}")
    qa_block = "\n\n".join(qa_rows)
    return (
        base.replace("{{existing_fact_sheet}}", json.dumps(partial_fact_sheet, indent=2))
        .replace("{{new_inputs}}", qa_block)
        + "\n\nReturn JSON only as {\"questions\": [...], \"partial_fact_sheet\": {...}} "
        + "or {\"fact_sheet\": {...}}."
    )


def _normalize_intake_question(raw_question: object, index: int) -> dict | None:
    if isinstance(raw_question, str):
        prompt = raw_question.strip()
        if not prompt:
            return None
        return {
            "id": f"q{index + 1}",
            "prompt": prompt,
            "kind": "text",
            "options": [],
            "allow_free_text": True,
        }
    if not isinstance(raw_question, dict):
        return None

    prompt = str(raw_question.get("prompt") or raw_question.get("question") or "").strip()
    if not prompt:
        return None

    raw_kind = str(raw_question.get("kind") or raw_question.get("type") or "text").strip().lower()
    kind = raw_kind if raw_kind in {"single_select", "multi_select", "text"} else "text"
    options = raw_question.get("options") or raw_question.get("choices") or []
    normalized_options = []
    if isinstance(options, list):
        normalized_options = [str(option).strip() for option in options if str(option).strip()]
    if kind != "text" and not normalized_options:
        kind = "text"

    return {
        "id": str(raw_question.get("id") or f"q{index + 1}"),
        "prompt": prompt,
        "kind": kind,
        "options": normalized_options,
        "allow_free_text": bool(raw_question.get("allow_free_text", kind == "text")),
    }


def _question_text(question: dict) -> str:
    return str(question.get("prompt") or question.get("id") or "").strip().lower()


def _is_low_value_question(question: dict) -> bool:
    text = _question_text(question)
    if not text:
        return True
    if any(hint in text for hint in _LOW_VALUE_QUESTION_HINTS):
        return True
    # Avoid over-indexing on detailed timeline questions during initial intake.
    if ("when did" in text or "what year" in text) and ("start" in text or "finish" in text or "end" in text):
        return True
    return False


def _is_high_value_question(question: dict) -> bool:
    text = _question_text(question)
    return any(hint in text for hint in _HIGH_VALUE_QUESTION_HINTS)


def _fallback_priority_questions(partial_fact_sheet: dict) -> list[dict]:
    """Return deterministic high-value questions when model output is noisy."""
    match_profile = dict(partial_fact_sheet.get("match_profile") or {})
    location_preferences = dict(match_profile.get("location_preferences") or {})
    availability = dict(match_profile.get("availability") or {})
    employment_preferences = dict(match_profile.get("employment_preferences") or {})

    rows: list[dict] = []
    if not (match_profile.get("target_roles") or []):
        rows.append(
            {
                "id": "target_roles",
                "prompt": "Which job roles are you targeting right now?",
                "kind": "text",
                "options": [],
                "allow_free_text": True,
            }
        )
    if not (location_preferences.get("preferred_countries") or []):
        rows.append(
            {
                "id": "preferred_countries",
                "prompt": "Which countries are you willing to work in?",
                "kind": "text",
                "options": [],
                "allow_free_text": True,
            }
        )
    if not str(match_profile.get("work_authorization") or "").strip():
        rows.append(
            {
                "id": "work_authorization",
                "prompt": "What is your current work authorization status?",
                "kind": "single_select",
                "options": [
                    "I already have authorization for my target country",
                    "I need employer sponsorship",
                    "Prefer not to say",
                ],
                "allow_free_text": True,
            }
        )
    if not str(availability.get("status") or "").strip() and employment_preferences.get("full_time") is None:
        rows.append(
            {
                "id": "availability",
                "prompt": "When are you available to start your next role?",
                "kind": "single_select",
                "options": [
                    "Immediately",
                    "Within 1 month",
                    "Within 3 months",
                    "Not sure yet",
                ],
                "allow_free_text": True,
            }
        )
    rows.append(
        {
            "id": "core_skills",
            "prompt": "What are your strongest tools or technical skills for your target roles?",
            "kind": "text",
            "options": [],
            "allow_free_text": True,
        }
    )
    # Keep intake short and high-impact.
    return rows[:_MAX_QUESTIONS_PER_BATCH]


def _select_intake_questions(raw_questions: list[object], partial_fact_sheet: dict) -> list[dict]:
    deduped: list[dict] = []
    seen_keys: set[str] = set()
    for index, raw in enumerate(raw_questions[:_MAX_QUESTIONS_PER_BATCH * 2]):
        normalized = _normalize_intake_question(raw, index)
        if not normalized:
            continue
        key = f"{normalized['id']}::{_question_text(normalized)}"
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(normalized)

    high_value = [question for question in deduped if _is_high_value_question(question) and not _is_low_value_question(question)]
    if high_value:
        return high_value[:_MAX_QUESTIONS_PER_BATCH]

    cleaned = [question for question in deduped if not _is_low_value_question(question)]
    if cleaned:
        return cleaned[:_MAX_QUESTIONS_PER_BATCH]

    return _fallback_priority_questions(partial_fact_sheet)


def _normalize_location_value(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        city = str(value.get("city") or "").strip()
        country = str(value.get("country") or "").strip()
        parts = [part for part in (city, country) if part]
        return ", ".join(parts) if parts else None
    return str(value).strip() or None


def _normalize_fact_sheet_records(items: object) -> list[dict]:
    normalized: list[dict] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        row = dict(item)
        if "location" in row:
            row["location"] = _normalize_location_value(row.get("location"))
        normalized.append(row)
    return normalized


def _normalize_languages(items: object) -> list[dict]:
    normalized: list[dict] = []
    for item in items or []:
        if isinstance(item, dict):
            name = str(item.get("name") or item.get("language") or "").strip()
            if not name:
                continue
            normalized.append({"name": name, "level": item.get("level")})
        elif isinstance(item, str) and item.strip():
            normalized.append({"name": item.strip(), "level": None})
    return normalized


def _normalize_missing_information(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, dict):
        rows = []
        for key, note in value.items():
            label = str(key).replace("_", " ").strip()
            message = str(note).strip()
            rows.append(f"{label}: {message}" if message else label)
        return [row for row in rows if row]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _normalize_confidence_summary(value: object) -> dict:
    if not isinstance(value, dict):
        return {}
    if "overall_confidence" in value or "notes" in value:
        return {
            "overall_confidence": value.get("overall_confidence"),
            "notes": [str(item) for item in value.get("notes", []) if str(item).strip()],
        }

    verified = int(value.get("verified", 0) or 0)
    missing = int(value.get("missing", 0) or 0)
    inferred = int(value.get("inferred", 0) or 0)
    overall = "high" if verified >= 5 and missing <= 1 else "medium" if verified >= 2 else "low"
    notes = [f"verified={verified}", f"inferred={inferred}", f"missing={missing}"]
    return {"overall_confidence": overall, "notes": notes}


def _normalize_evidence_index(value: object) -> list[dict]:
    if isinstance(value, list):
        normalized: list[dict] = []
        for index, item in enumerate(value, start=1):
            if isinstance(item, dict):
                normalized.append(
                    {
                        "id": str(item.get("id") or f"evidence_{index}"),
                        "source_type": str(item.get("source_type") or "evidence"),
                        "source_name": str(item.get("source_name") or ""),
                        "quote_or_summary": str(item.get("quote_or_summary") or ""),
                    }
                )
            elif isinstance(item, str) and item.strip():
                normalized.append(
                    {
                        "id": f"evidence_{index}",
                        "source_type": "evidence",
                        "source_name": item.strip(),
                        "quote_or_summary": item.strip(),
                    }
                )
        return normalized
    if isinstance(value, dict):
        normalized = []
        for key, source in value.items():
            label = str(key).strip()
            summary = str(source).strip()
            normalized.append(
                {
                    "id": label or f"evidence_{len(normalized) + 1}",
                    "source_type": "field_reference",
                    "source_name": summary,
                    "quote_or_summary": summary or label,
                }
            )
        return normalized
    return []


def _normalize_conflicts(value: object) -> list[dict]:
    normalized: list[dict] = []
    for item in value or []:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "field": str(item.get("field") or ""),
                "source_a": str(item.get("source_a") or ""),
                "source_b": str(item.get("source_b") or ""),
                "note": str(item.get("note") or ""),
            }
        )
    return normalized


def _to_boolish(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"yes", "true", "1", "full-time", "full time", "available", "open"}:
        return True
    if text in {"no", "false", "0", "not available", "unavailable"}:
        return False
    return None


def _normalize_match_profile(partial: dict) -> dict:
    raw = partial.get("match_profile")
    match_profile = dict(raw) if isinstance(raw, dict) else {}

    if not match_profile.get("target_roles"):
        target_roles = partial.get("target_role_families") or partial.get("target_roles") or []
        if isinstance(target_roles, list):
            match_profile["target_roles"] = [str(item).strip() for item in target_roles if str(item).strip()]

    if not match_profile.get("preferred_industries"):
        interests = partial.get("primary_domain_interests") or []
        if isinstance(interests, list):
            match_profile["preferred_industries"] = [str(item).strip() for item in interests if str(item).strip()]

    location_preferences = dict(match_profile.get("location_preferences") or {})
    target_regions = partial.get("target_regions") or []
    if not location_preferences.get("preferred_countries") and isinstance(target_regions, list):
        location_preferences["preferred_countries"] = [str(item).strip() for item in target_regions if str(item).strip()]
    relocate = partial.get("willing_to_relocate")
    if "willing_to_relocate" not in location_preferences:
        location_preferences["willing_to_relocate"] = _to_boolish(relocate)
    if location_preferences:
        match_profile["location_preferences"] = location_preferences

    availability_raw = match_profile.get("availability")
    if isinstance(availability_raw, dict):
        availability = {
            "status": availability_raw.get("status"),
            "earliest_start_date": availability_raw.get("earliest_start_date"),
            "notes": availability_raw.get("notes"),
        }
    else:
        availability = {
            "status": None,
            "earliest_start_date": None,
            "notes": None,
        }
        if isinstance(availability_raw, str) and availability_raw.strip():
            availability["status"] = "available"
            availability["notes"] = availability_raw.strip()
        elif partial.get("full_time_availability_note"):
            availability["status"] = "available"
            availability["notes"] = str(partial.get("full_time_availability_note")).strip()
    match_profile["availability"] = availability

    employment_raw = match_profile.get("employment_preferences")
    employment = dict(employment_raw) if isinstance(employment_raw, dict) else {}
    full_time_hint = str(partial.get("full_time_availability_note") or "")
    if "full_time" not in employment:
        employment["full_time"] = True if full_time_hint else _to_boolish(availability_raw)
    if "thesis_collaboration" not in employment:
        employment["thesis_collaboration"] = True if "thesis" in full_time_hint.lower() else None
    match_profile["employment_preferences"] = employment

    if "work_authorization" not in match_profile and partial.get("work_authorization"):
        match_profile["work_authorization"] = partial.get("work_authorization")

    return match_profile


def _canonical_minimal_fact_sheet(candidate: Candidate, partial: dict | None = None) -> dict:
    partial = dict(partial or {})
    person = dict(partial.get("person", {}))
    contact = dict(person.get("contact", {}))
    if candidate.full_name and not person.get("full_name"):
        person["full_name"] = candidate.full_name
    if candidate.email and not contact.get("email"):
        contact["email"] = candidate.email
    if contact:
        person["contact"] = contact

    missing_information = _normalize_missing_information(partial.get("missing_information"))
    return {
        "person": person,
        "match_profile": _normalize_match_profile(partial),
        "experience": _normalize_fact_sheet_records(partial.get("experience", [])),
        "education": _normalize_fact_sheet_records(partial.get("education", [])),
        "skills": dict(partial.get("skills", {})),
        "languages": _normalize_languages(partial.get("languages", [])),
        "completion_status": partial.get("completion_status", "usable_with_gaps"),
        "confidence_summary": _normalize_confidence_summary(partial.get("confidence_summary", {})),
        "missing_information": missing_information or _normalize_missing_information(partial.get("missing_information")),
        "conflicts": _normalize_conflicts(partial.get("conflicts", [])),
        "evidence_index": _normalize_evidence_index(partial.get("evidence_index", [])),
        "projects": list(partial.get("projects", [])),
        "change_log": list(partial.get("change_log", [])),
    }


def _ensure_candidate(session: Session, candidate_id: str) -> Candidate:
    candidate = session.get(Candidate, candidate_id)
    if candidate is None:
        raise ValueError(f"Candidate {candidate_id} not found")
    return candidate


def _safe_extract_text(path: Path, filename: str) -> str:
    try:
        return extract_text_auto(path)
    except Exception as exc:
        logger.warning("Could not extract text from %s: %s", filename, exc)
        return ""


def _shorten_text(text: str, *, max_chars: int) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) <= max_chars:
        return cleaned
    if max_chars < 200:
        return cleaned[:max_chars]

    head = int(max_chars * 0.7)
    tail = max_chars - head - 64
    if tail < 0:
        tail = 0
    omitted = len(cleaned) - head - tail
    marker = f"\n\n[... truncated {omitted} chars for intake budget ...]\n\n"
    return f"{cleaned[:head]}{marker}{cleaned[-tail:] if tail else ''}".strip()


def _prepare_intake_texts(extracted_texts: list[str]) -> list[str]:
    """De-duplicate and cap source text so local models stay within context limits."""
    prepared: list[str] = []
    seen_hashes: set[str] = set()
    remaining = _MAX_INTAKE_DOC_TOTAL_CHARS

    for raw_text in extracted_texts:
        text = (raw_text or "").strip()
        if not text:
            continue

        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if digest in seen_hashes:
            continue
        seen_hashes.add(digest)

        if remaining <= 0:
            break

        excerpt_budget = min(_MAX_INTAKE_DOC_CHARS_PER_FILE, remaining)
        excerpt = _shorten_text(text, max_chars=excerpt_budget)
        if not excerpt:
            continue

        prepared.append(excerpt)
        remaining -= len(excerpt)

    return prepared


def _looks_like_structured_fact_sheet(text: str) -> bool:
    cleaned = (text or "").strip()
    if not cleaned:
        return False
    return "MASTER FACT SHEET" in cleaned and "SECTION:" in cleaned and "ITEM_ID:" in cleaned


def _parse_language_entry(raw: str) -> dict | None:
    text = str(raw or "").strip()
    if not text:
        return None
    if ":" in text:
        name, level = text.split(":", 1)
        name = name.strip()
        level = level.strip() or None
    else:
        name, level = text, None
    if not name:
        return None
    return {"name": name, "level": level}


def _structured_skills_payload(parsed: dict) -> dict[str, list[str]]:
    inventory = parsed.get("skills_inventory") or {}
    payload = {
        "programming_languages": [],
        "frameworks_and_platforms": [],
        "cloud_and_infra": [],
        "data_and_analytics": [],
        "business_tools": [],
        "methods": [],
    }
    seen: dict[str, set[str]] = {key: set() for key in payload}

    def _extend(bucket: str, values: list[str]) -> None:
        for value in values:
            normalized = str(value).strip()
            if not normalized:
                continue
            lowered = normalized.casefold()
            if lowered in seen[bucket]:
                continue
            seen[bucket].add(lowered)
            payload[bucket].append(normalized)

    for key, raw_values in inventory.items():
        values = as_list(raw_values)
        key_upper = str(key).upper()
        if any(token in key_upper for token in ("PROGRAMMING", "LANGUAGE", "PYTHON", "SQL")):
            _extend("programming_languages", values)
        elif any(token in key_upper for token in ("FRAMEWORK", "PLATFORM", "ML", "NLP", "LLM", "MODEL")):
            _extend("frameworks_and_platforms", values)
        elif any(token in key_upper for token in ("CLOUD", "INFRA", "KUBERNETES", "AWS", "DOCKER", "DEVOPS")):
            _extend("cloud_and_infra", values)
        elif any(token in key_upper for token in ("DATA", "WAREHOUSE", "ANALYTICS", "DATABASE", "ETL", "ELT", "BI")):
            _extend("data_and_analytics", values)
        elif any(token in key_upper for token in ("BUSINESS", "POWER_BI", "TABLEAU")):
            _extend("business_tools", values)
        else:
            _extend("methods", values)

    if not any(payload.values()):
        for item in (parsed.get("experience_items") or []) + (parsed.get("project_items") or []):
            if not isinstance(item, dict):
                continue
            tools = as_list(item.get("TOOLS_AND_TECH", []))
            if tools:
                _extend("data_and_analytics", tools)
    return payload


def _structured_experience_items(parsed: dict) -> list[dict]:
    experiences: list[dict] = []
    for item in parsed.get("experience_items") or []:
        if not isinstance(item, dict):
            continue
        responsibilities = as_list(item.get("VERIFIED_CORE_FACTS", []))
        achievements = (
            as_list(item.get("ENRICHED_DESCRIPTION_BANK", []))[:3]
            or as_list(item.get("BEST_BULLETS_FOR_DATA_ENGINEERING", []))[:3]
        )
        evidence_refs = as_list(item.get("EVIDENCE_LINKS", [])) + as_list(item.get("METRICS_TO_CAPTURE", []))
        verification_status = "verified" if responsibilities else "partial" if achievements else "inferred"
        experiences.append(
            {
                "role_title": item.get("ROLE_TITLE", ""),
                "organization": item.get("ORGANIZATION", ""),
                "location": item.get("LOCATION") or None,
                "start_date": item.get("START_DATE") or None,
                "end_date": item.get("END_DATE") or None,
                "current": str(item.get("CURRENT", "")).strip().lower() in {"yes", "true", "current"},
                "role_family": item.get("SECTION_NAME") or item.get("TYPE") or None,
                "responsibilities": responsibilities,
                "tools": as_list(item.get("TOOLS_AND_TECH", [])),
                "achievements": achievements,
                "evidence_refs": evidence_refs,
                "verification_status": verification_status,
            }
        )
    return experiences


def _structured_project_items(parsed: dict) -> list[dict]:
    projects: list[dict] = []
    for item in parsed.get("project_items") or []:
        if not isinstance(item, dict):
            continue
        summary_parts = as_list(item.get("KEY_RESULTS", []))[:2]
        if not summary_parts:
            summary_parts = as_list(item.get("VERIFIED_CORE_FACTS", []))[:2]
        summary = " ".join(part for part in summary_parts if part).strip() or item.get("SHORT_RESUME_LINE") or None
        projects.append(
            {
                "name": item.get("PROJECT_NAME") or None,
                "summary": summary,
                "tools": as_list(item.get("TOOLS_AND_TECH", [])),
                "link": item.get("REPO_URL") or None,
            }
        )
    return projects


def _structured_education_items(parsed: dict) -> list[dict]:
    education: list[dict] = []
    for item in parsed.get("education_items") or []:
        if not isinstance(item, dict):
            continue
        notes = " ".join(as_list(item.get("NOTES", []))).strip() or None
        education.append(
            {
                "degree": item.get("DEGREE", ""),
                "field": item.get("FIELD") or None,
                "institution": item.get("INSTITUTION", ""),
                "location": item.get("LOCATION") or None,
                "start_date": item.get("START_DATE") or None,
                "end_date": item.get("END_DATE") or None,
                "status": item.get("STATUS") or None,
                "notes": notes,
            }
        )
    return education


def _fact_sheet_from_structured_source(candidate: Candidate, text: str) -> dict:
    parsed = parse_fact_sheet(text)
    core = parsed.get("core_profile") or {}
    open_items = list(parsed.get("open_items") or [])
    availability_note = " ".join(as_list(core.get("FULL_TIME_AVAILABILITY_NOTE", []))).strip()
    return {
        "person": {
            "full_name": core.get("FULL_NAME") or candidate.full_name,
            "preferred_name": core.get("PREFERRED_NAME") or None,
            "contact": {
                "email": core.get("PRIMARY_EMAIL") or candidate.email or "",
            },
        },
        "match_profile": {
            "target_roles": as_list(core.get("TARGET_ROLE_FAMILIES", [])),
            "preferred_industries": as_list(core.get("PRIMARY_DOMAIN_INTERESTS", [])),
            "location_preferences": {
                "preferred_countries": as_list(core.get("TARGET_REGIONS", [])),
                "willing_to_relocate": _to_boolish(core.get("WILLING_TO_RELOCATE")),
            },
            "availability": {
                "status": "available" if availability_note else None,
                "earliest_start_date": None,
                "notes": availability_note or None,
            },
            "employment_preferences": {
                "full_time": True if availability_note else None,
                "thesis_collaboration": True if "thesis" in availability_note.lower() else None,
            },
        },
        "experience": _structured_experience_items(parsed),
        "education": _structured_education_items(parsed),
        "skills": _structured_skills_payload(parsed),
        "languages": [entry for entry in (_parse_language_entry(item) for item in as_list(core.get("LANGUAGES", []))) if entry],
        "completion_status": "usable_with_gaps" if open_items else "complete",
        "confidence_summary": {
            "overall_confidence": "medium" if parsed.get("experience_items") else "low",
            "notes": [
                f"structured_fact_sheet_experience={len(parsed.get('experience_items') or [])}",
                f"structured_fact_sheet_projects={len(parsed.get('project_items') or [])}",
                f"structured_fact_sheet_open_items={len(open_items)}",
            ],
        },
        "missing_information": open_items,
        "conflicts": [],
        "evidence_index": [],
        "projects": _structured_project_items(parsed),
        "change_log": ["Structured master fact sheet parsed directly from uploaded source."],
    }


def store_uploaded_files(
    session: Session,
    candidate_id: str,
    uploaded_files: list[UploadedFile],
) -> list[CandidateSourceFile]:
    candidate = _ensure_candidate(session, candidate_id)
    base_dir = resolve_artifacts_dir(settings.artifacts_dir) / "candidate_sources" / candidate.id
    base_dir.mkdir(parents=True, exist_ok=True)

    stored_rows: list[CandidateSourceFile] = []
    for uploaded_file in uploaded_files:
        file_id = str(uuid.uuid4())
        safe_name = Path(uploaded_file.filename or f"{file_id}.bin").name
        stored_path = base_dir / f"{file_id}_{safe_name}"
        extracted_text = ""
        final_path: str | None = None
        try:
            stored_path.write_bytes(uploaded_file.content)
            final_path = str(stored_path)
            extracted_text = _safe_extract_text(stored_path, safe_name)
        except Exception as exc:
            logger.warning("Could not persist uploaded file %s: %s", safe_name, exc)

        row = CandidateSourceFile(
            id=file_id,
            candidate_id=candidate.id,
            original_name=safe_name,
            mime_type=uploaded_file.content_type,
            stored_path=final_path,
            extracted_text=extracted_text,
        )
        session.add(row)
        stored_rows.append(row)

    session.flush()
    return stored_rows


class FactSheetIntakeService:
    def __init__(self, session: Session, router) -> None:
        self.session = session
        self.router = router

    def _get_or_create_draft(self, candidate_id: str) -> CandidateIntakeDraft:
        draft = self.session.query(CandidateIntakeDraft).filter_by(candidate_id=candidate_id).first()
        if draft is None:
            draft = CandidateIntakeDraft(id=str(uuid.uuid4()), candidate_id=candidate_id, iteration=0)
            self.session.add(draft)
            self.session.flush()
        return draft

    def start_intake(
        self,
        candidate_id: str,
        uploaded_files: list[UploadedFile],
        profile_notes: str | None = None,
    ) -> IntakeResult:
        candidate = _ensure_candidate(self.session, candidate_id)
        prompt_pack = load_prompt_pack()
        draft = self._get_or_create_draft(candidate_id)
        stored_rows = store_uploaded_files(self.session, candidate_id, uploaded_files) if uploaded_files else []

        extracted_texts = [row.extracted_text or "" for row in stored_rows if row.extracted_text]
        if not extracted_texts:
            existing_rows = (
                self.session.query(CandidateSourceFile)
                .filter_by(candidate_id=candidate_id)
                .order_by(CandidateSourceFile.created_at.asc())
                .all()
            )
            extracted_texts = [row.extracted_text or "" for row in existing_rows if row.extracted_text]

        structured_source = next((text for text in extracted_texts if _looks_like_structured_fact_sheet(text)), None)
        if structured_source:
            canonical = _canonical_minimal_fact_sheet(candidate, _fact_sheet_from_structured_source(candidate, structured_source))
            FactSheetJsonIngestionService(self.session).ingest_json(candidate_id=candidate.id, fact_sheet=canonical)
            draft.partial_fact_sheet = canonical
            draft.pending_questions = None
            draft.iteration = 1
            self.session.add(draft)
            self.session.commit()
            return IntakeResult(status="complete", fact_sheet=canonical, iteration=1)

        extracted_texts = _prepare_intake_texts(extracted_texts)

        system_prompt = _build_intake_system_prompt(prompt_pack)
        user_prompt = _build_intake_user_prompt(
            prompt_pack,
            extracted_texts,
            profile_notes=profile_notes,
            existing_fact_sheet=draft.partial_fact_sheet,
        )
        generate_fn = self.router.generate_with_retry if isinstance(self.router, LLMRouter) else self.router.generate
        result = _parse_llm_response(
            generate_fn(
                role="small",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,
            )
        )
        return self._apply_intake_result(candidate, draft, result, next_iteration=1)

    def answer_questions(self, candidate_id: str, answers: dict[str, object]) -> IntakeResult:
        candidate = _ensure_candidate(self.session, candidate_id)
        draft = self.session.query(CandidateIntakeDraft).filter_by(candidate_id=candidate_id).first()
        if draft is None:
            raise ValueError(f"No active intake draft for candidate {candidate_id}")

        draft.last_answers = dict(answers)
        next_iteration = draft.iteration + 1
        if next_iteration >= _MAX_ITERATIONS:
            partial = _canonical_minimal_fact_sheet(candidate, draft.partial_fact_sheet)
            missing = list(partial.get("missing_information", []))
            if "Intake loop max iterations reached" not in missing:
                missing.append("Intake loop max iterations reached")
            partial["missing_information"] = missing
            FactSheetJsonIngestionService(self.session).ingest_json(candidate_id=candidate_id, fact_sheet=partial)
            draft.partial_fact_sheet = partial
            draft.pending_questions = None
            draft.iteration = next_iteration
            self.session.add(draft)
            self.session.commit()
            return IntakeResult(status="complete", fact_sheet=partial, iteration=next_iteration)

        prompt_pack = load_prompt_pack()
        system_prompt = _build_intake_system_prompt(prompt_pack)
        user_prompt = _build_answer_prompt(
            prompt_pack,
            partial_fact_sheet=draft.partial_fact_sheet or {},
            questions=list(draft.pending_questions or []),
            answers=answers,
        )
        generate_fn = self.router.generate_with_retry if isinstance(self.router, LLMRouter) else self.router.generate
        result = _parse_llm_response(
            generate_fn(
                role="small",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,
            )
        )
        return self._apply_intake_result(candidate, draft, result, next_iteration=next_iteration)

    def _apply_intake_result(
        self,
        candidate: Candidate,
        draft: CandidateIntakeDraft,
        result: dict,
        *,
        next_iteration: int,
    ) -> IntakeResult:
        partial_fact_sheet = result.get("partial_fact_sheet") or draft.partial_fact_sheet or {}
        fact_sheet = result.get("fact_sheet")
        raw_questions = list(result.get("questions", []))
        questions = _select_intake_questions(raw_questions, partial_fact_sheet) if raw_questions else []
        if questions and fact_sheet is None:
            draft.pending_questions = questions
            draft.partial_fact_sheet = partial_fact_sheet
            draft.iteration = next_iteration
            self.session.add(draft)
            self.session.commit()
            return IntakeResult(
                status="questions_needed",
                questions=questions,
                fact_sheet=partial_fact_sheet,
                iteration=next_iteration,
            )

        if fact_sheet is None:
            if partial_fact_sheet:
                canonical_partial = _canonical_minimal_fact_sheet(candidate, partial_fact_sheet)
                FactSheetJsonIngestionService(self.session).ingest_json(candidate_id=candidate.id, fact_sheet=canonical_partial)
                draft.partial_fact_sheet = canonical_partial
                draft.pending_questions = None
                draft.iteration = next_iteration
                self.session.add(draft)
                self.session.commit()
                return IntakeResult(status="complete", fact_sheet=canonical_partial, iteration=next_iteration)
            raise ValueError("LLM response contained neither 'questions' nor 'fact_sheet'")

        canonical = _canonical_minimal_fact_sheet(candidate, fact_sheet)
        FactSheetJsonIngestionService(self.session).ingest_json(candidate_id=candidate.id, fact_sheet=canonical)
        draft.partial_fact_sheet = canonical
        draft.pending_questions = None
        draft.iteration = next_iteration
        self.session.add(draft)
        self.session.commit()
        return IntakeResult(status="complete", fact_sheet=canonical, iteration=next_iteration)
