"""
Application settings — loaded from .env (or environment variables).

All behaviour of the job agent is controlled here. Copy .env.example to .env
and fill in your values. No hardcoded secrets or personal data anywhere else.

For public deployments: every setting has a sensible default so the system
works out of the box with minimal configuration.
"""

from pathlib import Path

from pydantic import Field
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

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+psycopg://job_agent:job_agent@localhost:5432/job_agent",
        alias="DATABASE_URL",
        description=(
            "SQLAlchemy-compatible PostgreSQL URL. "
            "Use @localhost when running API outside Docker; "
            "use @db when running inside Docker Compose."
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

    # ── Worker ────────────────────────────────────────────────────────────────
    worker_poll_seconds: int = Field(
        default=5,
        alias="WORKER_POLL_SECONDS",
        description="How often the background worker polls for pending tasks (seconds).",
    )

    # ── Artifacts ────────────────────────────────────────────────────────────
    artifacts_dir: Path = Field(
        default=Path("generated"),
        alias="ARTIFACTS_DIR",
        description="Directory for generated .tex, .pdf, and CSV export files.",
    )


settings = Settings()
