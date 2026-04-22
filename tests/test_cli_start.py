from __future__ import annotations

from click.testing import CliRunner
from unittest.mock import MagicMock

from job_agent.cli import cli


def test_wait_for_api_success(monkeypatch):
    """_wait_for_api succeeds when /health returns 200."""
    import httpx

    mock_response = MagicMock()
    mock_response.status_code = 200
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: mock_response)

    from job_agent.cli_start import _wait_for_api

    _wait_for_api()


def test_preflight_missing_config(tmp_path, monkeypatch):
    """start() exits with a clear message if user_settings.yml is missing."""
    import job_agent.cli_start as cli_start

    monkeypatch.setattr(cli_start, "_user_settings_file", lambda: tmp_path / "user_settings.yml")

    runner = CliRunner()
    result = runner.invoke(cli, ["start"])

    assert result.exit_code != 0
    assert "Not configured" in result.output
