# Phase Q6 — Adapter Split And Router Cleanup

Status: pending

## Goal

Split `job_agent/llm.py` into thin provider adapters while preserving the
public `LLMRouter.generate()` contract.

## Write Scope

- `job_agent/llm.py`
- `job_agent/llm_adapters/__init__.py` (new)
- `job_agent/llm_adapters/openai_adapter.py` (new)
- `job_agent/llm_adapters/gemini_adapter.py` (new)
- `job_agent/llm_adapters/claude_adapter.py` (new)
- `job_agent/llm_adapters/local_gateway_adapter.py` (new)
- `job_agent/llm_adapters/ollama_adapter.py` (new)
- `tests/test_llm_gemini.py`
- `tests/test_provider_cost_ux.py`

## Do Not Touch

- service-layer call sites
- workflow services
- route URLs
- prompt text

## Exact Changes

### 1. Preserve the public API

`LLMRouter` must still expose:

- `generate(...)`
- `generate_with_retry(...)`
- `generate_with_usage(...)`
- `generate_with_retry_usage(...)`
- `provider_status()`

Do not change these signatures.

### 2. Extract provider internals only

Move provider-specific code blocks into adapters without changing behavior:

- Gemini code from `generate_with_gemini`
- OpenAI code from `generate_with_openai`
- Claude code from `generate_with_claude`
- local OpenAI-compatible code from `_generate_local`
- Ollama code from `_generate_ollama`

Each adapter file should expose one function:

- `generate_openai_json(...)`
- `generate_gemini_json(...)`
- `generate_claude_json(...)`
- `generate_local_gateway_json(...)`
- `generate_ollama_json(...)`

and return:

```python
dict[str, Any] | tuple[dict[str, Any], dict[str, Any]]
```

### 3. Keep shared helpers in `job_agent/llm.py`

Do not move these yet:

- `_extract_json`
- `_usage_payload`
- role maps
- `provider_status()`

Those remain shared in `LLMRouter` for this phase.

### 4. Replace internal branches with adapter calls

For example, inside `generate_with_gemini(...)`, replace the body with a
delegation call to `generate_gemini_json(...)`.

The same pattern should be applied to OpenAI, Claude, Local Gateway, and
Ollama.

## Tests

Keep all existing provider tests passing.
Add at least one test that monkeypatches an adapter function and proves the
router delegates to it.

## Verification

Run:

```bash
pytest tests/test_llm_gemini.py tests/test_provider_cost_ux.py tests/test_provider_resilience.py -q
ruff check job_agent/llm.py job_agent/llm_adapters tests/test_llm_gemini.py tests/test_provider_cost_ux.py tests/test_provider_resilience.py
```

## Stop Conditions

Stop and report if:

- adapter extraction changes any public router signature
- usage payload behavior changes for existing tests
