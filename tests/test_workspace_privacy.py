from __future__ import annotations

import zipfile


def test_create_candidate_updates_existing_owner(client, db_session, tmp_path, monkeypatch):
    import job_agent.config as cfg
    import job_agent.routers.setup_state as setup_state
    import job_agent.user_config as user_config

    settings_path = tmp_path / "user_settings.yml"
    monkeypatch.setattr(user_config, "USER_SETTINGS_PATH", settings_path)
    monkeypatch.setattr(cfg, "_USER_SETTINGS_PATH", settings_path)
    monkeypatch.setattr(setup_state, "_USER_SETTINGS_FILE", settings_path)

    first = client.post(
        "/candidates",
        json={"full_name": "First Owner", "email": "first@example.com"},
    )
    assert first.status_code == 200
    first_id = first.json()["id"]

    second = client.post(
        "/candidates",
        json={"full_name": "Updated Owner", "email": "updated@example.com"},
    )
    assert second.status_code == 200
    payload = second.json()
    assert payload["id"] == first_id
    assert payload["full_name"] == "Updated Owner"

    from job_agent.models import Candidate

    rows = db_session.query(Candidate).all()
    assert len(rows) == 1
    assert rows[0].email == "updated@example.com"


def test_build_workspace_backup_includes_manifest_and_settings(tmp_path, monkeypatch):
    from job_agent.services import workspace as workspace_service

    settings_path = tmp_path / "config" / "user_settings.yml"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text("target_job_seniority: junior\n", encoding="utf-8")

    db_path = tmp_path / "job_agent.db"
    db_path.write_text("sqlite-placeholder", encoding="utf-8")

    artifacts_dir = tmp_path / "generated"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / "cv.txt").write_text("cv body", encoding="utf-8")
    backup_dir = tmp_path / "backups"

    monkeypatch.setattr(workspace_service, "user_settings_path", lambda: settings_path)
    monkeypatch.setattr(workspace_service, "sqlite_db_path", lambda: db_path)
    monkeypatch.setattr(workspace_service, "resolve_artifacts_dir", lambda _value: artifacts_dir)
    monkeypatch.setattr(workspace_service, "backups_dir", lambda: backup_dir)

    bundle_path = workspace_service.build_workspace_backup()
    try:
        assert bundle_path.exists()
        assert bundle_path.parent == backup_dir
        with zipfile.ZipFile(bundle_path) as bundle:
            names = set(bundle.namelist())
            assert "manifest.json" in names
            assert "workspace/user_settings.yml" in names
            assert "workspace/job_agent.db" in names
            assert "workspace/artifacts/cv.txt" in names
    finally:
        bundle_path.unlink(missing_ok=True)


def test_workspace_status_exposes_github_profile_share_url():
    from job_agent.services import workspace as workspace_service

    status = workspace_service.workspace_status()

    assert status["share_url"] == "https://github.com/josephfayyaz"


def test_workspace_reset_requires_phrase(client):
    response = client.post("/workspace/reset", json={"phrase": "wrong"})
    assert response.status_code == 422
    assert "START OVER" in response.json()["detail"]


def test_workspace_reset_clears_data_but_keeps_backups(client, db_session, tmp_path, monkeypatch):
    import job_agent.config as cfg
    import job_agent.user_config as user_config
    from job_agent.models import Candidate
    from job_agent.services import workspace as workspace_service

    settings_path = tmp_path / "user_settings.yml"
    settings_path.write_text("default_candidate_id: old\n", encoding="utf-8")
    monkeypatch.setattr(user_config, "USER_SETTINGS_PATH", settings_path)
    monkeypatch.setattr(cfg, "_USER_SETTINGS_PATH", settings_path)

    artifacts_dir = tmp_path / "generated"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / "cv.tex").write_text("draft", encoding="utf-8")

    backups_dir = tmp_path / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)
    (backups_dir / "keep.zip").write_text("backup", encoding="utf-8")

    monkeypatch.setattr(workspace_service, "resolve_artifacts_dir", lambda _value: artifacts_dir)
    monkeypatch.setattr(workspace_service, "backups_dir", lambda: backups_dir)
    monkeypatch.setattr(workspace_service, "legacy_runtime_paths", lambda: [])

    create = client.post("/candidates", json={"full_name": "Owner", "email": "owner@example.com"})
    assert create.status_code == 200
    assert db_session.query(Candidate).count() == 1

    response = client.post("/workspace/reset", json={"phrase": "START OVER"})
    assert response.status_code == 200
    assert response.json()["status"] == "reset"
    assert db_session.query(Candidate).count() == 0
    assert not settings_path.exists()
    assert not artifacts_dir.exists()
    assert backups_dir.exists()
    assert (backups_dir / "keep.zip").exists()


def test_workspace_delete_removes_backups(client, db_session, tmp_path, monkeypatch):
    import job_agent.config as cfg
    import job_agent.user_config as user_config
    from job_agent.services import workspace as workspace_service

    settings_path = tmp_path / "user_settings.yml"
    settings_path.write_text("default_candidate_id: old\n", encoding="utf-8")
    monkeypatch.setattr(user_config, "USER_SETTINGS_PATH", settings_path)
    monkeypatch.setattr(cfg, "_USER_SETTINGS_PATH", settings_path)

    artifacts_dir = tmp_path / "generated"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    backups_dir = tmp_path / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)
    (backups_dir / "remove.zip").write_text("backup", encoding="utf-8")

    monkeypatch.setattr(workspace_service, "resolve_artifacts_dir", lambda _value: artifacts_dir)
    monkeypatch.setattr(workspace_service, "backups_dir", lambda: backups_dir)
    monkeypatch.setattr(workspace_service, "legacy_runtime_paths", lambda: [])

    response = client.post("/workspace/delete", json={"phrase": "DELETE MY DATA"})
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"
    assert not backups_dir.exists()


def test_workspace_backups_open_endpoint(client, monkeypatch, tmp_path):
    import job_agent.routers.system as system_module

    opened: list[str] = []

    def _fake_open():
        path = tmp_path / "backups"
        path.mkdir(parents=True, exist_ok=True)
        opened.append(str(path))
        return path

    monkeypatch.setattr(system_module, "open_backups_folder", _fake_open)

    response = client.post("/workspace/backups/open")
    assert response.status_code == 200
    assert response.json()["status"] == "opened"
    assert opened


def test_workspace_reset_page_renders_backup_actions(client):
    response = client.get("/ui/workspace-reset?mode=reset")
    assert response.status_code == 200
    assert "Open Backup Folder" in response.text
    assert "Continue to Setup" in response.text
