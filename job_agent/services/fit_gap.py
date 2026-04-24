"""Role Readiness Map: compare a job description with candidate facts."""
from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from job_agent.llm import LLMRouter, ProviderUnavailableError
from job_agent.models import Candidate, JobPost
from job_agent.services.fact_sheet_renderer import FactSheetRenderer

logger = logging.getLogger(__name__)

FIT_LEVELS = {"Strong", "Close", "Thin Proof", "Missing"}
FIT_EMOJIS = {"Strong": "✅", "Close": "🟡", "Thin Proof": "🟠", "Missing": "🔴"}
NEXT_MOVES = {
    "Strong": "Include Now",
    "Close": "Add a Detail",
    "Thin Proof": "Fill a Gap",
    "Missing": "Build Experience",
}
DRAFT_READY = {
    "Strong": "Include Now",
    "Close": "Include Now",
    "Thin Proof": "Use Carefully",
    "Missing": "Hold for Now",
}
EMPTY_RESULT = {"rows": [], "summary": {"strong": 0, "close": 0, "thin": 0, "missing": 0}}

_SYSTEM_PROMPT = """\
You are a career coach comparing a candidate fact sheet against a job description.
Be strict: only credit evidence that is present in the fact sheet. Return JSON only.
"""

_USER_PROMPT_TEMPLATE = """\
## Job Description excerpt
{jd_excerpt}

## Candidate Fact Sheet summary
{fact_summary}

## Task
Extract up to 12 distinct requirements from the job description.
For each requirement, classify how well the candidate's facts cover it:
- Strong: clear direct evidence
- Close: related evidence, but not a perfect match
- Thin Proof: weak or indirect proof that needs more detail
- Missing: no credible evidence yet

Return ONLY this JSON object shape:
{{
  "requirements": [
    {{
      "requirement": "<concise paraphrase of what the job asks for>",
      "evidence": "<relevant fact-sheet evidence, or 'Nothing yet'>",
      "fit_level": "<Strong | Close | Thin Proof | Missing>"
    }}
  ]
}}
"""


class FitGapService:
    """Lazy-compute and cache role readiness maps on JobPost.extracted_metadata."""

    def __init__(self, session: Session, router: LLMRouter) -> None:
        self.session = session
        self.router = router

    def get_or_compute(self, job_id: UUID | str, candidate_id: str) -> dict[str, Any]:
        job = self.session.get(JobPost, self._coerce_uuid(job_id))
        if job is None:
            return dict(EMPTY_RESULT)

        meta = dict(job.extracted_metadata or {})
        cached = meta.get("fit_gaps")
        if isinstance(cached, dict) and cached.get("rows"):
            return cached

        result = self._compute(job=job, candidate_id=candidate_id)
        if result.get("rows"):
            meta["fit_gaps"] = result
            job.extracted_metadata = meta
            self.session.add(job)
            self.session.commit()
        return result

    def _compute(self, job: JobPost, candidate_id: str) -> dict[str, Any]:
        candidate = self.session.get(Candidate, str(candidate_id))
        if candidate is None:
            return dict(EMPTY_RESULT)

        fact_summary = FactSheetRenderer(session=self.session).render_short_summary(candidate)
        jd_excerpt = (job.description or "")[:1500]
        user_prompt = _USER_PROMPT_TEMPLATE.format(
            jd_excerpt=jd_excerpt,
            fact_summary=fact_summary,
        )

        try:
            raw = self.router.generate(
                role="small",
                system_prompt=_SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
            items = self._extract_items(raw)
        except (ProviderUnavailableError, ValueError) as exc:
            logger.warning("FitGapService LLM call failed: %s", exc)
            return dict(EMPTY_RESULT)

        rows = []
        counts: dict[str, int] = {"strong": 0, "close": 0, "thin": 0, "missing": 0}
        for item in items[:12]:
            if not isinstance(item, dict):
                continue
            fit = self._normalize_fit_level(item.get("fit_level"))
            key = "thin" if fit == "Thin Proof" else fit.lower()
            counts[key] += 1
            rows.append(
                {
                    "fit_level": fit,
                    "fit_emoji": FIT_EMOJIS[fit],
                    "what_they_ask": str(item.get("requirement") or "").strip(),
                    "what_you_have": str(item.get("evidence") or "Nothing yet").strip() or "Nothing yet",
                    "best_next_move": NEXT_MOVES[fit],
                    "draft_readiness": DRAFT_READY[fit],
                }
            )

        order = {"Missing": 0, "Thin Proof": 1, "Close": 2, "Strong": 3}
        rows.sort(key=lambda row: order.get(row["fit_level"], 99))
        return {"rows": rows, "summary": counts}

    @staticmethod
    def _coerce_uuid(value: UUID | str) -> UUID | str:
        if isinstance(value, UUID):
            return value
        try:
            return UUID(str(value))
        except ValueError:
            return str(value)

    @staticmethod
    def _extract_items(raw: Any) -> list[dict[str, Any]]:
        if isinstance(raw, str):
            parsed = json.loads(raw)
        else:
            parsed = raw

        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
        if isinstance(parsed, dict):
            for key in ("requirements", "rows", "items"):
                value = parsed.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
            if {"requirement", "fit_level"} <= set(parsed):
                return [parsed]
        raise ValueError("Fit-gap response did not contain a JSON array of requirements.")

    @staticmethod
    def _normalize_fit_level(value: Any) -> str:
        text = str(value or "Missing").strip().casefold()
        if "strong" in text:
            return "Strong"
        if "close" in text:
            return "Close"
        if "thin" in text:
            return "Thin Proof"
        return "Missing"
