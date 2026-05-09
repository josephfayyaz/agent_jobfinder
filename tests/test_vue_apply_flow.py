from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException

from job_agent.models import ResumeDraft, WorkflowTask


def _job_payload() -> dict[str, object]:
    return {
        "title": "Data Engineer",
        "company": "Acme",
        "location": "Milan, Italy",
        "description": "Build pipelines and analytics workflows.",
        "url": "https://example.com/jobs/123",
    }


def test_vue_apply_score_empty_description_returns_contract_422(client):
    response = client.post("/api/vue/apply/score", json={"job_description": ""})

    assert response.status_code == 422
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "validation_error"


def test_vue_apply_score_valid_description_returns_contract_success(client, monkeypatch):
    from start_apply import job_parser, scorer

    monkeypatch.setattr(job_parser, "parse_job_info", lambda text: _job_payload() | {"description": text})
    monkeypatch.setattr(
        scorer,
        "score_match",
        lambda job, fs: {
            "score": 88,
            "matched": ["Python", "SQL"],
            "gaps": ["dbt"],
            "summary": "Strong fit with one tooling gap.",
        },
    )
    monkeypatch.setattr(
        "job_agent.services.resource_loader.ResourceLoader.load_fact_sheet_text",
        lambda self: "fact sheet text",
    )

    response = client.post("/api/vue/apply/score", json={"job_description": "Data Engineer role"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["contract_version"] == 1
    assert payload["data"]["score"] == 88
    assert payload["data"]["job_data"]["company"] == "Acme"
    assert payload["data"]["track_options"] == []
    assert "Users" not in str(payload)


def test_vue_apply_score_setup_required_returns_safe_contract_error(client, monkeypatch):
    async def fake_apply_parse(*, job_text, db):
        del job_text, db
        raise HTTPException(
            status_code=409,
            detail={
                "error": "setup_required",
                "message": "Finish the quick setup first so Job Agent has a candidate profile and target roles.",
            },
        )

    monkeypatch.setattr("job_agent.routers.jobs.apply_parse", fake_apply_parse)

    response = client.post("/api/vue/apply/score", json={"job_description": "Data Engineer role"})

    assert response.status_code == 409
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "setup_required"
    assert "Users" not in str(payload)
    assert "secret" not in str(payload).lower()


def test_vue_apply_questions_missing_job_data_returns_contract_422(client):
    response = client.post("/api/vue/apply/questions", json={"gaps": []})

    assert response.status_code == 422
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "validation_error"


def test_vue_apply_questions_valid_payload_returns_contract_success(client, monkeypatch):
    async def fake_apply_questions(*, body, db):
        del db
        assert body["job"]["title"] == "Data Engineer"
        return {
            "questions": [
                {
                    "id": "q0",
                    "gap": "dbt",
                    "question": "Have you used dbt in production?",
                    "why": "This would strengthen pipeline evidence.",
                }
            ]
        }

    monkeypatch.setattr("job_agent.routers.jobs.apply_questions", fake_apply_questions)

    response = client.post(
        "/api/vue/apply/questions",
        json={"job_data": _job_payload(), "gaps": ["dbt"], "answers": {}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["questions"][0]["id"] == "q0"
    assert "secret" not in str(payload).lower()


def test_vue_apply_draft_missing_job_data_returns_contract_422(client):
    response = client.post("/api/vue/apply/draft", json={"answers": {}, "questions": []})

    assert response.status_code == 422
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "validation_error"


def test_vue_apply_draft_valid_payload_queues_task(client, db_session, db_track):
    response = client.post(
        "/api/vue/apply/draft",
        json={
            "job_data": _job_payload(),
            "track_slug": db_track.slug,
            "questions": [{"id": "q0", "gap": "dbt", "question": "Have you used dbt in production?"}],
            "answers": {"q0": "Yes, I shipped dbt models with tests."},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["task_id"]

    task = db_session.query(WorkflowTask).order_by(WorkflowTask.created_at.desc()).first()
    assert task is not None
    assert task.payload["resume_track_slug"] == db_track.slug
    assert task.payload["confirmed_facts"][0]["question_id"] == "q0"
    assert task.payload["confirmed_facts"][0]["confirmed"] is True


def test_vue_apply_status_unknown_task_returns_safe_contract_error(client):
    response = client.get("/api/vue/apply/status/not-a-real-task")

    assert response.status_code == 404
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "not_found"


def test_vue_apply_status_completed_returns_draft_id(client, db_session, db_job, db_track):
    draft = ResumeDraft(
        job_post_id=db_job.id,
        resume_track_id=db_track.id,
        provider="heuristic",
        status="drafted",
        content={"summary": "Ready"},
        review_feedback={},
    )
    db_session.add(draft)
    db_session.commit()
    db_session.refresh(draft)

    task = WorkflowTask(
        kind="cv_workflow",
        status="completed",
        payload={"job_post_id": str(db_job.id), "resume_track_slug": db_track.slug},
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    response = client.get(f"/api/vue/apply/status/{task.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["status"] == "completed"
    assert payload["data"]["draft_id"] == str(draft.id)


def test_apply_page_source_uses_router_push_and_drops_old_read_only_copy():
    source = Path("frontend/vue/src/pages/ApplyPage.vue").read_text()

    assert "window.location.href" not in source
    assert "This Vue shell does not call" not in source
    assert "use the legacy interface at" not in source
    assert "router.push(`/drafts/${nextDraftId}`)" in source
    assert "Generate Draft" in source
    assert "Setup required before applying" in source
    assert 'to="/onboarding"' in source
    assert 'to="/settings"' in source
    assert 'href="/ui/apply"' in source
    assert 'window.location.href = "/ui/onboarding"' not in source
    assert "Legacy apply fallback" in source
