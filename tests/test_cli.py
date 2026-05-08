from __future__ import annotations

import httpx
from click.testing import CliRunner

from job_agent.cli import cli


class _FakeResponse:
    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", "http://localhost:8000/test")
            response = httpx.Response(self.status_code, request=request, text=self.text)
            raise httpx.HTTPStatusError("error", request=request, response=response)


def test_health_command_runs(monkeypatch):
    def _request(method, url, timeout=30, **kwargs):
        del method, timeout, kwargs
        path = url.replace("http://localhost:8000", "")
        payloads = {
            "/health": {"status": "ok"},
            "/onboarding/status": {"configured": True, "candidate_id_set": True},
            "/providers": {
                "lm_studio": {"reachable": True},
                "openai": {"enabled": False},
                "anthropic": {"enabled": False},
            },
            "/settings/current": {"default_candidate_id": "abc-123", "settings_file_available": True},
            "/lm-studio/models": {"online": True, "models": ["a", "b", "c"]},
            "/jobs": [{"id": "1", "title": "Data Engineer", "company": "Acme", "status": "new"}],
            "/drafts": [],
            "/applications": [],
        }
        return _FakeResponse(payloads[path])

    monkeypatch.setattr(httpx, "request", _request)
    runner = CliRunner()
    result = runner.invoke(cli, ["health"])
    assert result.exit_code == 0
    assert "Job Agent Status" in result.output


def test_config_shows_seniority(monkeypatch):
    monkeypatch.setattr(
        httpx,
        "request",
        lambda method, url, timeout=30, **kwargs: _FakeResponse(
            {
                "provider_status": {"label": "LM Studio", "available": True},
                "openai_configured": False,
                "anthropic_configured": False,
                "gemini_configured": False,
                "target_job_seniority": "junior",
                "match_min_score": 75,
                "use_jobspy": False,
                "default_candidate_id": "abc-123",
                "cv_pass_score": 85,
                "cv_revise_score": 60,
                "bullet_clarify_word_limit": 22,
                "settings_file_available": True,
            }
        ),
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["config"])
    assert "target_job_seniority" in result.output


def test_jobs_list_runs(monkeypatch):
    monkeypatch.setattr(
        httpx,
        "request",
        lambda method, url, timeout=30, **kwargs: _FakeResponse(
            [
                {
                    "id": "job-1",
                    "title": "Data Engineer",
                    "company": "TestCo",
                    "location": "Turin, Italy",
                    "status": "new",
                }
            ]
        ),
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["jobs", "list"])
    assert result.exit_code == 0
    assert "Data Engineer" in result.output
