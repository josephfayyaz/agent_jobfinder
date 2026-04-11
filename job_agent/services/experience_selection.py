"""Per-job experience and project selection with per-role bullet scoring."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_STOP_WORDS = {
    "and",
    "the",
    "with",
    "for",
    "in",
    "a",
    "an",
    "of",
    "to",
    "at",
    "on",
    "is",
    "are",
    "be",
    "was",
    "were",
    "we",
    "our",
    "you",
}


def _tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9#+]+", (text or "").lower())
    return {word for word in words if word not in _STOP_WORDS and len(word) > 1}


def _score_text_against_keywords(text: str, keywords: set[str]) -> float:
    """Return overlap ratio: matched_keywords / total_keywords (0.0–1.0)."""
    if not keywords:
        return 0.0
    tokens = _tokenize(text)
    return len(tokens & keywords) / len(keywords)


@dataclass
class SelectedExperience:
    experience_fact: Any
    selected_bullets: list[str]
    relevance_score: float


@dataclass
class SelectedProject:
    project_fact: Any
    selected_bullets: list[str]
    relevance_score: float


def _bullet_count_for_mode(presentation_mode: str) -> tuple[int, int]:
    """Return (min_bullets, max_bullets) for the given presentation mode."""
    if presentation_mode == "junior":
        return (2, 3)
    if presentation_mode == "senior":
        return (3, 4)
    return (3, 3)


def _get_value(item: Any, *keys: str, default: Any = None) -> Any:
    for key in keys:
        if isinstance(item, dict):
            value = item.get(key)
        else:
            value = getattr(item, key, None)
        if value not in (None, "", []):
            return value
    return default


def _as_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if item not in (None, "")]
    return [str(value)]


def _track_bullet_keys(track_slug: str | None) -> list[str]:
    if not track_slug:
        return []
    normalized = track_slug.replace("-", "_")
    return [
        track_slug,
        normalized,
        normalized.upper(),
        f"BEST_BULLETS_FOR_{normalized.upper()}",
    ]


def _best_bullets_for_track(item: Any, track_slug: str | None) -> list[str]:
    best_bullets = _get_value(item, "best_bullets_by_track", default={})
    if not isinstance(best_bullets, dict):
        return []
    for key in _track_bullet_keys(track_slug):
        bullets = best_bullets.get(key)
        if bullets:
            return _as_string_list(bullets)
    return []


def _experience_title(exp: Any) -> str:
    return str(_get_value(exp, "title", "role_title", default="") or "")


def _experience_org(exp: Any) -> str:
    return str(_get_value(exp, "organization", "company", default="") or "")


def _experience_start_date(exp: Any) -> str:
    return str(_get_value(exp, "start_date", default="") or "")


def _experience_keywords(exp: Any) -> list[str]:
    return (
        _as_string_list(_get_value(exp, "keywords", "tools_and_tech", "skills", default=None))
        or _as_string_list(_get_value(exp, "tags", default=None))
    )


def _experience_bullets(exp: Any, track_slug: str | None) -> list[str]:
    return (
        _best_bullets_for_track(exp, track_slug)
        or _as_string_list(_get_value(exp, "bullets", "verified_core_facts", default=None))
        or _as_string_list(_get_value(exp, "enriched_description_bank", default=None))
    )


def _project_name(project: Any) -> str:
    return str(_get_value(project, "name", "project_name", default="") or "")


def _project_description(project: Any) -> str:
    return str(_get_value(project, "description", "summary", "short_resume_line", default="") or "")


def _project_keywords(project: Any) -> list[str]:
    return (
        _as_string_list(_get_value(project, "keywords", "tools_and_tech", "skills", default=None))
        or _as_string_list(_get_value(project, "tags", default=None))
    )


def _project_bullets(project: Any, track_slug: str | None) -> list[str]:
    return (
        _best_bullets_for_track(project, track_slug)
        or _as_string_list(_get_value(project, "bullets", "verified_core_facts", default=None))
        or _as_string_list(_get_value(project, "key_results", default=None))
        or _as_string_list(_get_value(project, "enriched_description_bank", default=None))
    )


def select_experiences_for_job(
    experiences: list[Any],
    job: Any,
    target_keywords: list[str],
    presentation_mode: str = "junior",
    *,
    max_roles: int = 5,
    track_slug: str | None = None,
) -> list[SelectedExperience]:
    """
    Score each experience against the job and return the top max_roles,
    each with a per-role selected bullet list sized to match presentation_mode.
    """
    if not experiences:
        return []

    job_text = " ".join(
        filter(
            None,
            [
                str(_get_value(job, "title", default="") or ""),
                str(_get_value(job, "description", default="") or ""),
                " ".join(target_keywords),
            ],
        )
    )
    job_keywords = _tokenize(job_text)

    scored: list[tuple[float, Any]] = []
    for exp in experiences:
        bullets = _experience_bullets(exp, track_slug)
        keywords = _experience_keywords(exp)
        exp_text = " ".join(
            filter(
                None,
                [
                    _experience_title(exp),
                    _experience_org(exp),
                    " ".join(bullets),
                    " ".join(keywords),
                ],
            )
        )
        score = _score_text_against_keywords(exp_text, job_keywords)
        scored.append((score, exp))

    scored.sort(key=lambda item: item[0], reverse=True)
    selected_scored = scored[:max_roles]
    if len(selected_scored) > 3 and selected_scored[-1][0] <= 0.2:
        selected_scored = selected_scored[:-1]

    min_bullets, max_bullets = _bullet_count_for_mode(presentation_mode)
    results: list[SelectedExperience] = []
    for score, exp in selected_scored:
        bullets = _experience_bullets(exp, track_slug)
        if len(bullets) <= max_bullets:
            chosen = bullets
        else:
            bullet_scores = [
                (_score_text_against_keywords(bullet, job_keywords), index, bullet)
                for index, bullet in enumerate(bullets)
            ]
            bullet_scores.sort(key=lambda item: item[0], reverse=True)
            top = bullet_scores[:max_bullets]
            top.sort(key=lambda item: item[1])
            chosen = [item[2] for item in top]
        if len(chosen) < min_bullets:
            chosen = bullets[:min_bullets]
        results.append(
            SelectedExperience(
                experience_fact=exp,
                selected_bullets=chosen,
                relevance_score=score,
            )
        )

    results.sort(key=lambda item: _experience_start_date(item.experience_fact), reverse=True)
    return results


def select_projects_for_job(
    projects: list[Any],
    job: Any,
    target_keywords: list[str],
    presentation_mode: str = "junior",
    *,
    max_projects: int = 3,
    track_slug: str | None = None,
) -> list[SelectedProject]:
    """
    Score each project against the job and return the top max_projects.
    Bullet selection follows the same presentation_mode rules as experiences.
    """
    if not projects:
        return []

    job_text = " ".join(
        filter(
            None,
            [
                str(_get_value(job, "title", default="") or ""),
                str(_get_value(job, "description", default="") or ""),
                " ".join(target_keywords),
            ],
        )
    )
    job_keywords = _tokenize(job_text)

    scored: list[tuple[float, Any]] = []
    for project in projects:
        bullets = _project_bullets(project, track_slug)
        keywords = _project_keywords(project)
        project_text = " ".join(
            filter(
                None,
                [
                    _project_name(project),
                    _project_description(project),
                    " ".join(bullets),
                    " ".join(keywords),
                ],
            )
        )
        score = _score_text_against_keywords(project_text, job_keywords)
        scored.append((score, project))

    scored.sort(key=lambda item: item[0], reverse=True)

    min_bullets, max_bullets = _bullet_count_for_mode(presentation_mode)
    results: list[SelectedProject] = []
    for score, project in scored[:max_projects]:
        bullets = _project_bullets(project, track_slug)
        if len(bullets) <= max_bullets:
            chosen = bullets
        else:
            bullet_scores = [
                (_score_text_against_keywords(bullet, job_keywords), index, bullet)
                for index, bullet in enumerate(bullets)
            ]
            bullet_scores.sort(key=lambda item: item[0], reverse=True)
            top = bullet_scores[:max_bullets]
            top.sort(key=lambda item: item[1])
            chosen = [item[2] for item in top]
        if len(chosen) < min_bullets:
            chosen = bullets[:min_bullets]
        results.append(
            SelectedProject(
                project_fact=project,
                selected_bullets=chosen,
                relevance_score=score,
            )
        )
    return results
