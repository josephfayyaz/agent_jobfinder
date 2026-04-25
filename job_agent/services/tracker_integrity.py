"""Consistency checks and safe repair actions for the local job tracker."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from job_agent.models import Application, CareerPageSource, JobPost, ResumeDraft


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TrackerIntegrityService:
    """Inspect the local pipeline and expose a compact health summary."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def evaluate(self) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        jobs_missing_queue = (
            self.session.query(JobPost)
            .filter((JobPost.queue_state.is_(None)) | (JobPost.queue_state == ""))
            .count()
        )
        if jobs_missing_queue:
            issues.append(
                self._issue(
                    code="missing_queue_state",
                    title="Jobs missing queue state",
                    count=jobs_missing_queue,
                    severity="warning",
                    auto_fixable=True,
                    detail="Some older jobs were ingested before the review queue existed.",
                )
            )

        applied_job_ids = {
            job_id
            for job_id, in self.session.query(Application.job_post_id).distinct().all()
            if job_id is not None
        }
        jobs_not_marked_applied = (
            self.session.query(JobPost)
            .filter(JobPost.id.in_(applied_job_ids), JobPost.status != "applied")
            .count()
            if applied_job_ids
            else 0
        )
        if jobs_not_marked_applied:
            issues.append(
                self._issue(
                    code="job_status_drift",
                    title="Applied jobs not marked as applied",
                    count=jobs_not_marked_applied,
                    severity="warning",
                    auto_fixable=True,
                    detail="Applications exist, but the related job rows still show an earlier lifecycle state.",
                )
            )

        duplicate_url_groups = (
            self.session.query(JobPost.canonical_apply_url, func.count(JobPost.id))
            .filter(JobPost.canonical_apply_url.is_not(None), JobPost.canonical_apply_url != "")
            .group_by(JobPost.canonical_apply_url)
            .having(func.count(JobPost.id) > 1)
            .count()
        )
        if duplicate_url_groups:
            issues.append(
                self._issue(
                    code="duplicate_jobs",
                    title="Duplicate apply URLs detected",
                    count=duplicate_url_groups,
                    severity="warning",
                    auto_fixable=False,
                    detail="Multiple jobs share the same canonical apply link and should be reviewed manually.",
                )
            )

        missing_artifacts = 0
        for draft in self.session.query(ResumeDraft).all():
            tex_path = str(draft.tex_path or "").strip()
            if not tex_path:
                missing_artifacts += 1
                continue
            if not Path(tex_path).expanduser().exists():
                missing_artifacts += 1
        if missing_artifacts:
            issues.append(
                self._issue(
                    code="missing_draft_artifacts",
                    title="Draft artifacts missing on disk",
                    count=missing_artifacts,
                    severity="warning",
                    auto_fixable=False,
                    detail="The draft record still exists, but the saved .tex file is missing from the artifacts folder.",
                )
            )

        stale_sources = (
            self.session.query(CareerPageSource)
            .filter(
                CareerPageSource.active.is_(True),
                CareerPageSource.last_checked_at.is_not(None),
                CareerPageSource.last_checked_at < (_utc_now() - timedelta(days=14)),
            )
            .count()
        )
        if stale_sources:
            issues.append(
                self._issue(
                    code="stale_sources",
                    title="Career page sources need a fresh scan",
                    count=stale_sources,
                    severity="info",
                    auto_fixable=False,
                    detail="Active watchlist companies have not been checked in over 14 days.",
                )
            )

        broken_job_links = 0
        for job in self.session.query(JobPost).all():
            metadata = dict(job.extracted_metadata or {})
            link_check = metadata.get("apply_link_check")
            if isinstance(link_check, dict) and str(link_check.get("status")) in {"missing", "unavailable"}:
                broken_job_links += 1
        if broken_job_links:
            issues.append(
                self._issue(
                    code="broken_apply_links",
                    title="Jobs with missing or unavailable apply links",
                    count=broken_job_links,
                    severity="warning",
                    auto_fixable=False,
                    detail="These jobs should be re-verified before you spend time generating a draft.",
                )
            )

        issue_count = sum(int(issue["count"]) for issue in issues)
        auto_fixable_count = sum(int(issue["count"]) for issue in issues if issue["auto_fixable"])
        return {
            "ok": issue_count == 0,
            "issue_count": issue_count,
            "auto_fixable_count": auto_fixable_count,
            "issues": issues,
            "checked_at": _utc_now().isoformat(),
        }

    def repair_safe_issues(self) -> dict[str, Any]:
        repaired = {
            "queue_state_backfilled": 0,
            "job_status_synced": 0,
            "canonical_urls_backfilled": 0,
        }

        missing_queue_jobs = (
            self.session.query(JobPost)
            .filter((JobPost.queue_state.is_(None)) | (JobPost.queue_state == ""))
            .all()
        )
        for job in missing_queue_jobs:
            job.queue_state = "new"
            repaired["queue_state_backfilled"] += 1

        applied_job_ids = {
            job_id
            for job_id, in self.session.query(Application.job_post_id).distinct().all()
            if job_id is not None
        }
        if applied_job_ids:
            jobs = (
                self.session.query(JobPost)
                .filter(JobPost.id.in_(applied_job_ids), JobPost.status != "applied")
                .all()
            )
            for job in jobs:
                job.status = "applied"
                job.queue_state = "shortlisted"
                repaired["job_status_synced"] += 1

        jobs_missing_canonical = (
            self.session.query(JobPost)
            .filter(
                ((JobPost.canonical_apply_url.is_(None)) | (JobPost.canonical_apply_url == "")),
                JobPost.source_url.is_not(None),
                JobPost.source_url != "",
            )
            .all()
        )
        for job in jobs_missing_canonical:
            job.canonical_apply_url = job.source_url
            repaired["canonical_urls_backfilled"] += 1

        self.session.commit()
        summary = self.evaluate()
        summary["repaired"] = repaired
        return summary

    def _issue(
        self,
        *,
        code: str,
        title: str,
        count: int,
        severity: str,
        auto_fixable: bool,
        detail: str,
    ) -> dict[str, Any]:
        return {
            "code": code,
            "title": title,
            "count": int(count),
            "severity": severity,
            "auto_fixable": auto_fixable,
            "detail": detail,
        }
