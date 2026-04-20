"""Scanner for Italian company career pages — discovers new job postings."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import httpx
from sqlalchemy import or_
from sqlalchemy.orm import Session, sessionmaker

from job_agent.db import SessionLocal
from job_agent.models import CareerPageScanLog, CareerPageSource, JobPost, JobTrackScore, ResumeTrack
from job_agent.services.ats_scanner import AtsApiScanner
from job_agent.services.matching import score_tracks_for_job

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,it;q=0.8",
}

_JOB_URL_PATTERNS = [
    re.compile(r"/job[s]?/", re.I),
    re.compile(r"/career[s]?/", re.I),
    re.compile(r"/position[s]?/", re.I),
    re.compile(r"/opening[s]?/", re.I),
    re.compile(r"/vacancy|vacancies", re.I),
    re.compile(r"/offerta|/lavora-con-noi", re.I),
]


def _looks_like_job_url(href: str) -> bool:
    """Return True if the URL pattern suggests it's a specific job listing."""
    return any(pattern.search(href) for pattern in _JOB_URL_PATTERNS)


def _extract_title_from_link(link_tag) -> str:
    """Best-effort: extract a job title from a link and its metadata."""
    title = link_tag.get_text(strip=True)
    if not title:
        title = link_tag.get("aria-label") or link_tag.get("title") or ""
    return title[:200]


class CareerPageScanner:
    """Scans active career page sources and creates JobPost records for new listings."""

    def scan_all(self, session: Session) -> int:
        """
        Scan all active CareerPageSource records.
        Returns total number of new JobPost records created.
        """
        sources = session.query(CareerPageSource).filter_by(active=True).all()
        logger.info("Scanning %d career page sources", len(sources))
        total_new = 0
        tracks = session.query(ResumeTrack).filter_by(active=True).all()

        for source in sources:
            try:
                new_count = self._scan_one(source, session, tracks)
                total_new += new_count
                source.last_checked_at = datetime.now(timezone.utc)
                source.last_new_jobs = new_count
            except Exception as exc:
                logger.error("Failed to scan %s: %s", source.company, exc)

        session.commit()
        logger.info("Career page scan complete: %d new jobs total", total_new)
        return total_new

    def scan_all_parallel(self, session: Session, max_workers: int | None = None) -> int:
        """
        Parallel version of scan_all() — fetches all career pages concurrently.
        Each source scan runs in its own thread-local DB session.
        """
        from job_agent.config import get_settings

        settings = get_settings()
        workers = max_workers or settings.scanner_max_workers
        source_ids = [source.id for source in session.query(CareerPageSource).filter_by(active=True).all()]
        if not source_ids:
            logger.info("No active career page sources to scan")
            return 0

        logger.info("Parallel scanning %d career pages with %d workers", len(source_ids), workers)

        bind = session.get_bind()
        if bind is not None:
            thread_session_factory = sessionmaker(
                bind=bind,
                autoflush=False,
                autocommit=False,
                expire_on_commit=False,
            )
        else:
            thread_session_factory = SessionLocal

        def _scan_source(source_id: int) -> int:
            with thread_session_factory() as thread_session:
                source = thread_session.get(CareerPageSource, source_id)
                if source is None or not source.active:
                    return 0
                tracks = thread_session.query(ResumeTrack).filter_by(active=True).all()
                try:
                    new_count = self._scan_one(source, thread_session, tracks)
                    source.last_checked_at = datetime.now(timezone.utc)
                    source.last_new_jobs = new_count
                    thread_session.commit()
                    return new_count
                except Exception as exc:
                    thread_session.rollback()
                    logger.error("Failed to scan %s: %s", source.company, exc)
                    return 0

        total_new = 0
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_source_id = {
                executor.submit(_scan_source, source_id): source_id for source_id in source_ids
            }
            for future in as_completed(future_to_source_id):
                source_id = future_to_source_id[future]
                try:
                    total_new += future.result()
                except Exception as exc:
                    logger.error("Thread failed for source %s: %s", source_id, exc)

        logger.info("Parallel career scan complete: %d new jobs total", total_new)
        return total_new

    def _record_scan_log(self, session: Session, source_id: int, jobs_found: int, new_count: int) -> None:
        session.add(
            CareerPageScanLog(
                source_id=source_id,
                jobs_found=jobs_found,
                new_jobs=new_count,
            )
        )

    def _scan_one(self, source: CareerPageSource, session: Session, tracks: list[ResumeTrack]) -> int:
        """
        Fetch one career page and extract job links.
        Returns count of new JobPost records created.
        """
        logger.debug("Scanning %s at %s", source.company, source.career_url)

        if source.ats_type and source.ats_slug:
            try:
                return self._scan_one_ats(source, session, tracks)
            except Exception as exc:
                logger.warning(
                    "ATS API scan failed for %s (%s), falling back to HTML scraper: %s",
                    source.company,
                    source.ats_type,
                    exc,
                )

        try:
            response = httpx.get(
                source.career_url,
                headers=_HEADERS,
                follow_redirects=True,
                timeout=15,
            )
        except httpx.RequestError as exc:
            logger.warning("Network error fetching %s: %s", source.career_url, exc)
            self._record_scan_log(session, source.id, jobs_found=0, new_count=0)
            return 0

        if not response.is_success:
            logger.warning("HTTP %d for %s", response.status_code, source.career_url)
            self._record_scan_log(session, source.id, jobs_found=0, new_count=0)
            return 0

        soup = BeautifulSoup(response.text, "lxml")
        links = soup.select(source.css_selector) if source.css_selector else soup.find_all("a", href=True)
        new_count = 0
        jobs_found = 0

        for link in links:
            href = link.get("href", "")
            if not href:
                continue

            if href.startswith("http"):
                url = href
            elif href.startswith("/"):
                url = urljoin(source.career_url, href)
            else:
                continue

            if not _looks_like_job_url(url):
                continue

            jobs_found += 1

            if (
                session.query(JobPost)
                .filter(or_(JobPost.canonical_apply_url == url, JobPost.source_url == url))
                .first()
            ):
                continue

            title = _extract_title_from_link(link)
            if not title or len(title) < 3:
                continue

            post = JobPost(
                source_name="career_page",
                canonical_apply_url=url,
                title=title,
                company=source.company,
                location=source.country,
                country=source.country,
                description="",
                source_url=url,
                status="new",
                created_at=datetime.now(timezone.utc),
                last_seen_at=datetime.now(timezone.utc),
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
            logger.info("New job from %s: %s [%s]", source.company, title, post.id)

        self._record_scan_log(session, source.id, jobs_found=jobs_found, new_count=new_count)
        return new_count

    def _scan_one_ats(self, source: CareerPageSource, session: Session, tracks: list[ResumeTrack]) -> int:
        ats_type = (source.ats_type or "").strip().lower()
        ats_slug = (source.ats_slug or "").strip()
        jobs = AtsApiScanner().fetch_jobs(ats_type, ats_slug)
        jobs_found = len(jobs)
        new_count = 0

        for job in jobs:
            url = str(job.get("url") or "").strip()
            title = str(job.get("title") or "").strip()[:200]
            location = str(job.get("location") or "").strip()
            if not url or not title:
                continue

            if (
                session.query(JobPost)
                .filter(or_(JobPost.canonical_apply_url == url, JobPost.source_url == url))
                .first()
            ):
                continue

            post = JobPost(
                source_name="career_page",
                canonical_apply_url=url,
                title=title,
                company=source.company,
                location=location or source.country,
                country=source.country,
                description="",
                source_url=url,
                status="new",
                created_at=datetime.now(timezone.utc),
                last_seen_at=datetime.now(timezone.utc),
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
            logger.info("New ATS job from %s: %s [%s]", source.company, title, post.id)

        self._record_scan_log(session, source.id, jobs_found=jobs_found, new_count=new_count)
        return new_count

    def check_velocity_spikes(self, session: Session) -> list[dict]:
        """
        Return sources where the most recent scan had new_jobs >= velocity_spike_threshold.
        Only considers scan logs from the last 2 hours to avoid re-alerting old spikes.
        """
        from job_agent.config import get_settings

        threshold = get_settings().velocity_spike_threshold
        cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
        logs = (
            session.query(CareerPageScanLog)
            .filter(
                CareerPageScanLog.new_jobs >= threshold,
                CareerPageScanLog.scanned_at >= cutoff,
            )
            .order_by(CareerPageScanLog.scanned_at.desc())
            .limit(20)
            .all()
        )
        spikes = []
        for log in logs:
            source = session.get(CareerPageSource, log.source_id)
            spikes.append(
                {
                    "company": source.company if source else "unknown",
                    "new_jobs": log.new_jobs,
                    "scanned_at": log.scanned_at.isoformat(),
                    "career_url": source.career_url if source else "",
                }
            )
        return spikes
