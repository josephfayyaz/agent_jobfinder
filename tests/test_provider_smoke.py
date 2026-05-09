from __future__ import annotations

import pytest


def test_provider_smoke_probe_returns_ok(monkeypatch):
    from job_agent import provider_smoke

    class Router:
        def generate_with_retry(self, **_kwargs):
            return {"ok": True}

    monkeypatch.setattr(provider_smoke, "LLMRouter", lambda: Router())
    result = provider_smoke.run_provider_smoke("probe")
    assert result["ok"] is True
    assert result["case"] == "probe"
    assert "ok" in result["keys"]


def test_provider_smoke_large_intake_prompt_is_much_larger_than_probe(monkeypatch):
    from job_agent import provider_smoke

    prompt_lengths: list[int] = []

    class Router:
        def generate_with_retry(self, **kwargs):
            prompt_lengths.append(len(str(kwargs.get("user_prompt") or "")))
            case_prompt = str(kwargs.get("user_prompt") or "")
            if "target_roles" in case_prompt:
                return {"summary": "x", "skills": ["Python"], "target_roles": ["Data Engineer"]}
            return {"ok": True}

    monkeypatch.setattr(provider_smoke, "LLMRouter", lambda: Router())
    provider_smoke.run_provider_smoke("probe")
    provider_smoke.run_provider_smoke("large_intake")

    assert len(prompt_lengths) == 2
    assert prompt_lengths[1] > prompt_lengths[0] * 10


def test_provider_smoke_raises_on_invalid_json(monkeypatch):
    from job_agent import provider_smoke

    class Router:
        def generate_with_retry(self, **_kwargs):
            raise ValueError("Could not extract valid JSON")

    monkeypatch.setattr(provider_smoke, "LLMRouter", lambda: Router())
    with pytest.raises(ValueError, match="valid JSON"):
        provider_smoke.run_provider_smoke("small_json")
