"""Gmail IMAP integration for LinkedIn job alert ingestion."""

from __future__ import annotations

import base64
import email
from email.message import Message
import imaplib
import logging
import re
import time
from typing import Any

from bs4 import BeautifulSoup
import httpx
from sqlalchemy.orm import Session

from job_agent.config import Settings, get_settings
from job_agent.models import JobPost, JobTrackScore, ResumeTrack
from job_agent.services.discovery_hub import (
    find_existing_job,
    merge_duplicate_job,
    record_discovery_event,
    source_profile,
    stamp_job_metadata,
)
from job_agent.services.gmail_oauth import GmailOAuthService
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
        self.oauth = GmailOAuthService(self.settings)

    def _is_configured(self) -> bool:
        return bool(
            self.oauth.is_connected()
            or (self.settings.gmail_email and self.settings.gmail_app_password)
        )

    def is_configured(self) -> bool:
        return self._is_configured()

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

    def _gmail_query(self) -> str:
        label = self.settings.gmail_label_filter.strip()
        if label:
            if "@" in label:
                return f"from:{label} is:unread"
            return f'from:{_LINKEDIN_SENDER} label:"{label}" is:unread'
        return f"from:{_LINKEDIN_SENDER} is:unread"

    def _sync_jobs_oauth(self, session: Session) -> list[JobPost]:
        access_token = self.oauth.get_access_token()
        if not access_token:
            return []

        headers = {"Authorization": f"Bearer {access_token}"}
        params = {
            "q": self._gmail_query(),
            "maxResults": int(self.settings.gmail_max_emails_per_sync),
        }
        try:
            list_resp = httpx.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                headers=headers,
                params=params,
                timeout=20,
            )
        except Exception as exc:
            logger.error("Gmail OAuth list request failed: %s", exc)
            return []
        if not list_resp.is_success:
            logger.error("Gmail OAuth list request failed (%s): %s", list_resp.status_code, list_resp.text[:200])
            return []

        payload = list_resp.json() if list_resp.content else {}
        rows = payload.get("messages", []) if isinstance(payload, dict) else []
        if not isinstance(rows, list):
            rows = []

        tracks = (
            session.query(ResumeTrack)
            .filter(ResumeTrack.active.is_(True))
            .order_by(ResumeTrack.title.asc())
            .all()
        )

        new_posts: list[JobPost] = []
        for item in rows:
            if not isinstance(item, dict) or not item.get("id"):
                continue
            message_id = str(item["id"])
            try:
                detail_resp = httpx.get(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
                    headers=headers,
                    params={"format": "raw"},
                    timeout=20,
                )
                if not detail_resp.is_success:
                    continue
                detail_payload = detail_resp.json() if detail_resp.content else {}
                raw = str(detail_payload.get("raw") or "")
                if not raw:
                    continue
                padded = raw + ("=" * ((4 - len(raw) % 4) % 4))
                raw_bytes = base64.urlsafe_b64decode(padded.encode("utf-8"))
                msg = email.message_from_bytes(raw_bytes)
                html = _get_html_body(msg)
                if not html:
                    continue
                for card in _extract_job_cards(html):
                    post = self._upsert_job_post(card, session, tracks)
                    if post is not None:
                        new_posts.append(post)
                httpx.post(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}/modify",
                    headers=headers,
                    json={"removeLabelIds": ["UNREAD"]},
                    timeout=20,
                )
            except Exception as exc:
                logger.warning("Failed to parse OAuth Gmail message %s: %s", message_id, exc)

        session.commit()
        if new_posts:
            from job_agent.services.job_fetcher import JobFetcher

            fetcher = JobFetcher()
            for post in new_posts:
                time.sleep(self.settings.linkedin_fetch_delay_seconds)
                fetcher.enrich_job(post, session)
            session.commit()
        logger.info("OAuth Gmail sync created %d new jobs", len(new_posts))
        return new_posts

    def sync_jobs(self, session: Session) -> list[JobPost]:
        """Fetch unread LinkedIn alert emails, parse cards, and upsert JobPosts."""
        if not self._is_configured():
            logger.debug("Gmail is not configured; skipping sync")
            return []

        # Prefer OAuth path when connected; keep IMAP App Password support as transition fallback.
        if self.oauth.is_connected():
            oauth_posts = self._sync_jobs_oauth(session)
            if oauth_posts or not (self.settings.gmail_email and self.settings.gmail_app_password):
                return oauth_posts

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
        """Create or merge a JobPost from a parsed Gmail job card."""
        url = card.get("url", "").strip()
        if not url:
            return None

        company = card.get("company", "Unknown") or "Unknown"
        title = card.get("title", "Unknown") or "Unknown"
        location = card.get("location", "")
        source_meta = source_profile("linkedin_email_alert", url)
        dedupe = find_existing_job(
            session,
            canonical_apply_url=url,
            source_url=url,
            company=company,
            title=title,
            location=location,
        )
        if dedupe.job is not None:
            merge_duplicate_job(
                dedupe.job,
                {
                    "canonical_apply_url": url,
                    "source_url": url,
                    "last_seen_at": None,
                },
            )
            stamp_job_metadata(
                dedupe.job,
                source_name="linkedin_email_alert",
                source_url=url,
                canonical_apply_url=url,
                company=company,
                title=title,
                location=location,
                canonical_reason=dedupe.reason,
            )
            record_discovery_event(
                session,
                source_name="linkedin_email_alert",
                source_url=url,
                outcome="duplicate",
                reason=dedupe.reason,
                acquisition_path=str(source_meta["path"]),
                canonical_key=dedupe.canonical_key,
                job_post_id=dedupe.job.id,
            )
            return None

        payload: dict[str, Any] = {
            "source_name": "linkedin_email_alert",
            "source_url": url,
            "canonical_apply_url": url,
            "company": company,
            "title": title,
            "location": location,
            "description": "",
            "queue_state": "new",
            "status": "new",
            "enrichment_status": "pending",
        }
        post = JobPost(**payload)
        stamp_job_metadata(
            post,
            source_name="linkedin_email_alert",
            source_url=url,
            canonical_apply_url=url,
            company=company,
            title=title,
            location=location,
            canonical_reason="new_import",
        )
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

        record_discovery_event(
            session,
            source_name="linkedin_email_alert",
            source_url=url,
            outcome="ingested",
            reason="new_import",
            acquisition_path=str(source_meta["path"]),
            canonical_key=str(dict(post.extracted_metadata or {}).get("canonical_key") or ""),
            job_post_id=post.id,
        )
        logger.info("New Gmail job ingested: %s @ %s [%s]", post.title, post.company, post.id)
        return post
