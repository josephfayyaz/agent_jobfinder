"""
Application settings — loaded from .env (or environment variables).

All behaviour of the job agent is controlled here. Copy .env.example to .env
and fill in your values. No hardcoded secrets or personal data anywhere else.

For public deployments: every setting has a sensible default so the system
works out of the box with minimal configuration.
"""

from pathlib import Path

import yaml

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── General ───────────────────────────────────────────────────────────────
    app_env: str = Field(
        default="development",
        alias="APP_ENV",
        description="Runtime environment: development | production",
    )
    default_candidate_id: str = Field(
        default="",
        alias="DEFAULT_CANDIDATE_ID",
        description=(
            "UUID of the default candidate used by legacy single-user endpoints "
            "(GET /profile, POST /fact-sources/ingest)."
        ),
    )

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="",
        alias="DATABASE_URL",
        description=(
            "SQLite DB path. Defaults to <project_root>/job_agent.db. "
            "Override with DATABASE_URL env var."
        ),
    )

    # ── LM Studio (local inference) ───────────────────────────────────────────
    lm_studio_base_url: str = Field(
        default="http://localhost:1234/v1",
        alias="LM_STUDIO_BASE_URL",
        description=(
            "Base URL of any OpenAI-compatible local inference server "
            "(LM Studio, Ollama, llama.cpp server, etc.). "
            "Use http://host.docker.internal:1234/v1 when running inside Docker."
        ),
    )

    # Model roles — map a function to a model name.
    # Leave a role empty ("") to fall back to the heuristic implementation.
    lm_studio_small_model: str = Field(
        default="qwen3.5-9b-mlx",
        alias="LM_STUDIO_SMALL_MODEL",
        description="Fast model for review, scoring, routing, and job matching.",
    )
    lm_studio_writer_model: str = Field(
        default="qwen3.5-27b-claude-4.6-opus-distilled-mlx",
        alias="LM_STUDIO_WRITER_MODEL",
        description="High-quality model for resume drafting, cover letters, outreach emails.",
    )
    lm_studio_mid_model: str = Field(
        default="openai/gpt-oss-20b",
        alias="LM_STUDIO_MID_MODEL",
        description=(
            "Mid-size model for expert enhancement proposals and structured extraction. "
            "Falls back to small_model if empty."
        ),
    )
    lm_studio_embedding_model: str = Field(
        default="text-embedding-nomic-embed-text-v1.5",
        alias="LM_STUDIO_EMBEDDING_MODEL",
        description="Embedding model for semantic job matching. Leave empty to use keyword-only matching.",
    )
    semantic_matching_weight: float = Field(
        default=0.4,
        alias="SEMANTIC_MATCHING_WEIGHT",
        description=(
            "Weight of semantic embedding score in final job matching. "
            "0.0 = keyword only, 1.0 = semantic only."
        ),
    )
    match_min_score: int = Field(
        default=75,
        alias="MATCH_MIN_SCORE",
        description=(
            "Minimum job-track match score (0-100) to surface a job in default listing. "
            "Jobs below this are ingested but hidden by default. Use ?show_all=true to bypass."
        ),
    )
    target_job_seniority: str = Field(
        default="junior",
        alias="TARGET_JOB_SENIORITY",
        description=(
            "Target seniority level for job scoring. Options: intern | junior | mid | senior | any. "
            "'junior' penalizes titles or descriptions indicating 4+ years experience requirement. "
            "'any' disables all seniority adjustments."
        ),
    )
    fact_sheet_path: str = Field(
        default="",
        alias="FACT_SHEET_PATH",
        description="Optional path to a fact sheet file to ingest on startup/onboarding.",
    )

    # Token budgets — these models use a reasoning/thinking phase before outputting.
    # Budget must cover BOTH reasoning tokens AND the actual response.
    # Increase if the model cuts off mid-output; decrease to save RAM/time.
    lm_studio_max_tokens_small: int = Field(
        default=4000,
        alias="LM_STUDIO_MAX_TOKENS_SMALL",
        description="Max tokens for small model calls (includes reasoning + output).",
    )
    lm_studio_max_tokens_writer: int = Field(
        default=6000,
        alias="LM_STUDIO_MAX_TOKENS_WRITER",
        description="Max tokens for writer model calls (includes reasoning + output).",
    )
    lm_studio_max_tokens_mid: int = Field(
        default=4000,
        alias="LM_STUDIO_MAX_TOKENS_MID",
        description="Max tokens for mid model calls.",
    )

    lm_studio_request_timeout_seconds: int = Field(
        default=120,
        alias="LM_STUDIO_REQUEST_TIMEOUT_SECONDS",
        description="HTTP timeout for LM Studio requests in seconds.",
    )

    # ── OpenAI (optional cloud escalation) ────────────────────────────────────
    openai_api_key: str = Field(
        default="",
        alias="OPENAI_API_KEY",
        description="Optional. Leave empty to disable OpenAI.",
    )
    openai_review_model: str = Field(
        default="gpt-4o",
        alias="OPENAI_REVIEW_MODEL",
        description="OpenAI model used for CV review when USE_OPENAI_REVIEW=true.",
    )
    openai_escalation_model: str = Field(
        default="gpt-4o",
        alias="OPENAI_ESCALATION_MODEL",
        description="OpenAI model used for full CV rewrite escalation.",
    )
    use_openai_review: bool = Field(
        default=False,
        alias="USE_OPENAI_REVIEW",
        description="Set true to use OpenAI for CV review (requires OPENAI_API_KEY).",
    )
    use_openai_escalation: bool = Field(
        default=False,
        alias="USE_OPENAI_ESCALATION",
        description="Set true to escalate failed drafts to OpenAI for rewrite.",
    )

    # ── Anthropic / Claude (optional final polish) ─────────────────────────────
    anthropic_api_key: str = Field(
        default="",
        alias="ANTHROPIC_API_KEY",
        description="Optional. Leave empty to disable Claude final polish.",
    )
    anthropic_model: str = Field(
        default="claude-sonnet-4-6",
        alias="ANTHROPIC_MODEL",
        description="Claude model for final resume polish and complex escalation.",
    )
    use_claude_final_review: bool = Field(
        default=False,
        alias="USE_CLAUDE_FINAL_REVIEW",
        description=(
            "Set true to send high-priority drafts through Claude for final polish "
            "(requires ANTHROPIC_API_KEY). Triggered by force_cloud_review=true on a task."
        ),
    )
    clearbit_api_key: str = Field(
        default="",
        alias="CLEARBIT_API_KEY",
        description=(
            "Optional Clearbit API key for company URL fallback. "
            "Leave empty to use DuckDuckGo-only resolution."
        ),
    )

    # ── CV Workflow thresholds ─────────────────────────────────────────────────
    cv_pass_score: int = Field(
        default=85,
        alias="CV_PASS_SCORE",
        description="Resume score (0-100) at or above which the draft is accepted as-is.",
    )
    cv_revise_score: int = Field(
        default=60,
        alias="CV_REVISE_SCORE",
        description=(
            "Resume score (0-100) at or above which the draft is revised. "
            "Below this threshold triggers a full rewrite or Claude escalation."
        ),
    )
    bullet_clarify_word_limit: int = Field(
        default=22,
        alias="BULLET_CLARIFY_WORD_LIMIT",
        description="Maximum words allowed per rewritten bullet. Bullets exceeding this are flagged.",
    )

    # ── Worker ────────────────────────────────────────────────────────────────
    worker_poll_seconds: int = Field(
        default=5,
        alias="WORKER_POLL_SECONDS",
        description="How often the background worker polls for pending tasks (seconds).",
    )
    scan_max_workers: int = Field(
        default=5,
        alias="SCAN_MAX_WORKERS",
        description=(
            "Max concurrent threads for parallel career page scanning and job enrichment. "
            "Set to 1 to disable parallelism."
        ),
    )
    scanner_max_workers: int = Field(
        default=4,
        alias="SCANNER_MAX_WORKERS",
        description="ThreadPoolExecutor workers for parallel scan.",
    )
    velocity_spike_threshold: int = Field(
        default=3,
        alias="VELOCITY_SPIKE_THRESHOLD",
        description="Number of new jobs in one scan that triggers a velocity spike alert.",
    )
    gmail_email: str = Field(
        default="",
        alias="GMAIL_EMAIL",
        description="Gmail address to poll for job alert emails.",
    )
    gmail_app_password: str = Field(
        default="",
        alias="GMAIL_APP_PASSWORD",
        description=(
            "Gmail App Password for IMAP access. "
            "Use an app password, never your main account password."
        ),
    )
    gmail_imap_host: str = Field(
        default="imap.gmail.com",
        alias="GMAIL_IMAP_HOST",
        description="IMAP host used for Gmail polling.",
    )
    gmail_label_filter: str = Field(
        default="LinkedIn Jobs",
        alias="GMAIL_LABEL_FILTER",
        description=(
            "Gmail label or sender filter used to narrow LinkedIn alert emails. "
            "Use a label name or sender email."
        ),
    )
    gmail_max_emails_per_sync: int = Field(
        default=50,
        alias="GMAIL_MAX_EMAILS_PER_SYNC",
        description="Maximum unread Gmail messages to process per sync run.",
    )
    gmail_auto_sync: bool = Field(
        default=False,
        alias="GMAIL_AUTO_SYNC",
        description="Enable automatic Gmail polling from the worker loop.",
    )
    gmail_sync_interval_minutes: int = Field(
        default=30,
        alias="GMAIL_SYNC_INTERVAL_MINUTES",
        description="Minutes between automatic Gmail sync runs.",
    )
    linkedin_fetch_delay_seconds: float = Field(
        default=2.0,
        alias="LINKEDIN_FETCH_DELAY_SECONDS",
        description="Seconds to wait between LinkedIn job page fetches.",
    )
    use_jobspy: bool = Field(
        default=False,
        alias="USE_JOBSPY",
        description=(
            "Enable JobSpy for active LinkedIn job discovery. "
            "Reads public job listings with no login required. Off by default."
        ),
    )
    jobspy_request_delay: float = Field(
        default=2.0,
        alias="JOBSPY_REQUEST_DELAY",
        description="Seconds to wait between JobSpy search requests to avoid rate limiting.",
    )
    jobspy_default_limit: int = Field(
        default=50,
        alias="JOBSPY_DEFAULT_LIMIT",
        description="Default number of results per JobSpy search call.",
    )
    jobspy_discover_interval_hours: int = Field(
        default=6,
        alias="JOBSPY_DISCOVER_INTERVAL_HOURS",
        description="How often (hours) the worker auto-runs JobSpy discovery. 0 = disabled.",
    )
    jobspy_discover_queries: list[str] = Field(
        default=[
            "MLOps Engineer",
            "AI Engineer",
            "Machine Learning Engineer",
            "Data Engineer",
            "Kubernetes Engineer",
        ],
        alias="JOBSPY_DISCOVER_QUERIES",
        description="Search queries run on each scheduled JobSpy discovery cycle.",
    )
    jobspy_discover_location: str = Field(
        default="Italy",
        alias="JOBSPY_DISCOVER_LOCATION",
        description="Default location for scheduled JobSpy discovery.",
    )

    @field_validator("jobspy_discover_queries", mode="before")
    @classmethod
    def parse_queries(cls, v):
        if isinstance(v, str):
            import json

            try:
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return [q.strip() for q in v.split(",") if q.strip()]
        return v

    # ── Artifacts ────────────────────────────────────────────────────────────
    artifacts_dir: Path = Field(
        default=Path("generated"),
        alias="ARTIFACTS_DIR",
        description="Directory for generated .tex, .pdf, and CSV export files.",
    )


_USER_SETTINGS_PATH = Path("config/user_settings.yml")

_YAML_TO_SETTINGS_FIELD = {
    "database_url": "database_url",
    "lm_studio_base_url": "lm_studio_base_url",
    "lm_studio_small_model": "lm_studio_small_model",
    "lm_studio_writer_model": "lm_studio_writer_model",
    "lm_studio_mid_model": "lm_studio_mid_model",
    "openai_api_key": "openai_api_key",
    "anthropic_api_key": "anthropic_api_key",
    "use_openai_review": "use_openai_review",
    "use_claude_final_review": "use_claude_final_review",
    "target_job_seniority": "target_job_seniority",
    "fact_sheet_path": "fact_sheet_path",
    "match_min_score": "match_min_score",
    "cv_pass_score": "cv_pass_score",
    "cv_revise_score": "cv_revise_score",
    "bullet_clarify_word_limit": "bullet_clarify_word_limit",
    "use_jobspy": "use_jobspy",
    "jobspy_discover_location": "jobspy_discover_location",
    "jobspy_discover_queries": "jobspy_discover_queries",
}


def load_user_settings_overlay(s: Settings, path: Path = _USER_SETTINGS_PATH) -> None:
    """Overlay config/user_settings.yml onto settings. Safe to call at startup."""
    if not path.exists():
        return
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return
    if not isinstance(data, dict):
        return

    for yaml_key, field_name in _YAML_TO_SETTINGS_FIELD.items():
        value = data.get(yaml_key)
        if yaml_key in data and value not in (None, ""):
            object.__setattr__(s, field_name, value)


settings = Settings()
load_user_settings_overlay(settings)


def get_settings() -> Settings:
    """Compatibility helper for services and tests that need the singleton settings."""
    return settings
