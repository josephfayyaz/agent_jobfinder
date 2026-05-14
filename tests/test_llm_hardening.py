"""Tests for LLM hardening: truncation error and key-safe error messages."""
from types import SimpleNamespace

import pytest
from unittest.mock import MagicMock, patch


def _make_mock_response(finish_reason="stop", content='{"result": "ok"}'):
    """Build a minimal mock that looks like an LM Studio response."""
    choice = MagicMock()
    choice.get = lambda key, default="": {"finish_reason": finish_reason, "message": MagicMock(get=lambda k, d="": content if k == "content" else "")}.get(key, default)
    choice.__getitem__ = lambda self, key: {"finish_reason": finish_reason}[key]
    response = MagicMock()
    response.json.return_value = {
        "choices": [{"finish_reason": finish_reason, "message": {"content": content, "reasoning_content": ""}}]
    }
    response.status_code = 200
    response.text = ""
    response.raise_for_status = MagicMock()
    return response


def test_finish_reason_length_raises_provider_unavailable():
    """Model hitting max_tokens must raise ProviderUnavailableError, not silently continue."""
    from job_agent.llm import ProviderUnavailableError
    from job_agent.llm_adapters.local_provider_adapter import _call_openai_compatible_local

    mock_response = _make_mock_response(finish_reason="length", content='{"partial": true}')

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = lambda s: mock_client
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response

        with pytest.raises(ProviderUnavailableError) as exc_info:
            _call_openai_compatible_local(
                model="test-model",
                max_tokens=128,
                settings_obj=SimpleNamespace(
                    lm_studio_request_timeout_seconds=5,
                    lm_studio_base_url="http://localhost:1234/v1",
                ),
                system_prompt="sys",
                user_prompt="user",
                temperature=0.2,
                provider_label="LM Studio",
                base_url="http://localhost:1234/v1",
                include_usage=False,
                json_extractor=lambda text: {"raw": text},
                usage_builder=lambda *_args, **_kwargs: {},
                provider_error_cls=ProviderUnavailableError,
            )

    assert "max_tokens" in str(exc_info.value).lower() or "cut off" in str(exc_info.value).lower(), (
        "Error message should mention max_tokens or 'cut off'"
    )


def test_claude_exception_message_is_truncated():
    """Claude exceptions must have messages truncated to 200 chars."""
    from job_agent.llm import LLMRouter, ProviderUnavailableError

    router = LLMRouter.__new__(LLMRouter)
    router._anthropic_client = MagicMock()

    long_message = "A" * 500  # Simulate a very long exception message
    router._anthropic_client.messages.create.side_effect = Exception(long_message)

    with pytest.raises(ProviderUnavailableError) as exc_info:
        router.generate_with_claude(system_prompt="sys", user_prompt="user")

    # The error message should contain at most 200 chars from the original exception
    error_str = str(exc_info.value)
    # The truncated portion of the original exception should be at most 200 chars
    # (the full message may be longer due to prefix text like "Claude request failed: ")
    original_in_message = error_str[error_str.find("Exception:"):]
    assert len(original_in_message) <= 220, (
        f"Exception message not truncated, got {len(original_in_message)} chars: {original_in_message[:50]}..."
    )
