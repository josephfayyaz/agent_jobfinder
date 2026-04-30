from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any, Callable

from sqlalchemy.orm import Session

from job_agent.models import CareerPageSource, JobPost, JobTrackScore, ResumeTrack
from job_agent.services.ats_scanner import AtsApiScanner
from job_agent.services.discovery_hub import (
    find_existing_job,
    merge_duplicate_job,
    record_discovery_event,
    source_profile,
    stamp_job_metadata,
)
from job_agent.services.jobspy_service import JobSpyService
from job_agent.services.matching import score_tracks_for_job

logger = logging.getLogger(__name__)


class AtsDiscoveryService:
    """Discover jobs from configured ATS feeds and normalize them into JobPost rows."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.scanner = AtsApiScanner()
        self.filters = JobSpyService()

    def discover_active_sources(
        self,
        *,
        roles: list[str],
        selected_country: str,
        seniority: str,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        counts = {
            "ats_sources_scanned": 0,
            "raw_hits": 0,
            "ats_raw_hits": 0,
            "duplicates": 0,
            "rejected_by_country": 0,
            "rejected_by_role": 0,
            "rejected_by_seniority": 0,
            "queued_for_scoring": 0,
            "saved_jobs": 0,
        }
        saved_job_ids: list[str] = []
        tracks = self.session.query(ResumeTrack).filter_by(active=True).all()
        sources = (
            self.session.query(CareerPageSource)
            .filter(
                CareerPageSource.active.is_(True),
                CareerPageSource.ats_type.is_not(None),
                CareerPageSource.ats_slug.is_not(None),
                CareerPageSource.country == selected_country,
            )
            .order_by(CareerPageSource.company.asc())
            .all()
        )

        if not sources:
            return {**counts, "saved_job_ids": saved_job_ids}

        seen_urls: set[str] = set()
        for index, source in enumerate(sources, start=1):
            counts["ats_sources_scanned"] = index
            if progress_callback:
                progress_callback(
                    {
                        "stage": "querying_ats",
                        "message": f"Querying {source.company} via {source.ats_type} ATS feed.",
                        "counts": counts,
                    }
                )
            source_name = f"ats_{str(source.ats_type or '').strip().lower()}"
            source_meta = source_profile(source_name, str(source.career_url or ""), ats_type=source.ats_type)
            try:
                jobs = self.scanner.fetch_jobs(str(source.ats_type or ""), str(source.ats_slug or ""))
            except Exception as exc:
                logger.warning(
                    "ATS discovery skipped %s (%s:%s): %s",
                    source.company,
                    source.ats_type,
                    source.ats_slug,
                    exc,
                )
                record_discovery_event(
                    self.session,
                    source_name=source_name,
                    source_url=str(source.career_url or ""),
                    outcome="failed",
                    reason=str(exc),
                    acquisition_path=str(source_meta["path"]),
                    canonical_key=f"{source_name}:{source.id}",
                    job_post_id=None,
                )
                continue
            counts["raw_hits"] += len(jobs)
            counts["ats_raw_hits"] += len(jobs)

            for job in jobs:
                url = str(job.get("url") or "").strip()
                title = str(job.get("title") or "").strip()[:200]
                location = str(job.get("location") or "").strip() or source.country
                description = str(job.get("description") or "").strip()
                if not url or not title:
                    counts["rejected_by_role"] += 1
                    continue
                if url in seen_urls:
                    counts["duplicates"] += 1
                    continue
                seen_urls.add(url)

                if not self.filters._passes_country_filter(location, selected_country):
                    counts["rejected_by_country"] += 1
                    continue
                if not self.filters._passes_role_filter(
                    title=title,
                    description=description,
                    role_query="",
                    all_roles=roles,
                ):
                    counts["rejected_by_role"] += 1
                    continue
                if not self.filters._passes_seniority_filter(
                    title=title,
                    description=description,
                    target_seniority=seniority,
                ):
                    counts["rejected_by_seniority"] += 1
                    continue

                dedupe = find_existing_job(
                    self.session,
                    canonical_apply_url=url,
                    source_url=url,
                    company=source.company,
                    title=title,
                    location=location,
                )
                source_meta = source_profile(source_name, url, ats_type=source.ats_type)
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
                        source_name=source_name,
                        source_url=url,
                        canonical_apply_url=url,
                        company=source.company,
                        title=title,
                        location=location,
                        ats_type=source.ats_type,
                        canonical_reason=dedupe.reason,
                    )
                    record_discovery_event(
                        self.session,
                        source_name=source_name,
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
                post = JobPost(
                    source_name=source_name,
                    source_url=url,
                    canonical_apply_url=url,
                    title=title,
                    company=source.company,
                    location=location,
                    country=selected_country,
                    seniority=seniority,
                    description=description,
                    queue_state="new",
                    status="new",
                    created_at=datetime.now(timezone.utc),
                    last_seen_at=datetime.now(timezone.utc),
                )
                stamp_job_metadata(
                    post,
                    source_name=source_name,
                    source_url=url,
                    canonical_apply_url=url,
                    company=source.company,
                    title=title,
                    location=location,
                    ats_type=source.ats_type,
                    canonical_reason="new_import",
                )
                self.session.add(post)
                self.session.flush()

                if tracks:
                    scored = score_tracks_for_job(post, tracks)
                    for result in scored:
                        self.session.add(
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
                    self.session,
                    source_name=source_name,
                    source_url=url,
                    outcome="ingested",
                    reason="new_import",
                    acquisition_path=str(source_meta["path"]),
                    canonical_key=str(dict(post.extracted_metadata or {}).get("canonical_key") or ""),
                    job_post_id=post.id,
                )

        self.session.commit()
        return {**counts, "saved_job_ids": saved_job_ids}
