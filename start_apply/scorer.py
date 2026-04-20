from __future__ import annotations

from job_agent.llm import LLMRouter


_SYSTEM_PROMPT = """You are a resume match analyst. Score how well a candidate's background matches
a job description. Be honest and precise. Return valid JSON only."""


def score_match(job: dict, fact_sheet: str, router: LLMRouter | None = None) -> dict:
    router = router or LLMRouter()
    requirements = job.get("requirements") or []
    req_text = "\n".join(f"- {item}" for item in requirements) or "- (no explicit requirements extracted)"
    user_prompt = f"""JOB: {job.get("title", "Unknown")} at {job.get("company", "Unknown")}
SENIORITY: {job.get("seniority", "unknown")}

JOB REQUIREMENTS:
{req_text}

CANDIDATE FACT SHEET (excerpt):
{fact_sheet[:4000]}

Score the match 0-100.
- 85-100: Strong match, apply directly
- 60-84: Good match, some gaps — clarification may help
- 0-59: Weak match, significant gaps

Return JSON:
{{
  "score": <int 0-100>,
  "matched": ["skill/experience that clearly matches"],
  "gaps": ["requirement with no clear evidence in fact sheet"],
  "summary": "2-sentence honest assessment"
}}"""
    data = router.generate(
        role="small",
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )
    raw_score = int(data.get("score", 0) or 0)
    return {
        "score": max(0, min(100, raw_score)),
        "matched": list(data.get("matched") or []),
        "gaps": list(data.get("gaps") or []),
        "summary": str(data.get("summary") or ""),
    }
