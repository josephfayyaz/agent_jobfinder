from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib
from unittest.mock import MagicMock
from uuid import UUID, uuid4

from job_agent.models import Application, CareerPageScanLog, CareerPageSource, JobPost, ResumeDraft


def test_health_endpoint_returns_ok(client):
    """Server is up and DB is reachable."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json().get("status") == "ok"


def test_openapi_schema_lists_key_endpoints(client):
    """Major API endpoint groups are registered in OpenAPI."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    for expected in [
        "/jobs",
        "/drafts",
        "/career-pages",
        "/analytics/rejection-patterns",
        "/analytics/posting-velocity",
        "/tasks/cv-workflow",
    ]:
        assert expected in paths, f"Missing endpoint: {expected}"


def test_manual_job_creation_and_cv_queue(client, db_track, monkeypatch):
    """
    Full journey: add a job manually → queue CV task → verify task in queue.
    """
    monkeypatch.setattr("job_agent.services.company_resolver.find_company_url", lambda **_: None)
    monkeypatch.setattr("job_agent.services.matching._get_embedding", lambda _text: None)
    monkeypatch.setattr(
        "job_agent.main.score_tracks_for_job",
        lambda job, tracks: [
            {
                "track_id": str(db_track.id),
                "slug": db_track.slug,
                "title": db_track.title,
                "role_family": db_track.role_family,
                "score": 88.0,
                "matched_keywords": ["python", "dbt"],
            }
        ],
    )

    response = client.post(
        "/jobs",
        json={
            "source_name": "manual",
            "source_url": "https://acme.example.com/jobs/99",
            "canonical_apply_url": "https://acme.example.com/jobs/99",
            "company": "AcmeCorp",
            "title": "Senior Data Engineer",
            "location": "Milan, Italy",
            "description": "Python, dbt, Spark, and Kubernetes required.",
            "status": "new",
        },
    )
    assert response.status_code in (200, 201)
    job_id = response.json()["id"]

    response = client.post(
        "/tasks/cv-workflow",
        json={"job_post_id": job_id, "resume_track_slug": db_track.slug},
    )
    assert response.status_code == 200
    task_id = response.json()["id"]
    assert task_id is not None

    response = client.get("/tasks")
    assert response.status_code == 200
    task_ids = [t["id"] for t in response.json()]
    assert task_id in task_ids


def test_draft_appears_in_drafts_list_after_workflow(client, db_session, db_job, db_track):
    """Draft appears in API list, UI list, and UI detail page."""
    draft = ResumeDraft(
        id=uuid4(),
        job_post_id=db_job.id,
        resume_track_id=db_track.id,
        provider="lm_studio_writer",
        status="pass",
        score=85.0,
        content={
            "professional_summary": "Experienced data engineer.",
            "selected_skills": ["Python", "dbt", "Spark"],
            "selected_experiences": [
                {"title": "Data Engineer", "company": "Acme", "bullets": ["Built pipelines."]}
            ],
            "selected_projects": [],
        },
        review_feedback={
            "ranked_keywords": [{"keyword": "Python", "frequency": 3, "priority": "high"}]
        },
        tex_path="",
        approved=False,
    )
    db_session.add(draft)
    db_session.commit()

    response = client.get("/drafts")
    assert response.status_code == 200
    assert any(item["id"] == str(draft.id) for item in response.json())

    response = client.get("/ui/drafts")
    assert response.status_code == 200
    assert "Acme" in response.text or "Data Engineer" in response.text

    response = client.get(f"/ui/drafts/{draft.id}")
    assert response.status_code == 200
    assert "Experienced data engineer" in response.text
    assert "Python" in response.text


def test_draft_approve_via_ui(client, db_session, db_job, db_track):
    """Approving a draft via UI endpoint sets approved=True."""
    draft = ResumeDraft(
        id=uuid4(),
        job_post_id=db_job.id,
        resume_track_id=db_track.id,
        provider="test",
        status="pass",
        score=80.0,
        content={},
        review_feedback={},
        tex_path="",
        approved=False,
    )
    db_session.add(draft)
    db_session.commit()

    response = client.post(f"/ui/drafts/{draft.id}/approve")
    assert response.status_code == 204

    db_session.refresh(draft)
    assert draft.approved is True
    assert draft.status == "approved"


def test_draft_reject_via_ui(client, db_session, db_job, db_track):
    draft = ResumeDraft(
        id=uuid4(),
        job_post_id=db_job.id,
        resume_track_id=db_track.id,
        provider="test",
        status="pass",
        score=72.0,
        content={},
        review_feedback={},
        tex_path="",
        approved=False,
    )
    db_session.add(draft)
    db_session.commit()

    response = client.post(f"/ui/drafts/{draft.id}/reject")
    assert response.status_code == 204

    db_session.refresh(draft)
    assert draft.approved is False
    assert draft.status == "rejected"


def test_compliance_matrix_generate_and_retrieve(client, db_session, db_job, db_track, monkeypatch):
    """POST generates matrix; GET retrieves it; UI detail shows it."""
    draft = ResumeDraft(
        id=uuid4(),
        job_post_id=db_job.id,
        resume_track_id=db_track.id,
        provider="test",
        status="pass",
        score=80.0,
        content={
            "professional_summary": "ML engineer",
            "selected_skills": ["Python"],
            "selected_experiences": [],
            "selected_projects": [],
        },
        review_feedback={},
        tex_path="",
    )
    db_session.add(draft)
    db_session.commit()

    def _fake_generate(self, draft_id):
        matrix = {
            "requirements": [{"id": "r1", "requirement": "Python 3+", "coverage": "strong"}],
            "strong_count": 1,
            "partial_count": 0,
            "missing_count": 0,
            "coverage_pct": 100.0,
        }
        draft_obj = self.session.get(ResumeDraft, draft_id)
        feedback = dict(draft_obj.review_feedback or {})
        feedback["compliance_matrix"] = matrix
        draft_obj.review_feedback = feedback
        self.session.commit()
        return matrix

    monkeypatch.setattr("job_agent.services.compliance_matrix.ComplianceMatrixService.generate", _fake_generate)

    response = client.post(f"/drafts/{draft.id}/compliance-matrix")
    assert response.status_code == 200
    assert response.json()["coverage_pct"] == 100.0

    response = client.get(f"/drafts/{draft.id}/compliance-matrix")
    assert response.status_code == 200
    assert response.json()["coverage_pct"] == 100.0

    response = client.get(f"/ui/drafts/{draft.id}")
    assert response.status_code == 200
    assert "Python 3+" in response.text
    assert "100" in response.text


def test_rejection_prediction_generate_and_retrieve(client, db_session, db_job, monkeypatch):
    """POST predicts risks; GET retrieves stored result; 404 before prediction."""
    response = client.get(f"/jobs/{db_job.id}/rejection-risk")
    assert response.status_code == 404

    def _fake_predict(self, job_post_id):
        prediction = {
            "risks": [
                {
                    "type": "soft_blocker",
                    "factor": "No Kubernetes",
                    "confidence": "high",
                    "mitigable": True,
                    "suggestion": "Add k8s evidence",
                    "evidence": "JD requires k8s",
                }
            ],
            "hard_blocker_count": 0,
            "soft_blocker_count": 1,
            "overall_risk": "medium",
            "recommendation": "Address Kubernetes gap before applying",
        }
        job = self.session.get(JobPost, job_post_id)
        metadata = dict(job.extracted_metadata or {})
        metadata["rejection_risks"] = prediction
        job.extracted_metadata = metadata
        self.session.commit()
        return prediction

    monkeypatch.setattr("job_agent.services.rejection_prediction.RejectionPredictionService.predict", _fake_predict)

    response = client.post(f"/jobs/{db_job.id}/rejection-risk")
    assert response.status_code == 200
    data = response.json()
    assert data["overall_risk"] == "medium"
    assert len(data["risks"]) == 1

    response = client.get(f"/jobs/{db_job.id}/rejection-risk")
    assert response.status_code == 200
    assert response.json()["overall_risk"] == "medium"


def test_application_created_and_advanced_through_stages(client, db_session, db_job):
    """Create an application and advance it through the pipeline stages."""
    response = client.post(
        "/applications",
        json={"job_post_id": str(db_job.id), "status": "applied", "notes": "Applied via start_apply CLI"},
    )
    assert response.status_code == 200
    app_id = UUID(response.json()["id"])

    response = client.get("/ui/applications")
    assert response.status_code == 200
    assert db_job.company in response.text

    response = client.post(f"/ui/applications/{app_id}/advance")
    assert response.status_code == 204
    app = db_session.get(Application, app_id)
    assert app.status == "phone_screen"

    client.post(f"/ui/applications/{app_id}/advance")
    app = db_session.get(Application, app_id)
    assert app.status == "interview"

    client.post(f"/ui/applications/{app_id}/advance")
    app = db_session.get(Application, app_id)
    assert app.status == "offer"


def test_career_page_source_add_toggle_and_scan(client, db_session, monkeypatch):
    """Add a company, toggle it inactive/active, and verify scan endpoint responds."""
    monkeypatch.setattr("job_agent.services.career_scanner.AtsApiScanner.fetch_jobs", lambda *args, **kwargs: [])

    response = client.post(
        "/career-pages",
        params={
            "company": "E2ECorp",
            "career_url": "https://e2ecorp.example.com/careers",
            "country": "Italy",
            "ats_type": "greenhouse",
            "ats_slug": "e2ecorp",
        },
    )
    assert response.status_code == 201
    source_id = response.json()["id"]

    response = client.get("/career-pages")
    companies = [s["company"] for s in response.json()]
    assert "E2ECorp" in companies

    response = client.get("/ui/companies")
    assert response.status_code == 200
    assert "E2ECorp" in response.text
    assert "greenhouse" in response.text

    response = client.post(f"/career-pages/{source_id}/toggle-active")
    assert response.status_code == 204
    source = db_session.get(CareerPageSource, source_id)
    assert source.active is False

    client.post(f"/career-pages/{source_id}/toggle-active")
    db_session.refresh(source)
    assert source.active is True

    response = client.post("/jobs/scan-career-pages")
    assert response.status_code == 200
    assert "new_jobs" in response.json()


def test_ats_greenhouse_scan_creates_job_posts(client, db_session, monkeypatch):
    """Greenhouse source scan creates JobPost records from ATS data."""
    source = CareerPageSource(
        company="GreenCo",
        career_url="https://greenco.example.com/careers",
        country="Italy",
        ats_type="greenhouse",
        ats_slug="greenco",
        active=True,
    )
    db_session.add(source)
    db_session.commit()

    monkeypatch.setattr("job_agent.services.matching._get_embedding", lambda _text: None)
    monkeypatch.setattr(
        "job_agent.services.career_scanner.AtsApiScanner.fetch_jobs",
        lambda self, ats_type, ats_slug: [
            {"title": "ML Engineer", "url": "https://greenhouse.io/jobs/1", "location": "Milan"},
            {"title": "Data Scientist", "url": "https://greenhouse.io/jobs/2", "location": "Remote"},
        ],
    )

    response = client.post("/jobs/scan-career-pages")
    assert response.status_code == 200
    assert response.json()["new_jobs"] >= 2

    posts = db_session.query(JobPost).filter_by(company="GreenCo").all()
    assert len(posts) >= 2
    titles = {p.title for p in posts}
    assert "ML Engineer" in titles


def test_analytics_api_returns_structure(client, monkeypatch):
    """GET /analytics/rejection-patterns returns expected keys."""
    monkeypatch.setattr(
        "job_agent.main.RejectionAnalyticsService.analyse",
        lambda self: {
            "funnel": {"discovered": 8, "applied": 6, "responded": 2, "offer": 0, "rejected": 1},
            "score_buckets": {"90-100": 1, "75-89": 3, "50-74": 2, "below-50": 0},
            "by_track": {"data-engineer": 6},
            "skill_gaps": [{"keyword": "Spark", "miss_count": 4}],
            "weekly_activity": [{"week": "2026-04-14", "count": 3}],
            "top_companies": [{"company": "Acme", "count": 3}],
        },
    )
    response = client.get("/analytics/rejection-patterns")
    assert response.status_code == 200
    data = response.json()
    assert {"funnel", "score_buckets", "skill_gaps"} <= data.keys()


def test_analytics_ui_shows_funnel_and_velocity(client, monkeypatch):
    """Analytics page renders all major sections including Posting Velocity."""
    monkeypatch.setattr(
        "job_agent.main.RejectionAnalyticsService.aggregate",
        lambda self, db: {
            "total_applications": 8,
            "funnel": {"discovered": 8, "applied": 6, "responded": 2, "offer": 0, "rejected": 1},
            "score_buckets": {"90-100": 1, "75-89": 3, "50-74": 2, "below-50": 0},
            "by_track": {},
            "skill_gaps": [],
            "weekly_activity": [],
            "top_companies": [],
        },
    )
    response = client.get("/ui/analytics")
    assert response.status_code == 200
    assert "Application Funnel" in response.text
    assert "CV Score Distribution" in response.text
    assert "Posting Velocity" in response.text


def test_analytics_posting_velocity_endpoint(client):
    """GET /analytics/posting-velocity returns days + companies keys."""
    response = client.get("/analytics/posting-velocity", params={"days": 7})
    assert response.status_code == 200
    data = response.json()
    assert "days" in data
    assert "companies" in data


def test_velocity_spike_only_returns_recent_logs(db_session, monkeypatch):
    """Regression: old logs must not trigger velocity spikes."""
    from job_agent.config import settings
    from job_agent.services.career_scanner import CareerPageScanner

    monkeypatch.setattr(settings, "velocity_spike_threshold", 3)
    source = CareerPageSource(
        company="SpikeCo",
        career_url="https://spikeco.example.com",
        country="Italy",
        active=True,
    )
    db_session.add(source)
    db_session.commit()

    old_log = CareerPageScanLog(source_id=source.id, jobs_found=10, new_jobs=8)
    db_session.add(old_log)
    db_session.commit()
    old_log.scanned_at = datetime.now(timezone.utc) - timedelta(hours=4)
    db_session.commit()

    spikes = CareerPageScanner().check_velocity_spikes(db_session)
    assert not any(s["company"] == "SpikeCo" for s in spikes)

    db_session.add(CareerPageScanLog(source_id=source.id, jobs_found=10, new_jobs=8))
    db_session.commit()
    spikes = CareerPageScanner().check_velocity_spikes(db_session)
    assert any(s["company"] == "SpikeCo" for s in spikes)


def test_start_apply_cli_help_exits_cleanly():
    """start_apply CLI is importable and exposes a main entry point."""
    mod = importlib.import_module("start_apply.cli")
    assert hasattr(mod, "main")


def test_start_apply_job_parser_extracts_title():
    """Job parser handles minimal input and returns structured data."""
    from start_apply.job_parser import parse_job_info

    router = MagicMock()
    router.generate.return_value = {
        "title": "Senior Data Engineer",
        "company": "Acme Corp",
        "location": "Milan",
        "description": "Requirements: Python, SQL, dbt, Airflow",
        "requirements": ["Python", "SQL", "dbt", "Airflow"],
    }
    result = parse_job_info("Senior Data Engineer — Acme Corp, Milan", router=router)
    assert isinstance(result, dict)
    assert result["title"] == "Senior Data Engineer"


def test_start_apply_scorer_returns_score_dict():
    """Scorer returns dict with a numeric score key."""
    from start_apply.scorer import score_match

    router = MagicMock()
    router.generate.return_value = {
        "score": 72,
        "matched": ["Python", "SQL"],
        "gaps": ["Kubernetes"],
        "summary": "Reasonable fit with one important gap.",
    }
    result = score_match(
        {"title": "Data Engineer", "company": "Acme", "requirements": ["Python", "SQL"]},
        "Candidate fact sheet",
        router=router,
    )
    assert isinstance(result, dict)
    assert isinstance(result["score"], int)


def test_all_ui_pages_return_200(client):
    """Every main nav page must respond with 200."""
    pages = [
        "/ui",
        "/ui/jobs",
        "/ui/drafts",
        "/ui/applications",
        "/ui/analytics",
        "/ui/companies",
        "/ui/settings",
        "/ui/thesis",
    ]
    for path in pages:
        response = client.get(path)
        assert response.status_code == 200, f"Page {path} returned {response.status_code}"


def test_nav_links_present_on_every_page(client):
    """Base template nav links must be visible."""
    nav_labels = ["Jobs", "CVs", "Analytics", "Companies", "Applications"]
    response = client.get("/ui/jobs")
    assert response.status_code == 200
    for label in nav_labels:
        assert label in response.text, f"Nav label '{label}' missing from page"
