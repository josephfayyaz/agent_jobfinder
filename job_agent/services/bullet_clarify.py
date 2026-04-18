from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from job_agent.config import settings
from job_agent.llm import LLMRouter
from job_agent.models import BulletClarification, ResumeDraft, ResumeTrack
from job_agent.services.prompts import (
    build_bullet_rewrite_prompt,
    build_bullet_rewrite_system_prompt,
    build_clarifying_questions_prompt,
    build_clarifying_questions_system_prompt,
    build_language_extraction_prompt,
    build_language_extraction_system_prompt,
)
from job_agent.services.workflows import CVWorkflowService


class BulletClarifyService:
    def __init__(self, session: Session, router: LLMRouter | None = None):
        self.session = session
        self.router = router or LLMRouter()

    def start_clarification(self, draft_id: UUID) -> BulletClarification:
        """
        Stage 1+2: Extract language map, generate questions if gaps exist.
        Returns a BulletClarification with status='pending_questions' or 'complete'
        (complete if no gaps found — skips straight to rewrite).
        """
        draft = self.session.get(ResumeDraft, draft_id)
        if draft is None:
            raise ValueError(f"Draft {draft_id} not found")

        track = self.session.get(ResumeTrack, draft.resume_track_id)
        if track is None:
            raise ValueError(f"Resume track {draft.resume_track_id} not found")
        wf = CVWorkflowService(self.session, self.router)
        context = wf._load_context(str(draft.job_post_id), track.slug)
        profile_dict = wf._context_profile_dict(context)
        job_dict = wf._job_dict(context.job)
        draft_content = draft.content or {}

        language_result = self.router.generate(
            role="small",
            system_prompt=build_language_extraction_system_prompt(),
            user_prompt=build_language_extraction_prompt(profile_dict, job_dict, draft_content),
        )
        language_map = list(language_result.get("language_map", []) or [])
        gap_count = int(language_result.get("gap_count", 0) or 0)

        questions: list[dict[str, Any]] = []
        if gap_count > 0:
            q_result = self.router.generate(
                role="small",
                system_prompt=build_clarifying_questions_system_prompt(),
                user_prompt=build_clarifying_questions_prompt(language_map, profile_dict, job_dict),
            )
            questions = list(q_result.get("questions", []) or [])

        clarification = BulletClarification(
            draft_id=draft_id,
            language_map={
                "map": language_map,
                "gap_count": gap_count,
                "summary": language_result.get("summary", ""),
            },
            questions=questions,
            status="pending_questions" if questions else "answered",
        )
        self.session.add(clarification)
        self.session.commit()
        self.session.refresh(clarification)

        if not questions:
            return self._run_rewrite(clarification, draft, profile_dict, job_dict, draft_content)

        return clarification

    def submit_answers(self, clarification_id: UUID, answers: list[dict]) -> BulletClarification:
        """
        Stage 3: Receive user answers, run rewrite with confirmed facts only.
        answers: [{question_id: str, answer: str, confirmed: bool}]
        """
        clarification = self.session.get(BulletClarification, clarification_id)
        if clarification is None:
            raise ValueError(f"Clarification session {clarification_id} not found")
        if clarification.status != "pending_questions":
            raise ValueError(f"Session is not awaiting answers (status={clarification.status})")

        clarification.answers = answers
        clarification.status = "answered"
        self.session.commit()

        draft = self.session.get(ResumeDraft, clarification.draft_id)
        if draft is None:
            raise ValueError(f"Draft {clarification.draft_id} not found")
        track = self.session.get(ResumeTrack, draft.resume_track_id)
        if track is None:
            raise ValueError(f"Resume track {draft.resume_track_id} not found")
        wf = CVWorkflowService(self.session, self.router)
        context = wf._load_context(str(draft.job_post_id), track.slug)
        profile_dict = wf._context_profile_dict(context)
        job_dict = wf._job_dict(context.job)
        draft_content = draft.content or {}

        return self._run_rewrite(clarification, draft, profile_dict, job_dict, draft_content)

    def _run_rewrite(
        self,
        clarification: BulletClarification,
        draft: ResumeDraft,
        profile_dict: dict,
        job_dict: dict,
        draft_content: dict,
    ) -> BulletClarification:
        del profile_dict
        word_limit = settings.bullet_clarify_word_limit
        rewrite_result = self.router.generate(
            role="writer",
            system_prompt=build_bullet_rewrite_system_prompt(word_limit),
            user_prompt=build_bullet_rewrite_prompt(
                clarification.language_map.get("map", []),
                clarification.answers,
                draft_content,
                job_dict,
                word_limit,
            ),
        )

        rewritten = self._enforce_word_limit(dict(rewrite_result or {}), word_limit)
        updated_content = self._merge_rewritten_bullets(draft_content, rewritten)
        draft.content = updated_content
        clarification.rewritten_bullets = rewritten
        clarification.status = "complete"
        self.session.commit()
        self.session.refresh(clarification)
        return clarification

    def _enforce_word_limit(self, rewrite_result: dict, word_limit: int) -> dict:
        """Truncate any bullet exceeding word_limit at the last complete word."""
        result = deepcopy(rewrite_result)
        for section in ("experiences", "projects"):
            for item in result.get(section, []) or []:
                fixed = []
                for bullet in item.get("bullets", []) or []:
                    words = str(bullet).split()
                    if len(words) > word_limit:
                        bullet = " ".join(words[:word_limit])
                    fixed.append(str(bullet))
                item["bullets"] = fixed
        return result

    def _merge_rewritten_bullets(self, draft_content: dict, rewritten: dict) -> dict:
        """
        Replace bullets in draft_content with rewritten versions,
        matched by original_title / original_name.
        """
        content = deepcopy(draft_content)
        rewrite_map_exp = {
            item.get("original_title", ""): item.get("bullets", [])
            for item in rewritten.get("experiences", []) or []
            if item.get("original_title")
        }
        rewrite_map_proj = {
            item.get("original_name", ""): item.get("bullets", [])
            for item in rewritten.get("projects", []) or []
            if item.get("original_name")
        }
        for exp in content.get("selected_experiences", []) or []:
            title = exp.get("title", "")
            if title in rewrite_map_exp:
                exp["bullets"] = rewrite_map_exp[title]
        for proj in content.get("selected_projects", []) or []:
            name = proj.get("name", "")
            if name in rewrite_map_proj:
                proj["bullets"] = rewrite_map_proj[name]
        return content
