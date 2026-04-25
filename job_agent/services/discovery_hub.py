"""Discovery metadata, dedup heuristics, and queue-facing source intelligence."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy.orm import Session

from job_agent.models import DiscoveryEvent, JobPost

_WHITESPACE_RE = re.compile(r"\s+")
_NON_WORD_RE = re.compile(r"[^a-z0-9]+")

SOURCE_PROFILES: dict[str, dict[str, object]] = {
    "career_page": {
        "path": "company_scan",
        "path_label": "Company page",
        "confidence": "Direct company",
        "tone": "good",
        "score": 95,
        "reasons": ["Captured from a company careers page.", "Usually closer to the canonical listing."],
        "direct_company": True,
    },
    "linkedin_email_alert": {
        "path": "gmail_alert",
        "path_label": "Email alert",
        "confidence": "Direct alert",
        "tone": "good",
        "score": 78,
        "reasons": ["Imported from your Gmail alerts.", "Useful lead, but still worth confirming against the company page."],
        "direct_company": False,
    },
    "jobspy_linkedin": {
        "path": "jobspy_linkedin",
        "path_label": "LinkedIn scan",
        "confidence": "Board repost",
        "tone": "warn",
        "score": 64,
        "reasons": ["Captured from board search results.", "May be a repost rather than the original company listing."],
        "direct_company": False,
    },
    "manual": {
        "path": "manual_import",
        "path_label": "Manual",
        "confidence": "Manual import",
        "tone": "good",
        "score": 80,
        "reasons": ["Added directly by you.", "Review the original source if details look incomplete."],
        "direct_company": False,
    },
    "manual_text": {
        "path": "manual_import",
        "path_label": "Manual text",
        "confidence": "Manual import",
        "tone": "good",
        "score": 72,
        "reasons": ["Pasted into the workspace manually.", "Quality depends on how complete the pasted text is."],
        "direct_company": False,
    },
    "manual_url": {
        "path": "manual_import",
        "path_label": "Manual URL",
        "confidence": "Manual import",
        "tone": "good",
        "score": 72,
        "reasons": ["Imported from a URL you supplied directly.", "Verify the link if the description looks thin."],
        "direct_company": False,
    },
}

ATS_SOURCE_TYPES = {
    "greenhouse": "ats_api",
    "lever": "ats_api",
    "ashby": "ats_api",
}


@dataclass(slots=True)
class DiscoveryMatch:
    job: JobPost | None
    reason: str
    canonical_key: str


def _normalize_part(value: str) -> str:
    compact = _WHITESPACE_RE.sub(" ", str(value or "").strip().lower())
    return _NON_WORD_RE.sub("", compact)


def heuristic_job_key(company: str, title: str, location: str) -> str:
    return "|".join(
        [
            _normalize_part(company),
            _normalize_part(title),
            _normalize_part(location),
        ]
    )


def source_profile(source_name: str, source_url: str = "", *, ats_type: str | None = None) -> dict[str, object]:
    profile: dict[str, object] = {}
    if ats_type in ATS_SOURCE_TYPES:
        profile = {
            "path": ATS_SOURCE_TYPES[ats_type or ""],
            "path_label": "ATS feed",
            "confidence": "Direct ATS",
            "tone": "good",
            "score": 92,
            "reasons": ["Imported from an applicant tracking system feed.", "Usually points to the original hiring workflow."],
            "direct_company": True,
        }
    if not profile:
        profile = dict(SOURCE_PROFILES.get(source_name, {}))
    if not profile and source_name.endswith("_linkedin"):
        profile = {
            "path": "job_board",
            "path_label": "Job board",
            "confidence": "Board repost",
            "tone": "warn",
            "score": 60,
            "reasons": ["Discovered via an external board.", "Treat as a lead until the company source is confirmed."],
            "direct_company": False,
        }
    if not profile:
        profile = {
            "path": "manual_import",
            "path_label": "Imported",
            "confidence": "Imported",
            "tone": "neutral",
            "score": 70,
            "reasons": ["Imported into the workspace.", "Review the original listing if trust signals are weak."],
            "direct_company": False,
        }

    host = urlparse(source_url).netloc.lower()
    if host and any(host.endswith(domain) for domain in ("greenhouse.io", "lever.co", "ashbyhq.com")):
        profile.setdefault("reasons", [])
        profile["reasons"] = list(profile["reasons"]) + ["Apply URL points to a known ATS host."]

    return profile


def discovery_metadata(
    *,
    source_name: str,
    source_url: str,
    canonical_apply_url: str,
    company: str,
    title: str,
    location: str,
    ats_type: str | None = None,
) -> dict[str, object]:
    profile = source_profile(source_name, source_url, ats_type=ats_type)
    return {
        "source_trail": {
            "source_name": source_name,
            "path": profile["path"],
            "path_label": profile["path_label"],
            "confidence_label": profile["confidence"],
            "tone": profile["tone"],
            "confidence_score": profile["score"],
            "reasons": list(profile["reasons"]),
            "direct_company_source": bool(profile["direct_company"]),
            "source_host": urlparse(source_url or canonical_apply_url).netloc.lower(),
        },
        "canonical_key": heuristic_job_key(company, title, location),
    }


def find_existing_job(
    session: Session,
    *,
    canonical_apply_url: str,
    source_url: str,
    company: str,
    title: str,
    location: str,
) -> DiscoveryMatch:
    canonical_apply_url = str(canonical_apply_url or "").strip()
    source_url = str(source_url or "").strip()
    if canonical_apply_url:
        existing = session.query(JobPost).filter(JobPost.canonical_apply_url == canonical_apply_url).first()
        if existing is not None:
            return DiscoveryMatch(existing, "canonical_apply_url", canonical_apply_url)

    if source_url:
        existing = session.query(JobPost).filter(JobPost.source_url == source_url).first()
        if existing is not None:
            return DiscoveryMatch(existing, "source_url", source_url)

    key = heuristic_job_key(company, title, location)
    if key != "||":
        jobs = (
            session.query(JobPost)
            .filter(
                JobPost.company == company,
                JobPost.title == title,
                JobPost.location == location,
            )
            .all()
        )
        if jobs:
            return DiscoveryMatch(jobs[0], "company_title_location", key)

    return DiscoveryMatch(None, "", key)


def stamp_job_metadata(
    job: JobPost,
    *,
    source_name: str,
    source_url: str,
    canonical_apply_url: str,
    company: str,
    title: str,
    location: str,
    ats_type: str | None = None,
    canonical_reason: str = "",
) -> None:
    metadata = dict(job.extracted_metadata or {})
    metadata.update(
        discovery_metadata(
            source_name=source_name,
            source_url=source_url,
            canonical_apply_url=canonical_apply_url,
            company=company,
            title=title,
            location=location,
            ats_type=ats_type,
        )
    )
    if canonical_reason:
        metadata["canonical_reason"] = canonical_reason
    job.extracted_metadata = metadata


def record_discovery_event(
    session: Session,
    *,
    source_name: str,
    source_url: str,
    outcome: str,
    reason: str,
    acquisition_path: str,
    canonical_key: str,
    job_post_id: UUID | None = None,
) -> None:
    session.add(
        DiscoveryEvent(
            source_name=source_name,
            source_url=source_url,
            outcome=outcome,
            reason=reason,
            acquisition_path=acquisition_path,
            canonical_key=canonical_key,
            job_post_id=job_post_id,
        )
    )


def discovery_health(session: Session) -> dict[str, object]:
    rows = session.query(DiscoveryEvent).all()
    by_source = Counter()
    outcomes = Counter()
    for row in rows:
        by_source[row.acquisition_path or "unknown"] += 1
        outcomes[row.outcome or "unknown"] += 1

    total_events = sum(outcomes.values())
    duplicate_count = outcomes.get("duplicate", 0)
    jobs = session.query(JobPost).all()
    full_descriptions = sum(1 for job in jobs if len(str(job.description or "").strip()) >= 400)

    return {
        "event_count": total_events,
        "duplicate_count": duplicate_count,
        "dedup_hit_rate_pct": round((duplicate_count / total_events) * 100.0, 1) if total_events else 0.0,
        "jobs_with_full_descriptions_pct": round((full_descriptions / len(jobs)) * 100.0, 1) if jobs else 0.0,
        "sources": [
            {"path": path, "count": count}
            for path, count in by_source.most_common()
        ],
        "outcomes": dict(outcomes),
    }


def merge_duplicate_job(existing: JobPost, incoming: dict[str, Any]) -> None:
    existing.last_seen_at = incoming.get("last_seen_at") or existing.last_seen_at
    if not str(existing.description or "").strip() and str(incoming.get("description") or "").strip():
        existing.description = str(incoming.get("description") or "")
        existing.enrichment_status = str(incoming.get("enrichment_status") or existing.enrichment_status or "pending")
    if not str(existing.company_url or "").strip() and str(incoming.get("company_url") or "").strip():
        existing.company_url = str(incoming.get("company_url") or "")
    if not str(existing.canonical_apply_url or "").strip() and str(incoming.get("canonical_apply_url") or "").strip():
        existing.canonical_apply_url = str(incoming.get("canonical_apply_url") or "")
