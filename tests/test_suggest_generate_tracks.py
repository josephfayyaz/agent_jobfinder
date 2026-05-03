"""Tests for suggest-tracks, generate-tracks, and GET tracks endpoints."""
from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from job_agent.main import app
from job_agent.db import SessionLocal, prepare_database
from job_agent.models import Candidate, CandidateSourceFile


@pytest.fixture(autouse=True)
def setup_db():
    prepare_database()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def candidate():
    db = SessionLocal()
    try:
        cand = Candidate(
            id=str(uuid4()),
            full_name="Test User",
            email=f"test-{uuid4()}@example.com",
        )
        db.add(cand)
        db.commit()
        db.refresh(cand)
        cand_id = cand.id
    finally:
        db.close()
    db2 = SessionLocal()
    try:
        return db2.get(Candidate, cand_id)
    finally:
        db2.close()


def test_suggest_tracks_returns_empty_on_no_source_files(client, candidate):
    resp = client.post(f"/candidates/{candidate.id}/suggest-tracks")
    assert resp.status_code == 200
    data = resp.json()
    assert "suggested_roles" in data
    assert isinstance(data["suggested_roles"], list)


def test_suggest_tracks_returns_roles_when_llm_succeeds(client, candidate):
    db = SessionLocal()
    try:
        src = CandidateSourceFile(
            id=str(uuid4()),
            candidate_id=candidate.id,
            original_name="cv.txt",
            extracted_text="Data Engineer with Python and SQL experience.",
            mime_type="text/plain",
        )
        db.add(src)
        db.commit()
    finally:
        db.close()

    mock_router = MagicMock()
    mock_router.generate.return_value = {"content": '["Data Engineer", "Analytics Engineer", "ML Engineer", "Data Analyst"]'}
    with patch("job_agent.routers.candidates.LLMRouter", return_value=mock_router):
        resp = client.post(f"/candidates/{candidate.id}/suggest-tracks")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["suggested_roles"]) == 4


def test_suggest_tracks_returns_empty_on_provider_unavailable(client, candidate):
    from job_agent.llm import ProviderUnavailableError
    db = SessionLocal()
    try:
        src = CandidateSourceFile(
            id=str(uuid4()),
            candidate_id=candidate.id,
            original_name="cv2.txt",
            extracted_text="Some CV text.",
            mime_type="text/plain",
        )
        db.add(src)
        db.commit()
    finally:
        db.close()
    mock_router = MagicMock()
    mock_router.generate.side_effect = ProviderUnavailableError("down")
    with patch("job_agent.routers.candidates.LLMRouter", return_value=mock_router):
        resp = client.post(f"/candidates/{candidate.id}/suggest-tracks")
    assert resp.status_code == 200
    assert resp.json()["suggested_roles"] == []


def test_suggest_tracks_returns_empty_on_value_error(client, candidate):
    db = SessionLocal()
    try:
        src = CandidateSourceFile(
            id=str(uuid4()),
            candidate_id=candidate.id,
            original_name="cv3.txt",
            extracted_text="Some CV text.",
            mime_type="text/plain",
        )
        db.add(src)
        db.commit()
    finally:
        db.close()
    mock_router = MagicMock()
    mock_router.generate.side_effect = ValueError("bad json")
    with patch("job_agent.routers.candidates.LLMRouter", return_value=mock_router):
        resp = client.post(f"/candidates/{candidate.id}/suggest-tracks")
    assert resp.status_code == 200
    assert resp.json()["suggested_roles"] == []


def test_generate_tracks_creates_custom_track(client, candidate):
    mock_router = MagicMock()
    mock_router.generate.return_value = {
        "content": '{"baseline_summary": "ML engineer focused on model deployment.", "target_keywords": ["python", "mlflow", "kubernetes"], "emphasis": {"experiences": ["deployment"], "projects": ["pipelines"], "skills": ["python"]}}'
    }
    with patch("job_agent.routers.candidates.LLMRouter", return_value=mock_router):
        resp = client.post(
            f"/candidates/{candidate.id}/generate-tracks",
            json={"roles": ["Machine Learning Engineer"]},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["generated"] + data["reused_seeds"] >= 1


def test_generate_tracks_reuses_seed_for_matching_role(client, candidate):
    resp = client.post(
        f"/candidates/{candidate.id}/generate-tracks",
        json={"roles": ["data engineer"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["reused_seeds"] >= 1
    assert data["generated"] == 0


def test_get_tracks_returns_list(client, candidate):
    resp = client.get(f"/candidates/{candidate.id}/tracks")
    assert resp.status_code == 200
    data = resp.json()
    assert "tracks" in data
    assert "total" in data
    assert isinstance(data["tracks"], list)
