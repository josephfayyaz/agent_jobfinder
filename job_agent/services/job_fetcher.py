"""LinkedIn job page fetcher for enriching JobPost descriptions."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
import time

from bs4 import BeautifulSoup
import httpx
from sqlalchemy.orm import Session

from job_agent.config import get_settings
from job_agent.models import JobPost, JobTrackScore, ResumeTrack
from job_agent.services.matching import score_tracks_for_job

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
_BACKOFF_ON_429 = 30


def _extract_from_json_ld(soup: BeautifulSoup) -> str | None:
    """Prefer JSON-LD description data when LinkedIn embeds it."""
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except Exception:
            continue
        if isinstance(data, dict) and data.get("description"):
            desc_soup = BeautifulSoup(data["description"], "lxml")
            return desc_soup.get_text(separator="\n", strip=True)
    return None


def _extract_from_html(soup: BeautifulSoup) -> str | None:
    """Fallback to known LinkedIn HTML containers when JSON-LD is absent."""
    selectors = [
        "div.show-more-less-html__markup",
        "div.description__text",
        "section.description",
        "div[class*='job-description']",
    ]
    for selector in selectors:
        element = soup.select_one(selector)
        if element is not None:
            return element.get_text(separator="\n", strip=True)
    return None


def fetch_job_description(url: str) -> str | None:
    """Fetch a LinkedIn job page and extract its human-readable description."""
    try:
        with httpx.Client(headers=_HEADERS, follow_redirects=True, timeout=15) as client:
            response = client.get(url)
    except httpx.RequestError as exc:
        logger.error("Network error fetching %s: %s", url, exc)
        return None

    if response.status_code == 429:
        logger.warning("Rate limited by LinkedIn (429), backing off %ds", _BACKOFF_ON_429)
        time.sleep(_BACKOFF_ON_429)
        return None
    if response.status_code == 403:
        logger.warning("LinkedIn blocked fetch (403) for %s", url)
        return None
    if not response.is_success:
        logger.warning("Non-200 response %d for %s", response.status_code, url)
        return None

    soup = BeautifulSoup(response.text, "lxml")
    description = _extract_from_json_ld(soup) or _extract_from_html(soup)
    if not description:
        logger.warning("Could not extract description from %s", url)
    return description


def _fetch_description_from_url(url: str) -> str | None:
    """Compatibility wrapper for threaded enrichment helpers."""
    return fetch_job_description(url)


@dataclass
class _FetchedDescription:
    """Result from a worker thread — plain data, no ORM."""

    job_id: object
    description: str
    company_url: str | None = None
    success: bool = True


def _fetch_one_thread(job_data: dict) -> _FetchedDescription:
    """
    Fetch job description for one job. Thread-safe because it avoids DB access.
    """
    job_id = job_data["id"]
    source_url = job_data["source_url"]

    if not source_url:
        return _FetchedDescription(job_id=job_id, description="", success=False)

    try:
        description = _fetch_description_from_url(source_url)
        return _FetchedDescription(
            job_id=job_id,
            description=description or "",
            success=bool(description),
        )
    except Exception as exc:
        logger.warning("Failed to fetch description for job %s: %s", job_id, exc)
        return _FetchedDescription(job_id=job_id, description="", success=False)


class JobFetcher:
    """Enrich JobPost rows by fetching full descriptions from LinkedIn URLs."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def enrich_job(self, job: JobPost, session: Session) -> bool:
        """Fetch a description for one job, then recompute its track scores."""
        if not job.source_url:
            return False

        description = _fetch_description_from_url(job.source_url)
        if not description:
            return False

        job.description = description
        job.last_seen_at = datetime.now(timezone.utc)

        tracks = session.query(ResumeTrack).filter_by(active=True).all()
        if tracks:
            self._upsert_scores(job, tracks, session)

        if not job.company_url and job.company and job.description:
            from job_agent.services.company_resolver import find_company_url

            resolved = find_company_url(
                company_name=job.company,
                location=job.location or "",
                description=job.description,
            )
            if resolved:
                job.company_url = resolved
                session.add(job)
                logger.info("Auto-resolved company_url for job %s: %s", job.id, resolved)

        session.flush()
        logger.info("Enriched job %s with %d chars of description", job.id, len(description))
        return True

    def enrich_pending(self, session: Session, limit: int = 20) -> int:
        """Enrich jobs that still have empty descriptions."""
        pending = (
            session.query(JobPost)
            .filter(
                (JobPost.description == "") | (JobPost.description.is_(None)),
                JobPost.source_url.is_not(None),
            )
            .limit(limit)
            .all()
        )
        if not pending:
            logger.debug("No pending jobs to enrich")
            return 0

        count = 0
        for index, job in enumerate(pending):
            if index > 0:
                time.sleep(self.settings.linkedin_fetch_delay_seconds)
            if self.enrich_job(job, session):
                count += 1

        session.commit()
        logger.info("LinkedIn enrichment complete: %d/%d jobs updated", count, len(pending))
        return count

    def enrich_pending_parallel(
        self,
        session: Session,
        limit: int = 20,
        max_workers: int | None = None,
    ) -> int:
        """
        Parallel version of enrich_pending() — fetches job descriptions concurrently.
        Returns count of jobs successfully enriched.
        """
        from job_agent.config import get_settings

        settings = get_settings()
        workers = max_workers or settings.scan_max_workers

        pending = (
            session.query(JobPost)
            .filter(
                (JobPost.description == "") | (JobPost.description.is_(None)),
                JobPost.source_url.is_not(None),
            )
            .limit(limit)
            .all()
        )

        if not pending:
            logger.info("No pending jobs to enrich")
            return 0

        logger.info("Parallel enriching %d jobs with %d workers", len(pending), workers)

        job_dicts = [
            {
                "id": job.id,
                "source_url": job.source_url,
                "company": job.company,
                "location": job.location,
            }
            for job in pending
        ]

        fetch_results: list[_FetchedDescription] = []
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_fetch_one_thread, job_data): job_data for job_data in job_dicts}
            for future in as_completed(futures):
                try:
                    fetch_results.append(future.result())
                except Exception as exc:
                    job_data = futures[future]
                    logger.error("Thread failed for job %s: %s", job_data["id"], exc)

        job_map = {job.id: job for job in pending}
        tracks = session.query(ResumeTrack).filter_by(active=True).all()
        enriched = 0

        for result in fetch_results:
            if not result.success or not result.description:
                continue
            job = job_map.get(result.job_id)
            if job is None:
                continue

            job.description = result.description
            job.last_seen_at = datetime.now(timezone.utc)
            if result.company_url and not job.company_url:
                job.company_url = result.company_url
            elif not job.company_url and job.company and job.description:
                from job_agent.services.company_resolver import find_company_url

                resolved = find_company_url(
                    company_name=job.company,
                    location=job.location or "",
                    description=job.description,
                )
                if resolved:
                    job.company_url = resolved

            if tracks:
                self._upsert_scores(job, tracks, session)
            session.add(job)
            enriched += 1

        session.commit()
        logger.info("Parallel enrichment complete: %d/%d jobs enriched", enriched, len(pending))
        return enriched

    def _upsert_scores(self, job: JobPost, tracks: list[ResumeTrack], session: Session) -> None:
        """Replace track scores using the full fetched description."""
        session.query(JobTrackScore).filter_by(job_post_id=job.id).delete()
        scored = score_tracks_for_job(
            {"title": job.title, "description": job.description},
            tracks,
        )
        for result in scored:
            track_id = result.get("track_id")
            if track_id is None:
                continue
            session.add(
                JobTrackScore(
                    job_post_id=job.id,
                    resume_track_id=track_id,
                    score=float(result["score"]),
                    matched_keywords=result["matched_keywords"],
                )
            )
