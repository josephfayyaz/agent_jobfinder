"""Tests for job-to-track matching algorithm."""
from __future__ import annotations

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
