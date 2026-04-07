from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any


PLACEHOLDER_MARKERS = ("VERIFY", "ADD_", "ADD_IF", "OMIT IN CV BY USER PREFERENCE", "END OF FILE")


def load_fact_sheet(path: str) -> tuple[str, str, str]:
    source_path = Path(path).expanduser().resolve()
    content = source_path.read_text(encoding="utf-8")
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return str(source_path), digest, content


def parse_fact_sheet(content: str) -> dict[str, Any]:
    sections: list[tuple[str, list[str]]] = []
    current_name: str | None = None
    current_lines: list[str] = []

    for raw_line in content.splitlines():
        line = raw_line.rstrip()
        if line.startswith("SECTION: "):
            if current_name is not None:
                sections.append((current_name, current_lines))
            current_name = line.split("SECTION: ", 1)[1].strip()
            current_lines = []
            continue
        if line.startswith("=================================================="):
            continue
        if current_name is not None:
            current_lines.append(line)

    if current_name is not None:
        sections.append((current_name, current_lines))

    parsed: dict[str, Any] = {
        "core_profile": {},
        "summary_bank": {},
        "skills_inventory": {},
        "keyword_sets": {},
        "custom_rules": {},
        "open_items": [],
        "education_items": [],
        "experience_items": [],
        "project_items": [],
    }

    for section_name, lines in sections:
        normalized = parse_key_value_block(lines)
        if section_name == "CORE PROFILE":
            parsed["core_profile"] = normalized
        elif section_name == "SUMMARY BANK":
            parsed["summary_bank"] = normalized
        elif section_name == "SKILLS INVENTORY":
            parsed["skills_inventory"] = normalized
        elif section_name == "ATS KEYWORD BANK":
            parsed["keyword_sets"] = normalized
        elif section_name == "CUSTOM CV DECISION RULES":
            parsed["custom_rules"] = normalized
        elif section_name == "OPEN ITEMS TO FILL NEXT":
            parsed["open_items"] = sanitize_list([line.removeprefix("- ").strip() for line in lines if line.strip()])
        elif section_name == "EDUCATION":
            for block in split_item_blocks(lines):
                item = parse_key_value_block(block)
                if item.get("ITEM_ID"):
                    parsed["education_items"].append(item)
        elif section_name in {"RESEARCH EXPERIENCE", "PROFESSIONAL EXPERIENCE", "TEACHING / ACADEMIC SERVICE"}:
            for block in split_item_blocks(lines):
                item = parse_key_value_block(block)
                if item.get("ITEM_ID"):
                    item["SECTION_NAME"] = section_name
                    parsed["experience_items"].append(item)
        elif section_name == "PROJECTS":
            for block in split_item_blocks(lines):
                item = parse_key_value_block(block)
                if item.get("ITEM_ID"):
                    parsed["project_items"].append(item)

    return parsed


def parse_key_value_block(lines: list[str]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_key: str | None = None
    current_value: list[str] = []

    def flush() -> None:
        nonlocal current_key, current_value
        if current_key is None:
            return
        data[current_key] = collapse_value(current_key, current_value)
        current_key = None
        current_value = []

    key_value_pattern = re.compile(r"^([A-Z0-9][A-Z0-9_ /&()-]*):(?:\s(.*))?$")

    for raw_line in lines:
        line = raw_line.rstrip()
        match = key_value_pattern.match(line)
        if match:
            flush()
            current_key = match.group(1).strip()
            initial = match.group(2) or ""
            current_value = [initial] if initial else []
            continue
        if current_key is None:
            continue
        current_value.append(line)

    flush()
    return {key: value for key, value in data.items() if value not in ("", [], {}, None)}


def split_item_blocks(lines: list[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for raw_line in lines:
        line = raw_line.rstrip()
        if line.startswith("ITEM_ID:"):
            if current:
                blocks.append(current)
            current = [line]
            continue
        if current:
            current.append(line)
    if current:
        blocks.append(current)
    return blocks or [lines]


def collapse_value(key: str, lines: list[str]) -> Any:
    cleaned = [line.strip() for line in lines if line.strip()]
    if not cleaned:
        return ""

    if all(line.startswith("- ") for line in cleaned):
        return sanitize_list([line[2:].strip() for line in cleaned])

    if key in {
        "VERIFIED_CORE_FACTS",
        "ENRICHED_DESCRIPTION_BANK",
        "TOOLS_AND_TECH",
        "KEY_RESULTS",
        "METRICS_TO_CAPTURE",
        "EVIDENCE_LINKS",
        "TAGS",
        "TARGET_REGIONS",
        "PRIMARY_DOMAIN_INTERESTS",
        "LANGUAGES",
        "GOOD_LEAD_OPTIONS",
        "RELEVANT_COURSES",
        "NOTES",
    }:
        return sanitize_list([line.removeprefix("- ").strip() for line in cleaned])

    if any(line.startswith("- ") for line in cleaned):
        return sanitize_list([line.removeprefix("- ").strip() for line in cleaned])

    return sanitize_text(" ".join(cleaned))


def sanitize_text(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    if any(marker in text for marker in PLACEHOLDER_MARKERS):
        return ""
    return text


def sanitize_list(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    for value in values:
        item = sanitize_text(value)
        if item:
            cleaned.append(item)
    return cleaned


def as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return sanitize_list(value)
    if isinstance(value, str):
        text = sanitize_text(value)
        return [text] if text else []
    return []
