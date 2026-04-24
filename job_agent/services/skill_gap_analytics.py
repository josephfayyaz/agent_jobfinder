"""Aggregate missing ATS keywords across non-archived drafts."""
from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy.orm import Session

from job_agent.models import ResumeDraft


class SkillGapAnalyticsService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def compute(self, candidate_id: str, top_n: int = 20) -> dict[str, Any]:
        """
        Return top missing skills across non-archived drafts.

        ResumeDraft is not candidate-scoped in the current schema. The
        candidate_id parameter is kept for API stability and future
        multi-candidate filtering; today this is a single-user aggregate.
        """
        if not candidate_id:
            return self._empty()

        drafts = (
            self.session.query(ResumeDraft)
            .filter(ResumeDraft.review_feedback.is_not(None))
            .all()
        )

        gap_counter: Counter[str] = Counter()
        total_drafts = 0
        display_terms: dict[str, str] = {}
        for draft in drafts:
            if self._is_archived(draft):
                continue
            feedback = draft.review_feedback or {}
            missing = feedback.get("missing_keywords", [])
            if not isinstance(missing, list):
                continue
            normalized = []
            for item in missing:
                term = str(item or "").strip()
                if not term:
                    continue
                key = term.casefold()
                display_terms.setdefault(key, term)
                normalized.append(key)
            if normalized:
                gap_counter.update(normalized)
                total_drafts += 1

        top_gaps = [
            {
                "skill": display_terms.get(skill, skill),
                "count": count,
                "pct": round((count / total_drafts) * 100) if total_drafts else 0,
            }
            for skill, count in gap_counter.most_common(top_n)
        ]

        return {
            "top_gaps": top_gaps,
            "total_drafts_analyzed": total_drafts,
            "unique_missing_skills": len(gap_counter),
        }

    @staticmethod
    def _is_archived(draft: ResumeDraft) -> bool:
        applications = list(getattr(draft, "applications", []) or [])
        return bool(applications) and all(app.status == "archived" for app in applications)

    @staticmethod
    def _empty() -> dict[str, Any]:
        return {
            "top_gaps": [],
            "total_drafts_analyzed": 0,
            "unique_missing_skills": 0,
        }
