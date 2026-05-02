from __future__ import annotations

from typing import Any


READINESS_READY = "ready"
READINESS_WARN = "usable_with_warnings"
READINESS_BLOCK = "insufficient_profile_data"


def _person_contact(profile: dict[str, Any]) -> tuple[str, str]:
    person = profile.get("person") if isinstance(profile.get("person"), dict) else {}
    contact = person.get("contact") if isinstance(person.get("contact"), dict) else {}
    full_name = str(person.get("full_name") or profile.get("full_name") or "").strip()
    email = str(contact.get("email") or profile.get("email") or "").strip()
    return full_name, email


def _experience_items(profile: dict[str, Any]) -> list[dict[str, Any]]:
    raw = profile.get("experience")
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    raw = profile.get("experiences")
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    return []


def _project_items(profile: dict[str, Any]) -> list[dict[str, Any]]:
    raw = profile.get("projects")
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    return []


def _education_items(profile: dict[str, Any]) -> list[dict[str, Any]]:
    raw = profile.get("education")
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    return []


def _language_items(profile: dict[str, Any]) -> list[dict[str, Any]]:
    raw = profile.get("languages")
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    raw = profile.get("spoken_languages")
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    return []


def _skill_list(profile: dict[str, Any]) -> list[str]:
    if isinstance(profile.get("global_skills"), list):
        return [str(item).strip() for item in profile.get("global_skills", []) if str(item).strip()]
    skills = profile.get("skills")
    if isinstance(skills, dict):
        flattened: list[str] = []
        for value in skills.values():
            if isinstance(value, list):
                flattened.extend(str(item).strip() for item in value if str(item).strip())
        return flattened
    if isinstance(profile.get("selected_skills"), list):
        return [str(item).strip() for item in profile.get("selected_skills", []) if str(item).strip()]
    return []


def _experience_has_dates(item: dict[str, Any]) -> bool:
    start = str(item.get("start_date") or item.get("dates") or "").strip()
    end = str(item.get("end_date") or "").strip()
    return bool(start or end)


def _has_meaningful_experience(item: dict[str, Any]) -> bool:
    title = str(item.get("role_title") or item.get("title") or "").strip()
    org = str(item.get("organization") or item.get("company") or "").strip()
    bullets = item.get("responsibilities") or item.get("verified_core_facts") or item.get("bullets") or []
    bullet_count = sum(1 for bullet in bullets if str(bullet).strip()) if isinstance(bullets, list) else 0
    return bool(title or org) and bullet_count > 0


def _has_meaningful_project(item: dict[str, Any]) -> bool:
    name = str(item.get("name") or item.get("project_name") or "").strip()
    summary = str(item.get("summary") or item.get("short_resume_line") or "").strip()
    bullets = item.get("key_results") or item.get("verified_core_facts") or item.get("bullets") or []
    bullet_count = sum(1 for bullet in bullets if str(bullet).strip()) if isinstance(bullets, list) else 0
    return bool(name) and bool(summary or bullet_count)


def evaluate_profile_readiness(profile: dict[str, Any]) -> dict[str, Any]:
    full_name, email = _person_contact(profile)
    education = _education_items(profile)
    experiences = _experience_items(profile)
    projects = _project_items(profile)
    languages = _language_items(profile)
    skills = _skill_list(profile)

    missing_sections: list[str] = []
    warnings: list[str] = []
    reasons: list[str] = []

    if not full_name:
        missing_sections.append("full_name")
        reasons.append("Add your name before generating a CV.")
    if not email:
        missing_sections.append("email")
        warnings.append("Email is missing from the profile.")
    if not education:
        missing_sections.append("education")
        reasons.append("Add at least one education entry.")
    if not skills:
        missing_sections.append("skills")
        reasons.append("Add a usable skills list.")

    meaningful_experiences = [item for item in experiences if _has_meaningful_experience(item)]
    meaningful_projects = [item for item in projects if _has_meaningful_project(item)]
    evidence_blocks = len(meaningful_experiences) + len(meaningful_projects)

    if evidence_blocks == 0:
        missing_sections.append("experience_or_evidence")
        reasons.append("Add at least one real experience or evidence-backed project.")
    elif evidence_blocks == 1:
        warnings.append("Only one evidence block is available, so the CV may still feel thin.")

    dated_experiences = [item for item in meaningful_experiences if _experience_has_dates(item)]
    if meaningful_experiences and not dated_experiences:
        warnings.append("Structured experience exists, but dates are missing.")
    if not meaningful_experiences and meaningful_projects:
        warnings.append("The profile has project evidence but no structured employment history.")

    if not languages:
        warnings.append("No spoken languages are stored yet.")

    enough_one_page_sections = int(bool(education)) + int(bool(skills)) + int(bool(evidence_blocks))
    if enough_one_page_sections < 3:
        reasons.append("The profile does not yet have enough grounded sections for a competitive one-page CV.")

    if missing_sections or evidence_blocks == 0 or enough_one_page_sections < 3:
        status = READINESS_BLOCK
    elif evidence_blocks >= 2 and (dated_experiences or len(meaningful_projects) >= 2) and len(skills) >= 4:
        status = READINESS_READY
    else:
        status = READINESS_WARN

    if status == READINESS_READY:
        reasons.append("The profile has enough grounded evidence to support a strong CV draft.")
    elif status == READINESS_WARN:
        reasons.append("The profile is usable, but it still needs stronger detail for a more competitive CV.")

    return {
        "status": status,
        "reasons": reasons,
        "missing_sections": list(dict.fromkeys(missing_sections)),
        "warnings": warnings,
        "counts": {
            "education": len(education),
            "experiences": len(meaningful_experiences),
            "projects": len(meaningful_projects),
            "skills": len(skills),
            "languages": len(languages),
            "evidence_blocks": evidence_blocks,
            "dated_experiences": len(dated_experiences),
        },
        "ready_for_final_cv": status != READINESS_BLOCK,
    }
