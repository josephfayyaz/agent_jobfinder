from __future__ import annotations

from pathlib import Path
import uuid

import yaml


def test_render_tex_uses_company_name_in_filename(tmp_path, monkeypatch, sample_profile):
    monkeypatch.setattr("job_agent.services.documents.settings.artifacts_dir", tmp_path)
    from job_agent.services.documents import render_resume_tex

    draft_id = str(uuid.uuid4())
    tex_path = render_resume_tex(
        profile=sample_profile,
        job={"title": "Data Engineer", "company": "Acme Corp"},
        track={"baseline_summary": "Summary"},
        content={
            "professional_summary": "Test",
            "selected_experiences": [],
            "selected_projects": [],
            "selected_skills": [],
            "tailoring_notes": [],
        },
        draft_id=draft_id,
    )

    name = Path(tex_path).name
    assert "Acme_Corp" in name or "Acme" in name
    assert draft_id[:8] in name
    assert name.endswith(".tex")


def test_artifacts_dir_created_if_missing(tmp_path, monkeypatch, sample_profile):
    new_dir = tmp_path / "subdir" / "cvs"
    monkeypatch.setattr("job_agent.services.documents.settings.artifacts_dir", new_dir)
    from job_agent.services.documents import render_resume_tex

    render_resume_tex(
        profile=sample_profile,
        job={"title": "Data Engineer", "company": "Acme"},
        track={"baseline_summary": "Summary"},
        content={
            "professional_summary": "Test",
            "selected_experiences": [],
            "selected_projects": [],
            "selected_skills": [],
            "tailoring_notes": [],
        },
        draft_id=str(uuid.uuid4()),
    )

    assert new_dir.exists()


def test_settings_save_accepts_artifacts_dir(client, tmp_path, monkeypatch):
    from job_agent import user_config

    settings_path = tmp_path / "us.yml"
    monkeypatch.setattr(user_config, "USER_SETTINGS_PATH", settings_path)
    response = client.post("/settings/save", json={"artifacts_dir": str(tmp_path)})

    assert response.status_code == 200
    data = yaml.safe_load(settings_path.read_text(encoding="utf-8"))
    assert data["artifacts_dir"] == str(tmp_path)
