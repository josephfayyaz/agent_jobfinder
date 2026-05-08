# Phase Q2 — Provider Error Taxonomy

Status: pending

## Goal

Normalize provider failures into stable app-level categories so routes no
longer need to inspect raw provider strings.

## Write Scope

- `job_agent/provider_errors.py` (new)
- `job_agent/llm.py`
- `job_agent/routers/system.py`
- `job_agent/routers/candidates.py`
- `tests/test_llm_gemini.py`
- `tests/test_intake.py`
- `tests/test_provider_resilience.py`

## Do Not Touch

- onboarding UI JS
- workflow prompt text
- database schema

## Exact Changes

### 1. Add new file `job_agent/provider_errors.py`

Create it with this exact content:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ProviderErrorInfo:
    provider: str
    category: str
    message: str
    retryable: bool = False


def error_info(provider: str, category: str, message: str, *, retryable: bool = False) -> ProviderErrorInfo:
    return ProviderErrorInfo(
        provider=str(provider or ""),
        category=str(category or "unavailable"),
        message=str(message or ""),
        retryable=bool(retryable),
    )
```

### 2. Replace the `ProviderUnavailableError` class in `job_agent/llm.py`

Replace the current class with:

```python
class ProviderUnavailableError(RuntimeError):
    \"\"\"Raised when a provider cannot be reached or returns an unexpected response.\"\"\"

    def __init__(
        self,
        message: str,
        *,
        provider: str = "",
        category: str = "unavailable",
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.provider = str(provider or "")
        self.category = str(category or "unavailable")
        self.retryable = bool(retryable)
```

### 3. Update raise sites in `job_agent/llm.py`

Do not rewrite every provider branch in this phase. Only upgrade the current
high-value failure paths:

- Gemini auth / HTTP errors
- Gemini blocked prompt
- Gemini empty content
- OpenAI quota
- local context-limit failures

Use categories from this fixed set:

- `auth`
- `quota`
- `rate_limit`
- `context_too_large`
- `unsupported_feature`
- `blocked_content`
- `empty_output`
- `malformed_json`
- `timeout`
- `unavailable`

Examples:

Replace:

```python
raise ProviderUnavailableError(
    f"Gemini blocked the prompt: {prompt_feedback.get('blockReason')}."
)
```

with:

```python
raise ProviderUnavailableError(
    f"Gemini blocked the prompt: {prompt_feedback.get('blockReason')}.",
    provider="gemini",
    category="blocked_content",
)
```

Replace the OpenAI quota branch with:

```python
raise ProviderUnavailableError(
    "OPENAI_QUOTA_EXCEEDED: OpenAI rate limit or quota reached. "
    "Check your billing or switch provider.",
    provider="openai",
    category="quota",
    retryable=False,
) from exc
```

For Gemini prompt-size/context failures, use:

```python
provider="gemini",
category="context_too_large",
retryable=True,
```

### 4. Replace string-parsing in `job_agent/routers/candidates.py`

Do not delete the current function. Replace its body.

Replace `_provider_failure_detail(exc)` with a category-first version:

```python
def _provider_failure_detail(exc: ProviderUnavailableError) -> str:
    category = str(getattr(exc, "category", "") or "unavailable")
    detail = str(exc)
    lowered = detail.lower()

    if category == "quota" or detail.startswith("OPENAI_QUOTA_EXCEEDED:"):
        return "OpenAI quota reached. Top up billing or switch provider in Settings, then try intake again."
    if category == "blocked_content":
        return (
            "The configured AI provider blocked the uploaded material during intake. "
            "Remove highly sensitive content, add shorter notes, or switch provider, then try intake again."
        )
    if category == "context_too_large":
        if str(getattr(exc, "provider", "")) == "gemini":
            return (
                "Gemini rejected the intake input as too large for this request. "
                "Upload fewer PDFs, shorten pasted notes, or retry after trimming duplicate content."
            )
        return (
            "The selected local model could not process the uploaded material within its context window. "
            "Remove duplicate source files, switch to a stronger local model, or use OpenAI/Claude for intake."
        )
    if "400 bad request" in lowered:
        return (
            "Your local model rejected the intake request (HTTP 400). "
            "Load a chat/instruct model, set at least 16k context window, and retry provider validation in Settings."
        )
    if "insufficient system resources" in lowered or "failed to load model" in lowered:
        return (
            "LM Studio could not load the selected model with current system resources. "
            "Choose a smaller local model in Settings or switch provider, then try again."
        )
    return "The configured AI provider is not responding. Check Settings, then try intake again."
```

### 5. Keep `/providers/validate` compatible

In `job_agent/routers/system.py`, do not redesign the public route.
Only update any internal provider validation helpers so new failure details can
later map cleanly into the same categories.

## Tests

Add or update tests so they assert category-aware behavior.

In `tests/test_intake.py`, add:

```python
def test_provider_failure_detail_prefers_error_category_for_gemini_context_issue():
    msg = _provider_failure_detail(
        ProviderUnavailableError(
            "Gemini prompt too large",
            provider="gemini",
            category="context_too_large",
            retryable=True,
        )
    )
    assert "gemini" in msg.lower()
    assert "too large" in msg.lower()
```

## Verification

Run:

```bash
pytest tests/test_llm_gemini.py tests/test_intake.py tests/test_provider_resilience.py -q
ruff check job_agent/provider_errors.py job_agent/llm.py job_agent/routers/candidates.py job_agent/routers/system.py tests/test_llm_gemini.py tests/test_intake.py tests/test_provider_resilience.py
```

## Stop Conditions

Stop and report if:

- any route starts depending on provider-specific raw error strings again
- category assignment forces a change to the public API response contract
