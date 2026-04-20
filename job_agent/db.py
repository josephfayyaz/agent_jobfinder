from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from job_agent.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def prepare_database() -> None:
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE job_posts DROP CONSTRAINT IF EXISTS uq_job_source"))
        connection.execute(text("ALTER TABLE resume_tracks ADD COLUMN IF NOT EXISTS active BOOLEAN DEFAULT TRUE"))
        connection.execute(text("ALTER TABLE job_posts ADD COLUMN IF NOT EXISTS source_id UUID"))
        connection.execute(text("ALTER TABLE job_posts ADD COLUMN IF NOT EXISTS canonical_apply_url VARCHAR(500) DEFAULT ''"))
        connection.execute(text("ALTER TABLE job_posts ADD COLUMN IF NOT EXISTS company_url VARCHAR(500)"))
        connection.execute(text("ALTER TABLE job_posts ADD COLUMN IF NOT EXISTS company_domain VARCHAR(200) DEFAULT ''"))
        connection.execute(text("ALTER TABLE job_posts ADD COLUMN IF NOT EXISTS city VARCHAR(120) DEFAULT ''"))
        connection.execute(text("ALTER TABLE job_posts ADD COLUMN IF NOT EXISTS country VARCHAR(120) DEFAULT ''"))
        connection.execute(text("ALTER TABLE job_posts ADD COLUMN IF NOT EXISTS remote_policy VARCHAR(80) DEFAULT ''"))
        connection.execute(text("ALTER TABLE job_posts ADD COLUMN IF NOT EXISTS salary_text VARCHAR(200) DEFAULT ''"))
        connection.execute(text("ALTER TABLE job_posts ADD COLUMN IF NOT EXISTS recruiter_name VARCHAR(200) DEFAULT ''"))
        connection.execute(text("ALTER TABLE job_posts ADD COLUMN IF NOT EXISTS recruiter_email VARCHAR(200) DEFAULT ''"))
        connection.execute(text("ALTER TABLE job_posts ADD COLUMN IF NOT EXISTS role_family VARCHAR(120) DEFAULT ''"))
        connection.execute(text("ALTER TABLE job_posts ADD COLUMN IF NOT EXISTS seniority VARCHAR(20)"))
        connection.execute(text("ALTER TABLE job_posts ADD COLUMN IF NOT EXISTS match_notes TEXT DEFAULT ''"))
        connection.execute(text("ALTER TABLE job_posts ADD COLUMN IF NOT EXISTS posted_date VARCHAR(80) DEFAULT ''"))
        connection.execute(text("ALTER TABLE job_posts ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ DEFAULT NOW()"))
        connection.execute(text("ALTER TABLE resume_drafts ADD COLUMN IF NOT EXISTS cover_letter_text TEXT"))
        connection.execute(text("ALTER TABLE resume_drafts ADD COLUMN IF NOT EXISTS cover_letter_subject VARCHAR(500)"))
        connection.execute(text("ALTER TABLE resume_drafts ADD COLUMN IF NOT EXISTS inferred_additions JSONB"))
        connection.execute(text("ALTER TABLE resume_drafts ADD COLUMN IF NOT EXISTS accepted_inferred_additions JSONB"))
        connection.execute(text("ALTER TABLE job_track_scores ADD COLUMN IF NOT EXISTS embedding_cache JSONB"))
        connection.execute(text("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS completion_status VARCHAR(20)"))
        connection.execute(text("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS confidence_summary JSONB"))
        connection.execute(text("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS spoken_languages JSONB"))
        connection.execute(text("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS skills_json JSONB"))
        connection.execute(text("ALTER TABLE experience_facts ADD COLUMN IF NOT EXISTS candidate_id VARCHAR(36)"))
        connection.execute(text("ALTER TABLE project_facts ADD COLUMN IF NOT EXISTS candidate_id VARCHAR(36)"))
        connection.execute(text("ALTER TABLE education_facts ADD COLUMN IF NOT EXISTS candidate_id VARCHAR(36)"))
        connection.execute(text("ALTER TABLE summary_variants ADD COLUMN IF NOT EXISTS candidate_id VARCHAR(36)"))
        connection.execute(text("ALTER TABLE keyword_sets ADD COLUMN IF NOT EXISTS candidate_id VARCHAR(36)"))
        connection.execute(text("ALTER TABLE fact_sources ADD COLUMN IF NOT EXISTS candidate_id VARCHAR(36)"))
        connection.execute(text("ALTER TABLE career_page_sources ADD COLUMN IF NOT EXISTS ats_type VARCHAR(50)"))
        connection.execute(text("ALTER TABLE career_page_sources ADD COLUMN IF NOT EXISTS ats_slug VARCHAR(200)"))
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS career_page_scan_logs (
                    id SERIAL PRIMARY KEY,
                    source_id INTEGER NOT NULL REFERENCES career_page_sources(id),
                    scanned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    jobs_found INTEGER NOT NULL DEFAULT 0,
                    new_jobs INTEGER NOT NULL DEFAULT 0
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_scan_logs_source_id
                    ON career_page_scan_logs(source_id)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_scan_logs_scanned_at
                    ON career_page_scan_logs(scanned_at)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS bullet_clarifications (
                    id UUID PRIMARY KEY,
                    draft_id UUID NOT NULL REFERENCES resume_drafts(id),
                    language_map JSONB NOT NULL DEFAULT '{}',
                    questions JSONB NOT NULL DEFAULT '[]',
                    answers JSONB NOT NULL DEFAULT '[]',
                    rewritten_bullets JSONB NOT NULL DEFAULT '{}',
                    status VARCHAR NOT NULL DEFAULT 'pending_questions',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_bullet_clarifications_draft_id
                    ON bullet_clarifications(draft_id)
                """
            )
        )
