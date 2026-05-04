# Release Spec 04 — P2 LLM Hardening (Truncation Error + API Key Log Safety)

## Priority: MEDIUM — implement after specs 01–03 are fully complete.

---

## Purpose

This spec fixes two LLM-related issues that silently corrupt data or leak sensitive information:

1. **Truncated LLM output is silently used** — when a model hits its token limit (`finish_reason == "length"`), the truncated JSON is partially repaired and silently passed to callers. This can write corrupt data to the database with no error visible to the user.
2. **API key material can appear in logs** — exception messages from the Anthropic, OpenAI, and Ollama clients can include the full upstream error string, which may contain API key fragments in certain error formats.

---

## Global Constraints (READ THESE FIRST)

1. **Python environment:** `conda run -n ML` only.
2. **`ProviderUnavailableError`** is defined in `job_agent/llm.py`. Import it from there; do not define a new one.
3. **All callers of `LLMRouter.generate()`** already catch `ProviderUnavailableError`. Raising it on truncation is safe — callers handle it gracefully (they log and continue or return an empty result).
4. **Do NOT change anything else in `llm.py`** except the two specific sections described below.
5. After completing: write report, append to `completed_agent_specs.txt`, move spec file.
6. Run full test suite after ALL changes. All tests must pass.

---

## Fix 1 of 2: Raise ProviderUnavailableError on finish_reason="length"

### File to modify
`/Users/youseffayyaz/Local_LLM/job_agent/llm.py`

### Problem
In `_call_lm_studio()`, around line 432, when `finish_reason == "length"`, the code only logs a warning and then continues to use the truncated (and possibly invalid) response. Callers receive silently corrupted data.

### Find this block (around lines 432–438):
```python
            if finish_reason == "length":
                logger.warning(
                    "Model '%s' hit max_tokens=%d and was cut off. "
                    "Increase LM_STUDIO_MAX_TOKENS_* in .env if output is incomplete.",
                    model,
                    max_tokens,
                )
```

### Replace with:
```python
            if finish_reason == "length":
                raise ProviderUnavailableError(
                    f"Model '{model}' output was cut off at max_tokens={max_tokens}. "
                    f"Increase LM_STUDIO_MAX_TOKENS_* in your .env or reduce the prompt size."
                )
```

**Why this is safe:** All callers of `LLMRouter.generate()` already catch `ProviderUnavailableError`. Raising here surfaces a retryable error instead of silently writing bad data. The caller can decide to retry with a smaller prompt or skip.

---

## Fix 2 of 2: Truncate API key–containing exception strings in error messages

### File to modify
`/Users/youseffayyaz/Local_LLM/job_agent/llm.py`

### Problem
Three `raise ProviderUnavailableError(...)` calls include `str(exc)` or `f"...{exc}"` from upstream clients without any length limit. Anthropic/OpenAI/Ollama error strings can be long and may contain API key fragments in certain error formats (e.g., "Invalid API key: sk-...").

### Change A — `generate_with_claude()` (around line 256)

**Find:**
```python
        except Exception as exc:
            raise ProviderUnavailableError(f"Claude request failed: {exc}") from exc
```

**Replace with:**
```python
        except Exception as exc:
            raise ProviderUnavailableError(
                f"Claude request failed: {type(exc).__name__}: {str(exc)[:200]}"
            ) from exc
```

### Change B — `generate_with_openai()` (find the `except Exception as exc` block inside that method)

First, read `llm.py` around lines 285–310 to find the exact `except Exception` block in `generate_with_openai()`. It will look like:

```python
        except Exception as exc:
            raise ProviderUnavailableError(
                f"OpenAI request failed for model '{model}': {exc}"
            ) from exc
```

**Replace with:**
```python
        except Exception as exc:
            raise ProviderUnavailableError(
                f"OpenAI request failed for model '{model}': {type(exc).__name__}: {str(exc)[:200]}"
            ) from exc
```

### Change C — Ollama error raise

Search `llm.py` for the Ollama-specific `ProviderUnavailableError` raise that includes `{exc}` in the message. Apply the same `:200` truncation pattern:

```python
# Any line like:
raise ProviderUnavailableError(f"...{exc}") from exc

# Replace the {exc} with:
f"{type(exc).__name__}: {str(exc)[:200]}"
```

**IMPORTANT:** Only apply this truncation to lines where `str(exc)` or `f"...{exc}"` is interpolated directly into the error message. Do NOT change the `ProviderUnavailableError: raise` re-raise at `except ProviderUnavailableError: raise`.

### How to find the Ollama raise
Run this to find all relevant lines:
```bash
grep -n "ProviderUnavailableError\|raise.*exc" /Users/youseffayyaz/Local_LLM/job_agent/llm.py | grep -v "^.*#"
```
Apply the truncation to every line that builds a message with `{exc}` but NOT to bare `raise` or `raise ProviderUnavailableError` with no interpolation.

---

## Tests to write

Create file: `tests/test_llm_hardening.py`

```python
"""Tests for LLM hardening: truncation error and key-safe error messages."""
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
    response.raise_for_status = MagicMock()
    return response


def test_finish_reason_length_raises_provider_unavailable():
    """Model hitting max_tokens must raise ProviderUnavailableError, not silently continue."""
    from job_agent.llm import LLMRouter, ProviderUnavailableError

    router = LLMRouter.__new__(LLMRouter)

    mock_response = _make_mock_response(finish_reason="length", content='{"partial": true}')

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = lambda s: mock_client
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response

        with pytest.raises(ProviderUnavailableError) as exc_info:
            router._call_lm_studio(
                target_url="http://localhost:1234/v1/chat/completions",
                model="test-model",
                system_prompt="sys",
                user_prompt="user",
                max_tokens=128,
                temperature=0.2,
                provider_label="LM Studio",
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
```

### Run test
```bash
conda run -n ML pytest tests/test_llm_hardening.py -v
```
Expected: both tests PASS. If `_call_lm_studio` is a private method and hard to test directly, write an integration-style test through `LLMRouter.generate()` with a mock that returns `finish_reason=length`.

---

## Verification

Run the full suite:
```bash
conda run -n ML pytest tests/ -x -q
```
All tests must pass.

Run linter:
```bash
conda run -n ML ruff check job_agent/llm.py
```
No errors allowed.

---

## Completion Steps (do these in order after all tests pass)

1. **Write a report** at `AGENT_SPECS/completed/release_spec_04_p2_llm_hardening.md` describing:
   - What you changed in each file (exact lines before and after)
   - How many `{exc}` interpolations you found and truncated in Ollama/OpenAI sections
   - Test results (pass count)
   - Any issues encountered and how you resolved them
   - Any suggestions for improvement

2. **Append to log:**
   ```
   release_spec_04_p2_llm_hardening.md — COMPLETE — <ISO timestamp>
   ```
   Append to `/Users/youseffayyaz/Local_LLM/completed_agent_specs.txt`.

3. **Move this spec file** from `AGENT_SPECS/pending/claude/release_spec_04_p2_llm_hardening.md` to `AGENT_SPECS/completed/release_spec_04_p2_llm_hardening.md`.
