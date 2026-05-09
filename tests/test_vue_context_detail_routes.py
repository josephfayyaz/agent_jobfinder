from __future__ import annotations

from pathlib import Path

from job_agent.models import Application, CareerPageSource, JobPost, ResumeDraft, ResumeTrack


def _make_job(db_session) -> JobPost:
    job = JobPost(
        company="ContextCo",
        title="Platform Engineer",
        description="Context detail route test job.",
        source_name="manual",
        status="queued",
        location="Rome, Italy",
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


def _make_track(db_session) -> ResumeTrack:
    track = ResumeTrack(
        slug="context-platform",
        title="Platform Engineering",
        role_family="platform",
        baseline_summary="Context route track.",
        target_keywords=["python", "platform"],
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
        score=88.0,
        content={"summary": "Context route draft"},
        review_feedback={},
        approved=False,
    )
    db_session.add(draft)
    db_session.commit()
    db_session.refresh(draft)
    return draft


def test_router_contains_context_detail_routes():
    source = Path("frontend/vue/src/router/index.js").read_text()

    assert 'path: "/jobs/:id"' in source
    assert 'path: "/applications/:id"' in source
    assert 'path: "/companies/:id"' in source


def test_context_detail_pages_exist_and_use_vue_api_fetch():
    job_source = Path("frontend/vue/src/pages/JobDetailPage.vue").read_text()
    application_source = Path("frontend/vue/src/pages/ApplicationDetailPage.vue").read_text()
    company_source = Path("frontend/vue/src/pages/CompanyDetailPage.vue").read_text()

    assert 'vueApiFetch(`/jobs/${jobId.value}`)' in job_source
    assert 'vueApiFetch(`/applications/${applicationId.value}`)' in application_source
    assert 'vueApiFetch(`/companies/${companyId.value}`)' in company_source
    assert "window.location.href" not in job_source
    assert "window.location.href" not in application_source
    assert "window.location.href" not in company_source
    assert '"/app/' not in job_source
    assert '"/app/' not in application_source
    assert '"/app/' not in company_source


def test_list_pages_link_to_new_detail_routes():
    jobs_source = Path("frontend/vue/src/pages/JobsPage.vue").read_text()
    applications_source = Path("frontend/vue/src/pages/ApplicationsPage.vue").read_text()
    companies_source = Path("frontend/vue/src/pages/CompaniesPage.vue").read_text()
    draft_detail_source = Path("frontend/vue/src/pages/DraftDetailPage.vue").read_text()

    assert ':to="`/jobs/${jobId(item)}`"' in jobs_source
    assert ':to="`/applications/${appId(item)}`"' in applications_source
    assert ':to="`/companies/${companyId(item)}`"' in companies_source
    assert "linkedJobTarget" in draft_detail_source
    assert "linkedApplicationTarget" in draft_detail_source
    assert '"/app/jobs"' not in draft_detail_source
    assert '"/app/applications"' not in draft_detail_source


def test_vue_context_detail_endpoints_return_safe_contract_errors(client):
    for path in (
        "/api/vue/jobs/not-a-real-id",
        "/api/vue/applications/not-a-real-id",
        "/api/vue/companies/not-a-real-id",
    ):
        response = client.get(path)
        assert response.status_code == 404
        payload = response.json()
        assert payload["ok"] is False
        assert payload["error"]["code"] == "not_found"


def test_vue_application_detail_contract_includes_safe_linked_context(client, db_session):
    job = _make_job(db_session)
    track = _make_track(db_session)
    draft = _make_draft(db_session, job, track)
    application = Application(
        job_post_id=job.id,
        resume_track_id=track.id,
        resume_draft_id=draft.id,
        status="interview",
    )
    db_session.add(application)
    db_session.commit()
    db_session.refresh(application)

    response = client.get(f"/api/vue/applications/{application.id}")

    assert response.status_code == 200
    item = response.json()["data"]["item"]
    assert item["id"] == str(application.id)
    assert item["job_id"] == str(job.id)
    assert item["draft_id"] == str(draft.id)
    assert item["title"] == "Platform Engineer"
    assert item["company"] == "ContextCo"
    assert item["location"] == "Rome, Italy"
    assert item["job"]["id"] == str(job.id)
    assert item["draft"]["id"] == str(draft.id)

    serialized = str(item).lower()
    assert "api_key" not in serialized
    assert "token" not in serialized
    assert "secret" not in serialized
    assert "password" not in serialized
    assert "tex_path" not in serialized
    assert "/users/" not in serialized


def test_vue_job_detail_contract_includes_safe_company_id_when_available(client, db_session):
    source = CareerPageSource(company="ContextCo", career_url="https://context.example/jobs", country="Italy")
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)

    job = _make_job(db_session)

    response = client.get(f"/api/vue/jobs/{job.id}")

    assert response.status_code == 200
    item = response.json()["data"]["item"]
    assert item["id"] == str(job.id)
    assert item["company_id"] == str(source.id)
    assert item["company_record"]["id"] == str(source.id)
    assert item["company_record"]["career_page_url_available"] is True


def test_vue_company_detail_contract_remains_safe(client, db_session):
    source = CareerPageSource(company="ContextCo", career_url="https://context.example/jobs", country="Italy")
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)

    response = client.get(f"/api/vue/companies/{source.id}")

    assert response.status_code == 200
    item = response.json()["data"]["item"]
    assert item["id"] == str(source.id)
    assert item["career_page_url_available"] is True
    serialized = str(item).lower()
    assert "api_key" not in serialized
    assert "token" not in serialized
    assert "secret" not in serialized
    assert "password" not in serialized
