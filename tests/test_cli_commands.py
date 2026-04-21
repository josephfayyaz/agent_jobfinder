from __future__ import annotations

import httpx
from click.testing import CliRunner

from job_agent.cli import cli


class _FakeResponse:
    def __init__(self, payload=None, status_code: int = 200):
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


def test_status_offline(monkeypatch):
    """status command handles server offline gracefully."""

    def _raise(*args, **kwargs):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(httpx, "request", _raise)
    runner = CliRunner()
    result = runner.invoke(cli, ["status"])
    assert "localhost:8000" in result.output


def test_companies_list_renders_table(monkeypatch):
    monkeypatch.setattr(
        httpx,
        "request",
        lambda method, url, timeout=30, **kwargs: _FakeResponse(
            [
                {
                    "id": 1,
                    "company": "Acme Corp",
                    "ats_type": "greenhouse",
                    "last_checked_at": "2026-04-19T14:00:00+02:00",
                    "last_new_jobs": 3,
                    "active": True,
                },
                {
                    "id": 2,
                    "company": "BetaCo",
                    "ats_type": None,
                    "last_checked_at": None,
                    "last_new_jobs": 0,
                    "active": False,
                },
            ]
        ),
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["companies", "list"])
    assert result.exit_code == 0
    assert "Acme Corp" in result.output
    assert "BetaCo" in result.output


def test_settings_set_converts_bool(monkeypatch):
    captured: list[tuple[str, dict]] = []

    def _request(method, url, timeout=30, **kwargs):
        path = url.replace("http://localhost:8000", "")
        if path == "/settings/save":
            captured.append((path, kwargs.get("json", {})))
            return _FakeResponse({"status": "saved"})
        if path == "/settings/reload":
            captured.append((path, kwargs.get("json", {})))
            return _FakeResponse({"status": "reloaded"})
        return _FakeResponse({})

    monkeypatch.setattr(httpx, "request", _request)
    monkeypatch.setattr("job_agent.cli._interactive", lambda: False)

    runner = CliRunner()
    result = runner.invoke(cli, ["settings", "set", "use_jobspy", "true"])

    assert result.exit_code == 0
    assert captured[0] == ("/settings/save", {"use_jobspy": True})
    assert captured[1][0] == "/settings/reload"
