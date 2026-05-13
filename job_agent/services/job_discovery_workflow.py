"""Queued discovery orchestration for JobSpy + ATS search runs.

This module owns the long-running discovery pipeline that used to live inside
``CVWorkflowService``. Keeping it separate makes the workflow layer easier to
read without changing the worker/task API that the rest of the app uses.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from job_agent.config import settings
from job_agent.llm import LLMRouter
from job_agent.models import JobPost, WorkflowTask
from job_agent.search_preferences import (
    MAX_DISCOVERY_ROLES,
    compose_discovery_location,
    normalize_role_list,
    normalize_search_region,
    primary_search_country,
)
from job_agent.services.ats_discovery import AtsDiscoveryService
from job_agent.services.job_fetcher import JobFetcher
from job_agent.services.job_fit_scoring import JobFitScoringService
from job_agent.services.job_description_quality import get_job_description_quality
from job_agent.services.jobspy_service import JobSpyDiscoveryError, JobSpyService


class JobDiscoveryWorkflow:
    """Run one persisted job discovery task and stream truthful progress."""

    def __init__(self, session: Session, router: LLMRouter | None = None) -> None:
        self.session = session
        self.router = router or LLMRouter()
        self.jobspy_service_cls = JobSpyService
        self.ats_discovery_cls = AtsDiscoveryService
        self.job_fetcher_cls = JobFetcher
        self.fit_scoring_cls = JobFitScoringService

    @staticmethod
    def empty_counts() -> dict[str, int]:
        return {
            "roles_queried": 0,
            "raw_hits": 0,
            "ats_sources_scanned": 0,
            "ats_raw_hits": 0,
            "duplicates": 0,
            "rejected_by_country": 0,
            "rejected_by_region": 0,
            "rejected_by_role": 0,
            "rejected_by_seniority": 0,
            "queued_for_scoring": 0,
            "scored_jobs": 0,
            "saved_jobs": 0,
            "detail_enrichment_attempted": 0,
            "detail_enrichment_improved": 0,
            "detail_enrichment_skipped": 0,
            "detail_enrichment_failed": 0,
            "awaiting_enrichment_count": 0,
            "provider_scored_count": 0,
            "fallback_scored_count": 0,
            "ready_for_threshold_count": 0,
            "visible_after_threshold": 0,
            "visible_in_default_view": 0,
        }

    def result_payload(
        self,
        payload: dict[str, Any],
        *,
        stage: str,
        message: str,
        counts: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        return {
            "source": "user_initiated_discovery",
            "stage": stage,
            "message": message,
            "candidate_id": payload.get("candidate_id"),
            "provider_mode": payload.get("provider_mode"),
            "country": payload.get("country"),
            "region": payload.get("region"),
            "location": payload.get("location"),
            "roles": payload.get("roles", []),
            "seniority": payload.get("seniority"),
            "threshold": int(payload.get("threshold") or settings.discovery_min_fit_score),
            "visible_cap": int(payload.get("visible_cap") or settings.discovery_max_visible_jobs),
            "counts": counts or self.empty_counts(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def merge_counts(base: dict[str, int], delta: dict[str, Any]) -> None:
        for key in base:
            if key not in delta:
                continue
            try:
                base[key] += int(delta[key])
            except (TypeError, ValueError):
                continue

    def persist_progress(
        self,
        task: WorkflowTask,
        payload: dict[str, Any],
        *,
        stage: str,
        message: str,
        counts: dict[str, int],
    ) -> None:
        task.result = self.result_payload(payload, stage=stage, message=message, counts=dict(counts))
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)

    def run(self, task: WorkflowTask) -> dict[str, Any]:
        payload = dict(task.payload or {})
        roles = normalize_role_list(payload.get("roles") or settings.jobspy_discover_queries)[:MAX_DISCOVERY_ROLES]
        payload["roles"] = roles
        payload["country"] = primary_search_country(
            payload.get("country") or settings.job_search_countries,
            payload.get("location") or settings.jobspy_discover_location or "Italy",
        )
        payload["region"] = normalize_search_region(payload.get("region") or settings.job_search_region or "")
        payload["location"] = compose_discovery_location(
            [payload["country"]],
            payload["region"],
            payload.get("location") or settings.jobspy_discover_location or "Italy",
        )
        payload["seniority"] = str(payload.get("seniority") or settings.target_job_seniority or "junior")
        payload["provider_mode"] = str(payload.get("provider_mode") or settings.llm_provider_mode or "openai")
        payload["candidate_id"] = payload.get("candidate_id") or settings.default_candidate_id.strip() or None
        payload["threshold"] = int(payload.get("threshold") or settings.discovery_min_fit_score)
        payload["visible_cap"] = int(payload.get("visible_cap") or settings.discovery_max_visible_jobs)
        source_ids = payload.get("career_source_ids") or []
        if not isinstance(source_ids, list):
            source_ids = []
        payload["career_source_ids"] = [int(item) for item in source_ids if str(item).strip().isdigit()]
        payload["include_direct_company_sources"] = bool(payload.get("include_direct_company_sources", False))
        payload["source_policy"] = str(payload.get("source_policy") or "job_boards_only")
        payload["include_ats"] = bool(
            payload.get("include_ats", False)
            and payload["include_direct_company_sources"]
            and payload["career_source_ids"]
        )

        counts = self.empty_counts()
        if not settings.use_jobspy:
            self.persist_progress(
                task,
                payload,
                stage="failed",
                message="Job discovery is disabled. Enable JobSpy for explicit searches in Settings > Job Discovery first.",
                counts=counts,
            )
            raise ValueError("Job discovery is disabled. Enable JobSpy for explicit searches in Settings > Job Discovery first.")
        if not roles:
            self.persist_progress(
                task,
                payload,
                stage="failed",
                message="No desired roles configured for discovery.",
                counts=counts,
            )
            raise ValueError("No desired roles configured for discovery.")

        self.persist_progress(
            task,
            payload,
            stage="running",
            message="Starting user-initiated discovery for the selected search scope.",
            counts=counts,
        )

        def on_progress(progress: dict[str, Any]) -> None:
            progress_counts = dict(progress.get("counts") or counts)
            self.persist_progress(
                task,
                payload,
                stage=str(progress.get("stage") or "running"),
                message=str(progress.get("message") or "Discovery in progress."),
                counts=progress_counts,
            )

        try:
            discovery_result = self.jobspy_service_cls().discover_for_roles(
                roles=roles,
                location=payload["location"],
                selected_country=payload["country"],
                selected_region=payload["region"],
                seniority=payload["seniority"],
                session=self.session,
                limit=int(payload.get("limit") or settings.jobspy_default_limit),
                sources=list(payload.get("sources") or ["linkedin"]),
                progress_callback=on_progress,
            )
            self.merge_counts(counts, discovery_result)
            saved_job_ids = [str(item) for item in discovery_result.get("saved_job_ids") or [] if str(item).strip()]
        except JobSpyDiscoveryError as exc:
            self.persist_progress(
                task,
                payload,
                stage="failed",
                message=str(exc),
                counts=counts,
            )
            raise ValueError(str(exc)) from exc
        except Exception as exc:
            self.persist_progress(
                task,
                payload,
                stage="failed",
                message=str(exc) or "Job discovery failed unexpectedly.",
                counts=counts,
            )
            raise

        if payload["include_ats"]:
            self.persist_progress(
                task,
                payload,
                stage="querying_ats",
                message="Querying selected company ATS feeds.",
                counts=counts,
            )
            ats_result = self.ats_discovery_cls(self.session).discover_active_sources(
                roles=roles,
                selected_country=payload["country"],
                selected_region=payload["region"],
                seniority=payload["seniority"],
                source_ids=payload["career_source_ids"],
                progress_callback=on_progress,
            )
            self.merge_counts(counts, ats_result)
            saved_job_ids.extend(
                [
                    str(item)
                    for item in ats_result.get("saved_job_ids") or []
                    if str(item).strip() and str(item) not in saved_job_ids
                ]
            )

        if saved_job_ids:
            self.persist_progress(
                task,
                payload,
                stage="detail_enrichment",
                message="Running selective JobSpy detail enrichment for promising survivors.",
                counts=counts,
            )
            detail_result = self.jobspy_service_cls().detail_enrich_survivors(
                saved_job_ids=saved_job_ids,
                session=self.session,
                selected_country=payload["country"],
                seniority=payload["seniority"],
                roles=roles,
                progress_callback=on_progress,
            )
            self.merge_counts(counts, detail_result)

        if saved_job_ids:
            self.persist_progress(
                task,
                payload,
                stage="fetching_descriptions",
                message="Fetching full job descriptions for saved discovery results.",
                counts=counts,
            )
            fetcher = self.job_fetcher_cls()
            for index, job_id in enumerate(saved_job_ids, start=1):
                normalized_job_id = self._coerce_job_uuid(job_id)
                if normalized_job_id is not None:
                    job = self.session.get(JobPost, normalized_job_id)
                    if job is not None:
                        fetcher.enrich_job(job, self.session)
                self.persist_progress(
                    task,
                    payload,
                    stage="fetching_descriptions",
                    message=f"Fetched descriptions for {index} of {len(saved_job_ids)} jobs.",
                    counts=counts,
                )

            self.persist_progress(
                task,
                payload,
                stage="scoring",
                message="Scoring saved jobs against the active candidate profile.",
                counts=counts,
            )
            scorer = self.fit_scoring_cls(self.session, router=self.router)
            for index, job_id in enumerate(saved_job_ids, start=1):
                scorer.score_and_persist(
                    job_id,
                    candidate_id=str(payload.get("candidate_id") or ""),
                    force=True,
                    commit=False,
                )
                counts["scored_jobs"] = index
                self.persist_progress(
                    task,
                    payload,
                    stage="scoring",
                    message=f"Scored {index} of {len(saved_job_ids)} jobs.",
                    counts=counts,
                )
            self.session.commit()

        score_state_counts = self.score_state_counts(
            saved_job_ids=saved_job_ids,
            candidate_id=str(payload.get("candidate_id") or ""),
            threshold=int(payload["threshold"]),
        )
        self.merge_counts(counts, score_state_counts)
        counts["visible_after_threshold"] = int(score_state_counts.get("visible_after_threshold") or 0)
        counts["visible_in_default_view"] = min(
            int(payload["visible_cap"]),
            int(score_state_counts.get("jd_ready_after_threshold") or 0),
        )

        if int(counts.get("saved_jobs", 0)) == 0:
            message = "Discovery completed, but no jobs were saved into the queue."
            stage = "completed_zero_results"
        elif int(counts.get("visible_in_default_view", 0)) == 0 and int(counts.get("awaiting_enrichment_count", 0)) > 0:
            message = (
                f"Discovery completed. {counts['awaiting_enrichment_count']} jobs need stronger descriptions "
                "before they can clear the fit threshold. Check the Awaiting enrichment lane."
            )
            stage = "completed_awaiting_enrichment"
        elif int(counts.get("visible_in_default_view", 0)) == 0:
            message = "Discovery completed, but no jobs are visible in the default queue yet."
            stage = "completed_zero_results"
        else:
            message = (
                f"Discovery completed. Saved {counts['saved_jobs']} jobs from the selected sources, "
                f"and {counts['visible_in_default_view']} are JD-ready in the default review queue."
            )
            stage = "completed"

        return self.result_payload(payload, stage=stage, message=message, counts=counts)

    def score_state_counts(
        self,
        *,
        saved_job_ids: list[str],
        candidate_id: str,
        threshold: int,
    ) -> dict[str, int]:
        counts = {
            "awaiting_enrichment_count": 0,
            "provider_scored_count": 0,
            "fallback_scored_count": 0,
            "ready_for_threshold_count": 0,
            "visible_after_threshold": 0,
            "jd_ready_after_threshold": 0,
        }
        if not saved_job_ids:
            return counts
        for job_id in saved_job_ids:
            normalized_job_id = self._coerce_job_uuid(job_id)
            if normalized_job_id is None:
                continue
            job = self.session.get(JobPost, normalized_job_id)
            if job is None:
                continue
            fit_map = dict((job.extracted_metadata or {}).get("candidate_fit") or {})
            fit = fit_map.get(candidate_id) if candidate_id else None
            if not isinstance(fit, dict):
                continue
            score_source = str(fit.get("score_source") or "")
            threshold_eligible = bool(fit.get("threshold_eligible", True))
            if not threshold_eligible or score_source == "awaiting_enrichment":
                counts["awaiting_enrichment_count"] += 1
            elif score_source == "provider":
                counts["provider_scored_count"] += 1
            elif score_source == "fallback":
                counts["fallback_scored_count"] += 1

            if threshold_eligible:
                counts["ready_for_threshold_count"] += 1
                try:
                    fit_score = int(round(float(fit.get("fit_score") or 0)))
                except (TypeError, ValueError):
                    fit_score = 0
                if fit_score >= threshold:
                    counts["visible_after_threshold"] += 1
                    if bool(get_job_description_quality(job).get("ready_for_provider_scoring", False)):
                        counts["jd_ready_after_threshold"] += 1
        return counts

    @staticmethod
    def _coerce_job_uuid(job_id: str) -> UUID | None:
        try:
            return UUID(str(job_id))
        except (TypeError, ValueError):
            return None
