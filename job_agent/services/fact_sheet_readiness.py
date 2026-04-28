from __future__ import annotations


def _count_skill_items(skills: object) -> int:
    if not isinstance(skills, dict):
        return 0
    count = 0
    for value in skills.values():
        if isinstance(value, list):
            count += sum(1 for item in value if str(item or "").strip())
        elif isinstance(value, str) and value.strip():
            count += 1
    return count


def fact_sheet_ground_truth_gaps(fact_sheet: dict | None) -> list[str]:
    """Return the minimum missing blocks needed for a usable single-user profile."""
    payload = dict(fact_sheet or {})
    experience = [item for item in (payload.get("experience") or []) if isinstance(item, dict)]
    education = [item for item in (payload.get("education") or []) if isinstance(item, dict)]
    projects = [item for item in (payload.get("projects") or []) if isinstance(item, dict)]
    skills_count = _count_skill_items(payload.get("skills") or {})

    gaps: list[str] = []
    if not (experience or education or projects):
        gaps.append("background_evidence")
    if not education and not experience and not projects:
        gaps.append("education_baseline")
    if skills_count <= 0:
        gaps.append("core_skills")
    return gaps


def fact_sheet_is_ground_truth_ready(fact_sheet: dict | None) -> bool:
    return not fact_sheet_ground_truth_gaps(fact_sheet)
