"""Read and write config/user_settings.yml safely."""

from __future__ import annotations

from pathlib import Path

import yaml

USER_SETTINGS_PATH = Path("config/user_settings.yml")
EXAMPLE_PATH = Path("config/user_settings.example.yml")

EDITABLE_FIELDS: dict[str, type] = {
    "lm_studio_base_url": str,
    "lm_studio_small_model": str,
    "lm_studio_writer_model": str,
    "lm_studio_mid_model": str,
    "openai_api_key": str,
    "anthropic_api_key": str,
    "use_openai_review": bool,
    "use_claude_final_review": bool,
    "target_job_seniority": str,
    "fact_sheet_path": str,
    "match_min_score": int,
    "cv_pass_score": int,
    "cv_revise_score": int,
    "bullet_clarify_word_limit": int,
    "use_jobspy": bool,
    "jobspy_discover_location": str,
    "jobspy_discover_queries": list,
}


def read_user_settings() -> dict:
    if not USER_SETTINGS_PATH.exists():
        return {}
    data = yaml.safe_load(USER_SETTINGS_PATH.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def write_user_settings(updates: dict) -> None:
    USER_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    current = read_user_settings()
    current.update({k: v for k, v in updates.items() if k in EDITABLE_FIELDS})
    USER_SETTINGS_PATH.write_text(
        yaml.safe_dump(current, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def set_field(key: str, value) -> None:
    if key not in EDITABLE_FIELDS:
        raise ValueError(f"Not an editable field: {key}")
    write_user_settings({key: value})
