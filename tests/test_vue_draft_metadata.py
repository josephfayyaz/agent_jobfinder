from __future__ import annotations

from pathlib import Path

from job_agent.models import CareerPageSource, JobPost, ResumeDraft, ResumeTrack


def _make_job(db_session, *, company: str, title: str, location: str, status: str = "new", source_name: str = "manual") -> JobPost:
    job = JobPost(
        company=company,
        title=title,
        description="Draft metadata test job.",
        location=location,
        source_name=source_name,
        status=status,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


def _make_track(db_session, *, slug: str = "metadata-track", title: str = "Metadata Track") -> ResumeTrack:
    track = ResumeTrack(
        slug=slug,
        title=title,
        role_family="data",
        baseline_summary="Metadata track baseline.",
        target_keywords=["python"],
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
        score=82.0,
        content={"summary": "Metadata draft"},
        review_feedback={},
        approved=False,
    )
    db_session.add(draft)
    db_session.commit()
    db_session.refresh(draft)
    return draft


def test_vue_draft_detail_includes_safe_linked_job_metadata(client, db_session):
    source = CareerPageSource(company="Acme", career_url="https://acme.example/jobs", country="Italy")
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)

    job = _make_job(
        db_session,
        company="Acme",
        title="Senior Data Engineer",
        location="Turin, Italy",
        status="queued",
        source_name="manual-import",
    )
    track = _make_track(db_session, slug="data-engineering", title="Data Engineering")
    draft = _make_draft(db_session, job, track)

    response = client.get(f"/api/vue/drafts/{draft.id}")

    assert response.status_code == 200
    payload = response.json()
    item = payload["data"]["item"]
    assert item["id"] == str(draft.id)
    assert item["title"] == "Senior Data Engineer"
    assert item["role"] == "Data Engineering"
    assert item["company"] == "Acme"
    assert item["location"] == "Turin, Italy"
    assert item["status"] == "drafted"
    assert item["approved"] is False
    assert item["job"] == {
        "id": str(job.id),
        "title": "Senior Data Engineer",
        "company": "Acme",
        "location": "Turin, Italy",
        "source": "manual-import",
        "status": "queued",
    }
    assert item["company_record"] == {
        "id": str(source.id),
        "name": "Acme",
        "career_page_url_available": True,
    }

    serialized = str(item).lower()
    assert "source_url" not in serialized
    assert "canonical_apply_url" not in serialized
    assert "company_url" not in serialized
    assert "career_url" not in serialized
    assert "api_key" not in serialized
    assert "token" not in serialized
    assert "secret" not in serialized
    assert "password" not in serialized
    assert "tex_path" not in serialized
    assert "/users/" not in serialized


def test_vue_draft_detail_handles_missing_linked_metadata_safely(client, db_session):
    job = _make_job(db_session, company="", title="", location="", source_name="", status="")
    track = _make_track(db_session, slug="fallback-track", title="Fallback Track")
    draft = _make_draft(db_session, job, track)

    response = client.get(f"/api/vue/drafts/{draft.id}")

    assert response.status_code == 200
    item = response.json()["data"]["item"]
    assert item["title"] is None
    assert item["role"] == "Fallback Track"
    assert item["company"] is None
    assert item["location"] is None
    assert item["job"] == {
        "id": str(job.id),
        "title": None,
        "company": None,
        "location": None,
        "source": None,
        "status": None,
    }
    assert item["company_record"] is None


def test_vue_drafts_list_includes_safe_metadata(client, db_session):
    job = _make_job(db_session, company="ListCo", title="Analytics Engineer", location="Milan, Italy")
    track = _make_track(db_session, slug="analytics-track", title="Analytics")
    draft = _make_draft(db_session, job, track)

    response = client.get("/api/vue/drafts")

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    item = next(entry for entry in items if entry["id"] == str(draft.id))
    assert item["title"] == "Analytics Engineer"
    assert item["role"] == "Analytics"
    assert item["company"] == "ListCo"
    assert item["location"] == "Milan, Italy"
    assert "source_url" not in str(item).lower()
    assert "company_url" not in str(item).lower()


def test_draft_detail_source_prefers_enriched_metadata_over_unknown_company_fallback():
    source = Path("frontend/vue/src/pages/DraftDetailPage.vue").read_text()

    assert 'detail.value?.company || linkedJob.value?.company || "Unknown company"' in source
    assert 'detail.value?.title' in source
    assert 'linkedJob.value?.title' in source
    assert "Linked job metadata" in source
    assert "Career page stored" in source
    assert 'to="/drafts"' in source
    assert "linkedJobTarget" in source
    assert "linkedApplicationTarget" in source
    assert 'to="/app/jobs"' not in source
    assert 'to="/app/applications"' not in source
    assert "window.location.href" not in source
    assert "Related workflow" in source
    assert "linkedJobLinkLabel" in source
    assert "linkedApplicationLinkLabel" in source
