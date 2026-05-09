from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from job_agent.config import settings
from job_agent.llm import LLMRouter, ProviderUnavailableError
from job_agent.models import ResumeDraft, ResumeTrack
from job_agent.providers import normalize_provider_mode
from job_agent.services.provider_input import shape_text_for_workflow
from job_agent.services.prompts import (
    build_compliance_matrix_prompt,
    build_compliance_matrix_system_prompt,
)
from job_agent.services.workflows import CVWorkflowService


class ComplianceMatrixService:
    def __init__(self, session: Session, router: LLMRouter | None = None):
        self.session = session
        self.router = router or LLMRouter()

    def generate(self, draft_id: UUID) -> dict[str, Any]:
        draft = self.session.get(ResumeDraft, draft_id)
        if draft is None:
            raise ValueError(f"Draft {draft_id} not found")

        track = self.session.get(ResumeTrack, draft.resume_track_id)
        if track is None:
            raise ValueError(f"Track for draft {draft_id} not found")

        workflow = CVWorkflowService(self.session, self.router)
        context = workflow._load_context(str(draft.job_post_id), track.slug)
        job_dict = workflow._job_dict(context.job)
        draft_content = draft.content or {}

        ranked_keywords = None
        if isinstance(draft.review_feedback, dict):
            ranked_keywords = draft.review_feedback.get("ranked_keywords")
        user_prompt = build_compliance_matrix_prompt(
            job_dict,
            draft_content,
            ranked_keywords=ranked_keywords,
        )
        safe_user_prompt = shape_text_for_workflow(
            user_prompt,
            workflow="compliance_matrix",
            provider_mode=normalize_provider_mode(getattr(settings, "llm_provider_mode", "openai")),
        )

        try:
            matrix = self.router.generate(
                role="small",
                system_prompt=build_compliance_matrix_system_prompt(),
                user_prompt=safe_user_prompt,
            )
        except (ProviderUnavailableError, ValueError):
            matrix = self._empty_matrix()

        matrix = self._normalize_matrix(matrix)
        feedback = dict(draft.review_feedback or {})
        feedback["compliance_matrix"] = matrix
        draft.review_feedback = feedback
        self.session.add(draft)
        self.session.commit()
        self.session.refresh(draft)
        return matrix

    def _empty_matrix(self) -> dict[str, Any]:
        return {
            "requirements": [],
            "strong_count": 0,
            "partial_count": 0,
            "missing_count": 0,
            "coverage_pct": 0.0,
            "error": "LM Studio unavailable",
        }

    def _normalize_matrix(self, matrix: Any) -> dict[str, Any]:
        if not isinstance(matrix, dict):
            return self._empty_matrix()
        normalized = dict(matrix)
        normalized.setdefault("requirements", [])
        normalized.setdefault("strong_count", 0)
        normalized.setdefault("partial_count", 0)
        normalized.setdefault("missing_count", 0)
        normalized.setdefault("coverage_pct", 0.0)
        if not isinstance(normalized.get("requirements"), list):
            normalized["requirements"] = []
        return normalized
