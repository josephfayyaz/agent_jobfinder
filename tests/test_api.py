from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

from job_agent.models import (
    Application,
    EnhancementProposal,
    JobTrackScore,
    OutreachDraft,
    ResumeDraft,
    ThesisTarget,
)


def jresp(r):
    """Pretty-print response JSON on assertion failure."""
    try:
        return r.json()
    except Exception:
        return r.text


def _track_score_payload(track, score: float = 88.0) -> list[dict[str, object]]:
    return [
        {
            "track_id": str(track.id),
            "slug": track.slug,
            "title": track.title,
            "role_family": track.role_family,
            "score": score,
            "matched_keywords": ["python", "sql"],
        }
    ]


def _create_draft(
    db_session,
    job_id,
    track_id,
    *,
    approved: bool = False,
    status: str = "drafted",
    score: float = 80.0,
    cover_letter_text: str | None = None,
    cover_letter_subject: str | None = None,
) -> ResumeDraft:
    draft = ResumeDraft(
        id=uuid4(),
        job_post_id=job_id,
        resume_track_id=track_id,
        provider="test",
        status=status,
        score=score,
        content={},
        review_feedback={},
        tex_path="fake.tex",
        cover_letter_text=cover_letter_text,
        cover_letter_subject=cover_letter_subject,
        approved=approved,
    )
    db_session.add(draft)
    db_session.commit()
    db_session.refresh(draft)
    return draft


def _create_application(
    db_session,
    job_id,
    *,
    status: str = "applied",
    resume_track_id=None,
    resume_draft_id=None,
) -> Application:
    application = Application(
        id=uuid4(),
        job_post_id=job_id,
        resume_track_id=resume_track_id,
        resume_draft_id=resume_draft_id,
        status=status,
    )
    db_session.add(application)
    db_session.commit()
    db_session.refresh(application)
    return application


def _create_target(db_session, **overrides) -> ThesisTarget:
    payload = {
        "type": "professor",
        "name": "Prof. Ada Lovelace",
        "institution": "PoliTo",
        "country": "Italy",
        "research_area": "MLOps",
        "status": "identified",
        "priority": 3,
    }
    payload.update(overrides)
    target = ThesisTarget(**payload)
    db_session.add(target)
    db_session.commit()
    db_session.refresh(target)
    return target


def _create_outreach_draft(db_session, target_id: int, **overrides) -> OutreachDraft:
    payload = {
        "target_id": target_id,
        "subject": "Thesis inquiry",
        "body_text": "Hello from a test draft.",
        "provider": "test",
        "status": "draft",
        "approved": None,
    }
    payload.update(overrides)
    draft = OutreachDraft(**payload)
    db_session.add(draft)
    db_session.commit()
    db_session.refresh(draft)
    return draft


def _patch_uuid_session_get(monkeypatch, db_session) -> None:
    original_get = db_session.get

    def _patched_get(model, ident, *args, **kwargs):
        if isinstance(ident, str):
            try:
                ident = UUID(ident)
            except ValueError:
                pass
        return original_get(model, ident, *args, **kwargs)

    monkeypatch.setattr(db_session, "get", _patched_get)


def test_health_returns_ok(client, monkeypatch):
    monkeypatch.setattr(
        "job_agent.services.documents.check_pdflatex",
        lambda: (True, "/usr/bin/pdflatex"),
    )

    response = client.get("/health")

    assert response.status_code == 200, jresp(response)
    data = response.json()
    assert data["status"] == "ok"
    assert "pdflatex" in data


def test_providers_returns_dict(client, monkeypatch):
    monkeypatch.setattr(
        "job_agent.main.LLMRouter.provider_status",
        lambda self: {
            "lm_studio": {"reachable": False, "models": []},
            "anthropic": {"configured": False},
        },
    )

    response = client.get("/providers")

    assert response.status_code == 200, jresp(response)
    data = response.json()
    assert isinstance(data, dict)
    assert "lm_studio" in data


def test_tracks_returns_list(client, db_track):
    response = client.get("/tracks")

    assert response.status_code == 200, jresp(response)
    data = response.json()
    assert isinstance(data, list)
    assert data[0]["id"] == str(db_track.id)


def test_job_sources_returns_list(client):
    response = client.get("/job-sources")

    assert response.status_code == 200, jresp(response)
    assert isinstance(response.json(), list)


def test_profile_returns_404_when_empty(client):
    response = client.get("/profile")

    assert response.status_code == 404, jresp(response)
    assert "detail" in response.json()


def test_profile_returns_profile_when_exists(client, db_profile):
    response = client.get("/profile")

    assert response.status_code == 200, jresp(response)
    assert "full_name" in response.json()


def test_create_job_returns_200(client, db_track, monkeypatch):
    monkeypatch.setattr(
        "job_agent.main.score_tracks_for_job",
        lambda _job, _tracks: _track_score_payload(db_track),
    )

    response = client.post(
        "/jobs",
        json={
            "title": "Data Engineer",
            "company": "Acme",
            "location": "Milan, Italy",
            "source_name": "manual",
            "source_url": "https://example.com/jobs/1",
            "description": "Python, SQL, dbt required for analytics pipeline role",
        },
    )

    assert response.status_code == 200, jresp(response)
    data = response.json()
    assert {"id", "title", "company"} <= data.keys()


def test_create_job_auto_resolves_company_url_when_missing(client, db_track, monkeypatch):
    monkeypatch.setattr(
        "job_agent.main.score_tracks_for_job",
        lambda _job, _tracks: _track_score_payload(db_track),
    )
    monkeypatch.setattr(
        "job_agent.services.company_resolver.find_company_url",
        lambda **_kwargs: "https://acme.example",
    )

    response = client.post(
        "/jobs",
        json={
            "title": "Data Engineer",
            "company": "Acme",
            "location": "Milan, Italy",
            "source_name": "manual",
            "source_url": "https://example.com/jobs/2",
            "description": "Build data products and pipelines.",
        },
    )

    assert response.status_code == 200, jresp(response)
    assert response.json()["company_url"] == "https://acme.example"


def test_list_jobs_returns_empty_list(client):
    response = client.get("/jobs")

    assert response.status_code == 200, jresp(response)
    assert response.json() == []


def test_list_jobs_returns_seeded_job(client, db_job):
    response = client.get("/jobs", params={"show_all": "true"})

    assert response.status_code == 200, jresp(response)
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1


def test_list_jobs_filters_by_min_score(client, db_session, db_job, db_track):
    db_session.add(
        JobTrackScore(
            job_post_id=db_job.id,
            resume_track_id=db_track.id,
            score=50,
            matched_keywords=["python"],
        )
    )
    db_session.commit()

    response = client.get("/jobs", params={"min_score": 75, "show_all": "false"})

    assert response.status_code == 200, jresp(response)
    assert response.json() == []

    response = client.get("/jobs", params={"min_score": 40, "show_all": "false"})

    assert response.status_code == 200, jresp(response)
    assert len(response.json()) == 1


def test_resolve_company_url_endpoint_sets_company_url(client, db_session, db_job, monkeypatch):
    _patch_uuid_session_get(monkeypatch, db_session)
    db_job.company_url = None
    db_session.commit()

    monkeypatch.setattr(
        "job_agent.services.company_resolver.find_company_url",
        lambda **_kwargs: "https://testco.example",
    )

    response = client.post(f"/jobs/{db_job.id}/resolve-company-url")

    assert response.status_code == 200, jresp(response)
    data = response.json()
    assert data["resolved"] is True
    assert data["company_url"] == "https://testco.example"

    db_session.refresh(db_job)
    assert db_job.company_url == "https://testco.example"


def test_resolve_company_url_endpoint_skips_when_already_set(client, db_session, db_job, monkeypatch):
    _patch_uuid_session_get(monkeypatch, db_session)
    db_job.company_url = "https://already.example"
    db_session.commit()

    def _resolver_should_not_be_called(**_kwargs):
        raise AssertionError("resolver should not be called when company_url is already set")

    monkeypatch.setattr(
        "job_agent.services.company_resolver.find_company_url",
        _resolver_should_not_be_called,
    )

    response = client.post(f"/jobs/{db_job.id}/resolve-company-url")

    assert response.status_code == 200, jresp(response)
    data = response.json()
    assert data["resolved"] is False
    assert data["company_url"] == "https://already.example"


def test_get_job_track_fit(client, db_session, db_job, db_track, monkeypatch):
    _patch_uuid_session_get(monkeypatch, db_session)
    monkeypatch.setattr(
        "job_agent.main.score_tracks_for_job",
        lambda _job, _tracks: _track_score_payload(db_track, score=74),
    )

    response = client.get(f"/jobs/{db_job.id}/track-fit")

    assert response.status_code == 200, jresp(response)
    data = response.json()
    assert {"job_post_id", "recommended_tracks"} <= data.keys()
    assert isinstance(data["recommended_tracks"], list)


def test_enrich_job_triggers_enrichment(client, db_session, db_job, monkeypatch):
    _patch_uuid_session_get(monkeypatch, db_session)
    monkeypatch.setattr("job_agent.main.JobFetcher.enrich_job", lambda self, job, db: True)

    response = client.post(f"/jobs/{db_job.id}/enrich")

    assert response.status_code == 200, jresp(response)
    data = response.json()
    assert {"enriched", "description_length"} <= data.keys()


def test_enrich_pending_returns_count(client, monkeypatch):
    monkeypatch.setattr("job_agent.main.JobFetcher.enrich_pending", lambda self, db, limit=20: 3)

    response = client.post("/jobs/enrich-pending")

    assert response.status_code == 200, jresp(response)
    assert "enriched" in response.json()


def test_queue_cv_workflow_creates_task(client, db_job, db_track):
    response = client.post(
        "/tasks/cv-workflow",
        json={"job_post_id": str(db_job.id), "resume_track_slug": db_track.slug},
    )

    assert response.status_code == 200, jresp(response)
    data = response.json()
    assert "id" in data
    assert data["status"] == "pending"


def test_get_task_returns_task(client, db_session, sample_workflow_task, monkeypatch):
    _patch_uuid_session_get(monkeypatch, db_session)
    response = client.get(f"/tasks/{sample_workflow_task.id}")

    assert response.status_code == 200, jresp(response)
    assert "status" in response.json()


def test_list_tasks_returns_list(client):
    response = client.get("/tasks")

    assert response.status_code == 200, jresp(response)
    assert isinstance(response.json(), list)


def test_queue_workflow_missing_job_returns_404(client, db_track):
    response = client.post(
        "/tasks/cv-workflow",
        json={
            "job_post_id": "00000000-0000-0000-0000-000000000000",
            "resume_track_slug": db_track.slug,
        },
    )

    assert response.status_code == 404, jresp(response)
    assert "detail" in response.json()


def test_list_drafts_empty(client):
    response = client.get("/drafts")

    assert response.status_code == 200, jresp(response)
    assert response.json() == []


def test_approve_draft_sets_approved_true(client, db_session, db_job, db_profile, db_track, monkeypatch):
    del db_profile
    _patch_uuid_session_get(monkeypatch, db_session)
    draft = _create_draft(db_session, db_job.id, db_track.id)

    response = client.post(f"/drafts/{draft.id}/approve")

    assert response.status_code == 200, jresp(response)
    data = response.json()
    assert data["approved"] is True
    assert data["status"] == "approved"


def test_get_draft_returns_draft(client, db_session, db_job, db_profile, db_track, monkeypatch):
    del db_profile
    _patch_uuid_session_get(monkeypatch, db_session)
    draft = _create_draft(db_session, db_job.id, db_track.id)

    response = client.get(f"/drafts/{draft.id}")

    assert response.status_code == 200, jresp(response)
    assert response.json()["id"] == str(draft.id)


def test_post_cover_letter_returns_json(client, db_session, db_job, db_profile, db_track, monkeypatch):
    del db_profile
    draft = _create_draft(db_session, db_job.id, db_track.id)

    def _fake_generate(self, draft_id, company_url=None):
        del self, company_url
        stored = db_session.get(ResumeDraft, draft_id)
        stored.cover_letter_subject = "Application for Data Engineer"
        stored.cover_letter_text = "Dear Hiring Team,\n\nThis is a test cover letter."
        db_session.commit()
        db_session.refresh(stored)
        return stored

    monkeypatch.setattr(
        "job_agent.services.cover_letter.CoverLetterService.generate_cover_letter",
        _fake_generate,
    )

    response = client.post(f"/drafts/{draft.id}/cover-letter")

    assert response.status_code == 200, jresp(response)
    data = response.json()
    assert {"draft_id", "subject", "body"} <= data.keys()


def test_get_cover_letter_returns_json(client, db_session, db_job, db_profile, db_track):
    del db_profile
    draft = _create_draft(
        db_session,
        db_job.id,
        db_track.id,
        cover_letter_text="Stored cover letter body.",
        cover_letter_subject="Stored subject",
    )

    response = client.get(f"/drafts/{draft.id}/cover-letter")

    assert response.status_code == 200, jresp(response)
    data = response.json()
    assert {"draft_id", "subject", "body"} <= data.keys()


def test_generate_enhancement_proposals_returns_list(
    client,
    db_session,
    db_job,
    db_profile,
    db_track,
    monkeypatch,
):
    del db_profile
    draft = _create_draft(db_session, db_job.id, db_track.id)
    proposal = EnhancementProposal(
        id=uuid4(),
        draft_id=draft.id,
        section="summary",
        original_text="Old text",
        proposed_text="New text",
        rationale="Better aligned",
        question_for_user="Use this version?",
        approved=None,
    )
    monkeypatch.setattr(
        "job_agent.main.CVWorkflowService.generate_enhancement_proposals",
        lambda self, draft_id: [proposal],
    )

    response = client.post(f"/drafts/{draft.id}/propose-enhancements")

    assert response.status_code == 200, jresp(response)
    data = response.json()
    assert isinstance(data, list)
    assert {"id", "section", "proposed_text"} <= data[0].keys()


def test_get_pending_approvals_returns_list(client, db_session, db_job, db_profile, db_track):
    del db_profile
    draft = _create_draft(db_session, db_job.id, db_track.id)
    db_session.add(
        EnhancementProposal(
            id=uuid4(),
            draft_id=draft.id,
            section="summary",
            original_text="Old text",
            proposed_text="New text",
            rationale="Better aligned",
            question_for_user="Approve?",
            approved=None,
        )
    )
    db_session.commit()

    response = client.get(f"/drafts/{draft.id}/pending-approvals")

    assert response.status_code == 200, jresp(response)
    data = response.json()
    assert isinstance(data, list)
    assert data[0]["section"] == "summary"


def test_apply_enhancements_returns_status(client, db_session, db_job, db_profile, db_track, monkeypatch):
    del db_profile
    draft = _create_draft(db_session, db_job.id, db_track.id)
    approved_id = uuid4()
    monkeypatch.setattr(
        "job_agent.main.CVWorkflowService.apply_approved_enhancements",
        lambda self, draft_id, approved_ids: draft,
    )

    response = client.post(
        f"/drafts/{draft.id}/apply-enhancements",
        json={"approved_proposal_ids": [str(approved_id)]},
    )

    assert response.status_code == 200, jresp(response)
    data = response.json()
    assert data["status"] == "enhancements_applied"
    assert "draft_id" in data


def test_add_career_page_returns_201(client):
    response = client.post(
        "/career-pages",
        params={
            "company": "Bending Spoons",
            "career_url": "https://jobs.bendingspoons.com",
            "country": "Italy",
        },
    )

    assert response.status_code == 201, jresp(response)
    data = response.json()
    assert {"id", "company", "career_url"} <= data.keys()


def test_list_career_pages_returns_list(client):
    response = client.get("/career-pages")

    assert response.status_code == 200, jresp(response)
    assert isinstance(response.json(), list)


def test_delete_career_page_returns_204(client):
    created = client.post(
        "/career-pages",
        params={
            "company": "Delete Me",
            "career_url": "https://example.com/jobs",
            "country": "Italy",
        },
    )
    source_id = created.json()["id"]

    response = client.delete(f"/career-pages/{source_id}")

    assert response.status_code == 204, response.text


def test_scan_career_pages_returns_count(client, monkeypatch):
    monkeypatch.setattr("job_agent.main.CareerPageScanner.scan_all", lambda self, db: 5)

    response = client.post("/jobs/scan-career-pages")

    assert response.status_code == 200, jresp(response)
    assert response.json()["new_jobs"] == 5


def test_jobs_from_text_creates_job(client):
    response = client.post(
        "/jobs/from-text",
        json={
            "text": (
                "Data Engineer\n"
                "Acme Corp\n"
                "Location: Turin, Italy\n"
                "Build ETL pipelines with Python and SQL."
            )
        },
    )

    assert response.status_code == 200, jresp(response)
    data = response.json()
    assert data["title"] == "Data Engineer"
    assert data["company"] == "Acme Corp"


def test_drafts_generate_queues_task(client, db_job, db_track):
    response = client.post("/drafts/generate", json={"job_id": str(db_job.id)})

    assert response.status_code == 200, jresp(response)
    data = response.json()
    assert "task_id" in data
    assert data["resume_track_slug"] == db_track.slug


def test_create_application(client, db_job):
    response = client.post(
        "/applications",
        json={"job_post_id": str(db_job.id), "status": "applied"},
    )

    assert response.status_code == 200, jresp(response)
    data = response.json()
    assert "id" in data
    assert data["status"] == "applied"


def test_list_applications_returns_list(client):
    response = client.get("/applications")

    assert response.status_code == 200, jresp(response)
    assert isinstance(response.json(), list)


def test_update_application_changes_status(client, db_session, db_job, monkeypatch):
    _patch_uuid_session_get(monkeypatch, db_session)
    application = _create_application(db_session, db_job.id, status="applied")

    response = client.patch(f"/applications/{application.id}", json={"status": "interview"})

    assert response.status_code == 200, jresp(response)
    assert response.json()["status"] == "interview"


def test_add_and_list_application_communications(client, db_session, db_job, monkeypatch):
    _patch_uuid_session_get(monkeypatch, db_session)
    application = _create_application(db_session, db_job.id)

    response = client.post(
        f"/applications/{application.id}/communications",
        json={
            "channel": "email",
            "direction": "inbound",
            "event_type": "message",
            "subject": "Interview invitation",
            "snippet": "Can we schedule a call?",
        },
    )

    assert response.status_code == 200, jresp(response)
    event = response.json()
    assert {"id", "application_id", "subject"} <= event.keys()

    response = client.get(f"/applications/{application.id}/communications")

    assert response.status_code == 200, jresp(response)
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1


def test_export_jobs_csv_endpoint_returns_metadata(client, db_job, monkeypatch, tmp_path):
    del db_job
    monkeypatch.setattr("job_agent.services.exporters.settings.artifacts_dir", tmp_path)

    response = client.post("/exports/jobs-csv")

    assert response.status_code == 200, jresp(response)
    data = response.json()
    assert {"id", "file_path", "row_count"} <= data.keys()


def test_list_exports_returns_list(client, db_job, monkeypatch, tmp_path):
    del db_job
    monkeypatch.setattr("job_agent.services.exporters.settings.artifacts_dir", tmp_path)
    response = client.post("/exports/jobs-csv")

    assert response.status_code == 200, jresp(response)

    response = client.get("/exports")

    assert response.status_code == 200, jresp(response)
    assert isinstance(response.json(), list)


def test_sync_gmail_returns_count(client, monkeypatch):
    posts = [SimpleNamespace(id=uuid4()), SimpleNamespace(id=uuid4())]
    monkeypatch.setattr("job_agent.main.GmailService.sync_jobs", lambda self, db: posts)

    response = client.post("/jobs/sync-gmail")

    assert response.status_code == 200, jresp(response)
    data = response.json()
    assert data["created"] == 2
    assert len(data["job_ids"]) == 2


def test_discover_disabled_returns_message(client, monkeypatch):
    monkeypatch.setattr("job_agent.main.settings.use_jobspy", False, raising=False)

    response = client.post(
        "/jobs/discover",
        json={"query": "Data Engineer", "location": "Italy", "sources": ["linkedin"], "limit": 5},
    )

    assert response.status_code == 400, jresp(response)
    assert "disabled" in response.text.lower()


def test_create_thesis_target_returns_201(client):
    response = client.post(
        "/thesis-targets",
        json={
            "type": "professor",
            "name": "Prof. Ada Lovelace",
            "institution": "PoliTo",
            "country": "Italy",
            "research_area": "Federated Learning",
            "priority": 2,
        },
    )

    assert response.status_code == 201, jresp(response)
    data = response.json()
    assert {"id", "name", "status"} <= data.keys()


def test_list_thesis_targets_returns_list(client):
    response = client.get("/thesis-targets")

    assert response.status_code == 200, jresp(response)
    assert isinstance(response.json(), list)


def test_get_thesis_target_returns_target(client, db_session):
    target = _create_target(db_session)

    response = client.get(f"/thesis-targets/{target.id}")

    assert response.status_code == 200, jresp(response)
    assert response.json()["id"] == target.id


def test_update_thesis_target_returns_updated(client, db_session):
    target = _create_target(db_session)

    response = client.patch(
        f"/thesis-targets/{target.id}",
        json={"status": "email_drafted", "notes": "Strong fit"},
    )

    assert response.status_code == 200, jresp(response)
    data = response.json()
    assert data["status"] == "email_drafted"
    assert data["notes"] == "Strong fit"


def test_add_and_list_target_communications(client, db_session):
    target = _create_target(db_session)

    response = client.post(
        f"/thesis-targets/{target.id}/communications",
        json={
            "direction": "outbound",
            "channel": "email",
            "event_type": "sent",
            "subject": "Thesis inquiry",
            "snippet": "Initial outreach",
            "notes": "Sent first contact",
        },
    )

    assert response.status_code == 201, jresp(response)
    data = response.json()
    assert {"id", "target_id", "subject"} <= data.keys()

    response = client.get(f"/thesis-targets/{target.id}/communications")

    assert response.status_code == 200, jresp(response)
    events = response.json()
    assert isinstance(events, list)
    assert len(events) == 1


def test_list_outreach_drafts_returns_list(client, db_session):
    target = _create_target(db_session)
    _create_outreach_draft(db_session, target.id)

    response = client.get(f"/thesis-targets/{target.id}/outreach-drafts")

    assert response.status_code == 200, jresp(response)
    assert isinstance(response.json(), list)


def test_approve_outreach_draft_returns_approved(client, db_session):
    target = _create_target(db_session, status="email_drafted")
    draft = _create_outreach_draft(db_session, target.id)
    sibling = _create_outreach_draft(
        db_session,
        target.id,
        subject="Older draft",
        status="approved",
        approved=True,
    )

    response = client.post(f"/outreach-drafts/{draft.id}/approve")

    assert response.status_code == 200, jresp(response)
    data = response.json()
    assert data["approved"] is True
    db_session.refresh(target)
    db_session.refresh(sibling)
    assert target.status == "email_approved"
    assert sibling.approved is False


def test_generate_outreach_email_returns_draft(client, db_session, monkeypatch):
    target = _create_target(db_session)

    def _fake_generate(self, target_id, session):
        del self
        draft = OutreachDraft(
            target_id=target_id,
            subject="Generated subject",
            body_text="Generated email body.",
            provider="test",
            status="draft",
            approved=None,
        )
        session.add(draft)
        session.commit()
        session.refresh(draft)
        return draft

    monkeypatch.setattr("job_agent.main.ThesisOutreachService.generate_email", _fake_generate)

    response = client.post(f"/thesis-targets/{target.id}/generate-email")

    assert response.status_code == 201, jresp(response)
    data = response.json()
    assert {"id", "target_id", "subject", "body_text"} <= data.keys()


def test_revise_outreach_draft_returns_new_draft(client, db_session, monkeypatch):
    target = _create_target(db_session)
    draft = _create_outreach_draft(db_session, target.id)

    def _fake_revise(self, draft_id, feedback, session):
        del self, feedback
        revised = OutreachDraft(
            target_id=target.id,
            subject="Revised subject",
            body_text="Revised email body.",
            provider="test",
            status="draft",
            approved=None,
        )
        session.add(revised)
        session.commit()
        session.refresh(revised)
        return revised

    monkeypatch.setattr("job_agent.main.ThesisOutreachService.revise_email", _fake_revise)

    response = client.post(f"/outreach-drafts/{draft.id}/revise", json={"feedback": "Shorten it"})

    assert response.status_code == 200, jresp(response)
    data = response.json()
    assert {"id", "subject", "body_text"} <= data.keys()


def test_mark_outreach_draft_sent_returns_sent_draft(client, db_session, monkeypatch):
    target = _create_target(db_session)
    draft = _create_outreach_draft(db_session, target.id)

    def _fake_mark_sent(self, draft_id, session):
        del self, draft_id
        stored = session.get(OutreachDraft, draft.id)
        stored.status = "sent"
        stored.sent_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(stored)
        return stored

    monkeypatch.setattr("job_agent.main.ThesisOutreachService.mark_sent", _fake_mark_sent)

    response = client.post(f"/outreach-drafts/{draft.id}/mark-sent")

    assert response.status_code == 200, jresp(response)
    assert response.json()["status"] == "sent"
