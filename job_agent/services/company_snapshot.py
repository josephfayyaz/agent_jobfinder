"""Focused company snapshots for shortlisted or high-fit jobs."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy.orm import Session

from job_agent.llm import LLMRouter, ProviderUnavailableError
from job_agent.models import CareerPageSource, CompanySnapshot, JobPost, JobTrackScore
from job_agent.services.job_signals import JobSignalService


def _company_host(url: str) -> str:
    return urlparse(url or "").netloc.replace("www.", "")


class CompanySnapshotService:
    def __init__(self, session: Session, router: LLMRouter | None = None) -> None:
        self.session = session
        self.router = router or LLMRouter()

    def eligible(self, job: JobPost) -> bool:
        if str(getattr(job, "enrichment_status", "") or "pending") in {"needs_input", "failed"}:
            return False
        if not str(getattr(job, "description", "") or "").strip():
            return False
        top_score = (
            self.session.query(JobTrackScore)
            .filter(JobTrackScore.job_post_id == job.id)
            .order_by(JobTrackScore.score.desc())
            .first()
        )
        best_score = float(top_score.score) if top_score is not None else 0.0
        return str(job.queue_state or "") == "shortlisted" or best_score >= 85

    def get_or_build(self, job_id: UUID, *, force: bool = False) -> CompanySnapshot:
        job = self.session.get(JobPost, job_id)
        if job is None:
            raise ValueError("Job not found.")
        if not self.eligible(job):
            raise ValueError("Company snapshot is unlocked only for shortlisted or high-fit roles.")

        snapshot = (
            self.session.query(CompanySnapshot)
            .filter(CompanySnapshot.job_post_id == job.id)
            .order_by(CompanySnapshot.updated_at.desc())
            .first()
        )
        if snapshot is not None and not force:
            return snapshot

        content, provider = self._build_snapshot_content(job)
        if snapshot is None:
            snapshot = CompanySnapshot(job_post_id=job.id, company_name=job.company)
            self.session.add(snapshot)

        snapshot.company_name = job.company
        snapshot.provider = provider
        snapshot.status = "ready"
        snapshot.content = content
        self.session.commit()
        self.session.refresh(snapshot)
        return snapshot

    def _build_snapshot_content(self, job: JobPost) -> tuple[dict[str, Any], str]:
        signals = JobSignalService(self.session).evaluate_job(job)
        company_source = (
            self.session.query(CareerPageSource)
            .filter(CareerPageSource.company == job.company)
            .order_by(CareerPageSource.created_at.desc())
            .first()
        )
        top_score = (
            self.session.query(JobTrackScore)
            .filter(JobTrackScore.job_post_id == job.id)
            .order_by(JobTrackScore.score.desc())
            .first()
        )
        matched = list(getattr(top_score, "matched_keywords", []) or [])[:5]
        source_url = job.company_url or (company_source.career_url if company_source else "")

        heuristic = {
            "headline": f"{job.company} snapshot for {job.title}",
            "mission_product": (
                f"Company site: {_company_host(source_url) or 'unknown'}."
                if source_url
                else "Mission is not stated directly in local data yet."
            ),
            "team_context": (
                f"Role family: {job.role_family or 'not classified yet'}. "
                f"Location: {job.location or job.country or 'not specified'}."
            ),
            "hiring_clues": [
                signals["freshness"]["label"],
                signals["confidence"]["label"],
                "Hiring surge" if signals.get("is_surging") else "No recent hiring surge signal",
            ],
            "talking_points": matched or [job.title, job.company],
            "open_questions": signals["suspicion"]["reasons"] or ["Ask how this role measures success in the first 90 days."],
        }

        try:
            result = self.router.generate_with_retry(
                role="small",
                system_prompt=(
                    "Summarize a company and role into a concise interview-prep snapshot. "
                    "Return JSON with keys: headline, mission_product, team_context, hiring_clues, talking_points, open_questions."
                ),
                user_prompt=(
                    f"Company: {job.company}\n"
                    f"Role: {job.title}\n"
                    f"Location: {job.location}\n"
                    f"Company URL: {job.company_url or ''}\n"
                    f"Job description:\n{job.description[:2500]}\n"
                    f"Signals: {heuristic}\n"
                ),
            )
            if isinstance(result, dict) and result.get("headline"):
                return result, "llm"
        except (ProviderUnavailableError, ValueError):
            pass

        return heuristic, "heuristic"
