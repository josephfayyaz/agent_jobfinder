from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import logging
import re
from typing import Any
from uuid import uuid4
from uuid import UUID

from sqlalchemy.orm import Session

from job_agent.config import settings
from job_agent.llm import LLMRouter, ProviderUnavailableError
from job_agent.models import (
    Candidate,
    EducationFact,
    ExperienceFact,
    FactSource,
    JobPost,
    MasterProfile,
    ProjectFact,
    ResumeDraft,
    ResumeTrack,
    WorkflowTask,
)
from job_agent.services.documents import render_resume_tex
from job_agent.services.experience_selection import (
    select_experiences_for_job,
    select_projects_for_job,
)
from job_agent.services.prompts import (
    build_reviewer_system_prompt,
    build_reviewer_user_prompt,
    build_revision_prompt,
    build_writer_system_prompt,
    build_writer_user_prompt,
    resolve_presentation_mode,
)

logger = logging.getLogger(__name__)


@dataclass
class WorkflowContext:
    profile: MasterProfile | None
    track: ResumeTrack
    job: JobPost
    candidate: Candidate | None = None


class CVWorkflowService:
    def __init__(self, session: Session, router: LLMRouter | None = None) -> None:
        self.session = session
        self.router = router or LLMRouter()

    def queue_cv_workflow(
        self,
        job_post_id: UUID,
        resume_track_slug: str,
        force_cloud_review: bool = False,
    ) -> WorkflowTask:
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
        draft_content, draft_provider, presentation_mode, inferred_additions = self._generate_draft(context)
        logger.info("Draft generated | provider=%s | job=%s", draft_provider, payload.get("job_post_id"))
        review = self._review_draft(
            context,
            draft_content,
            payload.get("force_cloud_review", False),
            presentation_mode,
        )
        logger.info(
            "Draft reviewed | score=%.0f | decision=%s",
            review.get("score", 0),
            review.get("decision", "unknown"),
        )
        final_content, final_provider = self._apply_review_decision(context, draft_content, review)
        logger.info("Final draft | provider=%s | score=%.0f", final_provider, float(review["score"]))

        draft = ResumeDraft(
            id=uuid4(),
            job_post_id=context.job.id,
            resume_track_id=context.track.id,
            provider=final_provider,
            status=review["decision"],
            score=float(review["score"]),
            content=final_content,
            inferred_additions=inferred_additions or None,
            review_feedback=review,
        )

        profile_data = self._context_profile_dict(context)
        tex_path = render_resume_tex(
            profile=profile_data,
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
        candidate: Candidate | None = None
        profile: MasterProfile | None = None
        candidate_id = settings.default_candidate_id.strip()
        if candidate_id:
            candidate = self.session.get(Candidate, candidate_id)
            if candidate is None:
                raise ValueError(f"Candidate not found for default_candidate_id={candidate_id}.")
        else:
            profile = self.session.get(MasterProfile, 1)
            if profile is None:
                raise ValueError("Master profile is missing.")
        job = self.session.get(JobPost, UUID(job_post_id))
        if job is None:
            raise ValueError("Job post not found.")
        track = self.session.query(ResumeTrack).filter(ResumeTrack.slug == track_slug).first()
        if track is None:
            raise ValueError("Resume track not found.")
        return WorkflowContext(profile=profile, track=track, job=job, candidate=candidate)

    def _generate_draft(
        self,
        context: WorkflowContext,
    ) -> tuple[dict[str, Any], str, str, list[dict[str, Any]]]:
        presentation_mode = resolve_presentation_mode(
            target_seniority=settings.target_job_seniority,
            job_seniority=context.job.seniority,
        )
        latest_source = self.session.query(FactSource).order_by(FactSource.imported_at.desc()).first()
        selected_experiences: list[Any] | None = None
        selected_projects: list[Any] | None = None
        if latest_source is not None:
            experiences = (
                self.session.query(ExperienceFact)
                .filter(ExperienceFact.fact_source_id == latest_source.id)
                .all()
            )
            projects = (
                self.session.query(ProjectFact)
                .filter(ProjectFact.fact_source_id == latest_source.id)
                .all()
            )
            selected_experiences = select_experiences_for_job(
                experiences=experiences,
                job=context.job,
                target_keywords=context.track.target_keywords or [],
                presentation_mode=presentation_mode,
                track_slug=context.track.slug,
            )
            selected_projects = select_projects_for_job(
                projects=projects,
                job=context.job,
                target_keywords=context.track.target_keywords or [],
                presentation_mode=presentation_mode,
                track_slug=context.track.slug,
            )

        profile_dict = self._context_profile_dict(context)
        track_dict = self._track_dict(context.track)
        job_dict = self._job_dict(context.job)
        try:
            raw_content = self.router.generate(
                role="writer",
                system_prompt=build_writer_system_prompt(),
                user_prompt=build_writer_user_prompt(
                    profile_dict,
                    track_dict,
                    job_dict,
                    selected_experiences=selected_experiences,
                    selected_projects=selected_projects,
                    presentation_mode=presentation_mode,
                    target_seniority=settings.target_job_seniority,
                ),
            )
            content, inferred_additions = self._normalize_writer_output(raw_content, context)
            return content, "lm_studio_writer", presentation_mode, inferred_additions
        except ProviderUnavailableError:
            return self._heuristic_draft(context), "heuristic_writer", presentation_mode, []

    def _review_draft(
        self,
        context: WorkflowContext,
        draft_content: dict[str, Any],
        force_cloud_review: bool,
        presentation_mode: str,
    ) -> dict[str, Any]:
        review: dict[str, Any] | None = None
        profile_dict = self._context_profile_dict(context)
        use_cloud = force_cloud_review or settings.use_claude_final_review or settings.use_openai_review
        if use_cloud:
            if settings.use_claude_final_review or force_cloud_review:
                try:
                    review = self.router.generate_with_claude(
                        system_prompt=build_reviewer_system_prompt(),
                        user_prompt=build_reviewer_user_prompt(
                            profile_dict,
                            self._track_dict(context.track),
                            self._job_dict(context.job),
                            draft_content,
                            presentation_mode=presentation_mode,
                        ),
                    )
                except ProviderUnavailableError:
                    pass
            if settings.use_openai_review:
                try:
                    review = self.router.generate_with_openai(
                        model=settings.openai_review_model,
                        system_prompt=build_reviewer_system_prompt(),
                        user_prompt=build_reviewer_user_prompt(
                            profile_dict,
                            self._track_dict(context.track),
                            self._job_dict(context.job),
                            draft_content,
                            presentation_mode=presentation_mode,
                        ),
                    )
                except ProviderUnavailableError:
                    pass

        if review is None:
            try:
                review = self.router.generate(
                    role="small",
                    system_prompt=build_reviewer_system_prompt(),
                    user_prompt=build_reviewer_user_prompt(
                        profile_dict,
                        self._track_dict(context.track),
                        self._job_dict(context.job),
                        draft_content,
                        presentation_mode=presentation_mode,
                    ),
                )
            except ProviderUnavailableError:
                review = self._heuristic_review(context, draft_content)

        review = self._apply_presentation_mismatch_gate(
            context=context,
            draft_content=draft_content,
            review=review,
            presentation_mode=presentation_mode,
        )
        review["comp_assessment"] = review.get("comp_assessment", {})
        review["legitimacy_score"] = review.get("legitimacy_score", 100)
        review["red_flags"] = review.get("red_flags", [])
        return review

    def _normalize_writer_output(
        self,
        writer_output: dict[str, Any],
        context: WorkflowContext,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        payload = dict(writer_output or {})
        inferred_additions = payload.pop("inferred_additions", []) or []

        if "professional_summary" in payload or "selected_experiences" in payload:
            if "selected_experiences" not in payload and "experience" in payload:
                payload["selected_experiences"] = self._normalize_experience_entries(payload.get("experience"))
            if "selected_projects" not in payload and "projects" in payload:
                payload["selected_projects"] = self._normalize_project_entries(payload.get("projects"))
            if "selected_skills" not in payload and "skills" in payload:
                payload["selected_skills"] = self._flatten_skill_payload(payload.get("skills"))
            payload.setdefault("headline", context.job.title or context.track.title)
            if "professional_summary" not in payload:
                payload["professional_summary"] = str(payload.get("summary", "") or "")
            payload.setdefault("selected_experiences", [])
            payload.setdefault("selected_projects", [])
            payload.setdefault("selected_skills", [])
            payload.setdefault("tailoring_notes", [])
            return payload, inferred_additions

        normalized = {
            "headline": str(payload.get("headline") or context.job.title or context.track.title),
            "professional_summary": str(payload.get("summary") or payload.get("professional_summary") or ""),
            "selected_experiences": self._normalize_experience_entries(payload.get("experience")),
            "selected_projects": self._normalize_project_entries(payload.get("projects")),
            "selected_skills": self._flatten_skill_payload(payload.get("skills")),
            "tailoring_notes": list(payload.get("tailoring_notes") or []),
        }
        return normalized, inferred_additions

    def _normalize_experience_entries(self, items: Any) -> list[dict[str, Any]]:
        experiences: list[dict[str, Any]] = []
        for item in items or []:
            if not isinstance(item, dict):
                continue
            experiences.append(
                {
                    "title": item.get("title") or item.get("role", ""),
                    "company": item.get("company") or item.get("org", ""),
                    "location": item.get("location", ""),
                    "dates": item.get("dates", ""),
                    "bullets": list(item.get("bullets") or []),
                }
            )
        return experiences

    def _normalize_project_entries(self, items: Any) -> list[dict[str, Any]]:
        projects: list[dict[str, Any]] = []
        for item in items or []:
            if not isinstance(item, dict):
                continue
            projects.append(
                {
                    "name": item.get("name", ""),
                    "description": item.get("description", ""),
                    "repo_url": item.get("repo_url", ""),
                    "bullets": list(item.get("bullets") or []),
                }
            )
        return projects

    def _flatten_skill_payload(self, payload: Any) -> list[str]:
        if isinstance(payload, list):
            return [str(item) for item in payload if item not in (None, "")]
        if not isinstance(payload, dict):
            return []
        ordered: list[str] = []
        seen: set[str] = set()
        for key in ("languages", "frameworks", "tools", "cloud", "other"):
            for item in payload.get(key, []):
                normalized = str(item).strip()
                if not normalized or normalized.lower() in seen:
                    continue
                seen.add(normalized.lower())
                ordered.append(normalized)
        return ordered

    def _apply_presentation_mismatch_gate(
        self,
        context: WorkflowContext,
        draft_content: dict[str, Any],
        review: dict[str, Any],
        presentation_mode: str,
    ) -> dict[str, Any]:
        if presentation_mode != "junior":
            return review

        headline_summary = " ".join(
            [
                str(draft_content.get("headline", "") or ""),
                str(draft_content.get("professional_summary", "") or ""),
            ]
        )
        draft_text_parts = [
            headline_summary,
            " ".join(str(skill) for skill in draft_content.get("selected_skills", [])),
            " ".join(str(note) for note in draft_content.get("tailoring_notes", [])),
        ]
        for experience in draft_content.get("selected_experiences", []):
            draft_text_parts.extend(
                [
                    str(experience.get("title", "") or ""),
                    str(experience.get("company", "") or ""),
                    " ".join(str(bullet) for bullet in experience.get("bullets", [])),
                ]
            )
        for project in draft_content.get("selected_projects", []):
            draft_text_parts.extend(
                [
                    str(project.get("name", "") or ""),
                    str(project.get("description", "") or ""),
                    " ".join(str(bullet) for bullet in project.get("bullets", [])),
                ]
            )
        draft_text = " ".join(part for part in draft_text_parts if part)

        source_profile = self._context_profile_dict(context)
        support_parts = [str(source_profile.get("public_brand_summary", "") or "")]
        for experience in source_profile.get("experiences") or []:
            support_parts.extend(
                [
                    str(experience.get("title") or experience.get("role_title") or ""),
                    str(experience.get("summary", "") or ""),
                    " ".join(str(bullet) for bullet in experience.get("bullets", [])),
                ]
            )
        for project in source_profile.get("projects") or []:
            support_parts.extend(
                [
                    str(project.get("name", "") or ""),
                    str(project.get("summary") or project.get("short_resume_line") or ""),
                    " ".join(str(bullet) for bullet in project.get("bullets", [])),
                ]
            )
        support_text = " ".join(part for part in support_parts if part)

        gaps = list(review.get("gaps") or [])
        if re.search(r"\b\d\+?\s+years?\s+of\s+experience\b", headline_summary, re.IGNORECASE):
            gaps.append("[MISMATCH] Aggregate years-of-experience phrasing found in headline or summary.")
        for verb in ("led", "architected", "owned"):
            if re.search(rf"\b{verb}\b", draft_text, re.IGNORECASE) and not re.search(
                rf"\b{verb}\b",
                support_text,
                re.IGNORECASE,
            ):
                gaps.append(f"[MISMATCH] Senior verb '{verb}' appears without fact-sheet support.")
        if re.search(r"\bstudent\b", draft_text, re.IGNORECASE):
            gaps.append("[MISMATCH] The draft uses prohibited education-only framing.")
        review["gaps"] = list(dict.fromkeys(gaps))
        return review

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
            # Targeted revision: small model is fast enough for edits
            try:
                revised = self.router.generate(
                    role="small",
                    system_prompt=build_writer_system_prompt(),
                    user_prompt=build_revision_prompt(
                        self._job_dict(context.job), draft_content, review
                    ),
                )
                return revised, "lm_studio_revision"
            except ProviderUnavailableError:
                return self._heuristic_revision(draft_content, review), "heuristic_revision"

        # Score below revise threshold: escalate to cloud or heuristic rewrite
        if settings.use_claude_final_review:
            try:
                rewritten = self.router.generate_with_claude(
                    system_prompt=build_writer_system_prompt(),
                    user_prompt=build_revision_prompt(
                        self._job_dict(context.job), draft_content, review
                    ),
                )
                return rewritten, "claude_rewrite"
            except ProviderUnavailableError:
                pass

        if settings.use_openai_escalation:
            try:
                rewritten = self.router.generate_with_openai(
                    model=settings.openai_escalation_model,
                    system_prompt=build_writer_system_prompt(),
                    user_prompt=build_revision_prompt(
                        self._job_dict(context.job), draft_content, review
                    ),
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

    def _candidate_profile_dict(self, candidate: Candidate) -> dict[str, Any]:
        experience_query = self.session.query(ExperienceFact).filter_by(candidate_id=candidate.id)
        if hasattr(ExperienceFact, "display_order"):
            experience_query = experience_query.order_by(getattr(ExperienceFact, "display_order"))
        experiences = []
        for experience in experience_query.all():
            tools = list(experience.tools_and_tech or [])
            role_title = experience.role_title or ""
            experiences.append(
                {
                    "role_title": role_title,
                    "title": role_title,
                    "company": getattr(experience, "company", None) or getattr(experience, "organization", "") or "",
                    "start_date": experience.start_date or "",
                    "end_date": experience.end_date or "",
                    "bullets": list(experience.verified_core_facts or []),
                    "tools": tools,
                    "skills": tools,
                    "summary": "",
                }
            )

        projects = []
        for project in self.session.query(ProjectFact).filter_by(candidate_id=candidate.id).all():
            tools = list(project.tools_and_tech or [])
            summary = project.short_resume_line or ""
            projects.append(
                {
                    "name": project.project_name,
                    "summary": summary,
                    "short_resume_line": summary,
                    "tools": tools,
                    "skills": tools,
                    "bullets": list(project.verified_core_facts or []),
                }
            )

        education = []
        for education_fact in self.session.query(EducationFact).filter_by(candidate_id=candidate.id).all():
            year = (
                getattr(education_fact, "graduation_year", None)
                or education_fact.end_date
                or ""
            )
            education.append(
                {
                    "degree": education_fact.degree or "",
                    "institution": education_fact.institution or "",
                    "year": year,
                }
            )

        skills_json = candidate.skills_json or {}
        return {
            "full_name": candidate.full_name,
            "email": candidate.email or "",
            "phone": "",
            "location": "",
            "linkedin_url": "",
            "github_url": "",
            "public_brand_summary": "",
            "global_skills": list(skills_json.get("skills", [])) if isinstance(skills_json, dict) else [],
            "experiences": experiences,
            "projects": projects,
            "education": education,
            "certifications": [],
            "achievements": [],
            "additional_notes": {},
        }

    def _context_profile_dict(self, context: WorkflowContext) -> dict[str, Any]:
        if context.candidate is not None:
            return self._candidate_profile_dict(context.candidate)
        if context.profile is not None:
            return self._profile_dict(context.profile)
        raise ValueError("Workflow context has neither profile nor candidate.")

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
        profile_data = self._context_profile_dict(context)
        experiences = profile_data.get("experiences") or []
        projects = profile_data.get("projects") or []
        global_skills = profile_data.get("global_skills") or []

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

    def generate_enhancement_proposals(self, draft_id: UUID) -> list:
        """Generate expert enhancement proposals for a draft and store them in DB."""
        from job_agent.models import EnhancementProposal
        from job_agent.services.prompts import build_enhancement_prompt

        draft = self.session.get(ResumeDraft, draft_id)
        if draft is None:
            raise ValueError(f"Draft {draft_id} not found")

        track = self.session.get(ResumeTrack, draft.resume_track_id)
        if track is None:
            raise ValueError(f"Resume track {draft.resume_track_id} not found")

        context = self._load_context(str(draft.job_post_id), track.slug)

        reviewer_gaps = []
        if draft.review_feedback:
            reviewer_gaps = draft.review_feedback.get("gaps", [])

        try:
            result = self.router.generate(
                role="mid",
                system_prompt=(
                    "You are an expert resume enhancement advisor. "
                    "Return valid JSON only. No markdown, no extra text."
                ),
                user_prompt=build_enhancement_prompt(
                    self._context_profile_dict(context),
                    self._job_dict(context.job),
                    draft.content or {},
                    reviewer_gaps,
                ),
            )
        except ProviderUnavailableError:
            result = self.router.generate(
                role="small",
                system_prompt=(
                    "You are an expert resume enhancement advisor. "
                    "Return valid JSON only. No markdown, no extra text."
                ),
                user_prompt=build_enhancement_prompt(
                    self._context_profile_dict(context),
                    self._job_dict(context.job),
                    draft.content or {},
                    reviewer_gaps,
                ),
            )

        proposals = []
        for proposal_payload in result.get("proposals", []):
            proposal = EnhancementProposal(
                draft_id=draft_id,
                section=proposal_payload.get("section", ""),
                original_text=proposal_payload.get("original_text", ""),
                proposed_text=proposal_payload.get("proposed_text", ""),
                rationale=proposal_payload.get("rationale", ""),
                question_for_user=proposal_payload.get("question_for_user", ""),
            )
            self.session.add(proposal)
            proposals.append(proposal)

        self.session.commit()
        return proposals

    def apply_approved_enhancements(self, draft_id: UUID, approved_ids: list[UUID]) -> ResumeDraft:
        """Apply user-approved enhancement proposals to the draft content."""
        import json

        from job_agent.models import EnhancementProposal

        draft = self.session.get(ResumeDraft, draft_id)
        if draft is None:
            raise ValueError(f"Draft {draft_id} not found")

        proposals = (
            self.session.query(EnhancementProposal)
            .filter(EnhancementProposal.draft_id == draft_id)
            .all()
        )

        content = dict(draft.content or {})

        for proposal in proposals:
            if proposal.id in approved_ids:
                proposal.approved = True
                content_str = json.dumps(content)
                content_str = content_str.replace(
                    json.dumps(proposal.original_text)[1:-1],
                    json.dumps(proposal.proposed_text)[1:-1],
                )
                try:
                    content = json.loads(content_str)
                except json.JSONDecodeError:
                    pass
            else:
                proposal.approved = False

        draft.content = content
        self.session.commit()
        self.session.refresh(draft)
        return draft
