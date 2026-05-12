"""JobSpy integration for active LinkedIn job discovery."""

from __future__ import annotations

from datetime import datetime, timezone
import importlib.metadata
import logging
import re
import time
from types import ModuleType
from typing import Any, Callable

from sqlalchemy.orm import Session

from job_agent.config import get_settings
from job_agent.models import JobPost, JobTrackScore, ResumeTrack
from job_agent.search_preferences import (
    detect_job_languages,
    job_matches_language_preferences,
    location_matches_region,
    normalize_role_list,
    normalize_search_region,
    primary_search_country,
)
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

        scrape_jobs = getattr(jobspy_module, "scrape_jobs", None)
        if scrape_jobs is None:
            raise ImportError("python-jobspy is installed, but scrape_jobs is missing.")

        if isinstance(jobspy_module, ModuleType):
            distributions = {
                str(name).casefold()
                for name in importlib.metadata.packages_distributions().get("jobspy", [])
            }
            if "python-jobspy" not in distributions:
                raise ImportError(
                    "The imported 'jobspy' module does not come from python-jobspy. "
                    "Install python-jobspy in the ML environment and remove conflicting jobspy packages."
                )
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
        selected_region = normalize_search_region(settings.job_search_region)

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

            if not location_matches_region(location_str, selected_region):
                continue

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
                    search_country=primary_search_country(settings.job_search_countries, settings.jobspy_discover_location),
                    search_region=selected_region,
                    search_location=location,
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
                search_country=primary_search_country(settings.job_search_countries, settings.jobspy_discover_location),
                search_region=selected_region,
                search_location=location,
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
        selected_region: str = "",
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
            "rejected_by_region": 0,
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
            if not location_matches_region(location_str, selected_region):
                counts["rejected_by_region"] += 1
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
                    search_country=selected_country,
                    search_region=selected_region,
                    search_location=location,
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
                search_country=selected_country,
                search_region=selected_region,
                search_location=location,
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

    # ── Phase E2: Selective second-pass detail enrichment ─────────────────

    def detail_enrich_survivors(
        self,
        *,
        saved_job_ids: list[str],
        session: Session,
        selected_country: str = "",
        seniority: str = "junior",
        roles: list[str] | None = None,
        limit: int | None = None,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """Selective second-pass detail enrichment for JobSpy-origin jobs.

        Uses ``python-jobspy`` with ``linkedin_fetch_description=True`` on
        a bounded subset of survivors that have weak JDs and no strong ATS
        description already present.

        Returns a dict with counts of enriched, skipped, and failed jobs.
        """
        from job_agent.services.job_description_quality import (
            evaluate_job_description,
            JD_QUALITY_META_KEY,
        )

        result = {
            "detail_enrichment_attempted": 0,
            "detail_enrichment_improved": 0,
            "detail_enrichment_skipped": 0,
            "detail_enrichment_failed": 0,
        }

        if not settings.jobspy_detail_enrichment_enabled:
            logger.info("JobSpy detail enrichment is disabled (JOBSPY_DETAIL_ENRICHMENT_ENABLED=false).")
            return result

        cap = limit or settings.jobspy_detail_enrichment_limit
        if cap <= 0:
            return result

        # ── Select survivors deterministically ────────────────────────────
        candidates: list[JobPost] = []
        for job_id_str in saved_job_ids:
            from uuid import UUID as _UUID
            try:
                job_uuid = _UUID(str(job_id_str))
            except (TypeError, ValueError):
                continue
            job = session.get(JobPost, job_uuid)
            if job is None:
                continue

            # Only enrich JobSpy-origin jobs (not ATS or manual)
            source = str(job.source_name or "").casefold()
            if "jobspy" not in source and "linkedin" not in source:
                result["detail_enrichment_skipped"] += 1
                continue

            # Skip jobs that already have a strong ATS or company-page description
            jd_quality = evaluate_job_description(
                description=job.description,
                source_name=job.source_name,
                source_url=job.source_url,
                company_url=job.company_url,
            )
            if jd_quality.get("ready_for_provider_scoring"):
                result["detail_enrichment_skipped"] += 1
                continue

            candidates.append(job)

        # ── Deterministic priority sort ───────────────────────────────────
        # Prefer: correct country > role match > seniority compat > weakest JD first
        normalized_roles = normalize_role_list(roles or [])

        def _priority_key(job: JobPost) -> tuple[int, int, int, int]:
            # Country match (0 = match, 1 = no match)
            country_match = 0 if self._passes_country_filter(
                str(job.location or ""), selected_country
            ) else 1

            # Role match (0 = match, 1 = no match)
            role_match = 0 if (
                not normalized_roles or self._passes_role_filter(
                    title=str(job.title or ""),
                    description=str(job.description or ""),
                    role_query=normalized_roles[0] if normalized_roles else "",
                    all_roles=normalized_roles,
                )
            ) else 1

            # Seniority compatibility (0 = compatible, 1 = not)
            seniority_match = 0 if self._passes_seniority_filter(
                title=str(job.title or ""),
                description=str(job.description or ""),
                target_seniority=seniority,
            ) else 1

            # JD quality (lower = weaker = higher priority for enrichment)
            quality = evaluate_job_description(
                description=job.description,
                source_name=job.source_name,
                source_url=job.source_url,
                company_url=job.company_url,
            )
            jd_score = int(quality.get("score") or 0)

            return (country_match, role_match, seniority_match, jd_score)

        candidates.sort(key=_priority_key)
        selected = candidates[:cap]

        if not selected:
            logger.info("No JobSpy jobs qualify for second-pass detail enrichment.")
            return result

        if progress_callback:
            progress_callback({
                "stage": "detail_enrichment",
                "message": f"Starting selective detail enrichment for {len(selected)} of {len(candidates)} eligible jobs.",
                "counts": result,
            })

        # ── Re-fetch with linkedin_fetch_description=True ─────────────────
        try:
            scrape_jobs = self._resolve_scrape_jobs()
        except ImportError:
            logger.error("python-jobspy not available for detail enrichment.")
            result["detail_enrichment_failed"] = len(selected)
            return result

        for index, job in enumerate(selected, start=1):
            result["detail_enrichment_attempted"] += 1
            source_url = str(job.source_url or "").strip()
            if not source_url:
                result["detail_enrichment_failed"] += 1
                continue

            try:
                detail_df = scrape_jobs(
                    site_name=["linkedin"],
                    search_term=str(job.title or ""),
                    location=str(job.location or selected_country or ""),
                    results_wanted=3,
                    linkedin_fetch_description=True,
                )
            except Exception as exc:
                logger.warning(
                    "Detail enrichment scrape failed for job %s: %s", job.id, exc
                )
                result["detail_enrichment_failed"] += 1
                time.sleep(settings.jobspy_request_delay)
                continue

            if detail_df is None or (hasattr(detail_df, "empty") and detail_df.empty):
                result["detail_enrichment_failed"] += 1
                time.sleep(settings.jobspy_request_delay)
                continue

            # Find the matching row by URL or best title match
            best_description = ""
            best_url = ""
            for _, row in detail_df.iterrows():
                row_data = row if isinstance(row, dict) else dict(row)
                row_url = str(row_data.get("job_url") or row_data.get("url") or "")
                row_desc = str(row_data.get("description") or "")

                if row_url == source_url and len(row_desc) > len(best_description):
                    best_description = row_desc
                    best_url = row_url
                elif not best_description and len(row_desc) > 120:
                    best_description = row_desc
                    best_url = row_url

            if not best_description or len(best_description) <= len(str(job.description or "")):
                result["detail_enrichment_failed"] += 1
                time.sleep(settings.jobspy_request_delay)
                continue

            # ── Persist richer data and provenance ────────────────────────
            job.description = best_description
            if best_url and not job.canonical_apply_url:
                job.canonical_apply_url = best_url
            job.last_seen_at = datetime.now(timezone.utc)

            # Re-evaluate JD quality after enrichment
            updated_quality = evaluate_job_description(
                description=job.description,
                source_name=job.source_name,
                source_url=job.source_url,
                company_url=job.company_url,
            )
            metadata = dict(job.extracted_metadata or {})
            metadata[JD_QUALITY_META_KEY] = updated_quality
            metadata["jobspy_detail_enriched"] = True
            metadata["jobspy_detail_enriched_at"] = datetime.now(timezone.utc).isoformat()
            if updated_quality.get("source_kind"):
                metadata.setdefault("jd_quality", {})
                if isinstance(metadata["jd_quality"], dict):
                    metadata["jd_quality"]["source_kind"] = "linkedin_enriched"
            if best_url:
                metadata["direct_job_url"] = best_url
            job.extracted_metadata = metadata

            # Update enrichment status
            if updated_quality.get("ready_for_provider_scoring"):
                job.enrichment_status = "ok"
            else:
                job.enrichment_status = "partial"

            session.add(job)
            result["detail_enrichment_improved"] += 1

            if progress_callback:
                progress_callback({
                    "stage": "detail_enrichment",
                    "message": f"Detail-enriched {index} of {len(selected)} jobs.",
                    "counts": result,
                })

            time.sleep(settings.jobspy_request_delay)

        session.flush()
        logger.info(
            "JobSpy detail enrichment: attempted=%d improved=%d skipped=%d failed=%d",
            result["detail_enrichment_attempted"],
            result["detail_enrichment_improved"],
            result["detail_enrichment_skipped"],
            result["detail_enrichment_failed"],
        )
        return result
