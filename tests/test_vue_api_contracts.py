from __future__ import annotations

from uuid import uuid4

from job_agent.models import Application, CareerPageSource, JobPost, ResumeDraft, ResumeTrack, ThesisTarget


def _make_job(db_session) -> JobPost:
    job = JobPost(
        company="Acme",
        title="Data Engineer",
        description="Build pipelines and analytics workflows.",
        source_name="manual",
        source_url="https://example.com/jobs/1",
        canonical_apply_url="https://example.com/jobs/1",
        location="Milan, Italy",
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


def _make_track(db_session) -> ResumeTrack:
    track = ResumeTrack(
        slug="data-engineering",
        title="Data Engineering",
        role_family="data",
        baseline_summary="Data engineering baseline.",
        target_keywords=["python", "sql"],
        emphasis={},
        linkedin_strategy="",
        github_strategy="",
        active=True,
    )
    db_session.add(track)
    db_session.commit()
    db_session.refresh(track)
    return track


def _make_draft(db_session, job: JobPost, track: ResumeTrack) -> ResumeDraft:
    draft = ResumeDraft(
        job_post_id=job.id,
        resume_track_id=track.id,
        provider="heuristic",
        status="drafted",
        content={"summary": "Test"},
        review_feedback={},
    )
    db_session.add(draft)
    db_session.commit()
    db_session.refresh(draft)
    return draft


def test_vue_api_health_contract(client):
    response = client.get("/api/vue/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["contract_version"] == 1
    assert payload["data"]["service"] == "vue-api"


def test_vue_api_navigation_contract(client):
    response = client.get("/api/vue/navigation")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert isinstance(payload["data"]["groups"], list)
    assert any(group["label"] == "Main" for group in payload["data"]["groups"])


def test_vue_api_setup_state_contract(client):
    response = client.get("/api/vue/setup/state")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "loaded" in payload["data"]
    assert "setup_complete" in payload["data"]
    assert "requires_setup" in payload["data"]


def test_vue_api_session_has_no_secret_looking_keys(client):
    response = client.get("/api/vue/session")

    assert response.status_code == 200
    payload = response.json()
    lowered_keys = {key.lower() for key in payload["data"].keys()}
    assert "api_key" not in lowered_keys
    assert "token" not in lowered_keys
    assert "secret" not in lowered_keys
    assert "password" not in lowered_keys


def test_vue_api_dashboard_summary_envelope(client):
    response = client.get("/api/vue/dashboard/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "cards" in payload["data"]
    assert "pdflatex_path" not in payload["data"]["sections"]["system"]


def test_vue_api_jobs_list_and_detail(client, db_session):
    job = _make_job(db_session)

    response = client.get("/api/vue/jobs")
    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["total"] >= 1
    assert any(item["id"] == str(job.id) for item in payload["data"]["items"])

    detail_response = client.get(f"/api/vue/jobs/{job.id}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["data"]["item"]["id"] == str(job.id)


def test_vue_api_jobs_missing_id_returns_contract_404(client):
    response = client.get(f"/api/vue/jobs/{uuid4()}")

    assert response.status_code == 404
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "not_found"


def test_vue_api_companies_list_and_detail(client, db_session):
    source = CareerPageSource(company="Acme", career_url="https://acme.example/jobs", country="Italy")
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)

    response = client.get("/api/vue/companies")
    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["total"] >= 1

    detail_response = client.get(f"/api/vue/companies/{source.id}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["data"]["item"]["id"] == str(source.id)


def test_vue_api_applications_and_drafts_contracts(client, db_session):
    job = _make_job(db_session)
    track = _make_track(db_session)
    draft = _make_draft(db_session, job, track)
    application = Application(job_post_id=job.id, resume_track_id=track.id, resume_draft_id=draft.id)
    db_session.add(application)
    db_session.commit()
    db_session.refresh(application)

    draft_response = client.get("/api/vue/drafts")
    assert draft_response.status_code == 200
    assert any(item["id"] == str(draft.id) for item in draft_response.json()["data"]["items"])

    draft_detail = client.get(f"/api/vue/drafts/{draft.id}")
    assert draft_detail.status_code == 200
    assert draft_detail.json()["data"]["item"]["id"] == str(draft.id)

    application_response = client.get("/api/vue/applications")
    assert application_response.status_code == 200
    assert any(item["id"] == str(application.id) for item in application_response.json()["data"]["items"])

    application_detail = client.get(f"/api/vue/applications/{application.id}")
    assert application_detail.status_code == 200
    assert application_detail.json()["data"]["item"]["id"] == str(application.id)


def test_vue_api_settings_exposes_no_secrets(client):
    response = client.get("/api/vue/settings")

    assert response.status_code == 200
    payload = response.json()
    serialized = str(payload).lower()
    assert "api_key" not in serialized
    assert "token" not in serialized
    assert "secret" not in serialized
    assert "password" not in serialized


def test_vue_api_apply_score_empty_description_returns_422(client):
    response = client.post("/api/vue/apply/score", json={"job_description": ""})

    assert response.status_code == 422
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "validation_error"


def test_vue_api_apply_score_non_empty_returns_contract_success(client, monkeypatch):
    from start_apply import job_parser, scorer

    monkeypatch.setattr(
        job_parser,
        "parse_job_info",
        lambda text: {
            "title": "Data Engineer",
            "company": "Acme",
            "location": "Italy",
            "description": text,
        },
    )
    monkeypatch.setattr(
        scorer,
        "score_match",
        lambda job, fs: {
            "score": 84,
            "matched": ["Python", "SQL"],
            "gaps": ["dbt"],
            "summary": "Strong fit overall.",
        },
    )
    monkeypatch.setattr(
        "job_agent.services.resource_loader.ResourceLoader.load_fact_sheet_text",
        lambda self: "fact sheet text",
    )

    response = client.post("/api/vue/apply/score", json={"job_description": "Data engineer role"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["score"] == 84
    assert payload["data"]["job_data"]["title"] == "Data Engineer"


def test_vue_api_workspace_reset_preview_is_safe(client):
    response = client.post(
        "/api/vue/workspace/reset-preview",
        json={"include_generated_files": True, "include_cached_results": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["destructive_action_taken"] is False


def test_vue_api_workspace_status_has_no_absolute_paths(client):
    response = client.get("/api/vue/workspace/status")

    assert response.status_code == 200
    payload = response.json()
    assert "app_home" not in payload["data"]
    assert "database_path" not in payload["data"]
    assert "artifacts_dir" not in payload["data"]
    assert "backups_dir" not in payload["data"]
    assert "user_settings_path" not in payload["data"]


def test_vue_api_unknown_route_returns_json(client):
    response = client.get("/api/vue/does-not-exist")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")


def test_vue_api_thesis_targets_contract(client, db_session):
    target = ThesisTarget(
        type="professor",
        name="Prof Example",
        institution="Example University",
        country="Italy",
        research_area="NLP",
    )
    db_session.add(target)
    db_session.commit()

    response = client.get("/api/vue/thesis/targets")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["total"] >= 1
