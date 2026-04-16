from __future__ import annotations

from pathlib import Path

import pytest

from job_agent.models import FactSource

FACT_SHEET_PATH = Path("/Users/youseffayyaz/Polito/Resume-CV/fact_sheet/master_fact_sheet.txt")


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


def _load_real_fact_sheet_or_skip() -> tuple[str, str]:
    if not FACT_SHEET_PATH.exists():
        pytest.skip(f"Fact sheet not found: {FACT_SHEET_PATH}")
    return str(FACT_SHEET_PATH), FACT_SHEET_PATH.read_text(encoding="utf-8")


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


def test_ingest_fact_source_creates_profile(client):
    source_path, content = _load_real_fact_sheet_or_skip()

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


def test_ingest_fact_source_idempotent(client, db_session):
    source_path, content = _load_real_fact_sheet_or_skip()

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
