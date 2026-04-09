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
        connection.execute(text("ALTER TABLE job_posts ADD COLUMN IF NOT EXISTS company_domain VARCHAR(200) DEFAULT ''"))
        connection.execute(text("ALTER TABLE job_posts ADD COLUMN IF NOT EXISTS city VARCHAR(120) DEFAULT ''"))
        connection.execute(text("ALTER TABLE job_posts ADD COLUMN IF NOT EXISTS country VARCHAR(120) DEFAULT ''"))
        connection.execute(text("ALTER TABLE job_posts ADD COLUMN IF NOT EXISTS remote_policy VARCHAR(80) DEFAULT ''"))
        connection.execute(text("ALTER TABLE job_posts ADD COLUMN IF NOT EXISTS salary_text VARCHAR(200) DEFAULT ''"))
        connection.execute(text("ALTER TABLE job_posts ADD COLUMN IF NOT EXISTS recruiter_name VARCHAR(200) DEFAULT ''"))
        connection.execute(text("ALTER TABLE job_posts ADD COLUMN IF NOT EXISTS recruiter_email VARCHAR(200) DEFAULT ''"))
        connection.execute(text("ALTER TABLE job_posts ADD COLUMN IF NOT EXISTS role_family VARCHAR(120) DEFAULT ''"))
        connection.execute(text("ALTER TABLE job_posts ADD COLUMN IF NOT EXISTS match_notes TEXT DEFAULT ''"))
        connection.execute(text("ALTER TABLE job_posts ADD COLUMN IF NOT EXISTS posted_date VARCHAR(80) DEFAULT ''"))
        connection.execute(text("ALTER TABLE job_posts ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ DEFAULT NOW()"))
        connection.execute(text("ALTER TABLE job_track_scores ADD COLUMN IF NOT EXISTS embedding_cache JSONB"))
