# Spec: Phase 1.2 — Add Anthropic SDK Dependency
Status: pending

## Context
`llm.py` already has `generate_with_claude()` which imports `anthropic` at runtime.
The `anthropic` package is not yet in `pyproject.toml`. This spec adds it and
verifies the import works cleanly.

## Changes

### File: `pyproject.toml`
#### Change 1: Add anthropic to dependencies
Find the `dependencies` list (it has fastapi, uvicorn, sqlalchemy, etc.) and add:

BEFORE (last line of dependencies list):
```
    "openai>=1.68,<2",
```
AFTER:
```
    "openai>=1.68,<2",
    "anthropic>=0.49,<1",
```

## Installation
After editing pyproject.toml, run:
```bash
/Users/youseffayyaz/miniforge3/bin/conda run -n ML pip install -e ".[dev]"
```

## Verification
```bash
/Users/youseffayyaz/miniforge3/bin/conda run -n ML python -c "import anthropic; print(anthropic.__version__)"
# Expected: prints a version like 0.49.x or higher

/Users/youseffayyaz/miniforge3/bin/conda run -n ML python -m ruff check job_agent/
# Expected: no errors
```

## Git
```bash
git add pyproject.toml
git commit -m "feat: add anthropic SDK dependency

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```
