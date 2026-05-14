from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
import hashlib
import re
import uuid
import os

from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from job_agent.config import settings
from job_agent.llm import LLMRouter
from job_agent.models import Candidate, CandidateIntakeDraft, CandidateSourceFile
from job_agent.providers import normalize_provider_mode
from job_agent.parsers.fact_sheet import as_list, parse_fact_sheet
from job_agent.runtime_paths import resolve_artifacts_dir
from job_agent.services.fact_sheet_json import FactSheetJsonIngestionService
from job_agent.services.fact_sheet_readiness import fact_sheet_ground_truth_gaps, fact_sheet_is_ground_truth_ready
from job_agent.services.file_extraction import extract_text_auto
from job_agent.services.provider_input import shape_text_blocks_for_workflow
from job_agent.services.resource_loader import extract_prompt_section, load_prompt_pack

logger = logging.getLogger(__name__)

_MAX_ITERATIONS = 5
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

_FREEFORM_ROLE_HINTS = (
    "accountant",
    "accounting",
    "accounts payable",
    "accounts receivable",
    "payroll",
    "bookkeeper",
    "manager",
    "analyst",
    "engineer",
    "developer",
    "scientist",
    "specialist",
    "consultant",
    "coordinator",
    "administrator",
    "assistant",
    "intern",
)
_FREEFORM_DATE_RANGE_RE = re.compile(
    r"\b(?:19|20)\d{2}\s*[-–]\s*(?:present|current|now|(?:19|20)\d{2})\b",
    re.IGNORECASE,
)
_FREEFORM_SKILL_CUE_RE = re.compile(
    r"(?:technical proficiency in|proficiency in|experience in|including|tools(?: used)?|software)\s+(.+)",
    re.IGNORECASE,
)
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_EDUCATION_SECTION_RE = re.compile(
    r"(?:^|\n)\s*(?:EDUCATION(?: AND TRAINING)?|ACADEMIC BACKGROUND)\s*\n(?P<body>[\s\S]*?)(?=\n\s*(?:WORK EXPERIENCE|PROFESSIONAL EXPERIENCE|PROJECTS|SKILLS|LANGUAGES|RECOMMENDATIONS?|CERTIFICATIONS?)\s*\n|$)",
    re.IGNORECASE,
)
_BRACKET_DATE_RE = re.compile(r"\[\s*([^\]]+?)\s*\]")
_CITY_COUNTRY_RE = re.compile(
    r"City:\s*(?P<city>[^|\n]+)(?:\|\s*Country:\s*(?P<country>[^|\n]+))?",
    re.IGNORECASE,
)
_FIELD_OF_STUDY_RE = re.compile(
    r"Field\(s\)\s+of\s+study:\s*(?P<field>[^|\n]+)",
    re.IGNORECASE,
)
_MSC_SUMMARY_RE = re.compile(
    r"(?:pursuing|studying|completed|finishing)\s+(?:an?\s+)?(?P<degree>MSc|M\.Sc\.|Master(?:'s)?(?:\s+Degree)?|BSc|B\.Sc\.|Bachelor(?:'s)?(?:\s+Degree)?)\s+in\s+(?P<field>[^.\n,]+?)\s+at\s+(?P<institution>[A-Z][^.\n,]+)",
    re.IGNORECASE,
)
_DEGREE_FIELD_RE = re.compile(
    r"^(?P<degree>Bachelor(?:'s)?(?:\s+Degree)?|BSc|B\.Sc\.|Master(?:'s)?(?:\s+Degree)?|MSc|M\.Sc\.|PhD|Doctorate)(?:\s+(?:of|in)\s+(?P<field>.+))?$",
    re.IGNORECASE,
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


def _source_kind_from_name(filename: str, mime_type: str | None = None) -> str:
    suffix = Path(filename or "").suffix.lower().lstrip(".")
    if suffix:
        return suffix
    if mime_type:
        return str(mime_type).split("/", 1)[-1].lower()
    return "text"


def _normalize_source_markdown(text: str) -> str:
    """Build deterministic markdown-like text from raw extraction output."""
    raw = str(text or "").replace("\x00", "")
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    raw = re.sub(r"[ \t]+", " ", raw)
    raw = re.sub(r"^[ \t]*[•▪◦]\s*", "- ", raw, flags=re.MULTILINE)
    raw = re.sub(r"\n{3,}", "\n\n", raw)

    known_headings = {
        "about myself",
        "academic background",
        "certifications",
        "education",
        "education and training",
        "experience",
        "languages",
        "projects",
        "skills",
        "work experience",
        "professional experience",
    }
    lines: list[str] = []
    previous_blank = False
    for raw_line in raw.splitlines():
        line = raw_line.strip()
        if not line:
            if lines and not previous_blank:
                lines.append("")
            previous_blank = True
            continue
        previous_blank = False

        compact = re.sub(r"\s+", " ", line)
        lower = compact.casefold().strip(":")
        if (
            lower in known_headings
            or (
                compact.isupper()
                and 3 <= len(compact) <= 60
                and not compact.startswith("- ")
                and bool(re.search(r"\s", compact))
                and not re.search(r"[_/@.]", compact)
            )
        ):
            heading = compact.strip(":").title()
            if lines and lines[-1] != "":
                lines.append("")
            lines.append(f"## {heading}")
            lines.append("")
            previous_blank = True
            continue
        if re.match(r"^[*-]\s+", compact):
            lines.append("- " + re.sub(r"^[*-]\s+", "", compact).strip())
            continue
        lines.append(compact)

    return "\n".join(lines).strip()


def _source_preview(text: str, *, max_chars: int = 900) -> str:
    return _shorten_text(text, max_chars=max_chars)


def _diagnostic_entry(
    *,
    stage: str,
    code: str,
    severity: str,
    message: str,
    source_id: str | None = None,
    source_label: str | None = None,
    details: dict[str, object] | None = None,
) -> dict[str, object]:
    entry: dict[str, object] = {
        "stage": str(stage).strip(),
        "code": str(code).strip(),
        "severity": str(severity).strip(),
        "message": str(message).strip(),
    }
    if source_id:
        entry["source_id"] = str(source_id).strip()
    if source_label:
        entry["source_label"] = str(source_label).strip()
    if details:
        entry["details"] = {
            str(key): value
            for key, value in details.items()
            if str(key).strip() and value not in (None, "", [], {})
        }
    return entry


def _sanitize_error_details(exc: BaseException) -> dict[str, object]:
    return {"error_type": exc.__class__.__name__}


def _dossier_diagnostics(dossier: object) -> list[dict[str, object]]:
    if not isinstance(dossier, dict):
        return []
    return [item for item in dossier.get("diagnostics") or [] if isinstance(item, dict)]


def _record_diagnostic(
    dossier: dict[str, object] | None,
    *,
    stage: str,
    code: str,
    severity: str,
    message: str,
    source_id: str | None = None,
    source_label: str | None = None,
    details: dict[str, object] | None = None,
) -> dict[str, object] | None:
    if not isinstance(dossier, dict):
        return dossier
    diagnostics = _dossier_diagnostics(dossier)
    entry = _diagnostic_entry(
        stage=stage,
        code=code,
        severity=severity,
        message=message,
        source_id=source_id,
        source_label=source_label,
        details=details,
    )
    if entry not in diagnostics:
        diagnostics.append(entry)
    dossier["diagnostics"] = diagnostics
    return dossier


def _record_promotion_issues(
    dossier: dict[str, object] | None,
    issues: list[dict[str, object]],
) -> dict[str, object] | None:
    if not isinstance(dossier, dict):
        return dossier
    for issue in issues:
        field = str(issue.get("field") or "").strip() or "unknown"
        message = str(issue.get("message") or "").strip() or "Provider field required normalization."
        stage = "provider_draft_shape" if field == "root" else "schema_promotion"
        code = "provider_payload_not_object" if field == "root" else "field_shape_normalized"
        _record_diagnostic(
            dossier,
            stage=stage,
            code=code,
            severity="warning",
            message=message,
            details={"field": field},
        )
    return dossier


def _source_entry(
    *,
    source_id: str,
    label: str,
    source_type: str,
    raw_text: str,
    order: int,
    warnings: list[str] | None = None,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    source_warnings = [str(item).strip() for item in (warnings or []) if str(item).strip()]
    diagnostics: list[dict[str, object]] = []
    text = str(raw_text or "")
    normalized_text = ""
    if text.strip():
        try:
            normalized_text = _normalize_source_markdown(text)
        except Exception as exc:
            normalized_text = _shorten_text(text, max_chars=1800)
            source_warnings.append("Source normalization failed; using raw-text fallback.")
            diagnostics.append(
                _diagnostic_entry(
                    stage="normalization",
                    code="source_normalization_failed",
                    severity="warning",
                    message="Source normalization failed; using raw-text fallback.",
                    source_id=source_id,
                    source_label=label,
                    details=_sanitize_error_details(exc),
                )
            )
    else:
        source_warnings.append("No readable text was extracted from this source.")
        diagnostics.append(
            _diagnostic_entry(
                stage="extraction",
                code="source_text_unavailable",
                severity="error",
                message="No readable text was extracted from this source.",
                source_id=source_id,
                source_label=label,
            )
        )
    return (
        {
            "source_id": source_id,
            "label": label,
            "source_type": source_type,
            "order": order,
            "raw_text": text,
            "normalized_text": normalized_text,
            "normalized_preview": _source_preview(normalized_text),
            "warnings": source_warnings,
        },
        diagnostics,
    )


def _build_source_dossier(
    *,
    candidate_id: str,
    source_rows: list[CandidateSourceFile],
    profile_notes: str | None = None,
) -> dict[str, object]:
    entries: list[dict[str, object]] = []
    diagnostics: list[dict[str, object]] = []
    for index, row in enumerate(source_rows, start=1):
        label = str(row.original_name or f"source-{index}").strip()
        entry, entry_diagnostics = _source_entry(
            source_id=str(row.id),
            label=label,
            source_type=_source_kind_from_name(label, row.mime_type),
            raw_text=row.extracted_text or "",
            order=index,
        )
        entries.append(entry)
        diagnostics.extend(entry_diagnostics)

    notes = str(profile_notes or "").strip()
    if notes:
        entry, entry_diagnostics = _source_entry(
            source_id=f"profile-notes-{uuid.uuid4()}",
            label="Manual profile notes",
            source_type="notes",
            raw_text=notes,
            order=len(entries) + 1,
        )
        entries.append(entry)
        diagnostics.extend(entry_diagnostics)

    return {
        "version": 1,
        "candidate_id": candidate_id,
        "entries": entries,
        "active_source_ids": [str(entry["source_id"]) for entry in entries],
        "draft_issues": [],
        "field_provenance": {},
        "diagnostics": diagnostics,
    }


def _dossier_entries(dossier: object) -> list[dict[str, object]]:
    if not isinstance(dossier, dict):
        return []
    return [entry for entry in dossier.get("entries") or [] if isinstance(entry, dict)]


def _dossier_texts(dossier: object, *, normalized: bool = True) -> list[str]:
    key = "normalized_text" if normalized else "raw_text"
    blocks: list[str] = []
    for entry in _dossier_entries(dossier):
        text = str(entry.get(key) or entry.get("raw_text") or "").strip()
        if not text:
            continue
        label = str(entry.get("label") or entry.get("source_id") or "source").strip()
        blocks.append(f"# Source: {label}\n\n{text}")
    return blocks


def _dossier_warnings(dossier: object) -> list[str]:
    warnings: list[str] = []
    for entry in _dossier_entries(dossier):
        label = str(entry.get("label") or entry.get("source_id") or "source").strip()
        for warning in entry.get("warnings") or []:
            text = str(warning or "").strip()
            if text:
                warnings.append(f"{label}: {text}")
    return warnings


def _build_answer_prompt(
    prompt_pack_text: str,
    partial_fact_sheet: dict,
    questions: list[dict],
    answers: dict[str, object],
    source_texts: list[str] | None = None,
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
    prompt = (
        base.replace("{{existing_fact_sheet}}", json.dumps(partial_fact_sheet, indent=2))
        .replace("{{new_inputs}}", qa_block)
        + "\n\nReturn JSON only as {\"questions\": [...], \"partial_fact_sheet\": {...}} "
        + "or {\"fact_sheet\": {...}}."
    )
    if source_texts:
        combined = "\n\n---\n\n".join(text for text in source_texts if text.strip())
        if combined.strip():
            prompt += f"\n\n=== ORIGINAL UPLOADED DOCUMENT TEXT ===\n{combined}"
    return prompt


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
            "required": True,
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
        "required": bool(raw_question.get("required", True)),
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
    ground_truth_gaps = set(fact_sheet_ground_truth_gaps(partial_fact_sheet))

    if "education_baseline" in ground_truth_gaps:
        rows.extend(
            [
                {
                    "id": "latest_education_degree",
                    "prompt": "What is your current or most recent degree, diploma, or training program?",
                    "kind": "text",
                    "options": [],
                    "allow_free_text": True,
                    "required": True,
                },
                {
                    "id": "latest_education_institution",
                    "prompt": "Which school, university, bootcamp, or training provider was it with?",
                    "kind": "text",
                    "options": [],
                    "allow_free_text": True,
                    "required": True,
                },
                {
                    "id": "latest_education_status",
                    "prompt": "What is the status of that education?",
                    "kind": "single_select",
                    "options": [
                        "Completed",
                        "In progress",
                        "Recently finished",
                        "Paused",
                    ],
                    "allow_free_text": False,
                    "required": True,
                },
            ]
        )
    if "background_evidence" in ground_truth_gaps:
        rows.append(
            {
                "id": "recent_proof",
                "prompt": (
                    "Briefly describe one relevant project, internship, thesis, coursework, freelance task, or job. "
                    "Mention what you built, analysed, or delivered."
                ),
                "kind": "text",
                "options": [],
                "allow_free_text": True,
                "required": True,
            }
        )
    if "core_skills" in ground_truth_gaps:
        rows.append(
            {
                "id": "core_skills",
                "prompt": "List the strongest tools, software, or technical skills you want the app to rely on.",
                "kind": "text",
                "options": [],
                "allow_free_text": True,
                "required": True,
            }
        )

    if not (match_profile.get("target_roles") or []):
        rows.append(
            {
                "id": "target_roles",
                "prompt": "Which job roles are you targeting right now?",
                "kind": "text",
                "options": [],
                "allow_free_text": True,
                "required": True,
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
                "required": True,
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
                "required": True,
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
                "required": True,
            }
        )
    # Keep intake short and high-impact.
    deduped: list[dict] = []
    seen_ids: set[str] = set()
    for row in rows:
        row_id = str(row.get("id") or "")
        if row_id in seen_ids:
            continue
        seen_ids.add(row_id)
        deduped.append(row)
    return deduped[:_MAX_QUESTIONS_PER_BATCH]


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


def _has_fact_evidence(fact_sheet: dict) -> bool:
    """Basic guard so intake cannot finish with an effectively empty profile."""
    experience = list(fact_sheet.get("experience") or [])
    projects = list(fact_sheet.get("projects") or [])
    education = list(fact_sheet.get("education") or [])
    skills = fact_sheet.get("skills") or {}
    if experience or projects or education:
        return True
    if isinstance(skills, dict):
        for value in skills.values():
            if isinstance(value, list) and any(str(item).strip() for item in value):
                return True
            if isinstance(value, str) and value.strip():
                return True
    return False


def _split_freeform_values(value: object) -> list[str]:
    if isinstance(value, list):
        parts = value
    else:
        text = str(value or "")
        for separator in ("\n", ";", ",", "|"):
            text = text.replace(separator, "\n")
        parts = text.splitlines()
    normalized: list[str] = []
    for item in parts:
        cleaned = str(item or "").strip(" -\t")
        if not cleaned:
            continue
        if any(existing.casefold() == cleaned.casefold() for existing in normalized):
            continue
        normalized.append(cleaned)
    return normalized


def _ensure_skill_buckets(skills: object) -> dict[str, list[str]]:
    payload = dict(skills or {}) if isinstance(skills, dict) else {}
    for key in (
        "programming_languages",
        "frameworks_and_platforms",
        "cloud_and_infra",
        "data_and_analytics",
        "business_tools",
        "methods",
    ):
        value = payload.get(key)
        payload[key] = list(value) if isinstance(value, list) else []
    return payload


def _append_skill_terms(skills: dict[str, list[str]], values: list[str]) -> None:
    for value in values:
        lower = value.casefold()
        if any(marker in lower for marker in ("python", "java", "c++", "javascript", "typescript", "sql", "r ")):
            bucket = "programming_languages"
        elif any(marker in lower for marker in ("aws", "azure", "gcp", "docker", "kubernetes", "linux", "terraform")):
            bucket = "cloud_and_infra"
        elif any(marker in lower for marker in ("tableau", "power bi", "excel", "sap", "crm", "salesforce")):
            bucket = "business_tools"
        elif any(marker in lower for marker in ("dbt", "airflow", "spark", "etl", "analytics", "pandas", "numpy")):
            bucket = "data_and_analytics"
        elif any(marker in lower for marker in ("scrum", "agile", "stakeholder", "testing", "research", "analysis")):
            bucket = "methods"
        else:
            bucket = "frameworks_and_platforms"
        if not any(existing.casefold() == value.casefold() for existing in skills[bucket]):
            skills[bucket].append(value)


def _ensure_manual_education_row(partial_fact_sheet: dict) -> dict:
    education = list(partial_fact_sheet.get("education") or [])
    for item in education:
        if isinstance(item, dict) and item.get("institution") and item.get("degree"):
            return item
    row = {"degree": "", "institution": "", "status": ""}
    education.append(row)
    partial_fact_sheet["education"] = education
    return row


def _ensure_manual_project_row(partial_fact_sheet: dict) -> dict:
    projects = list(partial_fact_sheet.get("projects") or [])
    for item in projects:
        if isinstance(item, dict) and str(item.get("name") or item.get("title") or "").strip():
            return item
    row = {
        "name": "Candidate-provided onboarding proof",
        "summary": "",
        "tools": [],
    }
    projects.append(row)
    partial_fact_sheet["projects"] = projects
    return row


def _apply_direct_answers_to_partial_fact_sheet(partial_fact_sheet: dict, answers: dict[str, object]) -> dict:
    updated = _canonical_minimal_fact_sheet(Candidate(id="manual", full_name=""), partial_fact_sheet)
    match_profile = dict(updated.get("match_profile") or {})
    location_preferences = dict(match_profile.get("location_preferences") or {})
    availability = dict(match_profile.get("availability") or {})
    employment_preferences = dict(match_profile.get("employment_preferences") or {})
    skills = _ensure_skill_buckets(updated.get("skills") or {})

    target_roles = _split_freeform_values(answers.get("target_roles"))
    if target_roles:
        match_profile["target_roles"] = target_roles[:5]

    countries = _split_freeform_values(answers.get("preferred_countries"))
    if countries:
        location_preferences["preferred_countries"] = countries[:5]

    work_authorization = str(answers.get("work_authorization") or "").strip()
    if work_authorization:
        match_profile["work_authorization"] = work_authorization
    else:
        country_auth = []
        for key, label in (
            ("work_authorization_italy", "Italy"),
            ("work_authorization_germany", "Germany"),
        ):
            value = str(answers.get(key) or "").strip()
            if value:
                country_auth.append(f"{label}: {value}")
        if country_auth:
            match_profile["work_authorization"] = "; ".join(country_auth)

    availability_answer = str(answers.get("availability") or "").strip()
    if availability_answer:
        availability["status"] = "available" if availability_answer != "Not sure yet" else "unknown"
        availability["notes"] = availability_answer
        employment_preferences["full_time"] = True

    education_degree = str(answers.get("latest_education_degree") or "").strip()
    education_institution = str(answers.get("latest_education_institution") or "").strip()
    education_status = str(answers.get("latest_education_status") or "").strip()
    if education_degree or education_institution or education_status:
        row = _ensure_manual_education_row(updated)
        if education_degree:
            row["degree"] = education_degree
        if education_institution:
            row["institution"] = education_institution
        if education_status:
            row["status"] = education_status

    recent_proof = str(answers.get("recent_proof") or "").strip()
    if recent_proof:
        row = _ensure_manual_project_row(updated)
        row["summary"] = recent_proof

    core_skills = _split_freeform_values(answers.get("core_skills"))
    if core_skills:
        _append_skill_terms(skills, core_skills)
        if updated.get("projects"):
            project = _ensure_manual_project_row(updated)
            project_tools = list(project.get("tools") or [])
            for value in core_skills[:8]:
                if not any(existing.casefold() == value.casefold() for existing in project_tools):
                    project_tools.append(value)
            project["tools"] = project_tools

    match_profile["location_preferences"] = location_preferences
    match_profile["availability"] = availability
    match_profile["employment_preferences"] = employment_preferences
    updated["match_profile"] = match_profile
    updated["skills"] = skills
    return updated


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


def _normalize_current_location(value: object) -> dict[str, str | None] | None:
    if value in (None, "", [], {}):
        return None
    if isinstance(value, dict):
        city = str(value.get("city") or "").strip() or None
        country = str(value.get("country") or "").strip() or None
        if city or country:
            return {"city": city, "country": country}
        return None
    text = str(value).strip()
    if not text:
        return None
    if "," in text:
        city_part, country_part = text.rsplit(",", 1)
        city = city_part.strip() or None
        country = country_part.strip() or None
        if city or country:
            return {"city": city, "country": country}
    return {"city": text, "country": None}


def _normalize_fact_sheet_records(items: object) -> list[dict]:
    normalized: list[dict] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        row = dict(item)
        if "field" not in row and row.get("field_of_study"):
            row["field"] = row.get("field_of_study")
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
            normalized.append({"name": name, "level": item.get("level") or item.get("proficiency")})
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
    def _confidence_label(raw: object) -> str | None:
        if raw is None:
            return None
        if isinstance(raw, (int, float)):
            score = float(raw)
            if score >= 0.8:
                return "high"
            if score >= 0.5:
                return "medium"
            return "low"
        text = str(raw).strip().casefold()
        if text in {"high", "medium", "low"}:
            return text
        try:
            numeric = float(text)
        except ValueError:
            return text or None
        if numeric >= 0.8:
            return "high"
        if numeric >= 0.5:
            return "medium"
        return "low"

    if not isinstance(value, dict):
        return {}
    if "overall_confidence" in value or "notes" in value:
        return {
            "overall_confidence": _confidence_label(value.get("overall_confidence")),
            "notes": [str(item) for item in value.get("notes", []) if str(item).strip()],
        }
    if "overall" in value:
        notes = []
        for key, item_value in value.items():
            if str(key) == "overall":
                continue
            text = str(item_value).strip()
            if text:
                notes.append(f"{key}={text}")
        return {
            "overall_confidence": _confidence_label(value.get("overall")),
            "notes": notes,
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


def _normalize_completion_status(value: object) -> str:
    text = str(value or "").strip().casefold()
    if text in {"complete", "completed", "done", "ready"}:
        return "complete"
    if text in {"usable_with_gaps", "usable", "partial", "partially_complete", "partially complete"}:
        return "usable_with_gaps"
    if text in {"incomplete", "missing", "draft"}:
        return "incomplete"
    return "usable_with_gaps"


def _merge_fact_sheet_dicts(base: object, overlay: object) -> object:
    if isinstance(base, dict) and isinstance(overlay, dict):
        merged = dict(base)
        for key, value in overlay.items():
            if key in merged:
                merged[key] = _merge_fact_sheet_dicts(merged[key], value)
            else:
                merged[key] = value
        return merged
    if isinstance(base, list) and isinstance(overlay, list):
        return overlay if overlay else base
    return overlay if overlay not in (None, "", [], {}) else base


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


def _normalize_work_authorization_value(value: object) -> str | None:
    if value in (None, "", [], {}):
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    if isinstance(value, list):
        parts = [str(item).strip() for item in value if str(item).strip()]
        return "; ".join(parts) if parts else None
    if isinstance(value, dict):
        parts: list[str] = []
        for key, raw_detail in value.items():
            label = str(key).strip()
            detail = str(raw_detail).strip()
            if label and detail:
                parts.append(f"{label}: {detail}")
            elif label:
                parts.append(label)
            elif detail:
                parts.append(detail)
        return "; ".join(parts) if parts else None
    cleaned = str(value).strip()
    return cleaned or None


def _normalize_match_profile(partial: dict) -> dict:
    raw = partial.get("match_profile")
    match_profile = dict(raw) if isinstance(raw, dict) else {}

    if not match_profile.get("target_roles"):
        target_roles = partial.get("target_role_families") or partial.get("target_roles") or partial.get("target_role") or []
        if isinstance(target_roles, list):
            match_profile["target_roles"] = [str(item).strip() for item in target_roles if str(item).strip()]
        elif isinstance(target_roles, str) and target_roles.strip():
            match_profile["target_roles"] = [target_roles.strip()]

    if not match_profile.get("preferred_industries"):
        interests = partial.get("primary_domain_interests") or []
        if isinstance(interests, list):
            match_profile["preferred_industries"] = [str(item).strip() for item in interests if str(item).strip()]

    location_preferences = dict(match_profile.get("location_preferences") or {})
    target_regions = partial.get("target_regions") or []
    if not location_preferences.get("preferred_countries") and isinstance(target_regions, list):
        location_preferences["preferred_countries"] = [str(item).strip() for item in target_regions if str(item).strip()]
    raw_location_preferences = partial.get("location_preferences")
    if not location_preferences.get("preferred_countries"):
        if isinstance(raw_location_preferences, list):
            location_preferences["preferred_countries"] = [
                str(item).strip() for item in raw_location_preferences if str(item).strip()
            ]
        elif isinstance(raw_location_preferences, str) and raw_location_preferences.strip():
            location_preferences["preferred_countries"] = _split_freeform_values(raw_location_preferences)
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

    if "work_authorization" in match_profile:
        match_profile["work_authorization"] = _normalize_work_authorization_value(
            match_profile.get("work_authorization")
        )
    elif partial.get("work_authorization"):
        match_profile["work_authorization"] = _normalize_work_authorization_value(
            partial.get("work_authorization")
        )

    return match_profile


def _normalize_skills_payload(raw_skills: object, partial: dict) -> dict[str, list[str]]:
    if isinstance(raw_skills, dict):
        normalized = _ensure_skill_buckets(raw_skills)
        if any(normalized.values()):
            return normalized
    else:
        normalized = _ensure_skill_buckets({})
        direct_values = _split_freeform_values(raw_skills)
        if direct_values:
            _append_skill_terms(normalized, direct_values)

    for row in partial.get("professional_experience") or []:
        if not isinstance(row, dict):
            continue
        _append_skill_terms(normalized, _split_freeform_values(row.get("skills")))

    return normalized


def _normalize_experience_payload(partial: dict) -> list[dict]:
    primary = partial.get("experience")
    if isinstance(primary, list) and primary:
        normalized: list[dict] = []
        for item in primary:
            if not isinstance(item, dict):
                continue
            row = dict(item)
            responsibilities = _split_freeform_values(row.get("responsibilities")) or _split_freeform_values(row.get("description"))
            tools = _split_freeform_values(row.get("tools")) or _split_freeform_values(row.get("skills"))
            achievements = _split_freeform_values(row.get("achievements"))
            evidence_refs = _split_freeform_values(row.get("evidence_refs"))
            verification_status = str(row.get("verification_status") or "").strip().lower()
            if verification_status not in {"verified", "partial", "inferred"}:
                verification_status = "partial" if responsibilities or tools or achievements else "inferred"
            normalized.append(
                {
                    "role_title": str(
                        row.get("role_title")
                        or row.get("role")
                        or row.get("title")
                        or partial.get("target_role")
                        or ""
                    ).strip(),
                    "organization": str(
                        row.get("organization")
                        or row.get("company")
                        or row.get("institution")
                        or row.get("employer")
                        or ""
                    ).strip(),
                    "location": _normalize_location_value(row.get("location")),
                    "start_date": row.get("start_date"),
                    "end_date": row.get("end_date"),
                    "current": row.get("current"),
                    "role_family": row.get("role_family") or row.get("type"),
                    "responsibilities": responsibilities,
                    "tools": tools,
                    "achievements": achievements,
                    "evidence_refs": evidence_refs,
                    "verification_status": verification_status,
                }
            )
        return normalized

    legacy = partial.get("professional_experience")
    normalized: list[dict] = []
    for item in legacy or []:
        if not isinstance(item, dict):
            continue
        description = str(item.get("description") or "").strip()
        row = {
            "role_title": str(item.get("role_title") or partial.get("target_role") or "").strip(),
            "organization": str(item.get("company") or "").strip(),
            "location": _normalize_location_value(item.get("location")),
            "responsibilities": [description] if description else [],
            "tools": _split_freeform_values(item.get("skills")),
        }
        normalized.append(row)
    return normalized


def _normalize_projects_payload(partial: dict) -> list[dict]:
    raw_projects = partial.get("projects")
    normalized: list[dict] = []
    for item in raw_projects or []:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "name": item.get("name") or item.get("title") or "",
                "summary": item.get("summary") or item.get("description") or None,
                "tools": list(item.get("tools") or []),
                "link": item.get("link") or item.get("repo_url") or None,
            }
        )
    return normalized


def _normalize_change_log(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _freeform_resume_paragraphs(text: str) -> list[list[str]]:
    paragraphs: list[list[str]] = []
    current: list[str] = []
    for raw_line in str(text or "").splitlines():
        line = " ".join(raw_line.strip().split())
        if not line:
            if current:
                paragraphs.append(current)
                current = []
            continue
        current.append(line)
    if current:
        paragraphs.append(current)
    return paragraphs


def _looks_like_freeform_role_title(line: str) -> bool:
    text = str(line or "").strip()
    if not text or len(text) > 120 or ":" in text or text.endswith("."):
        return False
    lowered = text.casefold()
    return any(hint in lowered for hint in _FREEFORM_ROLE_HINTS)


def _freeform_skill_terms(text: str) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()

    def _append(raw: str) -> None:
        cleaned = re.sub(r"\([^)]*\)", "", str(raw or "")).strip(" -,\t.;:")
        if len(cleaned) < 2:
            return
        lowered = cleaned.casefold()
        if lowered in seen:
            return
        seen.add(lowered)
        values.append(cleaned)

    for line in str(text or "").splitlines():
        normalized = " ".join(line.strip().split())
        if not normalized:
            continue
        source = None
        match = _FREEFORM_SKILL_CUE_RE.search(normalized)
        if match:
            source = match.group(1)
        elif any(token in normalized.casefold() for token in ("quickbooks", "excel", "sql", "python", "sap", "adp payroll")):
            source = normalized
        if not source:
            continue
        source = source.replace(" and ", "\n")
        source = source.replace(" / ", "\n")
        source = source.replace("/", "\n")
        source = source.replace(",", "\n")
        source = source.replace(";", "\n")
        for part in source.splitlines():
            _append(part)
    return values[:20]


def _freeform_resume_bullets(lines: list[str]) -> list[str]:
    bullets: list[str] = []
    seen: set[str] = set()
    for line in lines:
        text = " ".join(str(line or "").strip().split())
        if not text:
            continue
        parts = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
        for part in parts:
            cleaned = part.strip(" -\t")
            if len(cleaned) < 12:
                continue
            lowered = cleaned.casefold()
            if lowered in seen:
                continue
            seen.add(lowered)
            bullets.append(cleaned.rstrip(".") + ".")
    return bullets[:6]


def _freeform_resume_experience(text: str) -> list[dict[str, object]]:
    experiences: list[dict[str, object]] = []
    seen_keys: set[tuple[str, str, str]] = set()

    for paragraph in _freeform_resume_paragraphs(text):
        if not paragraph:
            continue

        role_title = ""
        organization = ""
        start_date = None
        end_date = None
        body_lines: list[str] = []

        date_line_index = next((index for index, line in enumerate(paragraph) if _FREEFORM_DATE_RANGE_RE.search(line)), None)
        if date_line_index is not None:
            dated_line = paragraph[date_line_index]
            match = _FREEFORM_DATE_RANGE_RE.search(dated_line)
            if match is not None:
                date_parts = [part.strip() for part in re.split(r"\s*[-–]\s*", match.group(0)) if part.strip()]
                if date_parts:
                    start_date = date_parts[0]
                if len(date_parts) > 1:
                    end_date = date_parts[1]
                organization = " ".join((dated_line[: match.start()] + dated_line[match.end():]).split()).strip(" -\t")
            if date_line_index > 0 and _looks_like_freeform_role_title(paragraph[0]):
                role_title = paragraph[0]
                body_lines.extend(paragraph[1:date_line_index])
            if not role_title and date_line_index + 1 < len(paragraph) and _looks_like_freeform_role_title(paragraph[date_line_index + 1]):
                role_title = paragraph[date_line_index + 1]
                body_lines.extend(paragraph[date_line_index + 2 :])
            else:
                body_lines.extend(paragraph[date_line_index + 1 :])
        elif _looks_like_freeform_role_title(paragraph[0]) and len(paragraph) > 1:
            role_title = paragraph[0]
            body_lines = paragraph[1:]
        else:
            continue

        bullets = _freeform_resume_bullets(body_lines)
        if not (role_title or organization or bullets):
            continue
        entry = {
            "role_title": role_title,
            "organization": organization,
            "start_date": start_date,
            "end_date": end_date,
            "responsibilities": bullets,
            "tools": _freeform_skill_terms("\n".join(body_lines)),
            "achievements": [],
            "evidence_refs": [],
            "verification_status": "partial" if bullets else "inferred",
        }
        key = (
            str(entry["role_title"]).casefold(),
            str(entry["organization"]).casefold(),
            str(entry["start_date"] or ""),
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)
        experiences.append(entry)
    return experiences[:6]


def _freeform_resume_overlay(text: str) -> dict[str, object]:
    raw = str(text or "").strip()
    if not raw or ":" in raw[:200]:
        return {}

    experience = _freeform_resume_experience(raw)
    skills = _freeform_skill_terms(raw)
    if not experience and not skills:
        return {}

    target_role = ""
    for row in experience:
        candidate_title = str(row.get("role_title") or "").strip()
        if candidate_title:
            target_role = candidate_title
            break

    projects: list[dict[str, object]] = []
    paragraphs = _freeform_resume_paragraphs(raw)
    if paragraphs:
        opening = " ".join(paragraphs[0])
        if len(opening) >= 40:
            projects.append(
                {
                    "title": "Profile note evidence",
                    "description": opening[:600],
                    "tools": skills[:8],
                }
            )

    overlay: dict[str, object] = {
        "experience": experience,
        "skills": skills,
    }
    if target_role:
        overlay["target_role"] = target_role
    if projects:
        overlay["projects"] = projects
    return overlay


def _profile_notes_overlay(profile_notes: str | None) -> dict:
    text = str(profile_notes or "").strip()
    if not text:
        return {}

    parsed: dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        label = key.strip().casefold()
        payload = value.strip()
        if not label or not payload:
            continue
        parsed[label] = payload

    overlay: dict[str, object] = {}
    if parsed.get("target role"):
        overlay["target_role"] = parsed["target role"]
    if parsed.get("preferred countries"):
        overlay["location_preferences"] = _split_freeform_values(parsed["preferred countries"])
    if parsed.get("languages"):
        languages = []
        for item in _split_freeform_values(parsed["languages"]):
            entry = _parse_language_entry(item)
            if entry:
                languages.append(entry)
        if languages:
            overlay["languages"] = languages
    if parsed.get("skills"):
        overlay["skills"] = _split_freeform_values(parsed["skills"])
    education_degree = parsed.get("education degree")
    education_institution = parsed.get("education institution")
    if education_degree or education_institution:
        overlay["education"] = [
            {
                "degree": education_degree or "",
                "institution": education_institution or "",
            }
        ]
    if parsed.get("most relevant proof"):
        overlay["projects"] = [
            {
                "title": "Profile note evidence",
                "description": parsed["most relevant proof"],
            }
        ]

    heuristic_overlay = _freeform_resume_overlay(text)
    if heuristic_overlay:
        if not overlay.get("target_role") and heuristic_overlay.get("target_role"):
            overlay["target_role"] = heuristic_overlay["target_role"]
        if not overlay.get("experience") and heuristic_overlay.get("experience"):
            overlay["experience"] = heuristic_overlay["experience"]
        if not overlay.get("skills") and heuristic_overlay.get("skills"):
            overlay["skills"] = heuristic_overlay["skills"]
        if not overlay.get("projects") and heuristic_overlay.get("projects"):
            overlay["projects"] = heuristic_overlay["projects"]
    return overlay


def _clean_source_line(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip(" \t\r\n|;"))


def _date_range_parts(raw: str) -> tuple[str | None, str | None, str | None]:
    text = _clean_source_line(raw)
    if not text:
        return None, None, None
    parts = re.split(r"\s*[–-]\s*", text, maxsplit=1)
    start = _clean_source_line(parts[0]) if parts else ""
    end = _clean_source_line(parts[1]) if len(parts) > 1 else ""
    status = "Current" if end.casefold() in {"current", "present", "now"} else ""
    return start or None, end or None, status or None


def _title_case_field(value: str) -> str:
    cleaned = _clean_source_line(value)
    replacements = {
        "msc": "MSc",
        "m.sc.": "MSc",
        "bsc": "BSc",
        "b.sc.": "BSc",
    }
    lowered = cleaned.casefold()
    if lowered in replacements:
        return replacements[lowered]
    if cleaned.isupper() or cleaned.islower():
        return cleaned.title()
    return cleaned


def _split_degree_and_field(title: str) -> tuple[str, str | None]:
    cleaned = _clean_source_line(title)
    match = _DEGREE_FIELD_RE.match(cleaned)
    if not match:
        return cleaned, None
    degree = _title_case_field(match.group("degree") or "")
    field = _clean_source_line(match.group("field") or "") or None
    return degree, field


def _summary_degree_hints(text: str) -> list[dict[str, str]]:
    hints: list[dict[str, str]] = []
    for match in _MSC_SUMMARY_RE.finditer(text or ""):
        degree = _title_case_field(match.group("degree") or "")
        field = _clean_source_line(match.group("field") or "")
        institution = _clean_source_line(match.group("institution") or "")
        if degree and field and institution:
            hints.append({"degree": degree, "field": field, "institution": institution})
    return hints


def _source_email_hint(texts: list[str]) -> str | None:
    candidates: list[tuple[int, str]] = []
    for text in texts:
        lowered = text.casefold()
        recommendation_index = lowered.find("recommendation")
        for match in _EMAIL_RE.finditer(text):
            email = match.group(0).strip()
            if not email:
                continue
            score = match.start()
            label_window = lowered[max(0, match.start() - 40) : match.start()]
            if "email" in label_window or "e-mail" in label_window:
                score -= 500
            if recommendation_index >= 0 and match.start() > recommendation_index:
                score += 20_000
            candidates.append((score, email))
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item[0])[0][1]


def _education_section_lines(text: str) -> list[str]:
    match = _EDUCATION_SECTION_RE.search(text or "")
    body = match.group("body") if match else text
    lines = [_clean_source_line(line) for line in str(body or "").splitlines()]
    ignored_prefixes = ("website:", "final grade:", "recommendations", "name:")
    return [
        line
        for line in lines
        if line
        and not line.strip().isdigit()
        and not any(line.casefold().startswith(prefix) for prefix in ignored_prefixes)
    ]


def _parse_source_education(text: str) -> list[dict[str, object]]:
    lines = _education_section_lines(text)
    summary_hints = _summary_degree_hints(text)
    education: list[dict[str, object]] = []
    seen: set[tuple[str, str, str]] = set()

    for index, line in enumerate(lines):
        date_match = _BRACKET_DATE_RE.search(line)
        if not date_match:
            continue
        institution = _clean_source_line(_BRACKET_DATE_RE.sub("", line))
        institution_lower = institution.casefold()
        if not institution or any(provider in institution_lower for provider in ("coursera", "udemy")):
            continue

        title = ""
        for previous in reversed(lines[max(0, index - 3) : index]):
            if not _BRACKET_DATE_RE.search(previous) and not previous.casefold().startswith(("city:", "country:")):
                title = previous
                break
        if not title:
            continue

        degree, field = _split_degree_and_field(title)
        for hint in summary_hints:
            if hint["institution"].casefold() in institution.casefold() or institution.casefold() in hint["institution"].casefold():
                degree = hint["degree"]
                field = hint["field"]
                break

        start_date, end_date, status = _date_range_parts(date_match.group(1))
        row: dict[str, object] = {
            "degree": degree,
            "field": field,
            "institution": institution,
            "start_date": start_date,
            "end_date": end_date,
            "status": status,
            "notes": "Recovered from uploaded source text.",
        }

        for next_line in lines[index + 1 : index + 5]:
            if _BRACKET_DATE_RE.search(next_line):
                break
            city_match = _CITY_COUNTRY_RE.search(next_line)
            if city_match:
                city = _clean_source_line(city_match.group("city") or "")
                country = _clean_source_line(city_match.group("country") or "")
                row["location"] = ", ".join(part for part in (city, country) if part) or None
            field_match = _FIELD_OF_STUDY_RE.search(next_line)
            if field_match:
                row["field"] = _clean_source_line(field_match.group("field") or "") or row.get("field")

        key = (
            str(row.get("institution") or "").casefold(),
            str(row.get("degree") or "").casefold(),
            str(row.get("start_date") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        education.append(row)

    return education[:6]


def _source_fact_hints_from_texts(texts: list[str]) -> dict[str, object]:
    source_texts = [str(text or "").strip() for text in texts if str(text or "").strip()]
    if not source_texts:
        return {}

    hints: dict[str, object] = {}
    email = _source_email_hint(source_texts)
    if email:
        hints["person"] = {"contact": {"email": email}}

    education: list[dict[str, object]] = []
    seen_education: set[tuple[str, str]] = set()
    for text in source_texts:
        for row in _parse_source_education(text):
            key = (
                str(row.get("institution") or "").casefold(),
                str(row.get("degree") or "").casefold(),
            )
            if key in seen_education:
                continue
            seen_education.add(key)
            education.append(row)
    if education:
        hints["education"] = education

    if hints:
        hints["change_log"] = ["Recovered obvious contact/education facts from uploaded source text."]
    return hints


def _stringify_source_hint(value: object) -> str:
    if value in (None, "", [], {}):
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, sort_keys=True)
    return str(value).strip()


def _append_source_conflict(payload: dict, field: str, existing: object, recovered: object) -> None:
    existing_text = _stringify_source_hint(existing)
    recovered_text = _stringify_source_hint(recovered)
    if not existing_text or not recovered_text or existing_text == recovered_text:
        return
    conflicts = list(payload.get("conflicts") or [])
    marker = (field, existing_text, recovered_text)
    for item in conflicts:
        if (
            str(item.get("field") or ""),
            str(item.get("source_a") or ""),
            str(item.get("source_b") or ""),
        ) == marker:
            return
    conflicts.append(
        {
            "field": field,
            "source_a": existing_text,
            "source_b": recovered_text,
            "note": "AI-structured intake and deterministic source-text recovery disagreed. Kept AI value for review.",
        }
    )
    payload["conflicts"] = conflicts


def _education_match_key(row: dict) -> tuple[str, str]:
    return (
        str(row.get("institution") or "").casefold(),
        str(row.get("degree") or "").casefold(),
    )


def _apply_source_fact_hints(payload: object, hints: dict[str, object]) -> dict:
    merged = dict(payload or {}) if isinstance(payload, dict) else {}
    if not hints:
        return merged

    hint_person = hints.get("person") if isinstance(hints.get("person"), dict) else {}
    hint_contact = hint_person.get("contact") if isinstance(hint_person.get("contact"), dict) else {}
    hint_email = str(hint_contact.get("email") or "").strip()
    if hint_email:
        person = dict(merged.get("person") or {})
        contact = dict(person.get("contact") or {})
        existing_email = str(contact.get("email") or merged.get("email") or "").strip()
        if existing_email and existing_email.casefold() != hint_email.casefold():
            _append_source_conflict(merged, "person.contact.email", existing_email, hint_email)
        elif not existing_email:
            contact["email"] = hint_email
            person["contact"] = contact
            merged["person"] = person
            merged.pop("email", None)

    hint_education = [item for item in hints.get("education") or [] if isinstance(item, dict)]
    if hint_education:
        existing_rows = [dict(item) for item in merged.get("education") or [] if isinstance(item, dict)]
        by_key = {_education_match_key(row): row for row in existing_rows if any(_education_match_key(row))}
        for hint_row in hint_education:
            key = _education_match_key(hint_row)
            target = by_key.get(key)
            if target is None:
                existing_rows.append(dict(hint_row))
                by_key[key] = existing_rows[-1]
                continue
            for field in ("degree", "field", "institution", "location", "start_date", "end_date", "status"):
                existing_value = target.get(field)
                hint_value = hint_row.get(field)
                if existing_value in (None, "", [], {}) and hint_value not in (None, "", [], {}):
                    target[field] = hint_value
                elif (
                    field in {"degree", "field", "institution"}
                    and hint_value not in (None, "", [], {})
                    and str(existing_value or "").casefold() != str(hint_value or "").casefold()
                ):
                    _append_source_conflict(
                        merged,
                        f"education.{field}",
                        existing_value,
                        hint_value,
                    )
        merged["education"] = existing_rows

    if hints.get("change_log"):
        change_log = list(merged.get("change_log") or [])
        for item in hints.get("change_log") or []:
            text = str(item or "").strip()
            if text and text not in change_log:
                change_log.append(text)
        merged["change_log"] = change_log
    return merged


def _canonical_minimal_fact_sheet(candidate: Candidate, partial: dict | None = None) -> dict:
    partial = dict(partial or {})
    person = dict(partial.get("person", {}))
    contact = dict(person.get("contact", {}))
    if not person.get("full_name") and partial.get("candidate_name"):
        person["full_name"] = str(partial.get("candidate_name")).strip()
    if candidate.full_name and not person.get("full_name"):
        person["full_name"] = candidate.full_name
    if not contact.get("email") and partial.get("email"):
        contact["email"] = str(partial.get("email")).strip()
    if candidate.email and not contact.get("email"):
        contact["email"] = candidate.email
    normalized_current_location = _normalize_current_location(person.get("current_location"))
    if normalized_current_location:
        person["current_location"] = normalized_current_location
    elif "current_location" in person:
        person.pop("current_location", None)
    if contact:
        person["contact"] = contact

    missing_information = _normalize_missing_information(partial.get("missing_information"))
    return {
        "person": person,
        "match_profile": _normalize_match_profile(partial),
        "experience": _normalize_experience_payload(partial),
        "education": _normalize_fact_sheet_records(partial.get("education", [])),
        "skills": _normalize_skills_payload(partial.get("skills", {}), partial),
        "languages": _normalize_languages(partial.get("languages", [])),
        "completion_status": _normalize_completion_status(partial.get("completion_status", "usable_with_gaps")),
        "confidence_summary": _normalize_confidence_summary(partial.get("confidence_summary", {})),
        "missing_information": missing_information or _normalize_missing_information(partial.get("missing_information")),
        "conflicts": _normalize_conflicts(partial.get("conflicts", [])),
        "evidence_index": _normalize_evidence_index(partial.get("evidence_index", [])),
        "projects": _normalize_projects_payload(partial),
        "change_log": _normalize_change_log(partial.get("change_log", [])),
    }


def _draft_issue(field: str, value: object, message: str) -> dict[str, object]:
    return {
        "field": field,
        "value_preview": _stringify_source_hint(value)[:300],
        "message": message,
    }


def _promote_intake_draft_to_canonical(
    candidate: Candidate,
    draft_payload: object,
    *,
    source_hints: dict[str, object] | None = None,
    dossier: dict[str, object] | None = None,
) -> tuple[dict, list[dict[str, object]]]:
    """Normalize unstable provider draft shapes before strict schema ingestion."""
    issues: list[dict[str, object]] = []
    if not isinstance(draft_payload, dict):
        issues.append(_draft_issue("root", draft_payload, "Provider draft was not an object."))
        draft_payload = {}

    payload = dict(draft_payload)
    if source_hints:
        payload = _apply_source_fact_hints(payload, source_hints)

    person = payload.get("person")
    if person is not None and not isinstance(person, dict):
        issues.append(_draft_issue("person", person, "Malformed person value was skipped."))
        payload.pop("person", None)

    for field in ("experience", "education", "projects", "languages"):
        value = payload.get(field)
        if value in (None, ""):
            continue
        if isinstance(value, dict):
            payload[field] = [value]
            issues.append(_draft_issue(field, value, "Object value was normalized to a single-item list."))
        elif not isinstance(value, list):
            payload[field] = []
            issues.append(_draft_issue(field, value, "Malformed list value was skipped."))

    canonical = _canonical_minimal_fact_sheet(candidate, payload)
    if issues and isinstance(dossier, dict):
        existing = [item for item in dossier.get("draft_issues") or [] if isinstance(item, dict)]
        dossier["draft_issues"] = [*existing, *issues]
    return canonical, issues


def _source_hint_for_value(dossier: object, value: object) -> str | None:
    if isinstance(value, list):
        text = " ".join(str(item or "").strip() for item in value if str(item or "").strip())
    else:
        text = str(value or "").strip()
    if not text:
        return None
    text_lower = text.casefold()
    for entry in _dossier_entries(dossier):
        haystack = f"{entry.get('normalized_text') or ''}\n{entry.get('raw_text') or ''}".casefold()
        if text_lower and text_lower in haystack:
            return str(entry.get("label") or entry.get("source_id") or "").strip() or None
    return None


def _review_field_entry(
    fact_sheet: dict,
    dotted_path: str,
    *,
    value: object,
    dossier: object,
    issues: list[dict[str, object]],
) -> dict[str, object]:
    issue = next((item for item in issues if str(item.get("field") or "") == dotted_path), None)
    source_hint = _source_hint_for_value(dossier, value)
    return {
        "path": dotted_path,
        "value": value,
        "source_hint": source_hint,
        "issue": issue.get("message") if issue else None,
    }


def build_review_payload(fact_sheet: dict, dossier: object | None = None) -> dict[str, object]:
    person = dict((fact_sheet or {}).get("person") or {})
    contact = dict(person.get("contact") or {})
    match_profile = dict((fact_sheet or {}).get("match_profile") or {})
    location_preferences = dict(match_profile.get("location_preferences") or {})
    current_location = person.get("current_location")
    if isinstance(current_location, dict):
        current_location_value = ", ".join(
            part for part in (current_location.get("city"), current_location.get("country")) if part
        )
    else:
        current_location_value = str(current_location or "").strip()

    issues = []
    if isinstance(dossier, dict):
        issues = [item for item in dossier.get("draft_issues") or [] if isinstance(item, dict)]

    fields = {
        "person.full_name": _review_field_entry(
            fact_sheet, "person.full_name", value=person.get("full_name") or "", dossier=dossier, issues=issues
        ),
        "person.contact.email": _review_field_entry(
            fact_sheet, "person.contact.email", value=contact.get("email") or "", dossier=dossier, issues=issues
        ),
        "person.contact.phone": _review_field_entry(
            fact_sheet, "person.contact.phone", value=contact.get("phone") or "", dossier=dossier, issues=issues
        ),
        "person.current_location": _review_field_entry(
            fact_sheet, "person.current_location", value=current_location_value, dossier=dossier, issues=issues
        ),
        "person.contact.linkedin_url": _review_field_entry(
            fact_sheet,
            "person.contact.linkedin_url",
            value=contact.get("linkedin_url") or "",
            dossier=dossier,
            issues=issues,
        ),
        "person.contact.github_url": _review_field_entry(
            fact_sheet,
            "person.contact.github_url",
            value=contact.get("github_url") or "",
            dossier=dossier,
            issues=issues,
        ),
        "person.headline": _review_field_entry(
            fact_sheet, "person.headline", value=person.get("headline") or "", dossier=dossier, issues=issues
        ),
        "match_profile.work_authorization": _review_field_entry(
            fact_sheet,
            "match_profile.work_authorization",
            value=match_profile.get("work_authorization") or "",
            dossier=dossier,
            issues=issues,
        ),
        "match_profile.location_preferences.preferred_countries": _review_field_entry(
            fact_sheet,
            "match_profile.location_preferences.preferred_countries",
            value=list(location_preferences.get("preferred_countries") or []),
            dossier=dossier,
            issues=issues,
        ),
        "match_profile.location_preferences.preferred_cities": _review_field_entry(
            fact_sheet,
            "match_profile.location_preferences.preferred_cities",
            value=list(location_preferences.get("preferred_cities") or []),
            dossier=dossier,
            issues=issues,
        ),
    }
    return {
        "fields": fields,
        "sources": [
            {
                "source_id": entry.get("source_id"),
                "label": entry.get("label"),
                "source_type": entry.get("source_type"),
                "normalized_preview": entry.get("normalized_preview") or "",
                "warnings": entry.get("warnings") or [],
            }
            for entry in _dossier_entries(dossier)
        ],
        "draft_issues": issues,
        "diagnostics": _dossier_diagnostics(dossier),
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

        dedupe_text = re.sub(r"^# Source:[^\n]*\n+", "", text, count=1).strip()
        digest = hashlib.sha256((dedupe_text or text).encode("utf-8")).hexdigest()
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
        parts = text.rsplit(" ", 1)
        if len(parts) == 2 and parts[1].upper() in {"A1", "A2", "B1", "B2", "C1", "C2"}:
            name, level = parts[0].strip(), parts[1].upper()
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


def delete_candidate_source_files(session: Session, candidate_id: str) -> int:
    rows = (
        session.query(CandidateSourceFile)
        .filter_by(candidate_id=candidate_id)
        .all()
    )
    removed = 0
    for row in rows:
        stored_path = str(row.stored_path or "").strip()
        if stored_path:
            try:
                os.remove(stored_path)
            except FileNotFoundError:
                pass
            except Exception as exc:
                logger.warning("Could not remove candidate source file %s: %s", stored_path, exc)
        session.delete(row)
        removed += 1
    session.flush()
    return removed


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

    def _ensure_draft_dossier(self, draft: CandidateIntakeDraft) -> dict[str, object]:
        dossier = dict(draft.source_dossier or {}) if isinstance(draft.source_dossier, dict) else {}
        if not dossier:
            dossier = {
                "version": 1,
                "candidate_id": draft.candidate_id,
                "entries": [],
                "active_source_ids": [],
                "draft_issues": [],
                "field_provenance": {},
                "diagnostics": [],
            }
        dossier.setdefault("version", 1)
        dossier.setdefault("candidate_id", draft.candidate_id)
        dossier.setdefault("entries", [])
        dossier.setdefault("active_source_ids", [])
        dossier.setdefault("draft_issues", [])
        dossier.setdefault("field_provenance", {})
        dossier.setdefault("diagnostics", [])
        return dossier

    def _attach_diagnostic(
        self,
        draft: CandidateIntakeDraft,
        *,
        stage: str,
        code: str,
        severity: str,
        message: str,
        source_id: str | None = None,
        source_label: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        dossier = self._ensure_draft_dossier(draft)
        _record_diagnostic(
            dossier,
            stage=stage,
            code=code,
            severity=severity,
            message=message,
            source_id=source_id,
            source_label=source_label,
            details=details,
        )
        draft.source_dossier = dossier
        flag_modified(draft, "source_dossier")
        self.session.add(draft)

    def _fail_with_diagnostic(
        self,
        draft: CandidateIntakeDraft,
        *,
        stage: str,
        code: str,
        severity: str,
        message: str,
        user_message: str,
        source_id: str | None = None,
        source_label: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        self._attach_diagnostic(
            draft,
            stage=stage,
            code=code,
            severity=severity,
            message=message,
            source_id=source_id,
            source_label=source_label,
            details=details,
        )
        self.session.commit()
        raise ValueError(user_message)

    def start_intake(
        self,
        candidate_id: str,
        uploaded_files: list[UploadedFile],
        profile_notes: str | None = None,
        *,
        reset_existing_draft: bool = False,
    ) -> IntakeResult:
        candidate = _ensure_candidate(self.session, candidate_id)
        prompt_pack = load_prompt_pack()
        draft = self._get_or_create_draft(candidate_id)
        if reset_existing_draft:
            draft.partial_fact_sheet = None
            draft.pending_questions = None
            draft.last_answers = None
            draft.source_dossier = None
            draft.iteration = 0
            self.session.add(draft)
            self.session.flush()
        stored_rows = store_uploaded_files(self.session, candidate_id, uploaded_files) if uploaded_files else []

        source_rows = stored_rows
        if not source_rows:
            existing_rows = (
                self.session.query(CandidateSourceFile)
                .filter_by(candidate_id=candidate_id)
                .order_by(CandidateSourceFile.created_at.asc())
                .all()
            )
            source_rows = list(existing_rows)
        dossier = _build_source_dossier(
            candidate_id=candidate_id,
            source_rows=source_rows,
            profile_notes=profile_notes,
        )
        draft.source_dossier = dossier
        self.session.add(draft)
        self.session.flush()

        raw_source_texts = _dossier_texts(dossier, normalized=False)
        source_hints = _source_fact_hints_from_texts(raw_source_texts)

        structured_source = next((text for text in raw_source_texts if _looks_like_structured_fact_sheet(text)), None)
        if structured_source:
            canonical, _issues = _promote_intake_draft_to_canonical(
                candidate,
                _fact_sheet_from_structured_source(candidate, structured_source),
                source_hints=source_hints,
                dossier=dossier,
            )
            _record_promotion_issues(dossier, _issues)
            try:
                FactSheetJsonIngestionService(self.session).ingest_json(candidate_id=candidate.id, fact_sheet=canonical)
            except (ValueError, JsonSchemaValidationError) as exc:
                self._fail_with_diagnostic(
                    draft,
                    stage="schema_promotion",
                    code="schema_ingest_failed",
                    severity="error",
                    message="Canonical fact-sheet ingestion failed after structured-source promotion.",
                    user_message=(
                        "Intake could not be finalized because the generated profile structure was inconsistent. "
                        "Please review your sources and retry."
                    ),
                    details=_sanitize_error_details(exc),
                )
            draft.partial_fact_sheet = canonical
            draft.pending_questions = None
            draft.source_dossier = dossier
            flag_modified(draft, "source_dossier")
            draft.iteration = 1
            self.session.add(draft)
            self.session.commit()
            return IntakeResult(status="complete", fact_sheet=canonical, iteration=1)

        provider_mode = normalize_provider_mode(getattr(settings, "llm_provider_mode", "openai"))
        extracted_texts = shape_text_blocks_for_workflow(
            _prepare_intake_texts(_dossier_texts(dossier, normalized=True)),
            workflow="intake",
            provider_mode=provider_mode,
        )

        system_prompt = _build_intake_system_prompt(prompt_pack)
        user_prompt = _build_intake_user_prompt(
            prompt_pack,
            extracted_texts,
            profile_notes=None,
            existing_fact_sheet=draft.partial_fact_sheet,
        )
        generate_fn = self.router.generate_with_retry if isinstance(self.router, LLMRouter) else self.router.generate
        try:
            result = _parse_llm_response(
                generate_fn(
                    role="small",
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.1,
                )
            )
        except ValueError as exc:
            self._fail_with_diagnostic(
                draft,
                stage="provider_draft_shape",
                code="provider_response_unparseable",
                severity="error",
                message="Provider returned an unparseable intake response payload.",
                user_message=(
                    "The AI provider returned an invalid intake response. "
                    "Please retry intake or switch provider in Settings."
                ),
                details=_sanitize_error_details(exc),
            )
        notes_overlay = _profile_notes_overlay(profile_notes)
        if notes_overlay:
            if isinstance(result.get("fact_sheet"), dict):
                result["fact_sheet"] = _merge_fact_sheet_dicts(result.get("fact_sheet") or {}, notes_overlay)
            else:
                result["partial_fact_sheet"] = _merge_fact_sheet_dicts(
                    result.get("partial_fact_sheet") or {},
                    notes_overlay,
                )
        return self._apply_intake_result(candidate, draft, result, next_iteration=1)

    def answer_questions(self, candidate_id: str, answers: dict[str, object]) -> IntakeResult:
        candidate = _ensure_candidate(self.session, candidate_id)
        draft = self.session.query(CandidateIntakeDraft).filter_by(candidate_id=candidate_id).first()
        if draft is None:
            raise ValueError(f"No active intake draft for candidate {candidate_id}")

        draft.last_answers = dict(answers)
        draft.partial_fact_sheet = _apply_direct_answers_to_partial_fact_sheet(draft.partial_fact_sheet or {}, answers)
        next_iteration = draft.iteration + 1
        if next_iteration >= _MAX_ITERATIONS:
            partial = _canonical_minimal_fact_sheet(candidate, draft.partial_fact_sheet)
            if not fact_sheet_is_ground_truth_ready(partial):
                draft.partial_fact_sheet = partial
                draft.pending_questions = _fallback_priority_questions(partial)
                draft.iteration = next_iteration
                self.session.add(draft)
                self.session.commit()
                return IntakeResult(
                    status="questions_needed",
                    questions=draft.pending_questions,
                    fact_sheet=partial,
                    iteration=next_iteration,
                )

            missing = list(partial.get("missing_information", []))
            if "Intake loop max iterations reached" not in missing:
                missing.append("Intake loop max iterations reached")
            partial["missing_information"] = missing
            try:
                FactSheetJsonIngestionService(self.session).ingest_json(candidate_id=candidate_id, fact_sheet=partial)
            except (ValueError, JsonSchemaValidationError) as exc:
                self._fail_with_diagnostic(
                    draft,
                    stage="schema_promotion",
                    code="schema_ingest_failed",
                    severity="error",
                    message="Canonical fact-sheet ingestion failed after max-iteration fallback.",
                    user_message=(
                        "Intake could not be finalized because the generated profile structure was inconsistent. "
                        "Please review your answers and retry."
                    ),
                    details=_sanitize_error_details(exc),
                )
            draft.partial_fact_sheet = partial
            draft.pending_questions = None
            draft.iteration = next_iteration
            self.session.add(draft)
            self.session.commit()
            return IntakeResult(status="complete", fact_sheet=partial, iteration=next_iteration)

        prompt_pack = load_prompt_pack()
        dossier = draft.source_dossier
        if not dossier:
            existing_rows = (
                self.session.query(CandidateSourceFile)
                .filter_by(candidate_id=candidate_id)
                .order_by(CandidateSourceFile.created_at.asc())
                .all()
            )
            dossier = _build_source_dossier(candidate_id=candidate_id, source_rows=list(existing_rows))
            draft.source_dossier = dossier
            self.session.add(draft)
            self.session.flush()
        provider_mode = normalize_provider_mode(getattr(settings, "llm_provider_mode", "openai"))
        source_texts = shape_text_blocks_for_workflow(
            _prepare_intake_texts(_dossier_texts(dossier, normalized=True)),
            workflow="intake",
            provider_mode=provider_mode,
        )
        system_prompt = _build_intake_system_prompt(prompt_pack)
        user_prompt = _build_answer_prompt(
            prompt_pack,
            partial_fact_sheet=draft.partial_fact_sheet or {},
            questions=list(draft.pending_questions or []),
            answers=answers,
            source_texts=source_texts,
        )
        generate_fn = self.router.generate_with_retry if isinstance(self.router, LLMRouter) else self.router.generate
        try:
            result = _parse_llm_response(
                generate_fn(
                    role="small",
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.1,
                )
            )
        except ValueError as exc:
            self._fail_with_diagnostic(
                draft,
                stage="provider_draft_shape",
                code="provider_response_unparseable",
                severity="error",
                message="Provider returned an unparseable intake response payload.",
                user_message=(
                    "The AI provider returned an invalid intake response while saving answers. "
                    "Please retry."
                ),
                details=_sanitize_error_details(exc),
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
        source_hints = _source_fact_hints_from_texts(_dossier_texts(draft.source_dossier, normalized=False))
        partial_fact_sheet = _merge_fact_sheet_dicts(draft.partial_fact_sheet or {}, result.get("partial_fact_sheet") or {})
        if source_hints:
            partial_fact_sheet = _apply_source_fact_hints(partial_fact_sheet, source_hints)
        fact_sheet = result.get("fact_sheet")
        raw_questions = list(result.get("questions", []))
        questions = _select_intake_questions(raw_questions, partial_fact_sheet)
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
            self._fail_with_diagnostic(
                draft,
                stage="provider_draft_shape",
                code="provider_response_missing_payload",
                severity="error",
                message="Provider response did not include questions or a fact_sheet payload.",
                user_message=(
                    "The AI provider response was incomplete and could not continue intake. "
                    "Please retry."
                ),
                details={"expected_keys": ["questions", "fact_sheet"]},
            )

        merged_fact_sheet = _merge_fact_sheet_dicts(draft.partial_fact_sheet or {}, fact_sheet)
        dossier = draft.source_dossier if isinstance(draft.source_dossier, dict) else None
        canonical, _issues = _promote_intake_draft_to_canonical(
            candidate,
            merged_fact_sheet,
            source_hints=source_hints,
            dossier=dossier,
        )
        if dossier is not None:
            _record_promotion_issues(dossier, _issues)
            draft.source_dossier = dict(dossier)
            flag_modified(draft, "source_dossier")
        updated_dossier = dict(dossier) if dossier is not None else None
        if not _has_fact_evidence(canonical) or not fact_sheet_is_ground_truth_ready(canonical):
            fallback_questions = _fallback_priority_questions(canonical)
            draft.pending_questions = fallback_questions
            draft.partial_fact_sheet = canonical
            if updated_dossier is not None:
                draft.source_dossier = updated_dossier
                flag_modified(draft, "source_dossier")
            draft.iteration = next_iteration
            self.session.add(draft)
            self.session.commit()
            return IntakeResult(
                status="questions_needed",
                questions=fallback_questions,
                fact_sheet=canonical,
                iteration=next_iteration,
            )
        try:
            FactSheetJsonIngestionService(self.session).ingest_json(candidate_id=candidate.id, fact_sheet=canonical)
        except (ValueError, JsonSchemaValidationError) as exc:
            self._fail_with_diagnostic(
                draft,
                stage="schema_promotion",
                code="schema_ingest_failed",
                severity="error",
                message="Canonical fact-sheet ingestion failed after provider promotion.",
                user_message=(
                    "Intake could not be finalized because the generated profile structure was inconsistent. "
                    "Please review your sources and retry."
                ),
                details=_sanitize_error_details(exc),
            )
        draft.partial_fact_sheet = canonical
        draft.pending_questions = None
        if updated_dossier is not None:
            draft.source_dossier = updated_dossier
            flag_modified(draft, "source_dossier")
        draft.iteration = next_iteration
        self.session.add(draft)
        self.session.commit()
        return IntakeResult(status="complete", fact_sheet=canonical, iteration=next_iteration)
