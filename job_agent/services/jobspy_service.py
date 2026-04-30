"""JobSpy integration for active LinkedIn job discovery."""

from __future__ import annotations

from datetime import datetime, timezone
import importlib.metadata
import logging
import re
import time
from typing import Any, Callable

from sqlalchemy.orm import Session

from job_agent.config import get_settings
from job_agent.models import JobPost, JobTrackScore, ResumeTrack
from job_agent.search_preferences import detect_job_languages, job_matches_language_preferences, normalize_role_list, primary_search_country
from job_agent.services.discovery_hub import (
    find_existing_job,
    merge_duplicate_job,
    record_discovery_event,
    source_profile,
    stamp_job_metadata,
)
from job_agent.services.matching import score_tracks_for_job

logger = logging.getLogger(__name__)
settings = get_settings()
_ROLE_TOKEN_STOPWORDS = {"and", "or", "for", "with", "the", "a", "an", "intern", "junior", "senior"}
_SENIOR_MARKERS = (" senior ", " lead ", " principal ", " staff ", " manager ", " director ", " head ")
_ENTRY_MARKERS = (" intern ", " internship ", " stage ", " trainee ", " graduate ", " junior ", " entry level ")


class JobSpyDiscoveryError(RuntimeError):
    """Explicit discovery failure for task-based discovery runs."""


def _build_seniority_query_suffix(target_seniority: str) -> str:
    """
    Append seniority-related terms to job queries to bias results toward
    the configured level. Returns empty string for 'mid', 'senior', 'any'.
    """
    if target_seniority == "intern":
        return " internship OR stage OR tirocinio"
    if target_seniority == "junior":
        return ' junior OR "entry level" OR graduate OR "new grad"'
    return ""


class JobSpyService:
    """Wraps jobspy library for LinkedIn public job board discovery."""

    @staticmethod
    def _resolve_scrape_jobs():
        import jobspy as jobspy_module

        distributions = {
            str(name).casefold()
            for name in importlib.metadata.packages_distributions().get("jobspy", [])
        }
        if "python-jobspy" not in distributions:
            raise ImportError(
                "The imported 'jobspy' module does not come from python-jobspy. "
                "Install python-jobspy in the ML environment and remove conflicting jobspy packages."
            )
        scrape_jobs = getattr(jobspy_module, "scrape_jobs", None)
        if scrape_jobs is None:
            raise ImportError("python-jobspy is installed, but scrape_jobs is missing.")
        return scrape_jobs

    def discover(
        self,
        query: str,
        location: str = "Italy",
        session: Session | None = None,
        limit: int | None = None,
        sources: list[str] | None = None,
    ) -> int:
        """
        Search for jobs using JobSpy, deduplicate against DB, create JobPost records.
        Returns count of new jobs ingested.
        """
        if not settings.use_jobspy:
            logger.info("JobSpy is disabled (USE_JOBSPY=false). Skipping discovery.")
            return 0
        if session is None:
            raise ValueError("A database session is required for JobSpy discovery.")

        try:
            scrape_jobs = self._resolve_scrape_jobs()
        except ImportError:
            logger.error("python-jobspy is not installed correctly. Run the project install command again.")
            return 0

        limit = limit or settings.jobspy_default_limit
        sources = sources or ["linkedin"]
        suffix = _build_seniority_query_suffix(settings.target_job_seniority)
        full_query = f"{query}{suffix}"
        location = location or primary_search_country(settings.job_search_countries, settings.jobspy_discover_location)

        logger.info(
            "JobSpy search: query=%r location=%r sources=%s limit=%d",
            full_query,
            location,
            sources,
            limit,
        )

        try:
            dataframe = scrape_jobs(
                site_name=sources,
                search_term=full_query,
                location=location,
                results_wanted=limit,
                country_indeed="Italy" if "italy" in location.lower() else None,
            )
        except Exception as exc:
            logger.error("JobSpy scrape failed: %s", exc)
            return 0

        if dataframe is None or dataframe.empty:
            logger.info("JobSpy returned no results for query=%r", full_query)
            return 0

        logger.info("JobSpy returned %d results", len(dataframe))

        tracks = session.query(ResumeTrack).filter_by(active=True).all()
        new_count = 0

        for _, row in dataframe.iterrows():
            row_data = row if isinstance(row, dict) else dict(row)
            url = str(row_data.get("job_url") or row_data.get("url") or "")
            if not url:
                continue

            title = str(row_data.get("title") or "Unknown")
            company = str(row_data.get("company") or "Unknown")
            location_str = str(row_data.get("location") or location)
            description = str(row_data.get("description") or "")
            detected_job_languages = detect_job_languages(description)
            source_meta = source_profile("jobspy_linkedin", url)

            if not job_matches_language_preferences(description, settings.job_search_languages):
                logger.info(
                    "Skipping job outside allowed language set: %s at %s (%s)",
                    title,
                    company,
                    ", ".join(str(item["name"]) for item in detected_job_languages) or "unknown",
                )
                continue

            dedupe = find_existing_job(
                session,
                canonical_apply_url=url,
                source_url=url,
                company=company,
                title=title,
                location=location_str,
            )
            if dedupe.job is not None:
                merge_duplicate_job(
                    dedupe.job,
                    {
                        "description": description,
                        "canonical_apply_url": url,
                        "source_url": url,
                        "last_seen_at": datetime.now(timezone.utc),
                    },
                )
                stamp_job_metadata(
                    dedupe.job,
                    source_name="jobspy_linkedin",
                    source_url=url,
                    canonical_apply_url=url,
                    company=company,
                    title=title,
                    location=location_str,
                    canonical_reason=dedupe.reason,
                )
                record_discovery_event(
                    session,
                    source_name="jobspy_linkedin",
                    source_url=url,
                    outcome="duplicate",
                    reason=dedupe.reason,
                    acquisition_path=str(source_meta["path"]),
                    canonical_key=dedupe.canonical_key,
                    job_post_id=dedupe.job.id,
                )
                continue

            post = JobPost(
                source_name="jobspy_linkedin",
                source_url=url,
                canonical_apply_url=url,
                title=title,
                company=company,
                location=location_str,
                description=description,
                extracted_metadata={"detected_job_languages": detected_job_languages} if detected_job_languages else {},
                queue_state="new",
                status="new",
                created_at=datetime.now(timezone.utc),
                last_seen_at=datetime.now(timezone.utc),
            )
            stamp_job_metadata(
                post,
                source_name="jobspy_linkedin",
                source_url=url,
                canonical_apply_url=url,
                company=company,
                title=title,
                location=location_str,
                canonical_reason="new_import",
            )
            session.add(post)
            session.flush()

            if tracks:
                scored = score_tracks_for_job(post, tracks)
                for result in scored:
                    session.add(
                        JobTrackScore(
                            job_post_id=post.id,
                            resume_track_id=result["track_id"],
                            score=result["score"],
                            matched_keywords=result["matched_keywords"],
                        )
                    )

            new_count += 1
            record_discovery_event(
                session,
                source_name="jobspy_linkedin",
                source_url=url,
                outcome="ingested",
                reason="new_import",
                acquisition_path=str(source_meta["path"]),
                canonical_key=str(dict(post.extracted_metadata or {}).get("canonical_key") or ""),
                job_post_id=post.id,
            )
            time.sleep(0.1)

        session.commit()
        logger.info("JobSpy: ingested %d new jobs", new_count)
        time.sleep(settings.jobspy_request_delay)
        return new_count

    def discover_for_roles(
        self,
        *,
        roles: list[str],
        location: str,
        selected_country: str,
        seniority: str,
        session: Session,
        limit: int | None = None,
        sources: list[str] | None = None,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, int]:
        if not settings.use_jobspy:
            raise JobSpyDiscoveryError(
                "Job discovery is disabled. Enable Automatic JobSpy in Settings > Job Discovery first."
            )
        if session is None:
            raise JobSpyDiscoveryError("A database session is required for JobSpy discovery.")

        try:
            scrape_jobs = self._resolve_scrape_jobs()
        except ImportError as exc:
            raise JobSpyDiscoveryError(
                "python-jobspy is not installed correctly in the ML environment. Reinstall dependencies and retry."
            ) from exc

        normalized_roles = normalize_role_list(roles)
        if not normalized_roles:
            raise JobSpyDiscoveryError("No desired roles configured for discovery.")

        limit = limit or settings.jobspy_default_limit
        sources = sources or ["linkedin"]
        counts = {
            "roles_queried": 0,
            "raw_hits": 0,
            "ats_sources_scanned": 0,
            "ats_raw_hits": 0,
            "duplicates": 0,
            "rejected_by_country": 0,
            "rejected_by_role": 0,
            "rejected_by_seniority": 0,
            "queued_for_scoring": 0,
            "scored_jobs": 0,
            "saved_jobs": 0,
            "visible_after_threshold": 0,
            "visible_in_default_view": 0,
        }
        saved_job_ids: list[str] = []

        discovered_rows: list[dict[str, Any]] = []
        if progress_callback:
            progress_callback(
                {
                    "stage": "querying",
                    "message": "Querying JobSpy for the selected discovery roles.",
                    "counts": counts,
                }
            )
        for index, role in enumerate(normalized_roles, start=1):
            full_query = f"{role}{_build_seniority_query_suffix(seniority)}"
            dataframe = scrape_jobs(
                site_name=sources,
                search_term=full_query,
                location=location,
                results_wanted=limit,
                country_indeed="Italy" if "italy" in location.lower() else None,
            )
            role_hits = 0 if dataframe is None or dataframe.empty else len(dataframe)
            counts["roles_queried"] = index
            counts["raw_hits"] += role_hits
            if dataframe is not None and not dataframe.empty:
                for _, row in dataframe.iterrows():
                    row_data = row if isinstance(row, dict) else dict(row)
                    row_data["_discovery_role"] = role
                    discovered_rows.append(row_data)
            if progress_callback:
                progress_callback(
                    {
                        "stage": "querying",
                        "message": f"Fetched {role_hits} hits for role '{role}'.",
                        "counts": counts,
                    }
                )

        tracks = session.query(ResumeTrack).filter_by(active=True).all()
        seen_urls: set[str] = set()
        if progress_callback:
            progress_callback(
                {
                    "stage": "deduplicating",
                    "message": "Deduplicating results and preparing basic filters.",
                    "counts": counts,
                }
            )
        for row_data in discovered_rows:
            url = str(row_data.get("job_url") or row_data.get("url") or "").strip()
            if not url:
                counts["rejected_by_role"] += 1
                continue
            if url in seen_urls:
                counts["duplicates"] += 1
                continue
            seen_urls.add(url)

            title = str(row_data.get("title") or "Unknown")
            company = str(row_data.get("company") or "Unknown")
            location_str = str(row_data.get("location") or location)
            description = str(row_data.get("description") or "")
            role_query = str(row_data.get("_discovery_role") or "")
            source_meta = source_profile("jobspy_linkedin", url)

            if not self._passes_country_filter(location_str, selected_country):
                counts["rejected_by_country"] += 1
                continue
            if progress_callback and (counts["rejected_by_country"] + counts["rejected_by_role"] + counts["rejected_by_seniority"] == 0):
                progress_callback(
                    {
                        "stage": "filtering",
                        "message": "Applying country, role, and seniority filters.",
                        "counts": counts,
                    }
                )
            if not self._passes_role_filter(title=title, description=description, role_query=role_query, all_roles=normalized_roles):
                counts["rejected_by_role"] += 1
                continue
            if not self._passes_seniority_filter(title=title, description=description, target_seniority=seniority):
                counts["rejected_by_seniority"] += 1
                continue

            dedupe = find_existing_job(
                session,
                canonical_apply_url=url,
                source_url=url,
                company=company,
                title=title,
                location=location_str,
            )
            if dedupe.job is not None:
                merge_duplicate_job(
                    dedupe.job,
                    {
                        "description": description,
                        "canonical_apply_url": url,
                        "source_url": url,
                        "last_seen_at": datetime.now(timezone.utc),
                    },
                )
                stamp_job_metadata(
                    dedupe.job,
                    source_name="jobspy_linkedin",
                    source_url=url,
                    canonical_apply_url=url,
                    company=company,
                    title=title,
                    location=location_str,
                    canonical_reason=dedupe.reason,
                )
                record_discovery_event(
                    session,
                    source_name="jobspy_linkedin",
                    source_url=url,
                    outcome="duplicate",
                    reason=dedupe.reason,
                    acquisition_path=str(source_meta["path"]),
                    canonical_key=dedupe.canonical_key,
                    job_post_id=dedupe.job.id,
                )
                counts["duplicates"] += 1
                continue

            counts["queued_for_scoring"] += 1
            detected_job_languages = detect_job_languages(description)
            post = JobPost(
                source_name="jobspy_linkedin",
                source_url=url,
                canonical_apply_url=url,
                title=title,
                company=company,
                country=selected_country,
                location=location_str,
                seniority=seniority,
                description=description,
                extracted_metadata={"detected_job_languages": detected_job_languages} if detected_job_languages else {},
                queue_state="new",
                status="new",
                created_at=datetime.now(timezone.utc),
                last_seen_at=datetime.now(timezone.utc),
            )
            stamp_job_metadata(
                post,
                source_name="jobspy_linkedin",
                source_url=url,
                canonical_apply_url=url,
                company=company,
                title=title,
                location=location_str,
                canonical_reason="new_import",
            )
            session.add(post)
            session.flush()

            if tracks:
                scored = score_tracks_for_job(post, tracks)
                for result in scored:
                    session.add(
                        JobTrackScore(
                            job_post_id=post.id,
                            resume_track_id=result["track_id"],
                            score=result["score"],
                            matched_keywords=result["matched_keywords"],
                        )
                    )

            counts["saved_jobs"] += 1
            saved_job_ids.append(str(post.id))
            record_discovery_event(
                session,
                source_name="jobspy_linkedin",
                source_url=url,
                outcome="ingested",
                reason="new_import",
                acquisition_path=str(source_meta["path"]),
                canonical_key=str(dict(post.extracted_metadata or {}).get("canonical_key") or ""),
                job_post_id=post.id,
            )

        session.commit()
        if progress_callback:
            progress_callback(
                {
                    "stage": "saving",
                    "message": "Saved filtered JobSpy results for candidate-fit scoring.",
                    "counts": counts,
                }
            )
        time.sleep(settings.jobspy_request_delay)
        return {**counts, "saved_job_ids": saved_job_ids}

    def _passes_country_filter(self, location_text: str, selected_country: str) -> bool:
        country = str(selected_country or "").strip().casefold()
        if not country:
            return True
        location_lower = f" {str(location_text or '').casefold()} "
        return f" {country} " in location_lower

    def _passes_role_filter(
        self,
        *,
        title: str,
        description: str,
        role_query: str,
        all_roles: list[str],
    ) -> bool:
        title_text = f" {title} ".casefold()
        description_text = f" {description} ".casefold()
        candidates = [role_query] + list(all_roles)
        for role in candidates:
            role_text = str(role or "").strip().casefold()
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
            title_overlap = sum(1 for token in tokens if f" {token} " in title_text)
            if title_overlap >= required_overlap:
                return True
            description_overlap = sum(1 for token in tokens if f" {token} " in description_text)
            if title_overlap >= 1 and description_overlap >= required_overlap:
                return True
        return False

    def _passes_seniority_filter(self, *, title: str, description: str, target_seniority: str) -> bool:
        seniority = str(target_seniority or "junior").strip().lower()
        text = f" {title} {description} ".casefold()
        has_senior_marker = any(marker in text for marker in _SENIOR_MARKERS) or bool(
            re.search(r"\b([4-9]|[1-9][0-9])\+?\s+years?\b", text)
        )
        has_entry_marker = any(marker in text for marker in _ENTRY_MARKERS)

        if seniority == "any":
            return True
        if seniority in {"intern", "junior"}:
            return not has_senior_marker
        if seniority == "mid":
            return not (" intern " in text or " internship " in text)
        if seniority == "senior":
            return has_senior_marker or not has_entry_marker
        return True
