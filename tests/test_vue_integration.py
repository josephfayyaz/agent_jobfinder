from __future__ import annotations

from uuid import uuid4


def test_vue_health_contract(client):
    response = client.get("/api/vue/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["contract_version"] == 1
    assert payload["data"] == {"service": "vue-api", "status": "ok"}


def test_vue_session_contract_is_local_first_and_secret_safe(client):
    response = client.get("/api/vue/session")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["authenticated"] is True
    assert payload["data"]["local_first"] is True
    assert payload["data"]["secrets_exposed"] is False


def test_vue_jobs_contract_returns_saved_jobs(client, db_session):
    from job_agent.models import JobPost

    job = JobPost(
        id=uuid4(),
        source_name="manual",
        source_url="https://example.test/jobs/1",
        canonical_apply_url="https://example.test/jobs/1",
        company="ExampleCo",
        title="Backend Engineer",
        location="Turin, Italy",
        description="Python and FastAPI service role.",
        status="new",
        queue_state="new",
    )
    db_session.add(job)
    db_session.commit()

    response = client.get("/api/vue/jobs")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["total"] == 1
    assert payload["data"]["items"][0]["id"] == str(job.id)
    assert payload["data"]["items"][0]["company"] == "ExampleCo"


def test_vue_spa_serves_app_prefix_without_shadowing_legacy_routes(client, tmp_path, monkeypatch):
    import job_agent.main as main_module

    index = tmp_path / "index.html"
    index.write_text("<!doctype html><div id=\"app\">Vue shell</div>", encoding="utf-8")
    monkeypatch.setattr(main_module, "_VUE_INDEX", index)

    response = client.get("/app/dashboard")
    assert response.status_code == 200
    assert "Vue shell" in response.text

    missing = client.get("/not-a-vue-route")
    assert missing.status_code == 404


def test_vue_spa_reports_missing_build(client, tmp_path, monkeypatch):
    import job_agent.main as main_module

    monkeypatch.setattr(main_module, "_VUE_INDEX", tmp_path / "missing-index.html")

    response = client.get("/app")

    assert response.status_code == 503
    assert response.json()["error"] == "Vue build not found. Run: npm run build:vue"
