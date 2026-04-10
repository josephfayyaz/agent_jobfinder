from __future__ import annotations

from click.testing import CliRunner

from job_agent.cli import cli


class _SessionContext:
    def __init__(self, session):
        self.session = session

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc, tb):
        return False


def test_health_command_runs():
    runner = CliRunner()
    result = runner.invoke(cli, ["health"])
    assert result.exit_code == 0


def test_config_shows_seniority():
    runner = CliRunner()
    result = runner.invoke(cli, ["config"])
    assert "seniority" in result.output.lower()


def test_jobs_list_runs(monkeypatch, db_session, db_job, db_track):
    from job_agent.models import JobTrackScore

    db_session.add(
        JobTrackScore(
            job_post_id=db_job.id,
            resume_track_id=db_track.id,
            score=88.0,
            matched_keywords=["python", "sql"],
        )
    )
    db_session.commit()

    monkeypatch.setattr("job_agent.cli.SessionLocal", lambda: _SessionContext(db_session))
    runner = CliRunner()
    result = runner.invoke(cli, ["jobs", "list"])
    assert result.exit_code == 0
