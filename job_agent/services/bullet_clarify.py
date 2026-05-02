from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from job_agent.config import settings
from job_agent.llm import LLMRouter, ProviderUnavailableError
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
        context = wf._load_context(
            str(draft.job_post_id),
            track.slug,
            candidate_id=draft.candidate_id,
        )
        profile_dict = wf._context_profile_dict(context)
        job_dict = wf._job_dict(context.job)
        draft_content = draft.content or {}

        try:
            language_result = self.router.generate(
                role="small",
                system_prompt=build_language_extraction_system_prompt(),
                user_prompt=build_language_extraction_prompt(profile_dict, job_dict, draft_content),
            )
        except (ProviderUnavailableError, ValueError):
            clarification = BulletClarification(
                draft_id=draft_id,
                status="complete",
                language_map={},
                questions=[],
                rewritten_bullets={},
            )
            self.session.add(clarification)
            self.session.commit()
            self.session.refresh(clarification)
            return clarification
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
        context = wf._load_context(
            str(draft.job_post_id),
            track.slug,
            candidate_id=draft.candidate_id,
        )
        profile_dict = wf._context_profile_dict(context)
        job_dict = wf._job_dict(context.job)
        draft_content = draft.content or {}

        try:
            return self._run_rewrite(clarification, draft, profile_dict, job_dict, draft_content)
        except (ProviderUnavailableError, ValueError):
            clarification.rewritten_bullets = {}
            clarification.status = "complete"
            self.session.commit()
            self.session.refresh(clarification)
            return clarification

    def suggest_bullet_rewrite(
        self,
        draft_id: UUID,
        bullet: str,
        *,
        target_section: str = "",
        target_item_index: int | None = None,
        target_bullet_index: int | None = None,
    ) -> BulletClarification:
        draft = self.session.get(ResumeDraft, draft_id)
        if draft is None:
            raise ValueError(f"Draft {draft_id} not found")

        bullet_text = bullet.strip()
        if not bullet_text:
            raise ValueError("bullet is required")

        track = self.session.get(ResumeTrack, draft.resume_track_id)
        if track is None:
            raise ValueError(f"Resume track {draft.resume_track_id} not found")

        wf = CVWorkflowService(self.session, self.router)
        context = wf._load_context(
            str(draft.job_post_id),
            track.slug,
            candidate_id=draft.candidate_id,
        )
        job_dict = wf._job_dict(context.job)
        draft_content = draft.content or {}
        word_limit = settings.bullet_clarify_word_limit

        system_prompt = (
            "You rewrite one resume bullet for accuracy and impact.\n"
            "Return valid JSON only with this schema: "
            '{"suggested_rewrite": "<rewritten bullet>"}.\n'
            "Rules:\n"
            f"- Maximum {word_limit} words.\n"
            "- Do not invent metrics, tools, dates, or scope.\n"
            "- Keep the rewrite factual and concise.\n"
            "- Produce exactly one rewritten bullet sentence."
        )
        user_prompt = (
            f"Job title: {job_dict.get('title', '')}\n"
            f"Company: {job_dict.get('company', '')}\n"
            f"Role context: {self._find_bullet_context(draft_content, bullet_text)}\n\n"
            f"Job description:\n{job_dict.get('description', '')}\n\n"
            f"Original bullet:\n{bullet_text}\n\n"
            "Rewrite the bullet so it is stronger, clearer, and better aligned to the role while staying truthful."
        )

        try:
            rewrite_result = self.router.generate(
                role="writer",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        except (ProviderUnavailableError, ValueError) as exc:
            raise ProviderUnavailableError("Bullet rewrite unavailable right now.") from exc

        suggested_rewrite = str(rewrite_result.get("suggested_rewrite", "") or "").strip()
        if not suggested_rewrite:
            raise ProviderUnavailableError("Bullet rewrite unavailable right now.")

        suggested_rewrite = self._truncate_bullet(" ".join(suggested_rewrite.split()), word_limit)
        located_section, located_item_index, located_bullet_index = self._resolve_target_location(
            draft_content,
            bullet_text,
            target_section=target_section,
            target_item_index=target_item_index,
            target_bullet_index=target_bullet_index,
        )
        clarification = BulletClarification(
            draft_id=draft_id,
            original_bullet=bullet_text,
            suggested_rewrite=suggested_rewrite,
            user_accepted=False,
            promoted_to_fact_sheet=False,
            target_section=located_section,
            target_item_index=located_item_index,
            target_bullet_index=located_bullet_index,
            language_map={},
            questions=[],
            answers=[],
            rewritten_bullets={},
            status="complete",
        )
        self.session.add(clarification)
        self.session.commit()
        self.session.refresh(clarification)
        return clarification

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
                    fixed.append(self._truncate_bullet(str(bullet), word_limit))
                item["bullets"] = fixed
        return result

    def _truncate_bullet(self, bullet: str, word_limit: int) -> str:
        words = str(bullet).split()
        if len(words) > word_limit:
            return " ".join(words[:word_limit])
        return str(bullet)

    def _find_bullet_context(self, draft_content: dict, bullet: str) -> str:
        for experience in draft_content.get("selected_experiences", []) or []:
            if bullet in (experience.get("bullets", []) or []):
                title = experience.get("title", "Unknown role")
                company = experience.get("company", "")
                if company:
                    return f"Experience bullet for {title} at {company}"
                return f"Experience bullet for {title}"

        for project in draft_content.get("selected_projects", []) or []:
            if bullet in (project.get("bullets", []) or []):
                return f"Project bullet for {project.get('name', 'Unknown project')}"

        return "Resume bullet"

    def _resolve_target_location(
        self,
        draft_content: dict,
        bullet: str,
        *,
        target_section: str,
        target_item_index: int | None,
        target_bullet_index: int | None,
    ) -> tuple[str, int | None, int | None]:
        normalized_section = target_section.strip().lower()
        if normalized_section in {"experience", "project"} and target_item_index is not None and target_bullet_index is not None:
            return normalized_section, target_item_index, target_bullet_index

        for section_name, items_key in (
            ("experience", "selected_experiences"),
            ("project", "selected_projects"),
        ):
            items = draft_content.get(items_key) or []
            for item_index, item in enumerate(items):
                bullets = list(item.get("bullets") or [])
                for bullet_index, existing_bullet in enumerate(bullets):
                    if str(existing_bullet) == bullet:
                        return section_name, item_index, bullet_index

        return "", None, None

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
