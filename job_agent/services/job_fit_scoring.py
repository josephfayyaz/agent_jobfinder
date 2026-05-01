from __future__ import annotations

import hashlib
import json
import re
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from job_agent.config import settings
from job_agent.llm import LLMRouter, ProviderUnavailableError
from job_agent.models import Candidate, JobPost, MatchProfile, ResumeTrack
from job_agent.providers import normalize_provider_mode
from job_agent.search_preferences import (
    detect_job_languages,
    language_level_rank,
    normalize_job_language_preferences,
    normalize_role_list,
    primary_search_country,
)
from job_agent.services.job_description_quality import get_job_description_quality
from job_agent.services.fact_sheet_renderer import FactSheetRenderer
from job_agent.services.matching import score_tracks_for_job

CANDIDATE_FIT_META_KEY = "candidate_fit"
_SENIOR_TITLE_TERMS = ("senior", "sr.", "lead", "principal", "staff", "manager", "director", "head ")
_ENTRY_TITLE_TERMS = ("intern", "internship", "junior", "jr.", "graduate", "trainee", "entry level", "new grad")
_ROLE_TOKEN_STOPWORDS = {"and", "or", "for", "with", "the", "a", "an", "intern", "junior", "senior"}
_SYSTEM_PROMPT = """\
You score candidate fit for jobs using only the supplied fact sheet evidence.
Return strict JSON. Do not invent qualifications the candidate does not have.
Language is a soft signal, not a hard blocker.
fit_score must be an integer from 0 to 100, not a 1 to 10 scale.
Use this rubric:
- 90-100: excellent fit, title and core skills align strongly, only minor gaps.
- 75-89: strong shortlist fit, most core requirements align, some gaps are acceptable.
- 50-74: partial fit, adjacent role or several meaningful gaps.
- 0-49: weak fit or clearly mismatched role.
For junior or graduate roles, do not heavily penalize missing enterprise-scale or senior-only experience when the foundations align.
If the job title directly matches one of the selected target roles and the candidate shows multiple pieces of matching evidence, that usually belongs in the 80+ shortlist range unless there is a major mismatch.
"""
_USER_PROMPT = """\
Candidate fact sheet summary:
{fact_summary}

Search profile:
- country: {country}
- roles: {roles}
- seniority target: {seniority}
- languages: {languages}

Job:
- title: {title}
- location: {location}
- country: {job_country}
- detected description languages: {job_languages}

Job description:
{description}

Return only JSON with this shape:
{{
  "fit_score": 0,
  "matched_evidence": ["short bullet"],
  "top_gaps": ["short bullet"],
  "language_assessment": {{
    "label": "good | stretch | risk | unknown",
    "reason": "short reason"
  }},
  "seniority_assessment": {{
    "label": "aligned | stretch | risk | unknown",
    "reason": "short reason"
  }},
  "short_reason": "one sentence"
}}
"""


def _job_metadata(job: JobPost | dict[str, Any]) -> dict[str, Any]:
    if isinstance(job, dict):
        meta = job.get("extracted_metadata")
    else:
        meta = getattr(job, "extracted_metadata", None)
    return dict(meta or {})


def get_cached_candidate_fit(job: JobPost | dict[str, Any], candidate_id: str | None) -> dict[str, Any] | None:
    if not candidate_id:
        return None
    fit_map = _job_metadata(job).get(CANDIDATE_FIT_META_KEY)
    if not isinstance(fit_map, dict):
        return None
    cached = fit_map.get(str(candidate_id))
    return dict(cached) if isinstance(cached, dict) else None


def effective_job_fit_score(
    job: JobPost | dict[str, Any],
    *,
    candidate_id: str | None,
    score_rows: list[Any] | None = None,
) -> int:
    cached = get_cached_candidate_fit(job, candidate_id)
    if cached is not None:
        return _clamp_score(cached.get("fit_score"))

    if score_rows:
        top = score_rows[0]
        return _clamp_score(getattr(top, "score", 0))

    track_scores = _job_metadata(job).get("track_scores")
    if isinstance(track_scores, list) and track_scores:
        top = track_scores[0] if isinstance(track_scores[0], dict) else {}
        return _clamp_score(top.get("score"))
    return 0


def effective_job_fit_details(
    job: JobPost | dict[str, Any],
    *,
    candidate_id: str | None,
    score_rows: list[Any] | None = None,
) -> dict[str, Any]:
    cached = get_cached_candidate_fit(job, candidate_id)
    if cached is not None:
        return cached

    quality = get_job_description_quality(job)
    if not bool(quality.get("ready_for_provider_scoring")):
        return {
            "fit_score": effective_job_fit_score(job, candidate_id=candidate_id, score_rows=score_rows),
            "score_source": "awaiting_enrichment",
            "provider_mode": normalize_provider_mode(getattr(settings, "llm_provider_mode", "openai")),
            "matched_evidence": [],
            "top_gaps": [str(quality.get("reason_summary") or "The job description is not ready for provider scoring.")],
            "language_assessment": {"label": "unknown", "reason": "Language fit will update after stronger enrichment."},
            "seniority_assessment": {"label": "unknown", "reason": "Seniority fit will update after stronger enrichment."},
            "short_reason": "Job description is too weak for provider scoring; awaiting stronger enrichment.",
            "threshold_eligible": False,
            "awaiting_enrichment": True,
        }

    matched_keywords: list[str] = []
    if score_rows:
        matched_keywords = [str(item) for item in getattr(score_rows[0], "matched_keywords", []) if str(item).strip()]
    elif isinstance(_job_metadata(job).get("track_scores"), list):
        top = _job_metadata(job)["track_scores"][0] if _job_metadata(job)["track_scores"] else {}
        if isinstance(top, dict):
            matched_keywords = [str(item) for item in top.get("matched_keywords", []) if str(item).strip()]

    return {
        "fit_score": effective_job_fit_score(job, candidate_id=candidate_id, score_rows=score_rows),
        "score_source": "fallback",
        "provider_mode": normalize_provider_mode(getattr(settings, "llm_provider_mode", "openai")),
        "matched_evidence": [f"Matched keywords: {', '.join(matched_keywords[:6])}"] if matched_keywords else [],
        "top_gaps": [],
        "language_assessment": {"label": "unknown", "reason": "Language fit was not explicitly scored yet."},
        "seniority_assessment": {"label": "unknown", "reason": "Seniority fit was not explicitly scored yet."},
        "short_reason": "Fallback score from resume-track keyword and embedding matching.",
        "threshold_eligible": True,
        "awaiting_enrichment": False,
    }


class JobFitScoringService:
    def __init__(self, session: Session, router: LLMRouter | None = None) -> None:
        self.session = session
        self.router = router or LLMRouter()

    def score_and_persist(
        self,
        job: JobPost | UUID | str,
        *,
        candidate_id: str | None,
        force: bool = False,
        commit: bool = True,
    ) -> dict[str, Any]:
        job_obj = self._resolve_job(job)
        if job_obj is None:
            raise ValueError("Job not found for candidate-fit scoring.")
        if not candidate_id:
            result = self._fallback_result(
                job_obj,
                candidate=None,
                search_profile=self._search_profile(None),
                fallback_reason="No active candidate is configured for provider scoring.",
            )
            self._persist(job_obj, "__default__", result, commit=commit)
            return result

        candidate = self.session.get(Candidate, str(candidate_id))
        search_profile = self._search_profile(candidate)
        fact_summary = self._fact_summary(candidate, search_profile)
        cache_key = self._cache_key(
            fact_summary=fact_summary,
            provider_mode=normalize_provider_mode(getattr(settings, "llm_provider_mode", "openai")),
            search_profile=search_profile,
        )
        cached = get_cached_candidate_fit(job_obj, str(candidate_id))
        if cached is not None and cached.get("cache_key") == cache_key and not force:
            return cached

        result = self._compute_result(
            job=job_obj,
            candidate=candidate,
            candidate_id=str(candidate_id),
            fact_summary=fact_summary,
            search_profile=search_profile,
        )
        result["cache_key"] = cache_key
        self._persist(job_obj, str(candidate_id), result, commit=commit)
        return result

    def _compute_result(
        self,
        *,
        job: JobPost,
        candidate: Candidate | None,
        candidate_id: str,
        fact_summary: str,
        search_profile: dict[str, Any],
    ) -> dict[str, Any]:
        if candidate is None:
            return self._fallback_result(
                job,
                candidate=None,
                search_profile=search_profile,
                fallback_reason=f"Candidate {candidate_id} could not be loaded for provider scoring.",
            )

        description = str(job.description or "").strip()
        quality = get_job_description_quality(job)
        if not bool(quality.get("ready_for_provider_scoring")):
            return self._awaiting_enrichment_result(
                job,
                candidate=candidate,
                search_profile=search_profile,
                fallback_reason=str(
                    quality.get("reason_summary") or "Job description is too weak for provider scoring."
                ),
            )

        provider_mode = normalize_provider_mode(getattr(settings, "llm_provider_mode", "openai"))
        language_assessment = self._language_assessment(
            detect_job_languages(description),
            search_profile.get("languages"),
        )
        seniority_assessment = self._seniority_assessment(
            title=str(job.title or ""),
            description=description,
            target_seniority=str(search_profile.get("seniority") or settings.target_job_seniority or "junior"),
        )

        try:
            raw = self.router.generate_with_retry(
                role="small",
                system_prompt=_SYSTEM_PROMPT,
                user_prompt=_USER_PROMPT.format(
                    fact_summary=fact_summary,
                    country=str(search_profile.get("country") or "Unknown"),
                    roles=", ".join(search_profile.get("roles") or []) or "Unknown",
                    seniority=str(search_profile.get("seniority") or "Unknown"),
                    languages=", ".join(
                        f"{row['name']} ({row['label']})" for row in search_profile.get("languages") or []
                    )
                    or "Unknown",
                    title=str(job.title or "Unknown"),
                    location=str(job.location or "Unknown"),
                    job_country=str(job.country or search_profile.get("country") or "Unknown"),
                    job_languages=", ".join(item["name"] for item in detect_job_languages(description)) or "Unknown",
                    description=description[:5000],
                ),
            )
        except (ProviderUnavailableError, ValueError):
            return self._fallback_result(
                job,
                candidate=candidate,
                search_profile=search_profile,
                fallback_reason="Active provider was unavailable for candidate-fit scoring.",
            )

        matched_evidence = _normalize_string_list(raw.get("matched_evidence"), limit=5)
        top_gaps = _normalize_string_list(raw.get("top_gaps"), limit=5)
        normalized_language = _normalize_assessment(raw.get("language_assessment"), default=language_assessment)
        normalized_seniority = _normalize_assessment(raw.get("seniority_assessment"), default=seniority_assessment)
        fit_score = _normalize_provider_fit_score(
            raw.get("fit_score"),
            matched_evidence=matched_evidence,
        )
        if (
            str(search_profile.get("seniority") or "").strip().lower() in {"intern", "junior"}
            and normalized_seniority.get("label") == "aligned"
            and len(matched_evidence) >= 2
            and _title_matches_search_roles(str(job.title or ""), search_profile.get("roles") or [])
        ):
            fit_score = max(fit_score, 80)

        return {
            "fit_score": fit_score,
            "score_source": "provider",
            "provider_mode": provider_mode,
            "matched_evidence": matched_evidence,
            "top_gaps": top_gaps,
            "language_assessment": normalized_language,
            "seniority_assessment": normalized_seniority,
            "short_reason": _normalize_short_reason(raw.get("short_reason")),
            "threshold_eligible": True,
            "awaiting_enrichment": False,
        }

    def _awaiting_enrichment_result(
        self,
        job: JobPost,
        *,
        candidate: Candidate | None,
        search_profile: dict[str, Any],
        fallback_reason: str,
    ) -> dict[str, Any]:
        result = self._fallback_result(
            job,
            candidate=candidate,
            search_profile=search_profile,
            fallback_reason="Job description is too weak for provider scoring; awaiting stronger enrichment.",
        )
        result["score_source"] = "awaiting_enrichment"
        result["short_reason"] = "Job description is too weak for provider scoring; awaiting stronger enrichment."
        result["top_gaps"] = _normalize_string_list(
            [str(fallback_reason or "").strip(), *list(result.get("top_gaps") or [])],
            limit=5,
        )
        result["threshold_eligible"] = False
        result["awaiting_enrichment"] = True
        return result

    def _fallback_result(
        self,
        job: JobPost,
        *,
        candidate: Candidate | None,
        search_profile: dict[str, Any],
        fallback_reason: str,
    ) -> dict[str, Any]:
        tracks = (
            self.session.query(ResumeTrack)
            .filter(ResumeTrack.active.is_(True))
            .order_by(ResumeTrack.title.asc())
            .all()
        )
        scored = score_tracks_for_job(job, tracks) if tracks else []
        top = scored[0] if scored else {}
        language_assessment = self._language_assessment(
            detect_job_languages(str(job.description or "")),
            search_profile.get("languages"),
        )
        seniority_assessment = self._seniority_assessment(
            title=str(job.title or ""),
            description=str(job.description or ""),
            target_seniority=str(search_profile.get("seniority") or settings.target_job_seniority or "junior"),
        )
        fit_score = float(top.get("score") or 0)
        if language_assessment["label"] == "stretch":
            fit_score -= 6
        elif language_assessment["label"] == "risk":
            fit_score -= 14
        if seniority_assessment["label"] == "stretch":
            fit_score -= 8
        elif seniority_assessment["label"] == "risk":
            fit_score -= 16

        matched_keywords = _normalize_string_list(top.get("matched_keywords"), limit=6)
        top_gaps: list[str] = []
        if candidate is None:
            top_gaps.append("No active candidate was available for provider-based fit scoring.")
        if language_assessment["label"] == "risk":
            top_gaps.append(language_assessment["reason"])
        if seniority_assessment["label"] == "risk":
            top_gaps.append(seniority_assessment["reason"])

        return {
            "fit_score": _clamp_score(fit_score),
            "score_source": "fallback",
            "provider_mode": normalize_provider_mode(getattr(settings, "llm_provider_mode", "openai")),
            "matched_evidence": (
                [f"Matched keywords: {', '.join(matched_keywords)}"] if matched_keywords else []
            ),
            "top_gaps": top_gaps[:5],
            "language_assessment": language_assessment,
            "seniority_assessment": seniority_assessment,
            "short_reason": fallback_reason,
            "threshold_eligible": True,
            "awaiting_enrichment": False,
        }

    def _persist(self, job: JobPost, candidate_key: str, result: dict[str, Any], *, commit: bool) -> None:
        metadata = dict(job.extracted_metadata or {})
        fit_map = dict(metadata.get(CANDIDATE_FIT_META_KEY) or {})
        stored = dict(result)
        stored["scored_at"] = stored.get("scored_at") or _iso_now()
        fit_map[str(candidate_key)] = stored
        metadata[CANDIDATE_FIT_META_KEY] = fit_map
        job.extracted_metadata = metadata
        self.session.add(job)
        if commit:
            self.session.commit()
            self.session.refresh(job)
        else:
            self.session.flush()

    def _resolve_job(self, job: JobPost | UUID | str) -> JobPost | None:
        if isinstance(job, JobPost):
            return job
        if isinstance(job, str):
            try:
                job = UUID(job)
            except ValueError:
                return None
        return self.session.get(JobPost, job)

    def _search_profile(self, candidate: Candidate | None) -> dict[str, Any]:
        match_profile = None
        if candidate is not None:
            match_profile = (
                self.session.query(MatchProfile)
                .filter(MatchProfile.candidate_id == str(candidate.id))
                .first()
            )
        roles = normalize_role_list(
            settings.jobspy_discover_queries
            or (match_profile.target_roles if match_profile is not None else [])
        )
        country = primary_search_country(
            getattr(settings, "job_search_countries", None)
            or ((match_profile.location_preferences or {}).get("preferred_countries") if match_profile else None),
            settings.jobspy_discover_location or "Italy",
        )
        languages = normalize_job_language_preferences(
            getattr(settings, "job_search_languages", None)
            or (candidate.spoken_languages if candidate is not None else [])
        )
        return {
            "country": country,
            "roles": roles,
            "seniority": str(getattr(settings, "target_job_seniority", "junior") or "junior"),
            "languages": languages,
        }

    def _fact_summary(self, candidate: Candidate | None, search_profile: dict[str, Any]) -> str:
        if candidate is None:
            return "No candidate facts available."
        summary = FactSheetRenderer(session=self.session).render_short_summary(candidate).strip()
        extra_lines = []
        if search_profile.get("roles"):
            extra_lines.append("Target roles: " + ", ".join(search_profile["roles"]))
        if search_profile.get("country"):
            extra_lines.append(f"Target country: {search_profile['country']}")
        if search_profile.get("languages"):
            extra_lines.append(
                "Working languages: "
                + ", ".join(f"{row['name']} ({row['label']})" for row in search_profile["languages"])
            )
        extra_text = "\n".join(extra_lines).strip()
        return f"{summary}\n{extra_text}".strip()

    @staticmethod
    def _cache_key(*, fact_summary: str, provider_mode: str, search_profile: dict[str, Any]) -> str:
        payload = {
            "provider_mode": provider_mode,
            "fact_summary": fact_summary,
            "search_profile": search_profile,
        }
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _language_assessment(
        detected_languages: list[dict[str, Any]],
        preferences: object,
    ) -> dict[str, str]:
        normalized = normalize_job_language_preferences(preferences)
        if not detected_languages:
            return {"label": "unknown", "reason": "The job description language could not be detected."}
        if not normalized:
            return {"label": "unknown", "reason": "No candidate language preferences were configured."}

        by_name = {row["name"].casefold(): row for row in normalized}
        matched = next((item for item in detected_languages if item["name"].casefold() in by_name), None)
        if matched is None:
            return {
                "label": "risk",
                "reason": f"Detected job language '{detected_languages[0]['name']}' is not in the configured candidate language set.",
            }

        level_rank = language_level_rank(by_name[matched["name"].casefold()]["level"])
        if level_rank >= 3:
            return {"label": "good", "reason": f"{matched['name']} is configured at a strong working level."}
        if level_rank == 2:
            return {"label": "stretch", "reason": f"{matched['name']} is configured at a working level and may need support."}
        return {"label": "risk", "reason": f"{matched['name']} is configured at a basic level only."}

    @staticmethod
    def _seniority_assessment(*, title: str, description: str, target_seniority: str) -> dict[str, str]:
        text = f" {title} {description} ".casefold()
        seniority = str(target_seniority or "junior").strip().lower()
        has_senior = any(term in text for term in _SENIOR_TITLE_TERMS) or bool(
            re.search(r"\b([4-9]|[1-9][0-9])\+?\s+years?\b", text)
        )
        has_entry = any(term in text for term in _ENTRY_TITLE_TERMS)

        if seniority == "any":
            return {"label": "aligned", "reason": "Seniority is unrestricted for this search profile."}
        if seniority in {"intern", "junior"}:
            if has_senior:
                return {"label": "risk", "reason": "The job appears to ask for senior-level experience."}
            if has_entry:
                return {"label": "aligned", "reason": "The job reads like an entry-level or junior role."}
            return {"label": "stretch", "reason": "The job level is not explicit, so the fit may need review."}
        if seniority == "mid":
            if has_entry:
                return {"label": "stretch", "reason": "The job looks more junior than the configured target level."}
            return {"label": "aligned", "reason": "The job level is compatible with a mid-level target."}
        if seniority == "senior":
            if has_senior:
                return {"label": "aligned", "reason": "The job explicitly signals a senior-level scope."}
            return {"label": "stretch", "reason": "The job does not clearly indicate senior-level scope."}
        return {"label": "unknown", "reason": "Seniority fit could not be determined."}


def _normalize_string_list(value: object, *, limit: int) -> list[str]:
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, list):
        values = [str(item).strip() for item in value if str(item).strip()]
    else:
        values = []
    return values[:limit]


def _normalize_assessment(value: object, *, default: dict[str, str]) -> dict[str, str]:
    if isinstance(value, dict):
        label = str(value.get("label") or default.get("label") or "unknown").strip().lower()
        if label not in {"good", "stretch", "risk", "unknown", "aligned"}:
            label = str(default.get("label") or "unknown")
        reason = str(value.get("reason") or default.get("reason") or "").strip() or str(default.get("reason") or "")
        return {"label": label, "reason": reason}
    return dict(default)


def _normalize_short_reason(value: object) -> str:
    text = str(value or "").strip()
    return text or "Candidate-fit score generated from the active provider."


def _clamp_score(value: object) -> int:
    try:
        score = int(round(float(value)))
    except (TypeError, ValueError):
        score = 0
    return max(0, min(100, score))


def _normalize_provider_fit_score(value: object, *, matched_evidence: list[str]) -> int:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0
    if 0 < numeric <= 10 and matched_evidence:
        numeric *= 10
    return _clamp_score(numeric)


def _iso_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _title_matches_search_roles(title: str, roles: object) -> bool:
    title_text = f" {str(title or '').casefold()} "
    for raw_role in normalize_role_list(roles):
        role_text = str(raw_role or "").strip().casefold()
        if not role_text:
            continue
        if role_text in title_text:
            return True
        tokens = [
            token for token in re.split(r"[^a-z0-9]+", role_text)
            if token and len(token) >= 2 and token not in _ROLE_TOKEN_STOPWORDS
        ]
        if not tokens:
            continue
        required_overlap = 1 if len(tokens) == 1 else 2
        overlap = sum(1 for token in tokens if f" {token} " in title_text)
        if overlap >= required_overlap:
            return True
    return False
