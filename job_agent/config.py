from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="development", alias="APP_ENV")
    database_url: str = Field(
        default="postgresql+psycopg://job_agent:job_agent@db:5432/job_agent",
        alias="DATABASE_URL",
    )
    lm_studio_base_url: str = Field(default="http://host.docker.internal:1234/v1", alias="LM_STUDIO_BASE_URL")
    lm_studio_small_model: str = Field(default="", alias="LM_STUDIO_SMALL_MODEL")
    lm_studio_writer_model: str = Field(default="", alias="LM_STUDIO_WRITER_MODEL")
    lm_studio_request_timeout_seconds: int = Field(default=90, alias="LM_STUDIO_REQUEST_TIMEOUT_SECONDS")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_review_model: str = Field(default="gpt-5.4", alias="OPENAI_REVIEW_MODEL")
    openai_escalation_model: str = Field(default="gpt-5.3-codex", alias="OPENAI_ESCALATION_MODEL")
    use_openai_review: bool = Field(default=False, alias="USE_OPENAI_REVIEW")
    use_openai_escalation: bool = Field(default=False, alias="USE_OPENAI_ESCALATION")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-sonnet-4-6", alias="ANTHROPIC_MODEL")
    use_claude_final_review: bool = Field(default=False, alias="USE_CLAUDE_FINAL_REVIEW")
    artifacts_dir: Path = Field(default=Path("generated"), alias="ARTIFACTS_DIR")
    worker_poll_seconds: int = Field(default=5, alias="WORKER_POLL_SECONDS")
    cv_pass_score: int = Field(default=85, alias="CV_PASS_SCORE")
    cv_revise_score: int = Field(default=60, alias="CV_REVISE_SCORE")


settings = Settings()
