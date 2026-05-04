"""Core orchestration for queued job discovery and CV generation.

This module is intentionally the workflow layer, not the rendering layer and
not the route layer. It coordinates:

- loading the correct candidate/profile + job + track context
- running discovery and scoring in the right order
- generating, reviewing, and persisting CV drafts
- keeping draft state bound to the candidate used at generation time

When future refactors split this file, preserve that ownership boundary.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import logging
import re
from typing import Any
from uuid import uuid4
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from job_agent.config import settings
from job_agent.llm import LLMRouter, ProviderUnavailableError
from job_agent.models import (
    Candidate,
    CandidateSourceFile,
    EducationFact,
    ExperienceFact,
    FactSource,
    JobTrackScore,
    JobPost,
    MasterProfile,
    ProjectFact,
    ResumeDraft,
    ResumeTrack,
    VerifiedCandidateFact,
    WorkflowTask,
)
from job_agent.parsers.fact_sheet import as_list, parse_fact_sheet
from job_agent.services.documents import render_resume_tex
from job_agent.services.draft_preview import build_preview_annotations
from job_agent.services.experience_selection import (
    select_experiences_for_job,
    select_projects_for_job,
)
from job_agent.services.ats_discovery import AtsDiscoveryService
from job_agent.services.job_fetcher import JobFetcher
from job_agent.services.job_fit_scoring import JobFitScoringService
from job_agent.services.job_discovery_workflow import JobDiscoveryWorkflow
from job_agent.services.job_target_profile import build_cv_target_fit, build_job_target_profile
from job_agent.services.jobspy_service import JobSpyService
from job_agent.services.profile_readiness import READINESS_BLOCK, evaluate_profile_readiness
from job_agent.services.prompts import (
    build_keyword_extraction_prompt,
    build_keyword_extraction_system_prompt,
    build_reviewer_system_prompt,
    build_reviewer_user_prompt,
    build_revision_prompt,
    build_writer_system_prompt,
    build_writer_user_prompt,
    resolve_presentation_mode,
)

logger = logging.getLogger(__name__)
MAX_VERIFIED_FACTS_FOR_PROMPT = 50
_GENERIC_TRACK_STOPWORDS = {
    "and",
    "the",
    "for",
    "with",
    "from",
    "role",
    "analyst",
    "specialist",
    "assistant",
}


@dataclass
class WorkflowContext:
    profile: MasterProfile | None
    track: ResumeTrack
    job: JobPost
    candidate: Candidate | None = None


class CVWorkflowService:
    """Coordinate the app's long-running discovery and CV workflows.

    The service owns orchestration and persistence decisions. Helper services
    own focused logic such as JD parsing, scoring, preview annotation, and PDF
    rendering.
    """
    def __init__(self, session: Session, router: LLMRouter | None = None) -> None:
        self.session = session
        self.router = router or LLMRouter()

    def queue_cv_workflow(
        self,
        job_post_id: UUID,
        resume_track_slug: str,
        force_cloud_review: bool = False,
        candidate_id: str | None = None,
    ) -> WorkflowTask:
        """Queue a CV task with a snapshot of the active candidate.

        Snapshotting the candidate at queue time prevents later changes to the
        default candidate from mutating who the draft is generated for.
        """
        resolved_candidate_id = candidate_id
        if resolved_candidate_id is None:
            resolved_candidate_id = settings.default_candidate_id.strip() or None
        task = WorkflowTask(
            kind="cv_workflow",
            payload={
                "job_post_id": str(job_post_id),
                "resume_track_slug": resume_track_slug,
                "force_cloud_review": force_cloud_review,
                "candidate_id": resolved_candidate_id,
            },
        )
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        return task

    @staticmethod
    def _empty_discovery_counts() -> dict[str, int]:
        return JobDiscoveryWorkflow.empty_counts()

    def _discovery_result(
        self,
        payload: dict[str, Any],
        *,
        stage: str,
        message: str,
        counts: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        return JobDiscoveryWorkflow(self.session, router=self.router).result_payload(
            payload,
            stage=stage,
            message=message,
            counts=counts or self._empty_discovery_counts(),
        )

    @staticmethod
    def _merge_discovery_counts(base: dict[str, int], delta: dict[str, Any]) -> None:
        JobDiscoveryWorkflow.merge_counts(base, delta)

    def _persist_discovery_progress(
        self,
        task: WorkflowTask,
        payload: dict[str, Any],
        *,
        stage: str,
        message: str,
        counts: dict[str, int],
    ) -> None:
        JobDiscoveryWorkflow(self.session, router=self.router).persist_progress(
            task,
            payload,
            stage=stage,
            message=message,
            counts=counts,
        )

    def run_job_discovery(self, task: WorkflowTask) -> dict[str, Any]:
        workflow = JobDiscoveryWorkflow(self.session, router=self.router)
        workflow.jobspy_service_cls = JobSpyService
        workflow.ats_discovery_cls = AtsDiscoveryService
        workflow.job_fetcher_cls = JobFetcher
        workflow.fit_scoring_cls = JobFitScoringService
        workflow.persist_progress = lambda task, payload, *, stage, message, counts: self._persist_discovery_progress(
            task,
            payload,
            stage=stage,
            message=message,
            counts=counts,
        )
        workflow.result_payload = lambda payload, *, stage, message, counts=None: self._discovery_result(
            payload,
            stage=stage,
            message=message,
            counts=counts,
        )
        workflow.merge_counts = lambda base, delta: self._merge_discovery_counts(base, delta)
        return workflow.run(task)

    def _count_visible_jobs(
        self,
        *,
        saved_job_ids: list[str],
        candidate_id: str,
        threshold: int,
    ) -> int:
        counts = JobDiscoveryWorkflow(self.session, router=self.router).score_state_counts(
            saved_job_ids=saved_job_ids,
            candidate_id=candidate_id,
            threshold=threshold,
        )
        return int(counts.get("visible_after_threshold") or 0)

    def _score_state_counts(
        self,
        *,
        saved_job_ids: list[str],
        candidate_id: str,
        threshold: int,
    ) -> dict[str, int]:
        return JobDiscoveryWorkflow(self.session, router=self.router).score_state_counts(
            saved_job_ids=saved_job_ids,
            candidate_id=candidate_id,
            threshold=threshold,
        )

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
            if task.kind == "cv_workflow":
                task.result = self.run_cv_workflow(task.payload)
            elif task.kind == "job_discovery":
                task.result = self.run_job_discovery(task)
            else:
                raise ValueError(f"Unsupported task kind: {task.kind}")
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
        """Execute the full CV pipeline for one job + track + candidate."""
        context = self._load_context(
            payload["job_post_id"],
            payload["resume_track_slug"],
            candidate_id=payload.get("candidate_id"),
        )
        readiness = self.profile_readiness_for_context(context)
        if readiness["status"] == READINESS_BLOCK:
            raise ValueError(
                "Profile readiness is insufficient for final CV generation. "
                + "; ".join(readiness.get("reasons") or ["Add more grounded evidence first."])
            )
        confirmed_facts = [
            answer
            for answer in payload.get("confirmed_facts", [])
            if answer.get("confirmed") and str(answer.get("answer") or "").strip()
        ]
        draft_content, draft_provider, presentation_mode, inferred_additions, ranked_keywords = self._generate_draft(
            context, confirmed_facts=confirmed_facts or None
        )
        missing_keywords = self._compute_missing_keywords(
            profile_dict=self._context_profile_dict(context),
            ranked_keywords=ranked_keywords,
        )
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
        final_content = self._backfill_sparse_draft(
            context=context,
            draft_content=final_content,
            selected_experiences=None,
            selected_projects=None,
            presentation_mode=presentation_mode,
        )
        final_content = self._sanitize_truthful_sparse_profile(context, final_content)
        logger.info("Final draft | provider=%s | score=%.0f", final_provider, float(review["score"]))

        # Store ranked keywords in review_feedback so G1 compliance matrix can use them later
        if ranked_keywords:
            review["ranked_keywords"] = ranked_keywords
        if missing_keywords:
            review["missing_keywords"] = missing_keywords
        if confirmed_facts:
            review["confirmed_facts"] = confirmed_facts
        review["profile_readiness"] = readiness

        profile_data = self._context_profile_dict(context)
        target_profile = self._ensure_job_target_profile(context.job)
        review["target_fit_map"] = build_cv_target_fit(
            job_profile=target_profile,
            profile_data=profile_data,
            verified_facts=self._load_verified_facts_for_prompt(context),
        )
        review["recommended_improvements"] = review["target_fit_map"].get("recommended_improvements", [])
        review["preview_annotations"] = build_preview_annotations(
            draft_content=final_content,
            profile_data=profile_data,
            accepted_item_ids=[],
        )

        draft = ResumeDraft(
            id=uuid4(),
            job_post_id=context.job.id,
            resume_track_id=context.track.id,
            candidate_id=context.candidate.id if context.candidate is not None else None,
            provider=final_provider,
            status=review["decision"],
            score=float(review["score"]),
            content=final_content,
            inferred_additions=inferred_additions or None,
            review_feedback=review,
        )

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

    def profile_readiness_for_context(self, context: WorkflowContext) -> dict[str, Any]:
        return evaluate_profile_readiness(self._context_profile_dict(context))

    def profile_readiness_for_job(self, job_post_id: str, track_slug: str) -> dict[str, Any]:
        context = self._load_context(job_post_id, track_slug)
        return self.profile_readiness_for_context(context)

    def _load_context(
        self,
        job_post_id: str,
        track_slug: str,
        *,
        candidate_id: str | None = None,
    ) -> WorkflowContext:
        """Load the exact job/track/candidate context for one workflow run.

        If an explicit candidate_id is supplied, it takes precedence over the
        current default candidate. That keeps saved drafts and queued tasks
        stable across restarts and later candidate switching.
        """
        candidate: Candidate | None = None
        profile: MasterProfile | None = None
        resolved_candidate_id = (candidate_id or "").strip()
        if not resolved_candidate_id:
            resolved_candidate_id = settings.default_candidate_id.strip()
        if resolved_candidate_id:
            candidate = self.session.get(Candidate, resolved_candidate_id)
            if candidate is None:
                logger.warning(
                    "Candidate not found for candidate_id=%s. Falling back to MasterProfile.",
                    resolved_candidate_id,
                )
                resolved_candidate_id = ""
        if not resolved_candidate_id:
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
        confirmed_facts: list[dict[str, Any]] | None = None,
    ) -> tuple[dict[str, Any], str, str, list[dict[str, Any]], list[dict[str, Any]] | None]:
        presentation_mode = resolve_presentation_mode(
            target_seniority=settings.target_job_seniority,
            job_seniority=context.job.seniority,
        )
        verified_facts = self._load_verified_facts_for_prompt(context)
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
        track_dict = self._prompt_track_dict(context)
        job_dict = self._job_dict(context.job)
        ranked_keywords: list[dict[str, Any]] | None = None
        truth_constraints = self._truth_constraints_for_profile(context, profile_dict)

        try:
            generate_fn = self.router.generate_with_retry if isinstance(self.router, LLMRouter) else self.router.generate
            kw_result = generate_fn(
                role="small",
                system_prompt=build_keyword_extraction_system_prompt(),
                user_prompt=build_keyword_extraction_prompt(job_dict),
            )
            ranked_keywords = kw_result.get("keywords") or None
            if ranked_keywords:
                logger.info(
                    "Keywords extracted | job=%s | count=%d | top=%s",
                    context.job.id,
                    len(ranked_keywords),
                    ranked_keywords[0].get("term", ""),
                )
        except ProviderUnavailableError:
            logger.warning("Keyword extraction skipped - LM Studio unavailable")
        except Exception as exc:
            logger.warning("Keyword extraction failed: %s", exc)

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
                    ranked_keywords=ranked_keywords,
                    confirmed_facts=confirmed_facts,
                    verified_facts=verified_facts or None,
                    truth_constraints=truth_constraints,
                ),
            )
            content, inferred_additions = self._normalize_writer_output(raw_content, context)
            content = self._backfill_sparse_draft(
                context=context,
                draft_content=content,
                selected_experiences=selected_experiences,
                selected_projects=selected_projects,
                presentation_mode=presentation_mode,
            )
            content = self._sanitize_truthful_sparse_profile(context, content)
            return content, "lm_studio_writer", presentation_mode, inferred_additions, ranked_keywords
        except ProviderUnavailableError:
            return self._sanitize_truthful_sparse_profile(context, self._heuristic_draft(context)), "heuristic_writer", presentation_mode, [], ranked_keywords

    def _load_verified_facts_for_prompt(self, context: WorkflowContext) -> list[dict[str, str]]:
        candidate_id = context.candidate.id if context.candidate is not None else None
        query = self.session.query(VerifiedCandidateFact).filter(VerifiedCandidateFact.is_active.is_(True))
        if candidate_id:
            query = query.filter(
                or_(
                    VerifiedCandidateFact.candidate_id == candidate_id,
                    VerifiedCandidateFact.candidate_id.is_(None),
                )
            )
        else:
            query = query.filter(VerifiedCandidateFact.candidate_id.is_(None))

        rows = (
            query.order_by(VerifiedCandidateFact.created_at.desc())
            .limit(MAX_VERIFIED_FACTS_FOR_PROMPT)
            .all()
        )
        rows.reverse()
        return [
            {
                "gap_label": row.gap_label,
                "evidence": row.evidence,
                "fact_type": row.fact_type or "general",
            }
            for row in rows
        ]

    def _compute_missing_keywords(
        self,
        *,
        profile_dict: dict[str, Any],
        ranked_keywords: list[dict[str, Any]] | None,
    ) -> list[str]:
        """Return JD keywords that are not present in the candidate's known skills."""
        if not ranked_keywords:
            return []

        candidate_skills_lower = {
            str(skill).strip().casefold()
            for skill in (profile_dict.get("global_skills") or [])
            if str(skill).strip()
        }
        missing: list[str] = []
        for keyword in ranked_keywords:
            if not isinstance(keyword, dict):
                continue
            term = str(keyword.get("term") or keyword.get("keyword") or "").strip()
            if not term:
                continue
            if term.casefold() not in candidate_skills_lower:
                missing.append(term)
        return list(dict.fromkeys(missing))

    def _review_draft(
        self,
        context: WorkflowContext,
        draft_content: dict[str, Any],
        force_cloud_review: bool,
        presentation_mode: str,
    ) -> dict[str, Any]:
        del force_cloud_review
        review: dict[str, Any] | None = None
        profile_dict = self._context_profile_dict(context)

        if review is None:
            try:
                review = self.router.generate(
                    role="small",
                    system_prompt=build_reviewer_system_prompt(),
                    user_prompt=build_reviewer_user_prompt(
                        profile_dict,
                        self._prompt_track_dict(context),
                        self._job_dict(context.job),
                        draft_content,
                        presentation_mode=presentation_mode,
                    ),
                )
            except (ProviderUnavailableError, ValueError):
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
            except (ProviderUnavailableError, ValueError):
                return self._heuristic_revision(draft_content, review), "heuristic_revision"

        # Score below revise threshold: use deterministic rewrite.
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
            bullets = list(experience.verified_core_facts or []) or list(experience.enriched_description_bank or [])
            dates = "–".join(
                part for part in [str(experience.start_date or ""), str(experience.end_date or "")] if part
            )
            experiences.append(
                {
                    "role_title": role_title,
                    "title": role_title,
                    "company": getattr(experience, "company", None) or getattr(experience, "organization", "") or "",
                    "organization": getattr(experience, "organization", "") or "",
                    "location": experience.location or "",
                    "start_date": experience.start_date or "",
                    "end_date": experience.end_date or "",
                    "dates": dates,
                    "bullets": bullets,
                    "tools": tools,
                    "skills": tools,
                    "summary": bullets[0] if bullets else "",
                }
            )

        projects = []
        for project in self.session.query(ProjectFact).filter_by(candidate_id=candidate.id).all():
            tools = list(project.tools_and_tech or [])
            summary = project.short_resume_line or ""
            bullets = list(project.verified_core_facts or [])
            if not bullets and summary:
                bullets = [summary]
            projects.append(
                {
                    "name": project.project_name,
                    "summary": summary,
                    "description": summary,
                    "short_resume_line": summary,
                    "tools": tools,
                    "repo_url": project.repo_url or "",
                    "skills": tools,
                    "bullets": bullets,
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
                    "field": education_fact.field or "",
                    "institution": education_fact.institution or "",
                    "status": education_fact.status or "",
                    "start_date": education_fact.start_date or "",
                    "end_date": education_fact.end_date or "",
                    "year": year,
                }
            )

        skills_json = candidate.skills_json or {}
        global_skills: list[str] = []
        if isinstance(skills_json, dict):
            seen: set[str] = set()
            for value in skills_json.values():
                if isinstance(value, list):
                    items = value
                elif value in (None, ""):
                    items = []
                else:
                    items = [value]
                for item in items:
                    normalized = str(item).strip()
                    if not normalized or normalized.casefold() in seen:
                        continue
                    seen.add(normalized.casefold())
                    global_skills.append(normalized)
        profile = {
            "full_name": candidate.full_name,
            "email": candidate.email or "",
            "phone": "",
            "location": "",
            "linkedin_url": "",
            "github_url": "",
            "public_brand_summary": "",
            "global_skills": global_skills,
            "experiences": experiences,
            "projects": projects,
            "education": education,
            "languages": list(candidate.spoken_languages or []),
            "certifications": [],
            "achievements": [],
            "additional_notes": {},
        }
        profile = self._overlay_structured_source_profile(candidate.id, profile)
        return profile

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

    def _prompt_track_dict(self, context: WorkflowContext) -> dict[str, Any]:
        track_dict = self._track_dict(context.track)
        job_id = getattr(context.job, "id", None)
        track_id = getattr(context.track, "id", None)
        if job_id is None or track_id is None:
            return track_dict
        score_row = (
            self.session.query(JobTrackScore)
            .filter(
                JobTrackScore.job_post_id == job_id,
                JobTrackScore.resume_track_id == track_id,
            )
            .first()
        )
        score = float(getattr(score_row, "score", 0.0) or 0.0)
        matched_keywords = list(getattr(score_row, "matched_keywords", []) or [])
        if matched_keywords or score >= 60:
            return track_dict

        title_tokens = [
            token
            for token in re.findall(r"[A-Za-z][A-Za-z&+/.-]{2,}", str(context.job.title or ""))
            if token.casefold() not in _GENERIC_TRACK_STOPWORDS
        ]
        slug = re.sub(r"[^a-z0-9]+", "-", str(context.job.title or "role").lower()).strip("-") or "role"
        return {
            "slug": f"job-targeted-{slug}",
            "title": f"{context.job.title or 'Role'} Targeted Track",
            "role_family": context.job.role_family or "general",
            "baseline_summary": (
                f"Tailor this resume specifically for {context.job.title or 'the role'} using only documented candidate evidence."
            ),
            "target_keywords": title_tokens[:8],
            "emphasis": {
                "focus": [context.job.title or "Target role", context.job.company or "Target company"],
                "mode": "truthful_role_targeting",
            },
            "linkedin_strategy": "",
            "github_strategy": "",
        }

    def _job_dict(self, job: JobPost) -> dict[str, Any]:
        target_profile = self._ensure_job_target_profile(job)
        return {
            "company": job.company,
            "title": job.title,
            "location": job.location,
            "role_track_hint": job.role_track_hint,
            "description": job.description,
            "extracted_metadata": job.extracted_metadata,
            "target_profile": target_profile,
        }

    def _heuristic_draft(self, context: WorkflowContext) -> dict[str, Any]:
        keywords = set(context.track.target_keywords)
        prompt_track = self._prompt_track_dict(context)
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
            "headline": context.job.title or prompt_track.get("title") or context.track.title,
            "professional_summary": (
                f"{prompt_track.get('baseline_summary', context.track.baseline_summary)} Tailored for {context.job.title} at "
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

    def _ensure_job_target_profile(self, job: JobPost) -> dict[str, Any]:
        metadata = dict(getattr(job, "extracted_metadata", {}) or {})
        existing = metadata.get("target_profile")
        if isinstance(existing, dict) and existing.get("requirements"):
            return existing
        target_profile = build_job_target_profile(
            title=str(getattr(job, "title", "") or ""),
            company=str(getattr(job, "company", "") or ""),
            description=str(getattr(job, "description", "") or ""),
            location=str(getattr(job, "location", "") or ""),
            country=str(getattr(job, "country", "") or ""),
            source_url=str(getattr(job, "source_url", "") or ""),
        )
        metadata["target_profile"] = target_profile
        job.extracted_metadata = metadata
        self.session.add(job)
        self.session.flush()
        return target_profile

    def _overlay_structured_source_profile(self, candidate_id: str, profile: dict[str, Any]) -> dict[str, Any]:
        source_row = (
            self.session.query(CandidateSourceFile)
            .filter(CandidateSourceFile.candidate_id == candidate_id)
            .order_by(CandidateSourceFile.created_at.desc())
            .first()
        )
        text = source_row.extracted_text if source_row is not None else ""
        if not text or "MASTER FACT SHEET" not in text or "SECTION:" not in text:
            return profile

        try:
            parsed = parse_fact_sheet(text)
        except Exception:
            return profile

        core = parsed.get("core_profile") or {}
        summary_bank = parsed.get("summary_bank") or {}
        skills_inventory = parsed.get("skills_inventory") or {}
        enriched = dict(profile)
        enriched["location"] = core.get("CURRENT_LOCATION") or profile.get("location") or ""
        enriched["phone"] = core.get("PHONE") or profile.get("phone") or ""
        enriched["linkedin_url"] = core.get("LINKEDIN") or profile.get("linkedin_url") or ""
        enriched["github_url"] = core.get("GITHUB") or profile.get("github_url") or ""
        enriched["public_brand_summary"] = (
            core.get("CURRENT_POSITIONING")
            or summary_bank.get("SHORT_PROFILE_LINE_FOR_LINKEDIN_OR_TOP_OF_CV")
            or profile.get("public_brand_summary")
            or ""
        )
        if not enriched.get("global_skills"):
            flattened: list[str] = []
            seen: set[str] = set()
            for raw_values in skills_inventory.values():
                for item in as_list(raw_values):
                    normalized = item.strip()
                    if not normalized or normalized.casefold() in seen:
                        continue
                    seen.add(normalized.casefold())
                    flattened.append(normalized)
            enriched["global_skills"] = flattened
        return enriched

    def _backfill_sparse_draft(
        self,
        *,
        context: WorkflowContext,
        draft_content: dict[str, Any],
        selected_experiences: list[Any] | None,
        selected_projects: list[Any] | None,
        presentation_mode: str,
    ) -> dict[str, Any]:
        patched = dict(draft_content)
        profile_data = self._context_profile_dict(context)
        if not str(patched.get("headline") or "").strip():
            patched["headline"] = context.job.title or context.track.title
        summary_text = str(patched.get("professional_summary") or "").strip()
        if not summary_text or len(summary_text.split()) < 8:
            fallback_summary = str(profile_data.get("public_brand_summary") or "").strip()
            if not fallback_summary:
                fallback_summary = (
                    f"{context.track.baseline_summary} Tailored for {context.job.title} at {context.job.company}."
                )
            patched["professional_summary"] = (
                fallback_summary
            )
        if not (patched.get("selected_experiences") or []) and selected_experiences:
            patched["selected_experiences"] = [
                {
                    "title": str(sel.experience_fact.role_title or ""),
                    "company": str(sel.experience_fact.organization or ""),
                    "location": str(sel.experience_fact.location or ""),
                    "dates": "–".join(part for part in [str(sel.experience_fact.start_date or ""), str(sel.experience_fact.end_date or "")] if part),
                    "bullets": list(sel.selected_bullets or []),
                }
                for sel in selected_experiences
            ]
        if not (patched.get("selected_experiences") or []):
            patched["selected_experiences"] = list(profile_data.get("experiences") or [])[:3]
        if not (patched.get("selected_projects") or []) and selected_projects:
            patched["selected_projects"] = [
                {
                    "name": str(sel.project_fact.project_name or ""),
                    "description": str(sel.project_fact.short_resume_line or ""),
                    "repo_url": str(sel.project_fact.repo_url or ""),
                    "bullets": list(sel.selected_bullets or []),
                }
                for sel in selected_projects
            ]
        if not (patched.get("selected_projects") or []):
            patched["selected_projects"] = list(profile_data.get("projects") or [])[:2]

        patched["selected_experiences"] = self._top_up_experience_entries(
            current=list(patched.get("selected_experiences") or []),
            profile_data=profile_data,
            presentation_mode=presentation_mode,
        )
        patched["selected_projects"] = self._top_up_project_entries(
            current=list(patched.get("selected_projects") or []),
            profile_data=profile_data,
            presentation_mode=presentation_mode,
        )
        selected_skills = list(patched.get("selected_skills") or [])
        if len(selected_skills) < 4:
            profile_skills = profile_data.get("global_skills") or []
            seen = {str(skill).casefold() for skill in selected_skills}
            for skill in profile_skills:
                normalized = str(skill).strip()
                if not normalized or normalized.casefold() in seen:
                    continue
                seen.add(normalized.casefold())
                selected_skills.append(normalized)
                if len(selected_skills) >= 12:
                    break
            if not selected_skills:
                selected_skills = list(context.track.emphasis.get("skills", [])[:8])
            patched["selected_skills"] = selected_skills
        return patched

    def _experience_row_key(self, item: dict[str, Any]) -> tuple[str, str]:
        return (
            str(item.get("title") or item.get("role_title") or "").strip().casefold(),
            str(item.get("company") or item.get("organization") or "").strip().casefold(),
        )

    def _project_row_key(self, item: dict[str, Any]) -> str:
        return str(item.get("name") or "").strip().casefold()

    def _draft_bullet_count(self, rows: list[dict[str, Any]]) -> int:
        return sum(
            len([str(bullet).strip() for bullet in (row.get("bullets") or []) if str(bullet).strip()])
            for row in rows
            if isinstance(row, dict)
        )

    def _top_up_experience_entries(
        self,
        *,
        current: list[dict[str, Any]],
        profile_data: dict[str, Any],
        presentation_mode: str,
    ) -> list[dict[str, Any]]:
        targets = {
            "junior": {"roles": 4, "bullets": 6},
            "mid": {"roles": 4, "bullets": 8},
            "senior": {"roles": 5, "bullets": 10},
        }[presentation_mode if presentation_mode in {"junior", "mid", "senior"} else "junior"]
        rows = [dict(item) for item in current if isinstance(item, dict)]
        seen = {self._experience_row_key(item) for item in rows}
        profile_rows = [dict(item) for item in (profile_data.get("experiences") or []) if isinstance(item, dict)]
        for row in profile_rows:
            if len(rows) >= targets["roles"] and self._draft_bullet_count(rows) >= targets["bullets"]:
                break
            key = self._experience_row_key(row)
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)
        return rows

    def _top_up_project_entries(
        self,
        *,
        current: list[dict[str, Any]],
        profile_data: dict[str, Any],
        presentation_mode: str,
    ) -> list[dict[str, Any]]:
        targets = {
            "junior": {"projects": 2, "bullets": 3},
            "mid": {"projects": 2, "bullets": 4},
            "senior": {"projects": 3, "bullets": 5},
        }[presentation_mode if presentation_mode in {"junior", "mid", "senior"} else "junior"]
        rows = [dict(item) for item in current if isinstance(item, dict)]
        seen = {self._project_row_key(item) for item in rows}
        profile_rows = [dict(item) for item in (profile_data.get("projects") or []) if isinstance(item, dict)]
        for row in profile_rows:
            if len(rows) >= targets["projects"] and self._draft_bullet_count(rows) >= targets["bullets"]:
                break
            key = self._project_row_key(row)
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)
        return rows

    def _truth_constraints_for_profile(
        self,
        context: WorkflowContext,
        profile_data: dict[str, Any],
    ) -> list[str]:
        constraints: list[str] = []
        experiences = list(profile_data.get("experiences") or [])
        projects = list(profile_data.get("projects") or [])
        has_experience = any(
            str(item.get("title") or item.get("role_title") or "").strip() or list(item.get("bullets") or [])
            for item in experiences
            if isinstance(item, dict)
        )
        if not has_experience:
            constraints.extend(
                [
                    "The profile has no structured employment history. Do not invent employers, date ranges, years of experience, or work responsibilities.",
                    "Use education, project evidence, and profile notes only. If the evidence is thin, keep the summary conservative and explicit.",
                    "Do not introduce metrics, counts, percentages, or business impact unless the exact evidence appears in the supplied profile facts.",
                    f"Do not claim seniority beyond what the documented evidence supports for {context.job.title or 'this role'}.",
                ]
            )
        if projects and not has_experience:
            constraints.append(
                "When using project or profile-note evidence, keep it in project-style bullets instead of rewriting it as formal employment."
            )
        return constraints

    def _sanitize_truthful_sparse_profile(
        self,
        context: WorkflowContext,
        draft_content: dict[str, Any],
    ) -> dict[str, Any]:
        profile_data = self._context_profile_dict(context)
        experiences = list(profile_data.get("experiences") or [])
        has_experience = any(
            str(item.get("title") or item.get("role_title") or "").strip() or list(item.get("bullets") or [])
            for item in experiences
            if isinstance(item, dict)
        )
        if has_experience:
            return draft_content

        sanitized = dict(draft_content or {})
        sanitized["headline"] = str(sanitized.get("headline") or context.job.title or context.track.title)
        sanitized["professional_summary"] = self._conservative_sparse_summary(context, profile_data)
        sanitized["selected_experiences"] = []
        sanitized["selected_projects"] = self._truthful_project_entries(profile_data)
        sanitized["selected_skills"] = self._truthful_skill_entries(profile_data)
        return sanitized

    def _truthful_project_entries(self, profile_data: dict[str, Any]) -> list[dict[str, Any]]:
        truthful_projects: list[dict[str, Any]] = []
        for project in list(profile_data.get("projects") or [])[:3]:
            if not isinstance(project, dict):
                continue
            bullets = [str(bullet).strip() for bullet in (project.get("bullets") or []) if str(bullet).strip()]
            if not bullets:
                summary = str(project.get("summary") or project.get("short_resume_line") or project.get("description") or "").strip()
                if summary:
                    bullets = [summary]
            truthful_projects.append(
                {
                    "name": str(project.get("name") or "Profile Evidence"),
                    "description": str(project.get("summary") or project.get("short_resume_line") or project.get("description") or "").strip(),
                    "repo_url": str(project.get("repo_url") or ""),
                    "bullets": bullets[:3],
                }
            )
        return truthful_projects

    def _truthful_skill_entries(self, profile_data: dict[str, Any]) -> list[str]:
        skills = [str(skill).strip() for skill in (profile_data.get("global_skills") or []) if str(skill).strip()]
        deduped: list[str] = []
        seen: set[str] = set()
        for skill in skills:
            key = skill.casefold()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(skill)
            if len(deduped) >= 10:
                break
        return deduped

    def _conservative_sparse_summary(self, context: WorkflowContext, profile_data: dict[str, Any]) -> str:
        job_title = str(context.job.title or "the role").strip()
        education_items = list(profile_data.get("education") or [])
        degree_bits: list[str] = []
        if education_items and isinstance(education_items[0], dict):
            degree = str(education_items[0].get("degree") or "").strip()
            field = str(education_items[0].get("field") or "").strip()
            if degree and field:
                degree_bits.append(f"{degree} in {field}")
            elif degree:
                degree_bits.append(degree)
            elif field:
                degree_bits.append(field)
        education_label = degree_bits[0] if degree_bits else "Candidate"

        projects = self._truthful_project_entries(profile_data)
        evidence_text = ""
        if projects:
            evidence_text = str(projects[0].get("description") or "")
            if not evidence_text:
                bullets = list(projects[0].get("bullets") or [])
                evidence_text = str(bullets[0] if bullets else "")
        evidence_text = evidence_text.rstrip(". ")
        skills = self._truthful_skill_entries(profile_data)
        skill_text = ", ".join(skills[:4])

        summary_parts = [f"{education_label} candidate targeting {job_title} roles."]
        if evidence_text:
            summary_parts.append(f"Documented evidence includes: {evidence_text}.")
        if skill_text:
            summary_parts.append(f"Working knowledge of {skill_text}.")
        return " ".join(summary_parts).strip()

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
