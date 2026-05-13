"""Database engine, session, and schema setup."""
from __future__ import annotations

from collections.abc import Generator
import logging
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from job_agent.config import settings
from job_agent.runtime_paths import bootstrap_runtime_state, default_database_path

logger = logging.getLogger(__name__)


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, _compiler, **_kw):
    return "TEXT"


@compiles(PGUUID, "sqlite")
def _compile_uuid_sqlite(_type, _compiler, **_kw):
    return "VARCHAR(36)"


def _default_db_url() -> str:
    """Resolve absolute path to the single-user workspace SQLite file."""
    return f"sqlite:///{default_database_path()}"


def _is_sqlite_url(url: str) -> bool:
    return not url or url.startswith("sqlite")


def _make_engine(url: str):
    bootstrap_runtime_state()
    resolved_url = url or _default_db_url()
    engine_kwargs: dict[str, object] = {"pool_pre_ping": True}
    if _is_sqlite_url(resolved_url):
        sqlite_path = Path(resolved_url.removeprefix("sqlite:///")).expanduser()
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        engine_kwargs["connect_args"] = {"check_same_thread": False, "timeout": 10}
    engine = create_engine(resolved_url, **engine_kwargs)

    if _is_sqlite_url(resolved_url):

        @event.listens_for(engine, "connect")
        def _set_pragmas(dbapi_conn, _record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=10000")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

    return engine


class Base(DeclarativeBase):
    pass


engine = _make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _safe_add_column(conn, table: str, column: str, col_type: str) -> None:
    """Add a column; silently skip if it already exists."""
    try:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
    except Exception:
        pass


def prepare_database() -> None:
    """Create all ORM tables then apply additive migrations."""
    import job_agent.models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    with engine.begin() as conn:
        _safe_add_column(conn, "job_posts", "source_id", "VARCHAR(36)")
        _safe_add_column(conn, "job_posts", "canonical_apply_url", "VARCHAR(500) DEFAULT ''")
        _safe_add_column(conn, "job_posts", "company_url", "VARCHAR(500)")
        _safe_add_column(conn, "job_posts", "company_domain", "VARCHAR(200) DEFAULT ''")
        _safe_add_column(conn, "job_posts", "city", "VARCHAR(120) DEFAULT ''")
        _safe_add_column(conn, "job_posts", "country", "VARCHAR(120) DEFAULT ''")
        _safe_add_column(conn, "job_posts", "remote_policy", "VARCHAR(80) DEFAULT ''")
        _safe_add_column(conn, "job_posts", "salary_text", "VARCHAR(200) DEFAULT ''")
        _safe_add_column(conn, "job_posts", "recruiter_name", "VARCHAR(200) DEFAULT ''")
        _safe_add_column(conn, "job_posts", "recruiter_email", "VARCHAR(200) DEFAULT ''")
        _safe_add_column(conn, "job_posts", "role_family", "VARCHAR(120) DEFAULT ''")
        _safe_add_column(conn, "job_posts", "seniority", "VARCHAR(20)")
        _safe_add_column(conn, "job_posts", "match_notes", "TEXT DEFAULT ''")
        _safe_add_column(conn, "job_posts", "extracted_metadata", "TEXT")
        _safe_add_column(conn, "job_posts", "queue_state", "VARCHAR(40) DEFAULT 'new'")
        _safe_add_column(conn, "job_posts", "posted_date", "VARCHAR(80) DEFAULT ''")
        _safe_add_column(conn, "job_posts", "enrichment_status", "VARCHAR(30) DEFAULT 'pending'")
        _safe_add_column(conn, "job_posts", "last_seen_at", "DATETIME DEFAULT CURRENT_TIMESTAMP")

        _safe_add_column(conn, "resume_tracks", "active", "INTEGER DEFAULT 1")
        _safe_add_column(conn, "resume_tracks", "is_custom", "INTEGER NOT NULL DEFAULT 0")
        _safe_add_column(conn, "resume_tracks", "candidate_id", "VARCHAR(36)")

        _safe_add_column(conn, "resume_drafts", "cover_letter_text", "TEXT")
        _safe_add_column(conn, "resume_drafts", "cover_letter_subject", "VARCHAR(500)")
        _safe_add_column(conn, "resume_drafts", "inferred_additions", "TEXT")
        _safe_add_column(conn, "resume_drafts", "accepted_inferred_additions", "TEXT")
        _safe_add_column(conn, "resume_drafts", "candidate_id", "VARCHAR(36)")

        _safe_add_column(conn, "job_track_scores", "embedding_cache", "TEXT")

        _safe_add_column(conn, "candidates", "completion_status", "VARCHAR(20)")
        _safe_add_column(conn, "candidates", "confidence_summary", "TEXT")
        _safe_add_column(conn, "candidates", "spoken_languages", "TEXT")
        _safe_add_column(conn, "candidates", "skills_json", "TEXT")

        _safe_add_column(conn, "experience_facts", "candidate_id", "VARCHAR(36)")
        _safe_add_column(conn, "project_facts", "candidate_id", "VARCHAR(36)")
        _safe_add_column(conn, "education_facts", "candidate_id", "VARCHAR(36)")
        _safe_add_column(conn, "summary_variants", "candidate_id", "VARCHAR(36)")
        _safe_add_column(conn, "keyword_sets", "candidate_id", "VARCHAR(36)")
        _safe_add_column(conn, "fact_sources", "candidate_id", "VARCHAR(36)")

        _safe_add_column(conn, "candidate_intake_drafts", "source_dossier", "TEXT")

        _safe_add_column(conn, "career_page_sources", "ats_type", "VARCHAR(50)")
        _safe_add_column(conn, "career_page_sources", "ats_slug", "VARCHAR(200)")

        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS career_page_scan_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id INTEGER NOT NULL REFERENCES career_page_sources(id),
                    scanned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    jobs_found INTEGER NOT NULL DEFAULT 0,
                    new_jobs INTEGER NOT NULL DEFAULT 0
                )
                """
            )
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_scan_logs_source_id ON career_page_scan_logs(source_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_scan_logs_scanned_at ON career_page_scan_logs(scanned_at)"))

        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS bullet_clarifications (
                    id VARCHAR(36) PRIMARY KEY,
                    draft_id VARCHAR(36) NOT NULL REFERENCES resume_drafts(id),
                    original_bullet TEXT NOT NULL DEFAULT '',
                    suggested_rewrite TEXT NOT NULL DEFAULT '',
                    user_accepted INTEGER NOT NULL DEFAULT 0,
                    promoted_to_fact_sheet INTEGER NOT NULL DEFAULT 0,
                    target_section VARCHAR(32) NOT NULL DEFAULT '',
                    target_item_index INTEGER,
                    target_bullet_index INTEGER,
                    language_map TEXT NOT NULL DEFAULT '{}',
                    questions TEXT NOT NULL DEFAULT '[]',
                    answers TEXT NOT NULL DEFAULT '[]',
                    rewritten_bullets TEXT NOT NULL DEFAULT '{}',
                    status VARCHAR NOT NULL DEFAULT 'pending_questions',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_bullet_clarifications_draft_id ON bullet_clarifications(draft_id)"))
        _safe_add_column(conn, "bullet_clarifications", "original_bullet", "TEXT DEFAULT ''")
        _safe_add_column(conn, "bullet_clarifications", "suggested_rewrite", "TEXT DEFAULT ''")
        _safe_add_column(conn, "bullet_clarifications", "user_accepted", "INTEGER DEFAULT 0")
        _safe_add_column(conn, "bullet_clarifications", "promoted_to_fact_sheet", "INTEGER DEFAULT 0")
        _safe_add_column(conn, "bullet_clarifications", "target_section", "VARCHAR(32) DEFAULT ''")
        _safe_add_column(conn, "bullet_clarifications", "target_item_index", "INTEGER")
        _safe_add_column(conn, "bullet_clarifications", "target_bullet_index", "INTEGER")

    logger.debug("Database prepared without startup-seeding career-page sources.")
