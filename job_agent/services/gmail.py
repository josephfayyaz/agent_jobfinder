"""Gmail IMAP integration for LinkedIn job alert ingestion."""

from __future__ import annotations

import email
from email.message import Message
import imaplib
import logging
import re
import time
from typing import Any

from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from job_agent.config import Settings, get_settings
from job_agent.models import JobPost, JobTrackScore, ResumeTrack
from job_agent.services.matching import score_tracks_for_job

logger = logging.getLogger(__name__)

_LINKEDIN_SENDER = "jobs-noreply@linkedin.com"
_JOB_URL_RE = re.compile(r"linkedin\.com/jobs/view/\d+")


def _get_html_body(msg: Message) -> str | None:
    """Extract the first HTML body from a MIME email message."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() != "text/html":
                continue
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            charset = part.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
    elif msg.get_content_type() == "text/html":
        payload = msg.get_payload(decode=True)
        if payload is None:
            return None
        charset = msg.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")

    return None


def _extract_job_cards(html: str) -> list[dict[str, str]]:
    """Parse LinkedIn job alert HTML and extract title/company/location/url cards."""
    soup = BeautifulSoup(html, "lxml")
    jobs: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    for link in soup.find_all("a", href=_JOB_URL_RE):
        url = str(link.get("href", "")).strip()
        clean_url = re.sub(r"\?.*$", "", url)
        if not clean_url or clean_url in seen_urls:
            continue
        seen_urls.add(clean_url)

        title = link.get_text(strip=True)
        if not title:
            continue

        container = link.find_parent("td") or link.find_parent("div") or link.parent
        container_text = container.get_text(separator="\n", strip=True) if container else ""
        lines = [line.strip() for line in container_text.split("\n") if line.strip()]

        company = lines[1] if len(lines) > 1 else ""
        location = lines[2] if len(lines) > 2 else ""
        if company == title:
            company = lines[2] if len(lines) > 2 else ""
            location = lines[3] if len(lines) > 3 else ""

        jobs.append(
            {
                "title": title,
                "company": company,
                "location": location,
                "url": clean_url,
            }
        )

    return jobs


class GmailService:
    """Poll Gmail for LinkedIn job alerts and ingest new JobPost records."""

    def __init__(self, app_settings: Settings | None = None) -> None:
        self.settings = app_settings or get_settings()

    def _is_configured(self) -> bool:
        return bool(self.settings.gmail_email and self.settings.gmail_app_password)

    def _connect(self) -> imaplib.IMAP4_SSL:
        conn = imaplib.IMAP4_SSL(self.settings.gmail_imap_host)
        conn.login(self.settings.gmail_email, self.settings.gmail_app_password)
        return conn

    def _search_query(self) -> str:
        label = self.settings.gmail_label_filter.strip()
        if label:
            if "@" in label:
                return f'FROM "{label}" UNSEEN'
            return f'FROM "{_LINKEDIN_SENDER}" UNSEEN'
        return f'FROM "{_LINKEDIN_SENDER}" UNSEEN'

    def sync_jobs(self, session: Session) -> list[JobPost]:
        """Fetch unread LinkedIn alert emails, parse cards, and upsert JobPosts."""
        if not self._is_configured():
            logger.debug("Gmail is not configured; skipping sync")
            return []

        try:
            conn = self._connect()
        except Exception as exc:
            logger.error("Gmail IMAP connection failed: %s", exc)
            return []

        new_posts: list[JobPost] = []
        try:
            conn.select("INBOX")
            _, uid_data = conn.uid("SEARCH", None, self._search_query())
            uids = uid_data[0].split() if uid_data and uid_data[0] else []
            uids = uids[: self.settings.gmail_max_emails_per_sync]

            logger.info("Gmail sync found %d unread LinkedIn alert emails", len(uids))
            tracks = (
                session.query(ResumeTrack)
                .filter(ResumeTrack.active.is_(True))
                .order_by(ResumeTrack.title.asc())
                .all()
            )

            for uid in uids:
                try:
                    _, msg_data = conn.uid("FETCH", uid, "(RFC822)")
                    if not msg_data or not isinstance(msg_data[0], tuple):
                        continue
                    raw = msg_data[0][1]
                    msg = email.message_from_bytes(raw)
                    html = _get_html_body(msg)
                    if not html:
                        continue

                    for card in _extract_job_cards(html):
                        post = self._upsert_job_post(card, session, tracks)
                        if post is not None:
                            new_posts.append(post)

                    conn.uid("STORE", uid, "+FLAGS", "\\Seen")
                except Exception as exc:
                    logger.warning("Failed to parse Gmail message uid=%s: %s", uid, exc)

            session.commit()
            if new_posts:
                from job_agent.services.job_fetcher import JobFetcher

                fetcher = JobFetcher()
                for post in new_posts:
                    time.sleep(self.settings.linkedin_fetch_delay_seconds)
                    fetcher.enrich_job(post, session)
                session.commit()
            logger.info("Gmail sync created %d new jobs", len(new_posts))
        finally:
            try:
                conn.logout()
            except Exception:
                pass

        return new_posts

    def _upsert_job_post(
        self,
        card: dict[str, str],
        session: Session,
        tracks: list[ResumeTrack],
    ) -> JobPost | None:
        """Create a JobPost from a parsed job card unless the URL already exists."""
        url = card.get("url", "").strip()
        if not url:
            return None

        existing = session.query(JobPost).filter(JobPost.source_url == url).first()
        if existing is not None:
            return None

        payload: dict[str, Any] = {
            "source_name": "linkedin_email_alert",
            "source_url": url,
            "canonical_apply_url": url,
            "company": card.get("company", "Unknown") or "Unknown",
            "title": card.get("title", "Unknown") or "Unknown",
            "location": card.get("location", ""),
            "description": "",
            "status": "new",
        }
        post = JobPost(**payload)
        session.add(post)
        session.flush()

        scored = score_tracks_for_job(
            {"title": post.title, "description": post.description},
            tracks,
        )
        for result in scored:
            track_id = result.get("track_id")
            if track_id is None:
                continue
            session.add(
                JobTrackScore(
                    job_post_id=post.id,
                    resume_track_id=track_id,
                    score=float(result["score"]),
                    matched_keywords=result["matched_keywords"],
                )
            )

        logger.info("New Gmail job ingested: %s @ %s [%s]", post.title, post.company, post.id)
        return post
