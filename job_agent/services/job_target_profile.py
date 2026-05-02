from __future__ import annotations

import re
from typing import Any

from job_agent.search_preferences import detect_job_languages

_STOPWORDS = {
    "the",
    "and",
    "with",
    "for",
    "that",
    "this",
    "from",
    "into",
    "your",
    "will",
    "have",
    "must",
    "role",
    "team",
    "work",
}

_CONTEXTUAL_MARKERS = (
    "about us",
    "who we are",
    "our mission",
    "our values",
    "company overview",
    "benefits",
    "why join",
    "perks",
    "we offer",
)
_MUST_HAVE_MARKERS = (
    "must have",
    "required",
    "requirement",
    "you have",
    "you bring",
    "mandatory",
)
_NICE_TO_HAVE_MARKERS = (
    "nice to have",
    "preferred",
    "bonus",
    "plus",
    "would be a plus",
)
_RESPONSIBILITY_MARKERS = (
    "responsib",
    "you will",
    "what you'll do",
    "what you will do",
    "in this role",
    "day-to-day",
    "assist",
    "support",
    "manage",
    "prepare",
    "analyze",
    "analyse",
    "build",
    "design",
    "monitor",
    "coordinate",
)
_TOOL_HINTS = (
    "excel",
    "power bi",
    "sap",
    "sql",
    "python",
    "airflow",
    "dbt",
    "tableau",
    "oracle",
    "salesforce",
    "cad",
    "matlab",
    "solidworks",
    "autocad",
)


def _split_requirement_candidates(description: str) -> list[str]:
    lines: list[str] = []
    for raw_line in str(description or "").splitlines():
        line = re.sub(r"\s+", " ", raw_line.strip().lstrip("-•*")).strip()
        if len(line) >= 12:
            lines.append(line)
    if not lines:
        lines = [
            fragment.strip()
            for fragment in re.split(r"(?<=[.!?])\s+", str(description or ""))
            if len(fragment.strip()) >= 12
        ]
    return lines


def _infer_requirement_tier(text: str) -> str:
    lowered = text.casefold()
    if any(marker in lowered for marker in _CONTEXTUAL_MARKERS):
        return "contextual"
    if any(marker in lowered for marker in _NICE_TO_HAVE_MARKERS):
        return "nice_to_have"
    if any(marker in lowered for marker in _MUST_HAVE_MARKERS):
        return "must_have"
    if any(marker in lowered for marker in _RESPONSIBILITY_MARKERS):
        return "important"
    return "important"


def _infer_seniority(text: str, title: str = "") -> str:
    lowered = f"{title} {text}".casefold()
    if any(token in lowered for token in ("intern", "trainee", "stage", "internship")):
        return "intern"
    if any(token in lowered for token in ("senior", "lead", "principal", "head", "staff", "director")):
        return "senior"
    if any(token in lowered for token in ("mid", "intermediate")):
        return "mid"
    if any(token in lowered for token in ("junior", "entry", "graduate", "associate")):
        return "junior"
    return "unknown"


def _extract_tools(description: str) -> list[str]:
    lowered = str(description or "").casefold()
    tools: list[str] = []
    for hint in _TOOL_HINTS:
        if hint in lowered:
            tools.append(hint.title() if hint != "sql" else "SQL")
    return tools


def _tokenize(text: str) -> set[str]:
    tokens = {
        token
        for token in re.findall(r"[a-z0-9][a-z0-9+/.-]{2,}", str(text or "").casefold())
        if token not in _STOPWORDS
    }
    return tokens


def build_job_target_profile(
    *,
    title: str,
    company: str,
    description: str,
    location: str = "",
    country: str = "",
    source_url: str = "",
) -> dict[str, Any]:
    candidates = _split_requirement_candidates(description)
    responsibilities: list[str] = []
    requirements: list[dict[str, Any]] = []
    contextual: list[str] = []
    seen: set[str] = set()

    for candidate in candidates:
        lowered = candidate.casefold()
        key = re.sub(r"\W+", " ", lowered).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        tier = _infer_requirement_tier(candidate)
        if tier == "contextual":
            contextual.append(candidate)
            continue
        if any(marker in lowered for marker in _RESPONSIBILITY_MARKERS):
            responsibilities.append(candidate)
        requirement_tokens = sorted(_tokenize(candidate))
        requirements.append(
            {
                "requirement": candidate,
                "tier": tier,
                "tokens": requirement_tokens,
            }
        )

    languages = detect_job_languages(description)
    role_snapshot = {
        "title": str(title or "").strip(),
        "company": str(company or "").strip(),
        "location": str(location or "").strip(),
        "country": str(country or "").strip(),
        "language": languages[0]["name"] if languages else "Unknown",
        "detected_languages": languages,
        "seniority": _infer_seniority(description, title=title),
        "source_url": str(source_url or "").strip(),
    }

    return {
        "role_snapshot": role_snapshot,
        "responsibilities": responsibilities[:8],
        "requirements": requirements[:12],
        "tools_platforms": _extract_tools(description),
        "education_or_certifications": [
            item["requirement"]
            for item in requirements
            if any(token in item["requirement"].casefold() for token in ("degree", "certification", "master", "bachelor", "diploma"))
        ][:6],
        "contextual_company_background": contextual[:8],
        "summary": {
            "must_have": sum(1 for item in requirements if item["tier"] == "must_have"),
            "important": sum(1 for item in requirements if item["tier"] == "important"),
            "nice_to_have": sum(1 for item in requirements if item["tier"] == "nice_to_have"),
            "contextual": len(contextual),
        },
    }


def _collect_profile_evidence(profile_data: dict[str, Any], verified_facts: list[dict[str, Any]] | None = None) -> list[dict[str, str]]:
    evidence: list[dict[str, str]] = []
    for experience in profile_data.get("experiences") or []:
        if not isinstance(experience, dict):
            continue
        bullets = experience.get("bullets") or []
        for bullet in bullets:
            text = str(bullet).strip()
            if text:
                evidence.append({"source_type": "direct_structured_experience", "text": text})
    for project in profile_data.get("projects") or []:
        if not isinstance(project, dict):
            continue
        bullets = project.get("bullets") or []
        for bullet in bullets:
            text = str(bullet).strip()
            if text:
                evidence.append({"source_type": "direct_structured_project", "text": text})
        summary = str(project.get("summary") or project.get("description") or "").strip()
        if summary:
            evidence.append({"source_type": "profile_note_evidence", "text": summary})
    for skill in profile_data.get("global_skills") or []:
        text = str(skill).strip()
        if text:
            evidence.append({"source_type": "skill_only_evidence", "text": text})
    for fact in verified_facts or []:
        text = str(fact.get("evidence") or "").strip()
        if text:
            evidence.append({"source_type": "verified_candidate_fact", "text": text})
    return evidence


def _best_evidence_for_requirement(
    requirement: str,
    evidence_rows: list[dict[str, str]],
) -> tuple[dict[str, str] | None, float]:
    req_tokens = _tokenize(requirement)
    if not req_tokens:
        return None, 0.0
    best: dict[str, str] | None = None
    best_score = 0.0
    for row in evidence_rows:
        evidence_tokens = _tokenize(row.get("text", ""))
        if not evidence_tokens:
            continue
        overlap = req_tokens & evidence_tokens
        score = len(overlap) / max(len(req_tokens), 1)
        if row.get("source_type") in {"direct_structured_experience", "direct_structured_project"}:
            score += 0.08
        elif row.get("source_type") == "verified_candidate_fact":
            score += 0.05
        if score > best_score:
            best = row
            best_score = score
    return best, min(best_score, 1.0)


def _gap_level(score: float, source_type: str | None) -> str:
    if source_type in {"direct_structured_experience", "direct_structured_project"} and score >= 0.38:
        return "strong_match"
    if score >= 0.52:
        return "strong_match"
    if score >= 0.26:
        return "partial_match"
    if score >= 0.12:
        return "stretch_match"
    return "high_gap"


def build_cv_target_fit(
    *,
    job_profile: dict[str, Any],
    profile_data: dict[str, Any],
    verified_facts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    requirement_rows = list(job_profile.get("requirements") or [])
    evidence_rows = _collect_profile_evidence(profile_data, verified_facts=verified_facts)
    fit_rows: list[dict[str, Any]] = []

    weighted_scores = 0.0
    weighted_possible = 0.0
    gap_penalty = 0.0
    evidence_hits = 0.0

    tier_weights = {"must_have": 1.5, "important": 1.0, "nice_to_have": 0.6, "contextual": 0.0}
    gap_penalties = {"strong_match": 0.0, "partial_match": 0.25, "stretch_match": 0.55, "high_gap": 1.0}

    for requirement in requirement_rows:
        text = str(requirement.get("requirement") or "").strip()
        tier = str(requirement.get("tier") or "important")
        if not text:
            continue
        weight = tier_weights.get(tier, 1.0)
        best, confidence = _best_evidence_for_requirement(text, evidence_rows)
        source_type = best.get("source_type") if best else "no_evidence"
        gap_level = _gap_level(confidence, source_type)
        fit_rows.append(
            {
                "requirement": text,
                "tier": tier,
                "matched_evidence": best.get("text") if best else "No grounded evidence found yet.",
                "evidence_source_type": source_type,
                "confidence": round(confidence, 3),
                "gap_level": gap_level,
            }
        )
        weighted_possible += weight
        weighted_scores += weight * confidence
        evidence_hits += weight if best else 0.0
        gap_penalty += weight * gap_penalties[gap_level]

    semantic_fit = round((weighted_scores / weighted_possible) * 100) if weighted_possible else 0
    evidence_coverage = round((evidence_hits / weighted_possible) * 100) if weighted_possible else 0
    truthfulness_safety = 100 if fit_rows else 0
    gap_severity = round((gap_penalty / weighted_possible) * 100) if weighted_possible else 100
    overall_match = round((semantic_fit * 0.45) + (evidence_coverage * 0.35) + (truthfulness_safety * 0.20))

    top_modifications: list[dict[str, Any]] = []
    for row in fit_rows:
        if row["gap_level"] == "strong_match":
            continue
        fixable_now = row["evidence_source_type"] not in {"no_evidence", "skill_only_evidence"}
        needs_confirmation = row["gap_level"] == "stretch_match" or row["evidence_source_type"] == "profile_note_evidence"
        cannot_fix_honestly = row["gap_level"] == "high_gap" and row["evidence_source_type"] == "no_evidence"
        top_modifications.append(
            {
                "change": row["requirement"],
                "why_it_matters": f"This is classified as {row['tier'].replace('_', ' ')} for the role.",
                "fixable_now": fixable_now,
                "needs_confirmation": needs_confirmation,
                "cannot_fix_honestly": cannot_fix_honestly,
                "gap_level": row["gap_level"],
            }
        )
    gap_rank = {"high_gap": 0, "stretch_match": 1, "partial_match": 2}
    top_modifications.sort(key=lambda item: (gap_rank.get(item["gap_level"], 3), not item["fixable_now"]))

    gap_summary = {
        "strong_match": sum(1 for row in fit_rows if row["gap_level"] == "strong_match"),
        "partial_match": sum(1 for row in fit_rows if row["gap_level"] == "partial_match"),
        "stretch_match": sum(1 for row in fit_rows if row["gap_level"] == "stretch_match"),
        "high_gap": sum(1 for row in fit_rows if row["gap_level"] == "high_gap"),
    }

    return {
        "rows": fit_rows,
        "scores": {
            "semantic_fit_score": semantic_fit,
            "evidence_coverage_score": evidence_coverage,
            "truthfulness_safety_score": truthfulness_safety,
            "gap_severity_score": gap_severity,
            "overall_match_score": overall_match,
        },
        "summary": gap_summary,
        "recommended_improvements": top_modifications[:5],
    }
