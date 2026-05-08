# Phase Q5 — Prompt Mode Split

Status: pending

## Goal

Move the longest workflow instructions out of Python string literals and into
versioned resource files while keeping Python interpolation where necessary.

## Write Scope

- `job_agent/resources/prompts/` (new package folder)
- `job_agent/services/resource_loader.py`
- `job_agent/services/prompts.py`
- `tests/test_prompts.py` (new or existing prompt tests file)

## Do Not Touch

- onboarding JS
- route handlers
- DB models
- intake prompt pack in `job_agent/resources/fact_sheet`

## Exact Changes

### 1. Add a new resource package

Create:

- `job_agent/resources/prompts/__init__.py`
- `job_agent/resources/prompts/writer_system.md`
- `job_agent/resources/prompts/reviewer_system.md`
- `job_agent/resources/prompts/compliance_system.md`

### 2. Move only system prompts first

Do not move every prompt in one pass.

Move these functions out of inline string literals:

- `build_writer_system_prompt()`
- `build_reviewer_system_prompt()`
- `build_compliance_matrix_system_prompt()`

### 3. Update `resource_loader.py`

Add:

```python
_PROMPT_RESOURCE_PKG = "job_agent.resources.prompts"


def load_prompt_resource(filename: str) -> str:
    return files(_PROMPT_RESOURCE_PKG).joinpath(filename).read_text(encoding="utf-8")
```

### 4. Replace the three system-prompt builders

In `job_agent/services/prompts.py`, replace the body of each targeted builder
with `return load_prompt_resource("...").strip()`.

At the import block, add:

```python
from job_agent.services.resource_loader import load_prompt_resource
```

Do not move user-prompt builders in this phase.

## Tests

Add tests that assert:

- the loader returns non-empty prompt text
- the three builder functions still contain the expected marker phrases

## Verification

Run:

```bash
pytest tests/test_prompts.py -q
ruff check job_agent/services/resource_loader.py job_agent/services/prompts.py tests/test_prompts.py
```

## Stop Conditions

Stop and report if:

- prompt text references variables that cannot live outside Python
- moving the prompt changes current test expectations unexpectedly
