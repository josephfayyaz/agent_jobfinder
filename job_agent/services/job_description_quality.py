from __future__ import annotations

import re
from typing import Any

from job_agent.models import JobPost

JD_QUALITY_META_KEY = "jd_quality"

_ATS_SOURCE_HINTS = ("greenhouse", "lever", "ashby", "ats_")
_DETAIL_PATTERNS = (
    r"\brequirements?\b",
    r"\bqualifications?\b",
    r"\bresponsibilit(?:y|ies)\b",
    r"\bwhat you(?:'ll| will) do\b",
    r"\babout (?:the )?role\b",
    r"\bmust have\b",
    r"\byou will\b",
    r"\bwe are looking for\b",
    r"\bwe are hiring\b",
    r"\bwe need\b",
    r"\bpreferred qualifications?\b",
)


def _normalize_text(description: str | None) -> str:
    return re.sub(r"\s+", " ", str(description or "")).strip()


def _source_kind(*, source_name: str | None, source_url: str | None, company_url: str | None) -> str:
    name = str(source_name or "").strip().casefold()
    source = str(source_url or "").strip().casefold()
    company = str(company_url or "").strip().casefold()

    if name == "manual":
        return "manual"
    if any(hint in name for hint in _ATS_SOURCE_HINTS):
        return "ats_structured"
    if "linkedin" in source:
        if company and "linkedin" not in company:
            return "linkedin_enriched"
        return "linkedin_snippet"
    if company:
        return "company_page"
    if source:
        return "company_page"
    return "unknown"


def evaluate_job_description(
    *,
    description: str | None,
    source_name: str | None,
    source_url: str | None,
    company_url: str | None,
) -> dict[str, object]:
    text = _normalize_text(description)
    source_kind = _source_kind(source_name=source_name, source_url=source_url, company_url=company_url)
    reason_codes: list[str] = []

    if not text:
        return {
            "score": 0,
            "label": "missing",
            "ready_for_provider_scoring": False,
            "reason_codes": ["missing_description"],
            "reason_summary": "No readable job description is available yet.",
            "source_kind": source_kind,
        }

    alpha_count = sum(1 for char in text if char.isalpha())
    if alpha_count < 40:
        return {
            "score": 8,
            "label": "thin",
            "ready_for_provider_scoring": False,
            "reason_codes": ["insufficient_alpha_text"],
            "reason_summary": "The saved job text is too thin to treat as a real description.",
            "source_kind": source_kind,
        }

    detail_hits = sum(1 for pattern in _DETAIL_PATTERNS if re.search(pattern, text, flags=re.IGNORECASE))
    bullet_hits = len(re.findall(r"(?:^|\s)[\-•]\s+\w+", str(description or "")))
    long_text = len(text)

    score = 0
    if long_text >= 1500:
        score += 45
    elif long_text >= 900:
        score += 36
    elif long_text >= 500:
        score += 26
    elif long_text >= 250:
        score += 16
    else:
        score += 8
        reason_codes.append("short_text")

    if detail_hits:
        score += min(20, detail_hits * 7)
    else:
        reason_codes.append("missing_role_detail_signals")

    if bullet_hits >= 2:
        score += 10
    elif bullet_hits == 1:
        score += 4

    if source_kind == "ats_structured":
        score += 18
    elif source_kind == "company_page":
        score += 14
    elif source_kind == "manual":
        score += 12
    elif source_kind == "linkedin_enriched":
        score += 8
    elif source_kind == "linkedin_snippet":
        score += 2
        reason_codes.append("board_snippet_only")

    ready = False
    label = "thin"
    if score >= 80 and long_text >= 400:
        label = "strong"
        ready = True
    elif score >= 60 and long_text >= 220 and (
        detail_hits > 0 or source_kind in {"ats_structured", "company_page", "manual"}
    ):
        label = "usable"
        ready = True
    elif source_kind in {"company_page", "manual"} and score >= 26 and long_text >= 110:
        label = "usable"
        ready = True
    elif source_kind == "ats_structured" and score >= 34 and long_text >= 110:
        label = "usable"
        ready = True
    elif source_kind == "linkedin_enriched" and score >= 46 and long_text >= 150:
        label = "usable"
        ready = True
    elif source_kind == "linkedin_snippet" and score >= 28 and long_text >= 500:
        label = "usable"
        ready = True
    elif long_text < 120:
        label = "thin"
        reason_codes.append("very_short_description")

    if ready:
        reason_summary = "The job description has enough detail for provider-based fit scoring."
    elif label == "thin":
        if source_kind == "linkedin_snippet":
            reason_summary = "Thin board snippet; needs stronger enrichment before provider scoring."
        else:
            reason_summary = "The job description exists, but it is still too thin for provider scoring."
    else:
        reason_summary = "The saved job text is not ready for provider scoring yet."

    deduped_codes: list[str] = []
    for code in reason_codes:
        if code not in deduped_codes:
            deduped_codes.append(code)

    return {
        "score": max(0, min(100, int(score))),
        "label": label,
        "ready_for_provider_scoring": ready,
        "reason_codes": deduped_codes,
        "reason_summary": reason_summary,
        "source_kind": source_kind,
    }


def get_job_description_quality(job: JobPost | dict[str, Any]) -> dict[str, object]:
    metadata = dict(getattr(job, "extracted_metadata", None) or (job.get("extracted_metadata") if isinstance(job, dict) else {}) or {})
    cached = metadata.get(JD_QUALITY_META_KEY)
    if isinstance(cached, dict):
        return dict(cached)
    if isinstance(job, dict):
        return evaluate_job_description(
            description=str(job.get("description") or ""),
            source_name=str(job.get("source_name") or ""),
            source_url=str(job.get("source_url") or ""),
            company_url=str(job.get("company_url") or ""),
        )
    return evaluate_job_description(
        description=str(getattr(job, "description", "") or ""),
        source_name=str(getattr(job, "source_name", "") or ""),
        source_url=str(getattr(job, "source_url", "") or ""),
        company_url=str(getattr(job, "company_url", "") or ""),
    )
