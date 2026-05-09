# Phase Q6B — OpenAI And Claude Adapters

Status: pending

## Goal

Extract the OpenAI and Claude request bodies from `job_agent/llm.py` into thin
cloud adapter modules while preserving the `LLMRouter` public contract and
current error behavior.

This phase assumes `Q6A` is already complete.

## Write Scope

- `job_agent/llm.py`
- `job_agent/llm_adapters/__init__.py`
- `job_agent/llm_adapters/openai_adapter.py` (new)
- `job_agent/llm_adapters/claude_adapter.py` (new)
- `tests/test_provider_resilience.py`

## Do Not Touch

- Gemini code
- local gateway / Ollama adapter code from `Q6A`
- prompt resource files
- service-layer call sites
- `job_agent/services/`
- `LLMRouter.generate()` signature

## Exact Change Boundary

Move only these method bodies behind adapter functions:

1. `LLMRouter.generate_with_openai(...)`
2. `LLMRouter.generate_with_claude(...)`

Keep these inside `job_agent/llm.py`:

- client construction in `LLMRouter.__init__`
- provider routing in `generate(...)`
- `_usage_payload`
- `ProviderUnavailableError`
- local-provider methods or delegations from `Q6A`
- Gemini helpers and Gemini method

## Required Adapter API

Create:

- `job_agent/llm_adapters/openai_adapter.py`
- `job_agent/llm_adapters/claude_adapter.py`

Expose exactly:

```python
def generate_openai_json(
    *,
    client: Any,
    model: str,
    system_prompt: str,
    user_prompt: str,
    timeout_seconds: float,
    include_usage: bool,
    json_extractor: Callable[[str], dict[str, Any]],
    usage_builder: Callable[..., dict[str, Any]],
    provider_error_cls: type[Exception],
) -> dict[str, Any] | tuple[dict[str, Any], dict[str, Any]]:
    ...

def generate_claude_json(
    *,
    client: Any,
    model: str,
    system_prompt: str,
    user_prompt: str,
    include_usage: bool,
    json_extractor: Callable[[str], dict[str, Any]],
    usage_builder: Callable[..., dict[str, Any]],
    provider_error_cls: type[Exception],
) -> dict[str, Any] | tuple[dict[str, Any], dict[str, Any]]:
    ...
```

## Router Wiring

In `job_agent/llm.py`:

1. import the two adapter functions
2. replace the body of `generate_with_openai(...)` with a delegation call
3. replace the body of `generate_with_claude(...)` with a delegation call
4. keep the existing auth prechecks in `job_agent/llm.py` before delegation

Important:

- the OpenAI quota/rate-limit mapping must stay behaviorally identical
- Claude usage payload extraction must stay behaviorally identical

## Required Tests

Add delegation tests in `tests/test_provider_resilience.py`:

1. monkeypatch `job_agent.llm.generate_openai_json` and assert
   `generate_with_openai(...)` delegates and returns the patched payload
2. monkeypatch `job_agent.llm.generate_claude_json` and assert
   `generate_with_claude(...)` delegates and returns the patched payload

Keep all existing OpenAI/Claude-related tests passing.

## Verification

Run:

```bash
pytest tests/test_provider_resilience.py tests/test_provider_cost_ux.py -q
ruff check job_agent/llm.py job_agent/llm_adapters/openai_adapter.py job_agent/llm_adapters/claude_adapter.py tests/test_provider_resilience.py tests/test_provider_cost_ux.py
```

## Stop Conditions

Stop and report if:

- adapter extraction forces changes to `LLMRouter.__init__`
- OpenAI or Claude auth checks must move out of `job_agent/llm.py`
- quota mapping behavior changes in existing tests

## Completion Handoff

When this phase is complete:

1. Move this spec to `AGENT_SPECS/archive/codex/completed/`
2. Write a completion report in `AGENT_SPECS/completed/`
3. Add a line to `completed_agent_specs.txt`:
   `phase_Q6B_openai_claude_adapters.md — COMPLETE — <timestamp> — extracted OpenAI and Claude request bodies into thin cloud adapters`
