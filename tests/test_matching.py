"""Tests for job-to-track matching algorithm."""
from __future__ import annotations

import pytest

from job_agent.config import get_settings
from job_agent.services.matching import score_tracks_for_job


def test_score_zero_match_is_low(sample_track):
    """A job with zero keyword matches should score below 30."""
    job = {"title": "Marketing Manager", "description": "Manage campaigns and social media."}
    results = score_tracks_for_job(job, [sample_track])
    assert results[0]["score"] < 30, "Zero-match job should score < 30 with new formula"


def test_score_strong_match_above_threshold(sample_track):
    """A clearly relevant job should score above the 60 revise threshold."""
    job = {
        "title": "Data Engineer",
        "description": "Strong Python, SQL, dbt, Airflow, PostgreSQL, ETL experience required.",
    }
    results = score_tracks_for_job(job, [sample_track])
    assert results[0]["score"] >= 60, "Strong match job should score >= 60"


def test_matched_keywords_returned(sample_track):
    """matched_keywords should list which track keywords appeared in the job."""
    job = {"title": "Data Engineer", "description": "python and sql experience required"}
    results = score_tracks_for_job(job, [sample_track])
    assert "python" in results[0]["matched_keywords"]
    assert "sql" in results[0]["matched_keywords"]


def test_score_capped_at_100(sample_track):
    """Score should never exceed 100."""
    job = {
        "title": "python sql dbt airflow etl warehouse postgresql data engineer",
        "description": " ".join(["python sql dbt airflow postgresql etl warehouse"] * 10),
    }
    results = score_tracks_for_job(job, [sample_track])
    assert results[0]["score"] <= 100


def test_multiple_tracks_sorted(sample_track):
    """Results should be sorted descending by score."""

    class WeakTrack:
        slug = "cloud-mlops"
        title = "Cloud MLOps"
        role_family = "cloud"
        target_keywords = ["kubernetes", "docker", "mlops"]
        baseline_summary = ""
        emphasis = {}

    job = {"title": "Data Engineer", "description": "python sql dbt airflow etl"}
    results = score_tracks_for_job(job, [sample_track, WeakTrack()])
    assert results[0]["score"] >= results[1]["score"], "Results should be sorted descending"


def test_cosine_similarity_identical_vectors():
    from job_agent.services.matching import _cosine_similarity

    vector = [1.0, 0.0, 0.0]
    assert _cosine_similarity(vector, vector) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal_vectors():
    from job_agent.services.matching import _cosine_similarity

    assert _cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_semantic_score_returns_zero_on_embedding_failure(monkeypatch):
    from job_agent.services import matching

    monkeypatch.setattr(matching, "_get_embedding", lambda text: None)
    result = matching.score_semantic("data engineer job", "python sql dbt")
    assert result == 0.0


def test_blend_uses_weight_config(monkeypatch, sample_job, sample_track):
    from job_agent.services import matching

    settings = get_settings()
    monkeypatch.setattr(matching, "_get_embedding", lambda text: [1.0, 0.0])
    monkeypatch.setattr(settings, "semantic_matching_weight", 0.5)

    results = matching.score_tracks_for_job(sample_job, [sample_track])
    assert len(results) == 1
    assert 0 <= results[0]["score"] <= 100


def test_fallback_to_keyword_when_weight_zero(monkeypatch, sample_job, sample_track):
    from job_agent.services import matching

    called: list[str] = []
    monkeypatch.setattr(matching, "_get_embedding", lambda text: called.append(text) or [1.0])
    monkeypatch.setattr(get_settings(), "semantic_matching_weight", 0.0)

    matching.score_tracks_for_job(sample_job, [sample_track])
    assert called == []
