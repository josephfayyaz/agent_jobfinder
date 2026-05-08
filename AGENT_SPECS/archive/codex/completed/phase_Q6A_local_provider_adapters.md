# Phase Q6A — Local Provider Adapters

Status: pending

## Goal

Extract only the local-provider generation paths from `job_agent/llm.py` into a
small adapter module while preserving `LLMRouter` public behavior.

This phase is intentionally narrow. Do not touch OpenAI, Claude, or Gemini in
this phase.

## Write Scope

- `job_agent/llm.py`
- `job_agent/llm_adapters/__init__.py` (new)
- `job_agent/llm_adapters/local_provider_adapter.py` (new)
- `tests/test_provider_resilience.py`

## Read-Only Reference Files

- `job_agent/providers.py`
- `job_agent/provider_errors.py`
- `tests/test_llm_gemini.py`

## Do Not Touch

- `job_agent/services/`
- route files
- prompt resource files
- OpenAI, Claude, or Gemini request code
- `LLMRouter.generate()` signature
- `LLMRouter.generate_with_usage()` signature

## Exact Change Boundary

Move only these internals behind adapter functions:

1. the body of `LLMRouter._generate_local(...)`
2. the body of `LLMRouter._generate_ollama(...)`
3. the shared request transport currently implemented by
   `LLMRouter._call_lm_studio(...)`

Keep these inside `job_agent/llm.py`:

- `ProviderUnavailableError`
- `_usage_payload`
- `_extract_json`
- `_repair_json_closers`
- provider routing in `generate(...)`
- cloud-provider methods
- `provider_status()`

## Required Adapter API

Create `job_agent/llm_adapters/local_provider_adapter.py` with exactly these
top-level functions:

```python
def generate_local_gateway_json(
    *,
    role: str,
    role_map: dict[str, tuple[str, str]],
    settings_obj: Any,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    include_usage: bool,
    json_extractor: Callable[[str], dict[str, Any]],
    usage_builder: Callable[..., dict[str, Any]],
    provider_error_cls: type[Exception],
) -> dict[str, Any] | tuple[dict[str, Any], dict[str, Any]]:
    ...

def generate_ollama_json(
    *,
    role: str,
    role_map: dict[str, tuple[str, str]],
    ollama_role_map: dict[str, str],
    settings_obj: Any,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    include_usage: bool,
    json_extractor: Callable[[str], dict[str, Any]],
    usage_builder: Callable[..., dict[str, Any]],
    provider_error_cls: type[Exception],
) -> dict[str, Any] | tuple[dict[str, Any], dict[str, Any]]:
    ...
```

Implementation note:

- put the low-level HTTP transport into a private helper inside this adapter
  file, for example `_call_openai_compatible_local(...)`
- do not expose that helper publicly

## Router Wiring

In `job_agent/llm.py`:

1. import the two adapter functions
2. replace the body of `_generate_local(...)` with a delegation call
3. replace the body of `_generate_ollama(...)` with a delegation call
4. delete the old `_call_lm_studio(...)` method only after both delegations are
   working and tests pass

## Required Tests

Add at least two delegation tests to `tests/test_provider_resilience.py`:

1. monkeypatch `job_agent.llm.generate_local_gateway_json` and assert
   `_generate_local(...)` returns that patched value
2. monkeypatch `job_agent.llm.generate_ollama_json` and assert
   `_generate_ollama(...)` returns that patched value

Also keep the existing provider-resilience tests passing unchanged.

## Verification

Run:

```bash
pytest tests/test_provider_resilience.py -q
ruff check job_agent/llm.py job_agent/llm_adapters/local_provider_adapter.py tests/test_provider_resilience.py
```

## Stop Conditions

Stop and report if:

- this phase requires changing any public `LLMRouter` signature
- cloud-provider methods need to be edited for imports or shared logic
- prompt shaping or provider capability logic appears coupled to this adapter

## Completion Handoff

When this phase is complete:

1. Move this spec to `AGENT_SPECS/archive/codex/completed/`
2. Write a completion report in `AGENT_SPECS/completed/`
3. Add a line to `completed_agent_specs.txt`:
   `phase_Q6A_local_provider_adapters.md — COMPLETE — <timestamp> — extracted local gateway and Ollama generation into a shared local-provider adapter`
