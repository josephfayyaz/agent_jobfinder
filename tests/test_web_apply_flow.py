from __future__ import annotations


def test_apply_parse_returns_score(client, monkeypatch):
    from start_apply import job_parser, scorer

    monkeypatch.setattr(
        job_parser,
        "parse_job_info",
        lambda text: {
            "title": "DE",
            "company": "A",
            "location": "IT",
            "description": text,
        },
    )
    monkeypatch.setattr(
        scorer,
        "score_match",
        lambda job, fs: {
            "score": 80,
            "matched": ["Python"],
            "gaps": ["SQL"],
            "summary": "Good match",
        },
    )
    monkeypatch.setattr(
        "job_agent.services.resource_loader.ResourceLoader.load_fact_sheet_text",
        lambda self: "fact sheet text",
    )

    response = client.post("/apply/parse", data={"job_text": "Data Engineer role at Acme"})
    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 80
    assert "Python" in data["matched"]


def test_apply_generate_creates_task(client):
    response = client.post(
        "/apply/generate",
        json={
            "job": {"title": "DE", "company": "Acme", "location": "IT", "description": "..."},
            "answers": [],
            "track_slug": "data-engineering",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert "job_id" in data


def test_apply_status_pending(client, db_session):
    from job_agent.models import WorkflowTask

    task = WorkflowTask(kind="cv_workflow", status="pending", payload={})
    db_session.add(task)
    db_session.commit()
    response = client.get(f"/apply/status/{task.id}")
    assert response.status_code == 200
    assert response.json()["status"] == "pending"


def test_apply_page_renders(client):
    response = client.get("/ui/apply")
    assert response.status_code == 200
    assert b"Paste Job Info" in response.content


def test_manual_target_analyze_returns_score_without_queue_insert(client, db_session, monkeypatch):
    from job_agent.models import JobPost
    from start_apply import job_parser, scorer

    monkeypatch.setattr(
        job_parser,
        "parse_job_info",
        lambda text: {
            "title": "Operations Analyst",
            "company": "BrightCo",
            "location": "Italy",
            "description": text,
        },
    )
    monkeypatch.setattr(
        scorer,
        "score_match",
        lambda job, fs: {
            "score": 77,
            "matched": ["Excel", "Reporting"],
            "gaps": ["SAP"],
            "summary": "Solid business-operations fit.",
        },
    )
    monkeypatch.setattr(
        "job_agent.services.resource_loader.ResourceLoader.load_fact_sheet_text",
        lambda self: "fact sheet text",
    )

    response = client.post("/ui/jobs/manual-target/analyze", json={"text": "Operations Analyst role"})
    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 77
    assert data["job"]["title"] == "Operations Analyst"
    assert db_session.query(JobPost).count() == 0
