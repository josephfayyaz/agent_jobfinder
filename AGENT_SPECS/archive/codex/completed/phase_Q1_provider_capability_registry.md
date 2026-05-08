# Phase Q1 — Provider Capability Registry

Status: pending

## Goal

Create one source of truth for provider capabilities so the app stops encoding
provider behavior implicitly inside `job_agent/llm.py`, `job_agent/routers/system.py`,
and workflow services.

## Write Scope

- `job_agent/providers.py`
- `job_agent/llm.py`
- `job_agent/routers/system.py`
- `tests/test_provider_resilience.py`

## Do Not Touch

- onboarding templates
- workflow services
- prompt text
- database models

## Exact Changes

### 1. Replace the current provider helper-only shape in `job_agent/providers.py`

Keep the existing readiness helpers, but add a capability registry above
`provider_readiness_snapshot()`.

Insert this block after `LEGACY_PROVIDER_PRIORITY`:

```python
PROVIDER_CAPABILITIES: dict[str, dict[str, Any]] = {
    "openai": {
        "label": "OpenAI",
        "supports_native_json": True,
        "supports_system_instruction": True,
        "supports_usage_metadata": True,
        "validation_probe": "live_generation",
        "workflow_prompt_char_limits": {
            "intake": 24_000,
            "jd_scoring": 18_000,
            "cv_writer": 20_000,
            "compliance_matrix": 18_000,
        },
    },
    "gemini": {
        "label": "Google Gemini",
        "supports_native_json": True,
        "supports_system_instruction": True,
        "supports_usage_metadata": True,
        "validation_probe": "live_generation",
        "workflow_prompt_char_limits": {
            "intake": 14_000,
            "jd_scoring": 16_000,
            "cv_writer": 18_000,
            "compliance_matrix": 16_000,
        },
    },
    "anthropic": {
        "label": "Claude",
        "supports_native_json": False,
        "supports_system_instruction": True,
        "supports_usage_metadata": True,
        "validation_probe": "models_list",
        "workflow_prompt_char_limits": {
            "intake": 22_000,
            "jd_scoring": 18_000,
            "cv_writer": 20_000,
            "compliance_matrix": 18_000,
        },
    },
    "lm_studio": {
        "label": "Local Gateway",
        "supports_native_json": False,
        "supports_system_instruction": False,
        "supports_usage_metadata": False,
        "validation_probe": "openai_chat_probe",
        "workflow_prompt_char_limits": {
            "intake": 12_000,
            "jd_scoring": 12_000,
            "cv_writer": 14_000,
            "compliance_matrix": 12_000,
        },
    },
    "ollama": {
        "label": "Ollama",
        "supports_native_json": False,
        "supports_system_instruction": False,
        "supports_usage_metadata": False,
        "validation_probe": "openai_chat_probe",
        "workflow_prompt_char_limits": {
            "intake": 10_000,
            "jd_scoring": 12_000,
            "cv_writer": 12_000,
            "compliance_matrix": 10_000,
        },
    },
}
```

### 2. Add these helpers at the end of `job_agent/providers.py`

```python
def provider_capabilities(mode: str | None = None) -> dict[str, Any]:
    normalized = normalize_provider_mode(mode or getattr(settings, "llm_provider_mode", "openai"))
    return dict(PROVIDER_CAPABILITIES.get(normalized) or PROVIDER_CAPABILITIES["openai"])


def provider_prompt_char_limit(workflow: str, mode: str | None = None, default: int = 12000) -> int:
    capabilities = provider_capabilities(mode)
    limits = dict(capabilities.get("workflow_prompt_char_limits") or {})
    return int(limits.get(workflow, default) or default)
```

### 3. Extend `provider_setup_status()`

Replace the return dict inside `provider_setup_status()` with:

```python
    return {
        "mode": mode,
        "configured": configured,
        "ready": ready,
        "capabilities": provider_capabilities(mode),
        **readiness,
    }
```

### 4. Use the registry in `job_agent/llm.py`

At the import block, change:

```python
from job_agent.providers import normalize_provider_mode, provider_setup_status
```

to:

```python
from job_agent.providers import (
    normalize_provider_mode,
    provider_capabilities,
    provider_setup_status,
)
```

Then remove any future hardcoded capability assumptions and read from:

```python
provider_capabilities(provider_mode)
```

Do not change runtime behavior yet except to make capability access available.

### 5. Expose registry values in `/providers`

In `job_agent/routers/system.py`, leave route names unchanged.
Do not redesign the response shape. Only ensure the existing `/providers`
payload already coming from `LLMRouter().provider_status()` is safe to extend
later using capability data.

No behavioral change is required in this phase beyond keeping compatibility.

## Tests

Add these exact tests to `tests/test_provider_resilience.py`:

```python
def test_provider_capabilities_returns_gemini_contract():
    from job_agent.providers import provider_capabilities

    payload = provider_capabilities("gemini")

    assert payload["label"] == "Google Gemini"
    assert payload["supports_native_json"] is True
    assert payload["workflow_prompt_char_limits"]["intake"] > 0


def test_provider_prompt_char_limit_uses_registry():
    from job_agent.providers import provider_prompt_char_limit

    assert provider_prompt_char_limit("intake", "gemini") == 14000
    assert provider_prompt_char_limit("cv_writer", "lm_studio") == 14000
```

## Verification

Run:

```bash
pytest tests/test_provider_resilience.py -q
ruff check job_agent/providers.py job_agent/llm.py job_agent/routers/system.py tests/test_provider_resilience.py
```

## Stop Conditions

Stop and report if:

- adding the capability payload breaks `/health/ai-status`
- any caller assumes `provider_setup_status()` contains only booleans

## Completion Handoff

When this phase is complete:

1. Move this spec to `AGENT_SPECS/archive/codex/completed/`
2. Write a completion report in `AGENT_SPECS/completed/`
3. Add a line to `completed_agent_specs.txt`:
   `phase_Q1_provider_capability_registry.md — COMPLETE — <timestamp> — added provider capability registry and prompt-limit helpers`
