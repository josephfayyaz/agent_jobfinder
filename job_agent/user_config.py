"""Read and write the single-user settings file safely."""

from __future__ import annotations

from pathlib import Path

import yaml

from job_agent.runtime_paths import user_settings_path
from job_agent.secrets import SENTINEL, SECRET_FIELDS, delete_secret, keyring_available, store_secret

USER_SETTINGS_PATH = user_settings_path()
EXAMPLE_PATH = Path("config/user_settings.example.yml")

EDITABLE_FIELDS: dict[str, type] = {
    "default_candidate_id": str,
    "llm_provider_mode": str,
    "lm_studio_base_url": str,
    "lm_studio_small_model": str,
    "lm_studio_writer_model": str,
    "lm_studio_mid_model": str,
    "ollama_base_url": str,
    "ollama_fast_model": str,
    "ollama_writer_model": str,
    "openai_api_key": str,
    "gemini_api_key": str,
    "openai_review_model": str,
    "openai_escalation_model": str,
    "anthropic_api_key": str,
    "anthropic_model": str,
    "use_openai_review": bool,
    "use_claude_final_review": bool,
    "target_job_seniority": str,
    "fact_sheet_path": str,
    "match_min_score": int,
    "discovery_min_fit_score": int,
    "discovery_max_visible_jobs": int,
    "cv_pass_score": int,
    "cv_revise_score": int,
    "bullet_clarify_word_limit": int,
    "use_jobspy": bool,
    "jobspy_detail_enrichment_enabled": bool,
    "jobspy_detail_enrichment_limit": int,
    "jobspy_discover_location": str,
    "job_search_countries": list,
    "job_search_region": str,
    "job_search_languages": list,
    "jobspy_discover_queries": list,
    "artifacts_dir": str,
    "gmail_email": str,
    "gmail_app_password": str,
    "gmail_oauth_client_id": str,
    "gmail_oauth_client_secret": str,
    "gmail_label_filter": str,
    "gmail_auto_sync": bool,
}


def read_user_settings() -> dict:
    if not USER_SETTINGS_PATH.exists():
        return {}
    data = yaml.safe_load(USER_SETTINGS_PATH.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def write_user_settings(updates: dict, *, clear_secrets: set[str] | None = None) -> None:
    USER_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    current = read_user_settings()
    filtered = {k: v for k, v in updates.items() if k in EDITABLE_FIELDS}
    clear_secrets = set(clear_secrets or set())

    for field in SECRET_FIELDS:
        if field in clear_secrets:
            delete_secret(field)
            current[field] = ""
            filtered.pop(field, None)
        elif field in filtered and str(filtered[field] or "").strip() == "":
            filtered.pop(field, None)

    if keyring_available():
        for field in SECRET_FIELDS:
            if field in filtered and filtered[field] and filtered[field] != SENTINEL:
                if store_secret(field, str(filtered[field])):
                    filtered[field] = SENTINEL

    current.update(filtered)
    USER_SETTINGS_PATH.write_text(
        yaml.safe_dump(current, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def set_field(key: str, value) -> None:
    if key not in EDITABLE_FIELDS:
        raise ValueError(f"Not an editable field: {key}")
    write_user_settings({key: value})


def delete_user_settings() -> None:
    if USER_SETTINGS_PATH.exists():
        USER_SETTINGS_PATH.unlink()
