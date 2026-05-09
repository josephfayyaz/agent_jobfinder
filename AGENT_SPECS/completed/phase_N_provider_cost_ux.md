# Phase N — Provider Cost UX

Status: complete  
Completed: 2026-05-07

## Outcome

Token usage tracking and a cloud-only pipeline guardrail were added without
changing the existing `LLMRouter.generate()` contract.

New behavior:

- `LLMRouter.generate_with_usage()`
- `LLMRouter.generate_with_retry_usage()`
- workflow-local token accumulation in `CVWorkflowService`
- optional cloud token budget via `MAX_PIPELINE_TOKENS`
- draft detail token usage display when metadata is present

## Real Usage Coverage

- OpenAI: real usage captured
- Anthropic: real usage captured
- Gemini: real usage captured from `usageMetadata` when present
- LM Studio / Ollama: explicit zero-token usage

## Key Files

- `job_agent/llm.py`
- `job_agent/config.py`
- `job_agent/services/workflows.py`
- `frontend/templates/draft_detail.html`

## Verification

- `tests/test_provider_cost_ux.py`
- `tests/test_ui_draft_detail.py`
- `tests/test_workflows.py`
- combined final suite: `71 passed`
