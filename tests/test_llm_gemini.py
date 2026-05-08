from __future__ import annotations

import httpx


def test_generate_with_gemini_uses_query_param_and_system_instruction(monkeypatch):
    import job_agent.config as cfg
    from job_agent.llm import LLMRouter

    tracked = {
        "gemini_api_key": cfg.settings.gemini_api_key,
        "gemini_model": cfg.settings.gemini_model,
    }

    class Response:
        is_success = True

        def json(self):
            return {
                "candidates": [
                    {"content": {"parts": [{"text": '{"ok": true}'}]}}
                ]
            }

    calls: list[dict] = []

    def fake_post(url, **kwargs):
        calls.append({"url": url, **kwargs})
        return Response()

    try:
        object.__setattr__(cfg.settings, "gemini_api_key", "AIza-test")
        object.__setattr__(cfg.settings, "gemini_model", "gemini-2.5-flash")
        monkeypatch.setattr(httpx, "post", fake_post)

        payload = LLMRouter().generate_with_gemini(
            system_prompt="You are structured.",
            user_prompt="Return {\"ok\": true}",
        )

        assert payload == {"ok": True}
        assert calls
        first = calls[0]
        assert first["params"]["key"] == "AIza-test"
        assert first["json"]["system_instruction"]["parts"][0]["text"] == "You are structured."
        assert first["json"]["contents"][0]["parts"][0]["text"] == 'Return {"ok": true}'
    finally:
        for key, value in tracked.items():
            object.__setattr__(cfg.settings, key, value)


def test_generate_with_gemini_retries_without_json_mode_on_invalid_argument(monkeypatch):
    import job_agent.config as cfg
    from job_agent.llm import LLMRouter

    tracked = {
        "gemini_api_key": cfg.settings.gemini_api_key,
        "gemini_model": cfg.settings.gemini_model,
    }

    class ErrorResponse:
        is_success = False
        status_code = 400
        text = '{"error":{"code":400,"message":"responseMimeType unsupported","status":"INVALID_ARGUMENT"}}'

        def raise_for_status(self):
            raise httpx.HTTPStatusError("400 error", request=None, response=self)

    class SuccessResponse:
        is_success = True

        def json(self):
            return {
                "candidates": [
                    {"content": {"parts": [{"text": '{"retry": true}'}]}}
                ]
            }

    calls: list[dict] = []

    def fake_post(url, **kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return ErrorResponse()
        return SuccessResponse()

    try:
        object.__setattr__(cfg.settings, "gemini_api_key", "AIza-test")
        object.__setattr__(cfg.settings, "gemini_model", "gemini-2.5-flash")
        monkeypatch.setattr(httpx, "post", fake_post)

        payload = LLMRouter().generate_with_gemini(
            system_prompt="System",
            user_prompt="User",
        )

        assert payload == {"retry": True}
        assert len(calls) == 2
        assert "responseMimeType" in calls[0]["json"]["generationConfig"]
        assert "responseMimeType" not in calls[1]["json"]["generationConfig"]
    finally:
        for key, value in tracked.items():
            object.__setattr__(cfg.settings, key, value)


def test_generate_with_gemini_retries_with_trimmed_prompt_on_size_error(monkeypatch):
    import job_agent.config as cfg
    from job_agent.llm import LLMRouter

    tracked = {
        "gemini_api_key": cfg.settings.gemini_api_key,
        "gemini_model": cfg.settings.gemini_model,
    }

    class ErrorResponse:
        is_success = False
        status_code = 400
        text = '{"error":{"code":400,"message":"Prompt is too long for this model context window","status":"INVALID_ARGUMENT"}}'

        def raise_for_status(self):
            raise httpx.HTTPStatusError("400 error", request=None, response=self)

    class SuccessResponse:
        is_success = True

        def json(self):
            return {
                "candidates": [
                    {"content": {"parts": [{"text": '{"trimmed": true}'}]}}
                ]
            }

    calls: list[dict] = []

    def fake_post(url, **kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return ErrorResponse()
        return SuccessResponse()

    try:
        object.__setattr__(cfg.settings, "gemini_api_key", "AIza-test")
        object.__setattr__(cfg.settings, "gemini_model", "gemini-2.5-flash")
        monkeypatch.setattr(httpx, "post", fake_post)

        payload = LLMRouter().generate_with_gemini(
            system_prompt="System",
            user_prompt="A" * 20000,
        )

        assert payload == {"trimmed": True}
        assert len(calls) == 2
        assert calls[0]["headers"]["x-goog-api-key"] == "AIza-test"
        assert "[... truncated for Gemini retry ...]" in calls[1]["json"]["contents"][0]["parts"][0]["text"]
        assert len(calls[1]["json"]["contents"][0]["parts"][0]["text"]) < len(calls[0]["json"]["contents"][0]["parts"][0]["text"])
        assert "responseMimeType" not in calls[1]["json"]["generationConfig"]
    finally:
        for key, value in tracked.items():
            object.__setattr__(cfg.settings, key, value)
