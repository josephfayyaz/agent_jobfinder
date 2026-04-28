from __future__ import annotations

from pathlib import Path

from job_agent.models import FactSource
from tests.test_fact_ingestion import SAMPLE_FACT_SHEET


def jresp(r):
    """Pretty-print response JSON on assertion failure."""
    try:
        return r.json()
    except Exception:
        return r.text


def _profile_payload(sample_profile: dict) -> dict:
    payload = dict(sample_profile)
    payload["additional_notes"] = {}
    return payload


def _write_sample_fact_sheet(tmp_path: Path) -> tuple[str, str]:
    path = tmp_path / "fact_sheet.txt"
    path.write_text(SAMPLE_FACT_SHEET, encoding="utf-8")
    return str(path), SAMPLE_FACT_SHEET


def test_put_profile_creates_profile(client, sample_profile):
    response = client.put("/profile", json=_profile_payload(sample_profile))

    assert response.status_code == 200, jresp(response)
    assert response.json()["full_name"] == "Test User"


def test_put_profile_updates_existing(client, sample_profile):
    payload = _profile_payload(sample_profile)
    response = client.put("/profile", json=payload)

    assert response.status_code == 200, jresp(response)

    payload["full_name"] = "Updated User"
    response = client.put("/profile", json=payload)

    assert response.status_code == 200, jresp(response)
    assert response.json()["full_name"] == "Updated User"


def test_fact_sources_latest_returns_404_initially(client):
    response = client.get("/fact-sources/latest")

    assert response.status_code == 404, jresp(response)
    assert "detail" in response.json()


def test_ingest_fact_source_creates_profile(client, tmp_path):
    source_path, content = _write_sample_fact_sheet(tmp_path)

    response = client.post(
        "/fact-sources/ingest",
        json={"source_path": source_path, "content": content},
    )

    assert response.status_code == 200, jresp(response)
    data = response.json()
    assert {"source_path", "source_hash", "reused_existing_source", "counts"} <= data.keys()
    assert any(count > 0 for count in data["counts"].values())

    response = client.get("/profile")

    assert response.status_code == 200, jresp(response)
    assert "full_name" in response.json()


def test_ingest_fact_source_idempotent(client, db_session, tmp_path):
    source_path, content = _write_sample_fact_sheet(tmp_path)

    response = client.post(
        "/fact-sources/ingest",
        json={"source_path": source_path, "content": content},
    )

    assert response.status_code == 200, jresp(response)
    first = response.json()

    response = client.post(
        "/fact-sources/ingest",
        json={"source_path": source_path, "content": content},
    )

    assert response.status_code == 200, jresp(response)
    second = response.json()
    assert second["reused_existing_source"] is True
    assert second["source_hash"] == first["source_hash"]
    assert db_session.query(FactSource).count() == 1


def test_ingest_default_fact_sheet_uses_configured_path(client, tmp_path):
    from job_agent.config import settings as runtime_settings

    source_path, _content = _write_sample_fact_sheet(tmp_path)
    original = runtime_settings.fact_sheet_path
    object.__setattr__(runtime_settings, "fact_sheet_path", source_path)
    try:
        response = client.post("/fact-sources/ingest-default")
    finally:
        object.__setattr__(runtime_settings, "fact_sheet_path", original)

    assert response.status_code == 200, jresp(response)
    assert response.json()["status"] == "ok"


def test_ingest_default_fact_sheet_rebuilds_from_latest_intake_draft(client, db_session):
    from job_agent.config import settings as runtime_settings
    from job_agent.models import Candidate, CandidateIntakeDraft

    candidate = Candidate(id="cand-rebuild", full_name="Rebuild Test", email="rebuild@example.com")
    db_session.add(candidate)
    db_session.add(
        CandidateIntakeDraft(
            id="draft-rebuild",
            candidate_id=candidate.id,
            partial_fact_sheet={
                "person": {"full_name": "Rebuild Test", "contact": {"email": "rebuild@example.com"}},
                "match_profile": {},
                "education": [{"degree": "BSc Physics", "institution": "Uni Test", "status": "Completed"}],
                "experience": [],
                "projects": [],
                "skills": {"programming_languages": ["Python"]},
                "languages": [],
                "completion_status": "usable_with_gaps",
                "confidence_summary": {},
                "missing_information": [],
                "conflicts": [],
                "evidence_index": [],
            },
            iteration=2,
        )
    )
    db_session.commit()
    object.__setattr__(runtime_settings, "default_candidate_id", candidate.id)

    response = client.post("/fact-sources/ingest-default")

    assert response.status_code == 200, jresp(response)
    assert response.json()["status"] == "ok"
    exported = client.get(f"/candidates/{candidate.id}/fact-sheet-json").json()
    assert exported["education"][0]["degree"] == "BSc Physics"
