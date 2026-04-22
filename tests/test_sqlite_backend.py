from __future__ import annotations

from pathlib import Path


def test_health_reports_sqlite(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "db_backend" in data
    assert data["db_backend"] == "sqlite"


def test_safe_add_column_idempotent(db_session):
    from job_agent.db import _safe_add_column

    with db_session.bind.connect() as conn:
        _safe_add_column(conn, "job_posts", "title", "TEXT")
        _safe_add_column(conn, "job_posts", "title", "TEXT")


def test_default_db_url_is_absolute_sqlite():
    from job_agent.db import _default_db_url

    url = _default_db_url()
    assert url.startswith("sqlite:///")
    path_part = url.removeprefix("sqlite:///")
    assert Path(path_part).is_absolute()
