"""Freshness, confidence, and apply-link signals for review queue jobs."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from job_agent.models import CareerPageScanLog, CareerPageSource, JobPost

logger = logging.getLogger(__name__)

LINK_CHECK_CACHE_HOURS = 24


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, str) and value.strip():
        text = value.strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    return None


@dataclass(slots=True)
class CompanySignal:
    latest_scan_at: datetime | None = None
    surge_scans: int = 0
    is_surging: bool = False


class JobSignalService:
    """Compute trust signals shown in the review queue."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def evaluate_many(self, jobs: list[JobPost]) -> dict[UUID, dict[str, Any]]:
        if not jobs:
            return {}

        company_signals = self._load_company_signals(jobs)
        return {
            job.id: self.evaluate_job(
                job,
                company_signal=company_signals.get((job.company or "").strip().casefold()),
            )
            for job in jobs
        }

    def evaluate_job(
        self,
        job: JobPost,
        *,
        company_signal: CompanySignal | None = None,
    ) -> dict[str, Any]:
        freshness = self._freshness_signal(job)
        confidence = self._confidence_signal(job, company_signal)
        link_check = self._link_check_from_metadata(job)
        suspicion = self._suspicion_signal(job, freshness, confidence, link_check)

        return {
            "freshness": freshness,
            "confidence": confidence,
            "link_check": link_check,
            "suspicion": suspicion,
            "is_surging": bool(company_signal and company_signal.is_surging),
            "surge_scans": int(company_signal.surge_scans if company_signal else 0),
        }

    def refresh_apply_link_check(self, job: JobPost, *, force: bool = False) -> dict[str, Any]:
        current = self._link_check_from_metadata(job)
        checked_at = _coerce_datetime(current.get("checked_at"))
        if not force and checked_at is not None and (_utc_now() - checked_at) < timedelta(hours=LINK_CHECK_CACHE_HOURS):
            return current

        url = str(job.canonical_apply_url or job.source_url or "").strip()
        result = self._run_apply_link_check(url)
        metadata = dict(job.extracted_metadata or {})
        metadata["apply_link_check"] = result
        job.extracted_metadata = metadata
        self.session.add(job)
        return result

    def _load_company_signals(self, jobs: list[JobPost]) -> dict[str, CompanySignal]:
        company_names = sorted({(job.company or "").strip() for job in jobs if (job.company or "").strip()})
        if not company_names:
            return {}

        sources = (
            self.session.query(CareerPageSource)
            .filter(CareerPageSource.company.in_(company_names))
            .all()
        )
        if not sources:
            return {}

        company_by_source_id = {source.id: source.company.strip().casefold() for source in sources if source.company.strip()}
        source_ids = list(company_by_source_id.keys())
        cutoff = _utc_now() - timedelta(days=7)
        logs = (
            self.session.query(CareerPageScanLog)
            .filter(CareerPageScanLog.source_id.in_(source_ids))
            .order_by(CareerPageScanLog.scanned_at.desc())
            .all()
        )

        grouped: dict[str, CompanySignal] = {}
        for log in logs:
            company_key = company_by_source_id.get(log.source_id)
            if company_key is None:
                continue
            signal = grouped.setdefault(company_key, CompanySignal())
            scanned_at = _coerce_datetime(log.scanned_at)
            if scanned_at is not None and (signal.latest_scan_at is None or scanned_at > signal.latest_scan_at):
                signal.latest_scan_at = scanned_at
            if scanned_at is not None and scanned_at >= cutoff and int(log.new_jobs or 0) > 0:
                signal.surge_scans += 1

        for signal in grouped.values():
            signal.is_surging = signal.surge_scans >= 2
        return grouped

    def _freshness_signal(self, job: JobPost) -> dict[str, Any]:
        posted_at = _coerce_datetime(getattr(job, "posted_date", None))
        last_seen = _coerce_datetime(job.last_seen_at)
        created_at = _coerce_datetime(job.created_at)
        anchor = posted_at or last_seen or created_at or _utc_now()
        age_days = max(0, int((_utc_now() - anchor).total_seconds() // 86400))
        if age_days <= 2:
            label, tone = "Fresh", "good"
        elif age_days <= 7:
            label, tone = "Recent", "good"
        elif age_days <= 21:
            label, tone = "Older posting", "warn"
        else:
            label, tone = "Stale listing", "risk"
        title_prefix = "Posted" if posted_at is not None else "Last seen"
        return {
            "label": label,
            "tone": tone,
            "days_old": age_days,
            "title": f"{title_prefix} about {age_days} day(s) ago.",
        }

    def _confidence_signal(self, job: JobPost, company_signal: CompanySignal | None) -> dict[str, Any]:
        last_seen = _coerce_datetime(job.last_seen_at) or _coerce_datetime(job.created_at)
        recent_scan_at = company_signal.latest_scan_at if company_signal else None

        if recent_scan_at is not None and (_utc_now() - recent_scan_at) <= timedelta(days=2):
            label = "Still active"
            tone = "good"
            detail = "Company watchlist saw this employer again in the last 48 hours."
        elif recent_scan_at is not None and (_utc_now() - recent_scan_at) <= timedelta(days=7):
            label = "Recently seen"
            tone = "good"
            detail = "Recent company-page scans still show activity around this employer."
        elif last_seen is not None and (_utc_now() - last_seen) <= timedelta(days=7):
            label = "Recently imported"
            tone = "neutral"
            detail = "The job entered your pipeline recently, but there is no confirming company scan yet."
        else:
            label = "Needs verification"
            tone = "warn"
            detail = "No recent company-page confirmation exists for this posting yet."

        if company_signal and company_signal.is_surging:
            detail = f"{detail} Hiring surge detected from {company_signal.surge_scans} recent scans."

        return {
            "label": label,
            "tone": tone,
            "title": detail,
        }

    def _link_check_from_metadata(self, job: JobPost) -> dict[str, Any]:
        metadata = dict(job.extracted_metadata or {})
        raw = metadata.get("apply_link_check")
        if not isinstance(raw, dict):
            return {
                "status": "unchecked",
                "label": "Link unverified",
                "tone": "neutral",
                "checked_at": None,
                "http_status": None,
                "title": "The apply link has not been checked yet.",
            }

        status = str(raw.get("status") or "unchecked")
        label_map = {
            "live": "Apply link live",
            "needs_verification": "Link unverified",
            "unavailable": "Link unavailable",
            "missing": "No apply link",
        }
        tone_map = {
            "live": "good",
            "needs_verification": "warn",
            "unavailable": "risk",
            "missing": "risk",
            "unchecked": "neutral",
        }
        title = str(raw.get("title") or label_map.get(status, "Link unverified"))
        return {
            "status": status,
            "label": label_map.get(status, "Link unverified"),
            "tone": tone_map.get(status, "neutral"),
            "checked_at": raw.get("checked_at"),
            "http_status": raw.get("http_status"),
            "title": title,
        }

    def _run_apply_link_check(self, url: str) -> dict[str, Any]:
        timestamp = _utc_now().isoformat()
        if not url:
            return {
                "status": "missing",
                "checked_at": timestamp,
                "http_status": None,
                "title": "This job does not have an apply link yet.",
            }

        headers = {
            "User-Agent": "Job-Agent/1.0 (+local-first queue verifier)",
            "Accept-Language": "en-US,en;q=0.9",
        }
        try:
            response = httpx.head(url, headers=headers, follow_redirects=True, timeout=4)
            status_code = int(response.status_code)
            if status_code in {400, 403, 405} or status_code >= 500:
                response = httpx.get(url, headers=headers, follow_redirects=True, timeout=4)
                status_code = int(response.status_code)
        except httpx.RequestError as exc:
            logger.info("Apply-link verification failed for %s: %s", url, exc)
            return {
                "status": "needs_verification",
                "checked_at": timestamp,
                "http_status": None,
                "title": "The link could not be verified from this machine right now.",
            }

        if 200 <= status_code < 400:
            host = urlparse(str(response.url)).netloc or urlparse(url).netloc
            return {
                "status": "live",
                "checked_at": timestamp,
                "http_status": status_code,
                "title": f"The apply link responded successfully from {host}.",
            }
        if status_code in {404, 410}:
            return {
                "status": "unavailable",
                "checked_at": timestamp,
                "http_status": status_code,
                "title": "The apply link appears unavailable. Refresh or verify before drafting.",
            }
        if status_code in {401, 403, 429}:
            return {
                "status": "needs_verification",
                "checked_at": timestamp,
                "http_status": status_code,
                "title": "The apply link is protected or rate-limited; verify it in a browser before drafting.",
            }
        return {
            "status": "needs_verification",
            "checked_at": timestamp,
            "http_status": status_code,
            "title": f"The link responded with HTTP {status_code}; verify it before drafting.",
        }

    def _suspicion_signal(
        self,
        job: JobPost,
        freshness: dict[str, Any],
        confidence: dict[str, Any],
        link_check: dict[str, Any],
    ) -> dict[str, Any]:
        reasons: list[str] = []
        description = str(job.description or "").strip()

        if not description or len(description) < 120:
            reasons.append("Job description is thin, so role details are still incomplete.")
        if not str(job.canonical_apply_url or job.source_url or "").strip():
            reasons.append("No apply link is stored for this role.")
        if confidence["label"] == "Needs verification":
            reasons.append("No recent company-page confirmation exists yet.")
        if freshness["days_old"] >= 30:
            reasons.append("Posting looks old relative to the current review window.")
        if link_check["status"] in {"missing", "unavailable"}:
            reasons.append("Apply link is missing or unavailable.")

        if not reasons:
            return {
                "label": "Looks credible",
                "tone": "good",
                "reasons": [],
                "title": "Freshness, source, and link checks do not show obvious issues.",
            }

        return {
            "label": "Needs verification",
            "tone": "warn",
            "reasons": reasons,
            "title": "Review before drafting: " + " ".join(reasons),
        }
