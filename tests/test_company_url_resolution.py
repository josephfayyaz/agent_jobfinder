from __future__ import annotations

from uuid import UUID


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

    assert response.status_code == 200
    assert response.json()["company_url"] == "https://acme.example"


def test_resolve_company_url_endpoint_sets_company_url(client, db_session, db_job, monkeypatch):
    _patch_uuid_session_get(monkeypatch, db_session)
    db_job.company_url = None
    db_session.commit()

    monkeypatch.setattr(
        "job_agent.services.company_resolver.find_company_url",
        lambda **_kwargs: "https://testco.example",
    )

    response = client.post(f"/jobs/{db_job.id}/resolve-company-url")

    assert response.status_code == 200
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

    assert response.status_code == 200
    data = response.json()
    assert data["resolved"] is False
    assert data["company_url"] == "https://already.example"
