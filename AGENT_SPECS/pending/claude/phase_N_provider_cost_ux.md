# Phase N — Provider Cost UX and Pipeline Budget Guardrail

## Priority
MEDIUM — can be implemented independently of phases K, L, M. No frontend dependencies.
Touches `llm.py`, `workflows.py`, `config.py`, and `draft_detail.html`.

## Purpose

When using cloud providers (OpenAI, Anthropic, Gemini), there is currently no visibility into
how many tokens a CV pipeline consumed or what it cost. A user could unknowingly run many
expensive pipeline passes without feedback.

This spec adds:
1. Token-usage tracking in `LLMRouter.generate()` — every call returns its token count
2. Accumulation of per-pass token counts in the CV workflow
3. A configurable hard budget that aborts the pipeline if exceeded
4. A lightweight token-usage pill in the draft detail UI

---

## Global Constraints (READ THESE FIRST)

1. **Python environment:** `conda run -n ML` for all runs. Never create a venv.
2. **`LLMRouter.generate()` raises TWO exception types** — all call sites must still catch
   both `ProviderUnavailableError` AND `ValueError`. Do not change exception behaviour.
3. **`generate()` signature change is breaking.** Every call site in the codebase must be
   updated to unpack the new tuple return. Run the grep in Step 1 before writing any code.
4. **Local providers return `0` tokens.** LM Studio and Ollama responses do not expose
   reliable billing usage; return `0` for them — do not estimate.
5. **Starlette TemplateResponse** requires keyword args:
   `TemplateResponse(request=request, name="x.html", context={...})`. Do not use positional args.
6. **No Alembic.** If a new column is needed on `WorkflowTask`, add it via
   `ALTER TABLE workflow_tasks ADD COLUMN IF NOT EXISTS ...` in `db.py`'s `prepare_database()`.
7. **Test with mocks.** Do not make live API calls in tests.

---

## Step 1 — Audit all `generate()` call sites

Before changing anything, run:

```bash
grep -rn "\.generate(" job_agent/ --include="*.py" | grep -v "__pycache__" | grep -v "test_"
```

Save this list. Every file listed must be updated in Step 3. Count the call sites — include
that count in the completion report.

Also run for `generate_with_retry`:

```bash
grep -rn "generate_with_retry\|generate_with_claude\|generate_with_openai\|generate_with_gemini" \
  job_agent/ --include="*.py" | grep -v "__pycache__" | grep -v "test_"
```

---

## Step 2 — Update `job_agent/llm.py`

### 2a — Change `generate()` return type

Find the `generate()` method in the `LLMRouter` class. Change its return from `str` to
`tuple[str, int]` where the second element is `tokens_used: int`.

**BEFORE** (simplified pattern — read the actual file for exact code):
```python
def generate(self, role: str, system_prompt: str, user_prompt: str, ...) -> str:
    ...
    text = self._generate_local(...)
    return text
```

**AFTER:**
```python
def generate(self, role: str, system_prompt: str, user_prompt: str, ...) -> tuple[str, int]:
    ...
    text, tokens = self._generate_local(...)
    return text, tokens
```

### 2b — Update each private provider method to return `(text, tokens)`

Update ALL private generation methods to return a `(str, int)` tuple:

- `_generate_local()` / `_call_lm_studio()` — return `(text, 0)` (no billing)
- `_generate_ollama()` (if exists) — return `(text, 0)`
- `generate_with_openai()` — parse `response["usage"]["total_tokens"]`; return `(text, tokens)`
- `generate_with_claude()` — parse `response.usage.input_tokens + response.usage.output_tokens`;
  return `(text, tokens)`
- `generate_with_gemini()` — parse `response["usageMetadata"]["totalTokenCount"]` if present,
  else `0`; return `(text, tokens)`

For each provider, read the actual response object structure in the existing code to find
where the response is parsed — add the token extraction there.

### 2c — Update `generate_with_retry()` if it exists

If there is a retry wrapper, update it to propagate the `(text, tokens)` tuple from the
underlying call.

### 2d — Type annotation

Add/update the return type annotation:
```python
def generate(...) -> tuple[str, int]:
```

---

## Step 3 — Update all call sites

For every file identified in Step 1, change the call pattern:

**BEFORE:**
```python
text = self.router.generate(role="writer", system_prompt=..., user_prompt=...)
```

**AFTER** (when tokens are needed — in workflows.py):
```python
text, tokens = self.router.generate(role="writer", system_prompt=..., user_prompt=...)
```

**AFTER** (when tokens are not needed — all other services):
```python
text, _ = self.router.generate(role="writer", system_prompt=..., user_prompt=...)
```

Only `services/workflows.py` needs to capture the token count. All other call sites
use `text, _ = ...`.

---

## Step 4 — Accumulate tokens in `job_agent/services/workflows.py`

Find the main CV pipeline method (likely `run_cv_workflow()` or `_process_cv_task()`).
Add token accumulation:

```python
# At the start of the pipeline method:
token_totals = {"writer": 0, "reviewer": 0, "reviser": 0}

# After each LLM call, accumulate:
draft_text, tokens = self.router.generate(role="writer", ...)
token_totals["writer"] += tokens

review_text, tokens = self.router.generate(role="small", ...)   # reviewer uses small
token_totals["reviewer"] += tokens

# (similarly for reviser passes)

# At the end, before storing the task result, add:
token_totals["total"] = sum(token_totals.values())
token_totals["provider"] = settings.llm_provider_mode

# Store in task result (merge with whatever result dict already exists):
result["token_usage"] = token_totals
```

Read `workflows.py` carefully — the exact method names and result structure may differ.
Adapt this pattern to the actual code; do not restructure the whole method.

---

## Step 5 — Add budget config in `job_agent/config.py`

Find the `Settings` class. Add one new field after the existing CV workflow fields:

```python
# Maximum total tokens allowed across a single CV pipeline run (writer + reviewer + reviser).
# Set to 0 to disable the limit. Only applies to cloud providers.
max_pipeline_tokens: int = 50_000
```

---

## Step 6 — Enforce budget in `workflows.py`

After each LLM call that accumulates tokens, check the budget:

```python
running_total = sum(token_totals.values())
if (
    settings.max_pipeline_tokens > 0
    and running_total > settings.max_pipeline_tokens
    and settings.llm_provider_mode not in ("lm_studio", "ollama")
):
    raise ValueError(
        f"Pipeline budget exceeded: {running_total} tokens used "
        f"(limit: {settings.max_pipeline_tokens}). "
        "Increase max_pipeline_tokens in settings or switch to a local provider."
    )
```

The `ValueError` will be caught by the worker's existing error handler and stored as the
task error message — no new exception type is needed.

---

## Step 7 — UI: token usage pill in `frontend/templates/draft_detail.html`

Find the section that displays the draft score badge (look for `score`, `approved`, or the
draft metadata header area). After the score badge, add a token usage pill that is only
shown when token data exists:

```html
<!-- Token usage pill — shown only for cloud-provider drafts -->
{% if task and task.result and task.result.get('token_usage') and task.result['token_usage'].get('total', 0) > 0 %}
<span class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium
             bg-yellow-50 text-yellow-800 border border-yellow-200"
      title="Tokens used: writer={{ task.result.token_usage.writer }}, reviewer={{ task.result.token_usage.reviewer }}, reviser={{ task.result.token_usage.reviser }}">
  ~{{ (task.result.token_usage.total // 1000) }}k tokens
  ({{ task.result.token_usage.provider | default('cloud') }})
</span>
{% endif %}
```

Read `draft_detail.html` to find the exact location and class style used for existing badges,
then match that style.

**Note:** `task` may not be directly available in the template context for all draft views.
Check what variables are passed from the router. If the task result is not in scope, add
`token_usage` to the `ResumeDraft` metadata or pass it via the route context — whichever
matches the existing pattern.

---

## Tests to write

Create `tests/test_provider_cost_ux.py`:

```python
"""
Tests for provider cost UX: token tracking, budget enforcement, and UI display.
"""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path


# ── LLMRouter token return ────────────────────────────────────────────────────

def test_generate_returns_tuple(tmp_path):
    """generate() must return (str, int) not just str."""
    from job_agent.llm import LLMRouter
    router = LLMRouter.__new__(LLMRouter)
    # Minimal mock: patch _call_lm_studio to return a tuple
    with patch.object(router, "_call_lm_studio", return_value=("hello", 0)):
        with patch.object(router, "_route_to_provider", return_value=("hello", 0)):
            # Adjust the mock target to match the actual dispatch method name
            pass
    # Primary assertion: the return type is tuple
    # (Full implementation test is in test_llm_gemini.py and similar)


def test_openai_provider_parses_tokens():
    """OpenAI response usage.total_tokens must be captured."""
    from job_agent.llm import LLMRouter
    mock_response = {
        "choices": [{"message": {"content": '{"result": "ok"}'}}],
        "usage": {"total_tokens": 1234, "prompt_tokens": 800, "completion_tokens": 434}
    }
    router = LLMRouter.__new__(LLMRouter)
    # Call the openai response parser directly if it's a standalone method,
    # or use a full mock of the HTTP call.
    # Adapt this test to the actual code structure in llm.py.
    # The key assertion:
    assert mock_response["usage"]["total_tokens"] == 1234


def test_local_provider_returns_zero_tokens():
    """LM Studio and Ollama must return 0 tokens (no billing)."""
    # Read llm.py and find the LM Studio response path.
    # Assert that the returned token count is 0 for local responses.
    # Implement as a unit test using mocked httpx responses.
    pass  # Replace with real implementation after reading llm.py


# ── Budget guardrail ──────────────────────────────────────────────────────────

def test_budget_exceeded_raises_value_error(db_session, settings_override):
    """Pipeline must fail with ValueError when token budget is exceeded."""
    from job_agent.services.workflows import CVWorkflowService
    from job_agent.config import settings

    # Set a tiny budget
    with patch.object(settings, "max_pipeline_tokens", 10):
        with patch.object(settings, "llm_provider_mode", "openai"):
            # Mock generate() to return a large token count
            service = CVWorkflowService.__new__(CVWorkflowService)
            service.router = MagicMock()
            service.router.generate.return_value = ("draft text", 500)  # exceeds budget of 10

            with pytest.raises(ValueError, match="budget exceeded"):
                # Call the pipeline method — adapt name to actual method in workflows.py
                pass  # Replace with actual call after reading workflows.py


def test_budget_not_enforced_for_local_providers(db_session):
    """Budget check must be skipped when using local providers."""
    from job_agent.config import settings
    with patch.object(settings, "max_pipeline_tokens", 1):  # impossibly small
        with patch.object(settings, "llm_provider_mode", "lm_studio"):
            # Local provider returns 0 tokens — should never trigger budget error
            # Implement after reading workflows.py
            pass


# ── Config field ──────────────────────────────────────────────────────────────

def test_max_pipeline_tokens_in_settings():
    """max_pipeline_tokens must be a configurable setting with a default."""
    from job_agent.config import settings
    assert hasattr(settings, "max_pipeline_tokens"), (
        "Settings must have max_pipeline_tokens field"
    )
    assert isinstance(settings.max_pipeline_tokens, int)
    assert settings.max_pipeline_tokens >= 0


# ── UI: token pill in draft_detail.html ──────────────────────────────────────

def test_draft_detail_has_token_usage_pill():
    """draft_detail.html must contain the token usage conditional block."""
    template = Path("frontend/templates/draft_detail.html").read_text()
    assert "token_usage" in template, (
        "draft_detail.html must render token usage when present in task result"
    )

def test_token_pill_is_conditional():
    """Token pill must not appear when token_usage is absent or zero."""
    template = Path("frontend/templates/draft_detail.html").read_text()
    # The block must be inside an if-condition, not unconditional
    assert "{% if" in template and "token_usage" in template, (
        "token_usage display must be inside a Jinja {% if %} block"
    )
```

---

## Verification

```bash
conda run -n ML pytest tests/test_provider_cost_ux.py -v
conda run -n ML pytest tests/ -x -q 2>&1 | tail -5
```

All tests must pass. Fix any `todo` / `pass` placeholders in the test file after reading
the actual `llm.py` and `workflows.py` implementations.

---

## Completion Steps (do these in order after all tests pass)

1. **Write a completion report** at `AGENT_SPECS/completed/phase_N_provider_cost_ux.md`
   using `AGENT_SPECS/completed/REPORT_TEMPLATE.md`. Include:
   - Total number of `generate()` call sites updated (from Step 1 audit)
   - Which provider response fields were used for token counts (OpenAI / Anthropic / Gemini)
   - Whether `token_usage` was stored on `WorkflowTask.result` or elsewhere
   - Test result (pass count)
   - Any deviations from this spec

2. **Append to log:**
   ```
   phase_N_provider_cost_ux — 2026-05-XX
   ```
   at the bottom of `completed_agent_specs.txt`.

3. **Move this spec file** from `AGENT_SPECS/pending/claude/` to `AGENT_SPECS/archive/claude/completed/`.
