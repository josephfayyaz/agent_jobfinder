# Phase Q6C — Gemini Adapter And Router Cleanup

Status: pending

## Goal

Extract the Gemini request path into its own adapter and finish the router
cleanup after `Q6A` and `Q6B` are already complete.

This is the highest-risk Q6 slice because Gemini has the most complex retry and
fallback behavior. Keep the scope tight.

## Preconditions

- `Q6A` is complete
- `Q6B` is complete

If either precondition is false, stop.

## Write Scope

- `job_agent/llm.py`
- `job_agent/llm_adapters/__init__.py`
- `job_agent/llm_adapters/gemini_adapter.py` (new)
- `tests/test_llm_gemini.py`
- `tests/test_provider_resilience.py`

## Do Not Touch

- provider capability registry from `Q1`
- provider error taxonomy from `Q2`
- smoke harness from `Q3`
- workflow input shaping from `Q4`
- prompt resource files from `Q5`
- service-layer call sites

## Exact Change Boundary

Move only the body of `LLMRouter.generate_with_gemini(...)` into an adapter
function, while keeping these helpers in `job_agent/llm.py`:

- `_gemini_api_url`
- `_gemini_text_from_response`
- `_gemini_body_preview`
- `_gemini_payload`
- `_gemini_size_or_context_issue`
- `_trim_prompt_for_retry`
- `_usage_payload`
- `ProviderUnavailableError`

Do not move those helpers in this phase. The adapter should call them via
injected callables.

## Required Adapter API

Create `job_agent/llm_adapters/gemini_adapter.py` and expose exactly:

```python
def generate_gemini_json(
    *,
    api_key: str,
    model: str,
    timeout_seconds: float,
    system_prompt: str,
    user_prompt: str,
    include_usage: bool,
    api_url_builder: Callable[[str], str],
    payload_builder: Callable[..., dict[str, Any]],
    text_from_response: Callable[[dict[str, Any]], str],
    body_preview: Callable[[httpx.Response], str],
    size_or_context_issue: Callable[[str], bool],
    trim_prompt_for_retry: Callable[[str], str],
    json_extractor: Callable[[str], dict[str, Any]],
    usage_builder: Callable[..., dict[str, Any]],
    provider_error_cls: type[Exception],
) -> dict[str, Any] | tuple[dict[str, Any], dict[str, Any]]:
    ...
```

Implementation rule:

- do not redefine Gemini helper logic inside the adapter
- call the injected helpers from `job_agent/llm.py`

## Router Wiring

In `job_agent/llm.py`:

1. import `generate_gemini_json`
2. keep the API-key presence check in `generate_with_gemini(...)`
3. replace the rest of the method body with a delegation call

After this phase, `job_agent/llm.py` should still own:

- public router methods
- routing branches
- shared helper functions
- provider status methods
- client construction

## Required Tests

Add:

1. a delegation test in `tests/test_provider_resilience.py` that monkeypatches
   `job_agent.llm.generate_gemini_json`
2. at least one regression test in `tests/test_llm_gemini.py` proving the
   adapter path still preserves:
   - plain-text retry on `responseMimeType` rejection, or
   - trimmed retry on oversized/context failures

## Verification

Run:

```bash
pytest tests/test_llm_gemini.py tests/test_provider_resilience.py tests/test_provider_cost_ux.py -q
ruff check job_agent/llm.py job_agent/llm_adapters/gemini_adapter.py tests/test_llm_gemini.py tests/test_provider_resilience.py tests/test_provider_cost_ux.py
```

## Stop Conditions

Stop and report if:

- Gemini helper extraction starts moving shared helper functions out of `job_agent/llm.py`
- retry semantics change in existing Gemini tests
- the adapter requires changes to provider capability or provider error modules

## Completion Handoff

When this phase is complete:

1. Move this spec to `AGENT_SPECS/archive/codex/completed/`
2. Write a completion report in `AGENT_SPECS/completed/`
3. Add a line to `completed_agent_specs.txt`:
   `phase_Q6C_gemini_adapter_and_router_cleanup.md — COMPLETE — <timestamp> — extracted Gemini request logic into an adapter and completed router cleanup without changing public contracts`
