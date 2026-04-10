from __future__ import annotations

from collections import Counter
import math
import re
from typing import TYPE_CHECKING, Any

import httpx

from job_agent.config import get_settings
from job_agent.models import ResumeTrack

if TYPE_CHECKING:
    from job_agent.config import Settings
    from job_agent.models import JobPost

# Seniority penalty: these terms in job title → -15 to the score
_SENIOR_TITLE_TERMS = frozenset([
    "senior", "sr.", "lead", "principal", "staff", "manager",
    "director", "head of", "vp", "vice president", "chief", "architect",
    "distinguished", "fellow",
])

# Seniority penalty: regex to detect years-of-experience requirements in description
_EXPERIENCE_YEAR_REGEX = re.compile(
    r"(\d+)\+?\s*(?:to\s*\d+\s*)?years?\s+(?:of\s+)?(?:professional\s+)?experience",
    re.IGNORECASE,
)

# Seniority boost: these terms in job title → +10 to the score (when target is intern/junior)
_JUNIOR_TITLE_TERMS = frozenset([
    "intern", "internship", "junior", "jr.", "entry level", "entry-level",
    "graduate", "trainee", "associate", "stage", "tirocinio", "apprentice",
    "new grad", "fresher",
])


def _job_value(job: Any, key: str) -> str:
    if isinstance(job, dict):
        return str(job.get(key, "") or "")
    return str(getattr(job, key, "") or "")


def _get_embedding(text: str) -> list[float] | None:
    """Call the LM Studio embedding endpoint and return a vector or None on failure."""
    settings = get_settings()
    if not settings.lm_studio_embedding_model or not text.strip():
        return None
    try:
        response = httpx.post(
            f"{settings.lm_studio_base_url}/embeddings",
            json={"input": text[:8000], "model": settings.lm_studio_embedding_model},
            timeout=settings.lm_studio_request_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        return payload["data"][0]["embedding"]
    except Exception as exc:
        import logging

        logging.getLogger(__name__).warning("Embedding request failed: %s", exc)
        return None


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity in [0.0, 1.0]. Returns 0.0 on zero vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (mag_a * mag_b)))


def score_semantic(job_text: str, track_keyword_text: str) -> float:
    """Compute cosine similarity between job text and track keywords on a 0-100 scale."""
    job_embedding = _get_embedding(job_text)
    if not job_embedding:
        return 0.0
    track_embedding = _get_embedding(track_keyword_text)
    if not track_embedding:
        return 0.0
    return _cosine_similarity(job_embedding, track_embedding) * 100


def _compute_keyword_score(job: dict[str, Any] | Any, track: ResumeTrack) -> tuple[float, list[str]]:
    """Preserve the existing keyword scoring logic as the baseline score."""
    title = _job_value(job, "title").lower()
    description = _job_value(job, "description").lower()
    text = f"{title} {description}"
    token_counts = Counter(token.strip(".,:;()[]") for token in text.split())

    matched_keywords = [keyword for keyword in track.target_keywords if keyword.lower() in text]
    keyword_hits = sum(token_counts.get(keyword.lower(), 0) for keyword in track.target_keywords)
    family_bonus = 0
    if track.role_family in text:
        family_bonus += 8
    if any(part in title for part in track.slug.split("-")):
        family_bonus += 5

    score = min(100, 20 + len(matched_keywords) * 8 + keyword_hits * 3 + family_bonus)
    return float(score), matched_keywords[:10]


def _apply_seniority_adjustment(score: float, job: "JobPost", settings: "Settings") -> float:
    """
    Adjust match score based on configured seniority target.
    Only applies when target_job_seniority is 'intern' or 'junior'.
    Does nothing when target_job_seniority is 'mid', 'senior', or 'any'.
    """
    if settings.target_job_seniority not in ("intern", "junior"):
        return score

    title_lower = _job_value(job, "title").lower()
    desc_lower = _job_value(job, "description").lower()[:3000]

    for term in _SENIOR_TITLE_TERMS:
        if term in title_lower:
            score -= 15
            break

    for match in _EXPERIENCE_YEAR_REGEX.finditer(desc_lower):
        years = int(match.group(1))
        if years >= 4:
            score -= 20
            break

    for term in _JUNIOR_TITLE_TERMS:
        if term in title_lower:
            score += 10
            break

    return max(0.0, min(100.0, score))


def score_tracks_for_job(job: dict[str, Any] | Any, tracks: list[ResumeTrack]) -> list[dict[str, Any]]:
    settings = get_settings()
    weight = settings.semantic_matching_weight
    title = _job_value(job, "title")
    description = _job_value(job, "description")
    scored: list[dict[str, Any]] = []
    for track in tracks:
        keyword_score, matched_keywords = _compute_keyword_score(job, track)
        semantic_score = 0.0
        if weight > 0 and description:
            track_keyword_text = " ".join(track.target_keywords or [])
            job_text = f"{title} {description}"[:8000]
            if track_keyword_text:
                semantic_score = score_semantic(job_text, track_keyword_text)

        if weight > 0 and semantic_score > 0:
            final_score = (1 - weight) * keyword_score + weight * semantic_score
        else:
            final_score = keyword_score
        final_score = _apply_seniority_adjustment(final_score, job, settings)

        scored.append(
            {
                "track_id": getattr(track, "id", None),
                "slug": track.slug,
                "title": track.title,
                "role_family": track.role_family,
                "score": min(100, round(final_score, 1)),
                "matched_keywords": matched_keywords,
            }
        )

    return sorted(scored, key=lambda item: item["score"], reverse=True)
