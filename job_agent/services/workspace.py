"""Workspace-level backup and privacy operations for the single-user app."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

from sqlalchemy.orm import Session

from job_agent.config import settings
from job_agent.db import Base
from job_agent.runtime_paths import (
    app_home,
    backups_dir,
    default_database_path,
    legacy_runtime_paths,
    resolve_artifacts_dir,
    user_settings_path,
)
from job_agent.seed import seed_reference_data
from job_agent.user_config import delete_user_settings

SHARE_REPOSITORY_URL = "https://github.com/josephfayyaz"
RESET_CONFIRMATION_PHRASE = "START OVER"
DELETE_CONFIRMATION_PHRASE = "DELETE MY DATA"


def sqlite_db_path() -> Path:
    db_url = settings.database_url or f"sqlite:///{default_database_path()}"
    if db_url.startswith("sqlite:///"):
        return Path(db_url.removeprefix("sqlite:///")).expanduser().resolve()
    return default_database_path().resolve()


def workspace_status() -> dict[str, object]:
    runtime_home = app_home()
    artifacts_dir = resolve_artifacts_dir(settings.artifacts_dir)
    db_path = sqlite_db_path()
    backup_dir = backups_dir()
    backup_count = len(list(backup_dir.glob("job_agent_backup_*.zip"))) if backup_dir.exists() else 0
    return {
        "app_home": str(runtime_home),
        "user_settings_path": str(user_settings_path()),
        "database_path": str(db_path),
        "artifacts_dir": str(artifacts_dir),
        "backups_dir": str(backup_dir),
        "backup_count": backup_count,
        "share_url": SHARE_REPOSITORY_URL,
        "has_backupable_db": db_path.exists(),
        "legacy_runtime_present": any(path.exists() for path in legacy_runtime_paths()),
    }


def _add_to_zip(bundle: zipfile.ZipFile, source: Path, target_root: str) -> None:
    if not source.exists():
        return
    if source.is_file():
        bundle.write(source, arcname=target_root)
        return
    for child in source.rglob("*"):
        if child.is_file():
            bundle.write(child, arcname=str(Path(target_root) / child.relative_to(source)))


def build_workspace_backup() -> Path:
    runtime_snapshot = workspace_status()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = backups_dir()
    backup_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = backup_dir / f"job_agent_backup_{timestamp}.zip"

    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        manifest = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "workspace": runtime_snapshot,
        }
        bundle.writestr("manifest.json", json.dumps(manifest, indent=2))
        _add_to_zip(bundle, user_settings_path(), "workspace/user_settings.yml")
        _add_to_zip(bundle, sqlite_db_path(), "workspace/job_agent.db")

        artifacts_dir = resolve_artifacts_dir(settings.artifacts_dir)
        if artifacts_dir.exists():
            _add_to_zip(bundle, artifacts_dir, "workspace/artifacts")

    return bundle_path


def open_backups_folder() -> Path:
    path = backups_dir()
    path.mkdir(parents=True, exist_ok=True)

    if sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    elif os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
    else:
        opener = shutil.which("xdg-open")
        if not opener:
            raise RuntimeError("xdg-open is not available on this system.")
        subprocess.Popen([opener, str(path)])

    return path


def _clear_database(session: Session) -> None:
    connection = session.connection()
    try:
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
    except Exception:
        pass

    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()

    seed_reference_data(session)
    session.commit()

    try:
        connection.exec_driver_sql("PRAGMA wal_checkpoint(TRUNCATE)")
    except Exception:
        pass
    try:
        session.commit()
        connection.exec_driver_sql("VACUUM")
    except Exception:
        pass
    try:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
    except Exception:
        pass


def _safe_remove(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
        return
    path.unlink(missing_ok=True)


def wipe_workspace(session: Session, *, delete_downloads: bool) -> dict[str, object]:
    """Clear all user/runtime data while keeping the installed code intact."""
    _clear_database(session)

    delete_user_settings()
    _safe_remove(resolve_artifacts_dir(settings.artifacts_dir))
    if delete_downloads:
        _safe_remove(backups_dir())

    current_db = sqlite_db_path()
    for legacy_path in legacy_runtime_paths():
        if legacy_path.resolve() == current_db:
            continue
        _safe_remove(legacy_path)

    return {
        "downloads_removed": delete_downloads,
    }


def reset_confirmation_phrase() -> str:
    return RESET_CONFIRMATION_PHRASE


def delete_confirmation_phrase() -> str:
    return DELETE_CONFIRMATION_PHRASE
