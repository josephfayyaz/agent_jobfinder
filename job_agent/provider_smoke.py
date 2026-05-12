from __future__ import annotations

from typing import Any

from job_agent.config import settings
from job_agent.llm import LLMRouter
from job_agent.providers import normalize_provider_mode

SMOKE_CASES: dict[str, dict[str, Any]] = {
    "probe": {
        "required_keys": ["ok"],
    },
    "small_json": {
        "required_keys": ["items", "count"],
    },
    "medium_json": {
        "required_keys": ["skills", "location", "summary"],
    },
    "large_intake": {
        "required_keys": ["summary", "skills", "target_roles"],
    },
}


def _case_payload(case: str) -> tuple[str, str]:
    if case == "probe":
        return (
            "Return strict JSON only.",
            'Return {"ok": true}.',
        )
    if case == "small_json":
        return (
            "Return strict JSON only.",
            'Return {"items": ["alpha", "beta"], "count": 2}.',
        )
    if case == "medium_json":
        return (
            "Summarize the input into strict JSON only.",
            (
                "Given this short profile:\n"
                "- Python\n- SQL\n- Italy\n"
                'Return {"skills": [...], "location": "...", "summary": "..."}'
            ),
        )
    if case == "large_intake":
        large_block = ("Experience: built ETL pipelines with Python and SQL.\n" * 300).strip()
        return (
            "Extract a compact fact summary. Return strict JSON only.",
            (
                f"{large_block}\n\n"
                'Return {"summary": "...", "skills": ["..."], "target_roles": ["..."]}'
            ),
        )
    raise ValueError(f"Unknown smoke case: {case}")


def _validate_payload(case: str, payload: dict[str, Any]) -> None:
    required = list(SMOKE_CASES.get(case, {}).get("required_keys") or [])
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"Smoke case '{case}' response missing keys: {missing}")


def run_provider_smoke(case: str, role: str = "small") -> dict[str, Any]:
    if case not in SMOKE_CASES:
        raise ValueError(f"Unknown smoke case: {case}")
    provider_mode = normalize_provider_mode(getattr(settings, "llm_provider_mode", "openai"))
    system_prompt, user_prompt = _case_payload(case)
    payload, usage = LLMRouter().generate_with_retry_usage(
        role=role,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )
    if not isinstance(payload, dict):
        raise ValueError(f"Smoke case '{case}' did not return a JSON object.")
    _validate_payload(case, payload)
    return {
        "provider_mode": provider_mode,
        "case": case,
        "ok": True,
        "keys": sorted(payload.keys()),
        "usage": usage,
    }
