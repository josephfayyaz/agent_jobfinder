from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any
from uuid import uuid4
from uuid import UUID

from sqlalchemy.orm import Session

from job_agent.config import settings
from job_agent.llm import LLMRouter, ProviderUnavailableError
from job_agent.models import JobPost, MasterProfile, ResumeDraft, ResumeTrack, WorkflowTask
from job_agent.services.documents import render_resume_tex
from job_agent.services.prompts import (
    build_reviewer_system_prompt,
    build_reviewer_user_prompt,
    build_revision_prompt,
    build_writer_system_prompt,
    build_writer_user_prompt,
)


@dataclass
class WorkflowContext:
    profile: MasterProfile
    track: ResumeTrack
    job: JobPost


class CVWorkflowService:
    def __init__(self, session: Session, router: LLMRouter | None = None) -> None:
        self.session = session
        self.router = router or LLMRouter()

    def queue_cv_workflow(self, job_post_id: UUID, resume_track_slug: str, force_cloud_review: bool) -> WorkflowTask:
        task = WorkflowTask(
            kind="cv_workflow",
            payload={
                "job_post_id": str(job_post_id),
                "resume_track_slug": resume_track_slug,
                "force_cloud_review": force_cloud_review,
            },
        )
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        return task

    def process_next_task(self) -> WorkflowTask | None:
        task = (
            self.session.query(WorkflowTask)
            .filter(WorkflowTask.status == "pending")
            .order_by(WorkflowTask.created_at.asc())
            .first()
        )
        if task is None:
            return None

        task.status = "running"
        self.session.commit()

        try:
            if task.kind != "cv_workflow":
                raise ValueError(f"Unsupported task kind: {task.kind}")
            task.result = self.run_cv_workflow(task.payload)
            task.status = "completed"
            task.error_message = ""
        except Exception as exc:
            task.status = "failed"
            task.error_message = str(exc)
        finally:
            self.session.commit()
            self.session.refresh(task)

        return task

    def run_cv_workflow(self, payload: dict[str, Any]) -> dict[str, Any]:
        context = self._load_context(payload["job_post_id"], payload["resume_track_slug"])
        draft_content, draft_provider = self._generate_draft(context)
        review = self._review_draft(context, draft_content, payload.get("force_cloud_review", False))
        final_content, final_provider = self._apply_review_decision(context, draft_content, review)

        draft = ResumeDraft(
            id=uuid4(),
            job_post_id=context.job.id,
            resume_track_id=context.track.id,
            provider=final_provider,
            status=review["decision"],
            score=float(review["score"]),
            content=final_content,
            review_feedback=review,
        )

        tex_path = render_resume_tex(
            profile=self._profile_dict(context.profile),
            job=self._job_dict(context.job),
            track=self._track_dict(context.track),
            content=final_content,
            draft_id=str(draft.id),
        )
        draft.tex_path = tex_path
        self.session.add(draft)
        self.session.commit()
        self.session.refresh(draft)

        return {
            "draft_id": str(draft.id),
            "score": draft.score,
            "decision": review["decision"],
            "provider": draft.provider,
            "tex_path": draft.tex_path,
        }

    def _load_context(self, job_post_id: str, track_slug: str) -> WorkflowContext:
        profile = self.session.get(MasterProfile, 1)
        if profile is None:
            raise ValueError("Master profile is missing.")
        job = self.session.get(JobPost, UUID(job_post_id))
        if job is None:
            raise ValueError("Job post not found.")
        track = self.session.query(ResumeTrack).filter(ResumeTrack.slug == track_slug).first()
        if track is None:
            raise ValueError("Resume track not found.")
        return WorkflowContext(profile=profile, track=track, job=job)

    def _generate_draft(self, context: WorkflowContext) -> tuple[dict[str, Any], str]:
        try:
            content = self.router.generate_with_lm_studio(
                model=settings.lm_studio_writer_model,
                system_prompt=build_writer_system_prompt(),
                user_prompt=build_writer_user_prompt(
                    self._profile_dict(context.profile),
                    self._track_dict(context.track),
                    self._job_dict(context.job),
                ),
            )
            return content, "lm_studio_writer"
        except ProviderUnavailableError:
            return self._heuristic_draft(context), "heuristic_writer"

    def _review_draft(
        self,
        context: WorkflowContext,
        draft_content: dict[str, Any],
        force_cloud_review: bool,
    ) -> dict[str, Any]:
        use_openai = force_cloud_review or settings.use_openai_review
        if use_openai:
            try:
                return self.router.generate_with_openai(
                    model=settings.openai_review_model,
                    system_prompt=build_reviewer_system_prompt(),
                    user_prompt=build_reviewer_user_prompt(
                        self._profile_dict(context.profile),
                        self._track_dict(context.track),
                        self._job_dict(context.job),
                        draft_content,
                    ),
                )
            except ProviderUnavailableError:
                pass

        try:
            return self.router.generate_with_lm_studio(
                model=settings.lm_studio_small_model,
                system_prompt=build_reviewer_system_prompt(),
                user_prompt=build_reviewer_user_prompt(
                    self._profile_dict(context.profile),
                    self._track_dict(context.track),
                    self._job_dict(context.job),
                    draft_content,
                ),
            )
        except ProviderUnavailableError:
            return self._heuristic_review(context, draft_content)

    def _apply_review_decision(
        self,
        context: WorkflowContext,
        draft_content: dict[str, Any],
        review: dict[str, Any],
    ) -> tuple[dict[str, Any], str]:
        score = float(review["score"])
        if score >= settings.cv_pass_score:
            return draft_content, "review_pass"

        if score >= settings.cv_revise_score:
            try:
                revised = self.router.generate_with_lm_studio(
                    model=settings.lm_studio_small_model or settings.lm_studio_writer_model,
                    system_prompt=build_writer_system_prompt(),
                    user_prompt=build_revision_prompt(self._job_dict(context.job), draft_content, review),
                )
                return revised, "lm_studio_revision"
            except ProviderUnavailableError:
                return self._heuristic_revision(draft_content, review), "heuristic_revision"

        if settings.use_openai_escalation:
            try:
                rewritten = self.router.generate_with_openai(
                    model=settings.openai_escalation_model,
                    system_prompt=build_writer_system_prompt(),
                    user_prompt=build_revision_prompt(self._job_dict(context.job), draft_content, review),
                )
                return rewritten, "openai_escalation"
            except ProviderUnavailableError:
                pass

        return self._heuristic_revision(draft_content, review), "heuristic_rewrite"

    def _profile_dict(self, profile: MasterProfile) -> dict[str, Any]:
        return {
            "full_name": profile.full_name,
            "email": profile.email,
            "phone": profile.phone,
            "location": profile.location,
            "linkedin_url": profile.linkedin_url,
            "github_url": profile.github_url,
            "public_brand_summary": profile.public_brand_summary,
            "experiences": profile.experiences,
            "projects": profile.projects,
            "education": profile.education,
            "certifications": profile.certifications,
            "achievements": profile.achievements,
            "global_skills": profile.global_skills,
            "additional_notes": profile.additional_notes,
        }

    def _track_dict(self, track: ResumeTrack) -> dict[str, Any]:
        return {
            "slug": track.slug,
            "title": track.title,
            "role_family": track.role_family,
            "baseline_summary": track.baseline_summary,
            "target_keywords": track.target_keywords,
            "emphasis": track.emphasis,
            "linkedin_strategy": track.linkedin_strategy,
            "github_strategy": track.github_strategy,
        }

    def _job_dict(self, job: JobPost) -> dict[str, Any]:
        return {
            "company": job.company,
            "title": job.title,
            "location": job.location,
            "role_track_hint": job.role_track_hint,
            "description": job.description,
            "extracted_metadata": job.extracted_metadata,
        }

    def _heuristic_draft(self, context: WorkflowContext) -> dict[str, Any]:
        keywords = set(context.track.target_keywords)
        experiences = context.profile.experiences or []
        projects = context.profile.projects or []
        global_skills = context.profile.global_skills or []

        selected_experiences = self._pick_relevant_items(experiences, keywords, "title")
        selected_projects = self._pick_relevant_items(projects, keywords, "name")
        selected_skills = [skill for skill in global_skills if skill.lower() in keywords][:10]
        if not selected_skills:
            selected_skills = context.track.emphasis.get("skills", [])[:8]

        return {
            "headline": context.track.title,
            "professional_summary": (
                f"{context.track.baseline_summary} Tailored for {context.job.title} at "
                f"{context.job.company}."
            ),
            "selected_experiences": selected_experiences[:3],
            "selected_projects": selected_projects[:2],
            "selected_skills": selected_skills,
            "tailoring_notes": [
                f"Focus on {context.track.role_family} relevance.",
                f"Match the terminology used in the job description for {context.job.company}.",
                "Keep the public narrative consistent across LinkedIn and GitHub.",
            ],
        }

    def _pick_relevant_items(self, items: list[dict], keywords: set[str], name_key: str) -> list[dict]:
        scored_items: list[tuple[int, dict]] = []
        for item in items:
            haystack = " ".join(
                [
                    str(item.get(name_key, "")),
                    str(item.get("summary", "")),
                    " ".join(item.get("bullets", [])),
                    " ".join(item.get("skills", [])),
                ]
            ).lower()
            score = sum(1 for keyword in keywords if keyword in haystack)
            scored_items.append((score, item))
        return [item for score, item in sorted(scored_items, key=lambda pair: pair[0], reverse=True) if score >= 0]

    def _heuristic_review(self, context: WorkflowContext, draft_content: dict[str, Any]) -> dict[str, Any]:
        job_text = f"{context.job.title} {context.job.description}".lower()
        job_tokens = [token.strip(".,:;()[]") for token in job_text.split()]
        token_counts = Counter(token for token in job_tokens if len(token) > 3)
        important_keywords = [token for token, _ in token_counts.most_common(12)]

        draft_text = " ".join(
            [
                draft_content.get("professional_summary", ""),
                " ".join(draft_content.get("selected_skills", [])),
                " ".join(note for note in draft_content.get("tailoring_notes", [])),
            ]
        ).lower()
        matched = [keyword for keyword in important_keywords if keyword in draft_text]
        score = min(100, 60 + len(matched) * 4 + len(draft_content.get("selected_experiences", [])) * 5)

        if score >= settings.cv_pass_score:
            decision = "pass"
        elif score >= settings.cv_revise_score:
            decision = "revise"
        else:
            decision = "rewrite"

        missing = [keyword for keyword in important_keywords if keyword not in matched][:5]
        return {
            "score": score,
            "decision": decision,
            "strengths": [
                f"Matched keywords: {', '.join(matched[:5]) or 'limited keyword match'}",
                f"Resume track selected: {context.track.title}",
            ],
            "gaps": [f"Missing or weak emphasis on: {', '.join(missing) or 'no major gaps found'}"],
            "must_fix": [f"Add clearer evidence for {item}" for item in missing[:3]],
            "keyword_coverage": matched,
            "revised_summary": (
                f"{draft_content.get('professional_summary', '')} Emphasize {', '.join(missing[:3])}."
            ).strip(),
        }

    def _heuristic_revision(self, draft_content: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
        revised = dict(draft_content)
        revised_summary = review.get("revised_summary")
        if revised_summary:
            revised["professional_summary"] = revised_summary
        must_fix = review.get("must_fix", [])
        revised["tailoring_notes"] = list(dict.fromkeys(draft_content.get("tailoring_notes", []) + must_fix))
        return revised
