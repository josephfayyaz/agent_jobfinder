# Phase Q4 — Workflow Input Shaping

Status: pending

## Goal

Move prompt-size shaping into a dedicated shared layer instead of hardcoding
different trimming logic in each workflow.

## Write Scope

- `job_agent/services/provider_input.py` (new)
- `job_agent/services/intake.py`
- `job_agent/services/job_fit_scoring.py`
- `job_agent/services/workflows.py`
- `job_agent/services/compliance_matrix.py`
- `tests/test_intake.py`
- `tests/test_job_fit_scoring.py`
- `tests/test_provider_cost_ux.py`

## Do Not Touch

- prompt wordsmithing
- route URLs
- DB models
- frontend

## Exact Changes

### 1. Add new module `job_agent/services/provider_input.py`

Create these exact public helpers:

```python
from __future__ import annotations

from job_agent.providers import normalize_provider_mode, provider_prompt_char_limit


def trim_text_head_tail(text: str, limit: int, marker: str) -> str:
    cleaned = str(text or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    keep_head = max(200, limit // 2)
    keep_tail = max(120, limit - keep_head - len(marker) - 8)
    return f"{cleaned[:keep_head].rstrip()}\\n\\n{marker}\\n\\n{cleaned[-keep_tail:].lstrip()}".strip()


def shape_text_for_workflow(text: str, *, workflow: str, provider_mode: str | None = None) -> str:
    mode = normalize_provider_mode(provider_mode)
    limit = provider_prompt_char_limit(workflow, mode)
    return trim_text_head_tail(text, limit, "[... provider-safe truncation ...]")


def shape_text_blocks_for_workflow(blocks: list[str], *, workflow: str, provider_mode: str | None = None) -> list[str]:
    mode = normalize_provider_mode(provider_mode)
    total_limit = provider_prompt_char_limit(workflow, mode)
    if not blocks:
        return []
    per_block_limit = max(1000, total_limit // max(1, len(blocks)))
    return [
        trim_text_head_tail(str(block or ""), per_block_limit, "[... block truncated ...]")
        for block in blocks
        if str(block or "").strip()
    ]
```

### 2. Integrate into onboarding intake

In `job_agent/services/intake.py`, inside `start_intake()` and `answer_questions()`,
after `_prepare_intake_texts(...)`, add:

```python
from job_agent.providers import normalize_provider_mode
from job_agent.services.provider_input import shape_text_blocks_for_workflow
```

Then replace:

```python
extracted_texts = _prepare_intake_texts(extracted_texts)
```

with:

```python
provider_mode = normalize_provider_mode(getattr(settings, "llm_provider_mode", "openai"))
extracted_texts = shape_text_blocks_for_workflow(
    _prepare_intake_texts(extracted_texts),
    workflow="intake",
    provider_mode=provider_mode,
)
```

Make the same replacement for `source_texts` in `answer_questions()`.

### 3. Integrate into job fit scoring

In `job_agent/services/job_fit_scoring.py`, before sending the `_USER_PROMPT`,
shape the job description with:

```python
from job_agent.services.provider_input import shape_text_for_workflow
```

Then change the job description interpolation input so `description` becomes:

```python
safe_description = shape_text_for_workflow(
    str(job.description or ""),
    workflow="jd_scoring",
    provider_mode=normalize_provider_mode(getattr(settings, "llm_provider_mode", "openai")),
)
```

Use `safe_description` instead of raw `job.description`.

### 4. Integrate into CV workflow and compliance matrix

In `job_agent/services/workflows.py`, inside `_generate_json_with_usage(...)`,
shape `user_prompt` before calling the router.

Do not overgeneralize. Add a local variable:

```python
workflow_name = "cv_writer" if role == "writer" else "jd_scoring"
safe_user_prompt = shape_text_for_workflow(
    user_prompt,
    workflow=workflow_name,
    provider_mode=normalize_provider_mode(getattr(settings, "llm_provider_mode", "openai")),
)
```

Then pass `safe_user_prompt` to the router instead of `user_prompt`.

In `job_agent/services/compliance_matrix.py`, shape the generated prompt with
workflow `"compliance_matrix"` before calling `self.router.generate(...)`.

## Tests

Add tests that assert:

- Gemini intake gets smaller shaped blocks than OpenAI for the same input
- JD scoring uses the shaping helper for long descriptions
- CV/compliance prompts are shaped before provider calls

## Verification

Run:

```bash
pytest tests/test_intake.py tests/test_job_fit_scoring.py tests/test_provider_cost_ux.py -q
ruff check job_agent/services/provider_input.py job_agent/services/intake.py job_agent/services/job_fit_scoring.py job_agent/services/workflows.py job_agent/services/compliance_matrix.py tests/test_intake.py tests/test_job_fit_scoring.py tests/test_provider_cost_ux.py
```

## Stop Conditions

Stop and report if:

- shaping causes tests to fail because prompts become too small to satisfy
  existing schema expectations
