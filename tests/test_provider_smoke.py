from __future__ import annotations

import pytest


def test_provider_smoke_probe_returns_ok(monkeypatch):
    from job_agent import provider_smoke

    class Router:
        def generate_with_retry_usage(self, **_kwargs):
            return {"ok": True}, {"provider": "openai", "tokens": 3, "input_tokens": 2, "output_tokens": 1}

    monkeypatch.setattr(provider_smoke, "LLMRouter", lambda: Router())
    result = provider_smoke.run_provider_smoke("probe")
    assert result["ok"] is True
    assert result["case"] == "probe"
    assert "ok" in result["keys"]
    assert result["usage"]["provider"] == "openai"
    assert result["usage"]["tokens"] == 3


def test_provider_smoke_large_intake_prompt_is_much_larger_than_probe(monkeypatch):
    from job_agent import provider_smoke

    prompt_lengths: list[int] = []

    class Router:
        def generate_with_retry_usage(self, **kwargs):
            prompt_lengths.append(len(str(kwargs.get("user_prompt") or "")))
            case_prompt = str(kwargs.get("user_prompt") or "")
            if "target_roles" in case_prompt:
                return (
                    {"summary": "x", "skills": ["Python"], "target_roles": ["Data Engineer"]},
                    {"provider": "gemini", "tokens": 30, "input_tokens": 21, "output_tokens": 9},
                )
            return {"ok": True}, {"provider": "gemini", "tokens": 2, "input_tokens": 1, "output_tokens": 1}

    monkeypatch.setattr(provider_smoke, "LLMRouter", lambda: Router())
    provider_smoke.run_provider_smoke("probe")
    result = provider_smoke.run_provider_smoke("large_intake")

    assert len(prompt_lengths) == 2
    assert prompt_lengths[1] > prompt_lengths[0] * 10
    assert result["usage"]["provider"] == "gemini"
    assert result["usage"]["tokens"] == 30


def test_provider_smoke_raises_on_invalid_json(monkeypatch):
    from job_agent import provider_smoke

    class Router:
        def generate_with_retry_usage(self, **_kwargs):
            raise ValueError("Could not extract valid JSON")

    monkeypatch.setattr(provider_smoke, "LLMRouter", lambda: Router())
    with pytest.raises(ValueError, match="valid JSON"):
        provider_smoke.run_provider_smoke("small_json")


def test_provider_smoke_preserves_context_too_large_category(monkeypatch):
    from job_agent import provider_smoke
    from job_agent.llm import ProviderUnavailableError

    class Router:
        def generate_with_retry_usage(self, **_kwargs):
            raise ProviderUnavailableError(
                "LM Studio request exceeded the model context window.",
                provider="lm_studio",
                category="context_too_large",
                retryable=True,
            )

    monkeypatch.setattr(provider_smoke, "LLMRouter", lambda: Router())
    with pytest.raises(ProviderUnavailableError) as exc_info:
        provider_smoke.run_provider_smoke("large_intake")
    assert exc_info.value.category == "context_too_large"
