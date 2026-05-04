"""Cross-platform runtime paths for the single-user workspace."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import sqlite3
import sys

APP_NAME = "Job Agent"
APP_SLUG = "job-agent"


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def app_home() -> Path:
    override = os.getenv("JOB_AGENT_HOME", "").strip()
    if override:
        return Path(override).expanduser().resolve()

    home = Path.home()
    if sys.platform == "darwin":
        return (home / "Library" / "Application Support" / APP_NAME).resolve()
    if os.name == "nt":
        base = Path(os.getenv("LOCALAPPDATA") or home / "AppData" / "Local")
        return (base / APP_NAME).resolve()
    base = Path(os.getenv("XDG_DATA_HOME") or home / ".local" / "share")
    return (base / APP_SLUG).resolve()


def config_dir() -> Path:
    return app_home() / "config"


def backups_dir() -> Path:
    return app_home() / "backups"


def default_database_path() -> Path:
    return app_home() / "job_agent.db"


def user_settings_path() -> Path:
    return config_dir() / "user_settings.yml"


def gmail_oauth_token_path() -> Path:
    return config_dir() / "gmail_oauth_token.json"


def gmail_oauth_state_path() -> Path:
    return config_dir() / "gmail_oauth_state.json"


def default_artifacts_dir() -> Path:
    return app_home() / "generated"


def resolve_artifacts_dir(value: str | Path | None) -> Path:
    raw = Path(value or "generated").expanduser()
    if raw.is_absolute():
        return raw.resolve()
    return (app_home() / raw).resolve()


def legacy_user_settings_path() -> Path:
    return project_root() / "config" / "user_settings.yml"


def legacy_database_path() -> Path:
    return project_root() / "job_agent.db"


def legacy_artifacts_dir() -> Path:
    return project_root() / "generated"


def legacy_runtime_paths() -> list[Path]:
    return [
        legacy_user_settings_path(),
        legacy_database_path(),
        legacy_database_path().with_suffix(".db-shm"),
        legacy_database_path().with_suffix(".db-wal"),
        legacy_artifacts_dir(),
    ]


def ensure_runtime_dirs() -> None:
    for path in [app_home(), config_dir(), backups_dir()]:
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise RuntimeError(
                f"Cannot create app data directory at {path}: {exc}. "
                f"Set the JOB_AGENT_HOME environment variable to a writable directory "
                f"and restart the application."
            ) from exc


def _copy_sqlite_database(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(src) as source, sqlite3.connect(dst) as target:
        source.backup(target)


def bootstrap_runtime_state() -> dict[str, str]:
    """Create the runtime home and non-destructively import legacy repo-local state."""
    ensure_runtime_dirs()
    migrated: dict[str, str] = {}

    dst_settings = user_settings_path()
    src_settings = legacy_user_settings_path()
    if not dst_settings.exists() and src_settings.exists():
        shutil.copy2(src_settings, dst_settings)
        migrated["user_settings"] = str(dst_settings)

    dst_db = default_database_path()
    src_db = legacy_database_path()
    if not dst_db.exists() and src_db.exists():
        try:
            _copy_sqlite_database(src_db, dst_db)
        except sqlite3.Error:
            shutil.copy2(src_db, dst_db)
        migrated["database"] = str(dst_db)

    dst_artifacts = default_artifacts_dir()
    src_artifacts = legacy_artifacts_dir()
    if not dst_artifacts.exists() and src_artifacts.exists():
        shutil.copytree(src_artifacts, dst_artifacts, dirs_exist_ok=True)
        migrated["artifacts"] = str(dst_artifacts)

    return migrated
