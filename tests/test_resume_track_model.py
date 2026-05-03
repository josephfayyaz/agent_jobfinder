"""Verify ResumeTrack has the new is_custom and candidate_id fields."""
from job_agent.models import ResumeTrack


def test_resume_track_has_is_custom():
    cols = {col.key for col in ResumeTrack.__table__.columns}
    assert "is_custom" in cols


def test_resume_track_has_candidate_id():
    cols = {col.key for col in ResumeTrack.__table__.columns}
    assert "candidate_id" in cols


def test_is_custom_default_false():
    track = ResumeTrack(
        slug="test-slug",
        title="Test",
        role_family="data",
        baseline_summary="summary",
    )
    assert track.is_custom is False


def test_candidate_id_nullable():
    track = ResumeTrack(
        slug="test-slug2",
        title="Test2",
        role_family="data",
        baseline_summary="summary",
    )
    assert track.candidate_id is None
