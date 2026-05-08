from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import MagicMock

import httpx
import pytest

from job_agent.config import settings
from job_agent.llm import LLMRouter
from job_agent.services.compliance_matrix import ComplianceMatrixService
from job_agent.services.workflows import CVWorkflowService


class _DummyOpenAIClient:
    def __init__(self, response):
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=lambda **_kwargs: response))


class _DummyAnthropicClient:
    def __init__(self, response):
        self.messages = SimpleNamespace(create=lambda **_kwargs: response)


def test_generate_with_usage_captures_openai_usage(monkeypatch):
    tracked = {
        "llm_provider_mode": settings.llm_provider_mode,
        "openai_api_key": settings.openai_api_key,
        "openai_review_model": settings.openai_review_model,
    }
    try:
        object.__setattr__(settings, "llm_provider_mode", "openai")
        object.__setattr__(settings, "openai_api_key", "")
        object.__setattr__(settings, "openai_review_model", "gpt-4o-mini")
        router = LLMRouter()
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'))],
            usage=SimpleNamespace(prompt_tokens=11, completion_tokens=7, total_tokens=18),
        )
        router._openai_client = _DummyOpenAIClient(response)

        payload, usage = router.generate_with_usage(
            role="small",
            system_prompt="system",
            user_prompt="user",
        )

        assert payload == {"ok": True}
        assert usage["provider"] == "openai"
        assert usage["tokens"] == 18
        assert usage["input_tokens"] == 11
        assert usage["output_tokens"] == 7
    finally:
        for key, value in tracked.items():
            object.__setattr__(settings, key, value)


def test_generate_with_usage_captures_gemini_usage(monkeypatch):
    tracked = {
        "llm_provider_mode": settings.llm_provider_mode,
        "gemini_api_key": settings.gemini_api_key,
        "gemini_model": settings.gemini_model,
    }
    try:
        object.__setattr__(settings, "llm_provider_mode", "gemini")
        object.__setattr__(settings, "gemini_api_key", "AIza-test")
        object.__setattr__(settings, "gemini_model", "gemini-test")

        def fake_post(*_args, **_kwargs):
            request = httpx.Request("POST", "https://example.com")
            return httpx.Response(
                200,
                request=request,
                json={
                    "candidates": [{"content": {"parts": [{"text": '{"answer": "ok"}'}]}}],
                    "usageMetadata": {
                        "promptTokenCount": 21,
                        "candidatesTokenCount": 9,
                        "totalTokenCount": 30,
                    },
                },
            )

        monkeypatch.setattr(httpx, "post", fake_post)
        router = LLMRouter()

        payload, usage = router.generate_with_usage(
            role="small",
            system_prompt="system",
            user_prompt="user",
        )

        assert payload == {"answer": "ok"}
        assert usage["provider"] == "gemini"
        assert usage["tokens"] == 30
        assert usage["input_tokens"] == 21
        assert usage["output_tokens"] == 9
    finally:
        for key, value in tracked.items():
            object.__setattr__(settings, key, value)


def test_generate_with_usage_reports_zero_for_local_provider(monkeypatch):
    tracked = {
        "llm_provider_mode": settings.llm_provider_mode,
        "lm_studio_small_model": settings.lm_studio_small_model,
    }
    try:
        object.__setattr__(settings, "llm_provider_mode", "lm_studio")
        object.__setattr__(settings, "lm_studio_small_model", "local-model")
        router = LLMRouter()

        def fake_call(**kwargs):
            if kwargs.get("include_usage"):
                return {"status": "ok"}, {
                    "provider": "lm_studio",
                    "model": kwargs.get("model", ""),
                    "tokens": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                }
            return {"status": "ok"}

        monkeypatch.setattr(router, "_call_lm_studio", fake_call)

        payload, usage = router.generate_with_usage(
            role="small",
            system_prompt="system",
            user_prompt="user",
        )

        assert payload == {"status": "ok"}
        assert usage["provider"] == "lm_studio"
        assert usage["tokens"] == 0
    finally:
        for key, value in tracked.items():
            object.__setattr__(settings, key, value)


def test_workflow_token_usage_accumulates_and_enforces_budget(db_session):
    tracked = {
        "llm_provider_mode": settings.llm_provider_mode,
        "max_pipeline_tokens": settings.max_pipeline_tokens,
    }
    try:
        object.__setattr__(settings, "llm_provider_mode", "openai")
        object.__setattr__(settings, "max_pipeline_tokens", 20)
        service = CVWorkflowService(db_session)
        usage = service._empty_token_usage()

        service._record_token_usage(
            usage,
            "writer",
            {"provider": "openai", "model": "gpt-4o-mini", "tokens": 9, "input_tokens": 5, "output_tokens": 4},
        )
        service._record_token_usage(
            usage,
            "reviewer",
            {"provider": "openai", "model": "gpt-4o-mini", "tokens": 7, "input_tokens": 4, "output_tokens": 3},
        )

        assert usage["writer"] == 9
        assert usage["reviewer"] == 7
        assert usage["total"] == 16

        with pytest.raises(ValueError):
            service._record_token_usage(
                usage,
                "reviser",
                {"provider": "openai", "model": "gpt-4o-mini", "tokens": 8, "input_tokens": 3, "output_tokens": 5},
            )
    finally:
        for key, value in tracked.items():
            object.__setattr__(settings, key, value)


def test_workflow_generate_json_with_usage_shapes_writer_prompt_before_router_call(monkeypatch):
    tracked = {
        "llm_provider_mode": settings.llm_provider_mode,
    }
    try:
        object.__setattr__(settings, "llm_provider_mode", "gemini")
        router = MagicMock()
        router.generate.return_value = {"ok": True}
        service = CVWorkflowService(session=MagicMock(), router=router)

        payload, usage = service._generate_json_with_usage(
            role="writer",
            system_prompt="System",
            user_prompt="X" * 25000,
        )

        assert payload == {"ok": True}
        assert usage["provider"] == "gemini"
        shaped_prompt = router.generate.call_args.kwargs["user_prompt"]
        assert "[... provider-safe truncation ...]" in shaped_prompt
        assert len(shaped_prompt) < 20000
    finally:
        for key, value in tracked.items():
            object.__setattr__(settings, key, value)


def test_compliance_matrix_shapes_prompt_before_provider_call(monkeypatch):
    import job_agent.services.compliance_matrix as compliance_module

    tracked = {
        "llm_provider_mode": settings.llm_provider_mode,
    }
    try:
        object.__setattr__(settings, "llm_provider_mode", "gemini")
        draft = SimpleNamespace(
            resume_track_id=uuid4(),
            job_post_id=uuid4(),
            content={},
            review_feedback={},
        )
        track = SimpleNamespace(slug="data-engineer")
        session = MagicMock()
        session.get.side_effect = [draft, track]
        router = MagicMock()
        router.generate.return_value = {"requirements": []}

        class FakeWorkflow:
            def __init__(self, _session, _router):
                pass

            def _load_context(self, _job_post_id, _track_slug):
                return SimpleNamespace(job=SimpleNamespace())

            def _job_dict(self, _job):
                return {"title": "Role", "description": "desc"}

        monkeypatch.setattr(compliance_module, "CVWorkflowService", FakeWorkflow)
        monkeypatch.setattr(
            compliance_module,
            "build_compliance_matrix_prompt",
            lambda *_args, **_kwargs: "X" * 25000,
        )
        monkeypatch.setattr(
            compliance_module,
            "build_compliance_matrix_system_prompt",
            lambda: "System",
        )

        service = ComplianceMatrixService(session=session, router=router)
        service.generate(uuid4())

        shaped_prompt = router.generate.call_args.kwargs["user_prompt"]
        assert "[... provider-safe truncation ...]" in shaped_prompt
        assert len(shaped_prompt) < 18000
    finally:
        for key, value in tracked.items():
            object.__setattr__(settings, key, value)
