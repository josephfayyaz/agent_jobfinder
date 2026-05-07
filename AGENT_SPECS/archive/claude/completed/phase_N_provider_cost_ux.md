# Phase N — Token Usage Visibility and Pipeline Budget Guardrail

## Priority
Medium.

This phase may be implemented independently of K, L, and M.

## Goal

Add token-usage visibility and a configurable per-pipeline budget guardrail for
cloud providers without breaking the current `LLMRouter.generate()` contract.

## Why this spec was rewritten

The older version assumed `LLMRouter.generate()` returned plain text and proposed
a breaking repo-wide signature change. That is unsafe for the real codebase and
too risky for a local `aider` + Qwen 3.5 27B implementation pass.

This version is intentionally safer:

- keep `generate()` backward-compatible
- add a new opt-in usage-aware path
- update only the workflow layer that actually needs token accounting

## Aider-Safe Constraints

1. Do not change the return type of `LLMRouter.generate()`.
2. Do not update every router/service call site in the repo.
3. Local providers must report zero tokens unless real usage is already exposed.
4. Do not hardcode dollar prices from provider marketing pages in this phase.
5. Keep write scope to at most:
   - `job_agent/llm.py`
   - `job_agent/config.py`
   - `job_agent/services/workflows.py`
   - one UI template or route-context file if needed for display
   - new tests
6. Preserve current exception behavior:
   - `ProviderUnavailableError`
   - `ValueError`

## Do Not Touch

- unrelated service call sites
- onboarding flow
- provider validation routes unless needed for test support
- database schema unless there is no existing place to store token usage

## Mandatory Audit First

Run:

```bash
rg -n "\\.generate\\(|generate_with_retry\\(" job_agent --glob "*.py"
```

Then inspect:

- `job_agent/llm.py`
- `job_agent/services/workflows.py`
- the draft detail route/template that currently exposes workflow metadata

Write down:

- where provider responses already expose usage
- where workflow results are already stored
- whether draft detail already has access to task result metadata

## Required Design

### N1 — Keep `generate()` unchanged

`LLMRouter.generate()` must continue returning the parsed payload that current
callers expect.

### N2 — Add a new usage-aware method

Add a new method in `job_agent/llm.py`, for example:

```python
def generate_with_usage(...) -> tuple[dict[str, Any], dict[str, Any]]:
    ...
```

The second tuple item should be a small usage dict, for example:

```python
{
    "provider": "openai",
    "tokens": 1234,
    "input_tokens": 800,
    "output_tokens": 434,
}
```

If exact input/output counts are unavailable, use:

```python
{
    "provider": "...",
    "tokens": total_or_zero,
}
```

### N3 — Provider-specific usage handling

Use real provider response usage only where already available:

- OpenAI: use response usage fields
- Anthropic: use response usage fields
- Gemini: use `usageMetadata` if present
- LM Studio / Ollama: return zero unless the current response already exposes reliable totals

Do not estimate token usage heuristically in this phase.

### N4 — Workflow-only accumulation

Update only `job_agent/services/workflows.py` to call the new usage-aware method.

Other services should keep using `generate()`.

Accumulate a workflow-local structure such as:

```python
token_usage = {
    "provider": settings.llm_provider_mode,
    "writer": 0,
    "reviewer": 0,
    "reviser": 0,
    "total": 0,
}
```

### N5 — Configurable budget limit

Add a config field in `job_agent/config.py`:

- `max_pipeline_tokens`

Only enforce it for cloud providers.

If exceeded during the workflow, raise a `ValueError` with a clear message.

### N6 — UI display only if data is already available

Add a small token usage pill or metadata line to the draft detail UI only if the
current route already has access to workflow result metadata.

If it does not, use the least invasive current storage path already used by the
workflow, such as `review_feedback` or task result payload.

Do not introduce a broad new persistence scheme in this phase.

## Implementation Steps

1. audit response usage fields in `llm.py`
2. add `generate_with_usage()`
3. keep `generate()` as a wrapper or parallel path
4. update only `workflows.py`
5. add `max_pipeline_tokens` to config
6. surface token usage in the draft detail path if context already supports it

## Tests

Create:

- `tests/test_provider_cost_ux.py`

### Minimum assertions

1. usage-aware generation returns payload plus usage dict
2. OpenAI usage is captured from mocked response
3. Gemini usage is captured from mocked response when present
4. local providers report zero
5. workflow accumulation totals tokens correctly
6. budget limit raises `ValueError` when exceeded

Prefer mocked unit tests. No live provider calls.

## Verification

Run:

```bash
/Users/youseffayyaz/miniforge3/envs/ML/bin/python -m pytest \
  tests/test_provider_cost_ux.py -q
```

Then run the workflow-related existing tests that touch drafting:

```bash
/Users/youseffayyaz/miniforge3/envs/ML/bin/python -m pytest \
  tests/test_api.py \
  tests/test_ui_draft_detail.py \
  tests/test_cv_phase_f.py -q
```

Then:

```bash
/Users/youseffayyaz/miniforge3/envs/ML/bin/python -m ruff check job_agent tests/test_provider_cost_ux.py tests/test_api.py tests/test_ui_draft_detail.py tests/test_cv_phase_f.py
```

## Stop Conditions

Stop and scale down if:

- adding UI display requires broad route-context refactors
- token usage is unavailable for a provider and no clean fallback exists
- preserving `generate()` while adding usage proves more invasive than expected

In that case, ship:

- usage-aware method
- workflow accumulation
- budget enforcement

and leave UI display for a follow-up spec.

## Completion

After implementation:

1. write `AGENT_SPECS/completed/phase_N_provider_cost_ux.md`
2. record:
   - which providers expose real usage
   - where token usage is stored
   - whether UI display shipped or was deferred
   - tests run
3. append to `completed_agent_specs.txt`
