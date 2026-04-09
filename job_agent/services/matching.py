from __future__ import annotations

from collections import Counter
from typing import Any

from job_agent.models import ResumeTrack


def score_tracks_for_job(job: dict[str, Any], tracks: list[ResumeTrack]) -> list[dict[str, Any]]:
    title = str(job.get("title", "")).lower()
    description = str(job.get("description", "")).lower()
    text = f"{title} {description}"
    token_counts = Counter(token.strip(".,:;()[]") for token in text.split())

    scored: list[dict[str, Any]] = []
    for track in tracks:
        matched_keywords = [keyword for keyword in track.target_keywords if keyword.lower() in text]
        keyword_hits = sum(token_counts.get(keyword.lower(), 0) for keyword in track.target_keywords)
        family_bonus = 0
        if track.role_family in text:
            family_bonus += 8
        if any(part in title for part in track.slug.split("-")):
            family_bonus += 5

        score = min(100, 20 + len(matched_keywords) * 8 + keyword_hits * 3 + family_bonus)
        scored.append(
            {
                "track_id": getattr(track, "id", None),
                "slug": track.slug,
                "title": track.title,
                "role_family": track.role_family,
                "score": score,
                "matched_keywords": matched_keywords[:10],
            }
        )

    return sorted(scored, key=lambda item: item["score"], reverse=True)
