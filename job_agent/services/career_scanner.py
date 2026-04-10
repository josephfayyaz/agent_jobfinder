"""Scanner for Italian company career pages — discovers new job postings."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import httpx
from sqlalchemy.orm import Session

from job_agent.models import CareerPageSource, JobPost, JobTrackScore, ResumeTrack
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

    def _scan_one(self, source: CareerPageSource, session: Session, tracks: list[ResumeTrack]) -> int:
        """
        Fetch one career page and extract job links.
        Returns count of new JobPost records created.
        """
        logger.debug("Scanning %s at %s", source.company, source.career_url)

        try:
            response = httpx.get(
                source.career_url,
                headers=_HEADERS,
                follow_redirects=True,
                timeout=15,
            )
        except httpx.RequestError as exc:
            logger.warning("Network error fetching %s: %s", source.career_url, exc)
            return 0

        if not response.is_success:
            logger.warning("HTTP %d for %s", response.status_code, source.career_url)
            return 0

        soup = BeautifulSoup(response.text, "lxml")
        links = soup.select(source.css_selector) if source.css_selector else soup.find_all("a", href=True)
        new_count = 0

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

            if session.query(JobPost).filter_by(source_url=url).first():
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

        return new_count
