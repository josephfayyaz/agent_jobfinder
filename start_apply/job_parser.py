from __future__ import annotations

from job_agent.llm import LLMRouter


_SYSTEM_PROMPT = """You are extracting structured job information from raw text. The user may have
pasted a job description, a URL, a company name, or any combination. Extract
what you can. Return valid JSON only. Use null for fields you cannot determine."""


def parse_job_info(raw_text: str, router: LLMRouter | None = None) -> dict:
    router = router or LLMRouter()
    user_prompt = f"""Extract job information from the following raw text:

{raw_text}

Return JSON:
{{
  "title": "...",
  "company": "...",
  "location": "...",
  "url": "... or null",
  "description": "full job description text",
  "requirements": ["requirement 1", "requirement 2", ...],
  "nice_to_have": ["nice to have 1", ...],
  "seniority": "junior|mid|senior|intern|unknown"
}}"""
    data = router.generate(
        role="small",
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )
    return {
        "title": str(data.get("title") or "Unknown Role"),
        "company": str(data.get("company") or "Unknown Company"),
        "location": str(data.get("location") or "Unknown Location"),
        "url": data.get("url"),
        "description": str(data.get("description") or raw_text),
        "requirements": list(data.get("requirements") or []),
        "nice_to_have": list(data.get("nice_to_have") or []),
        "seniority": str(data.get("seniority") or "unknown"),
    }
