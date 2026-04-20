from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from job_agent.llm import LLMRouter, ProviderUnavailableError
from job_agent.models import JobPost, ResumeTrack
from job_agent.services.prompts import (
    build_rejection_prediction_prompt,
    build_rejection_prediction_system_prompt,
)
from job_agent.services.workflows import CVWorkflowService


class RejectionPredictionService:
    def __init__(self, session: Session, router: LLMRouter | None = None):
        self.session = session
        self.router = router or LLMRouter()

    def predict(self, job_post_id: UUID) -> dict[str, Any]:
        job = self.session.get(JobPost, job_post_id)
        if job is None:
            raise ValueError(f"JobPost {job_post_id} not found")

        track = self.session.query(ResumeTrack).filter_by(active=True).first()
        if track is None:
            raise ValueError("No active resume track found")

        workflow = CVWorkflowService(self.session, self.router)
        context = workflow._load_context(str(job_post_id), track.slug)
        profile_dict = workflow._context_profile_dict(context)
        job_dict = workflow._job_dict(job)
        job_dict["seniority"] = job.seniority

        try:
            prediction = self.router.generate(
                role="small",
                system_prompt=build_rejection_prediction_system_prompt(),
                user_prompt=build_rejection_prediction_prompt(job_dict, profile_dict),
            )
        except (ProviderUnavailableError, ValueError):
            prediction = {
                "risks": [],
                "hard_blocker_count": 0,
                "soft_blocker_count": 0,
                "overall_risk": "unknown",
                "recommendation": "LM Studio unavailable - prediction skipped",
                "error": "provider_unavailable",
            }

        metadata = dict(job.extracted_metadata or {})
        metadata["rejection_risks"] = prediction
        job.extracted_metadata = metadata
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return prediction
