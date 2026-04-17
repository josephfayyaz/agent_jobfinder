# Phase 1.4.0 — Vendor Fact Sheet Resources into Project

## Goal

Runtime code must never read from `/Users/youseffayyaz/Polito/Resume-CV/fact_sheet/` (a
user-local path outside the repo). The canonical files needed at runtime — schema, prompt
pack, tool spec, renderer spec, renderer prompt, render template — are copied into the project
at `job_agent/resources/fact_sheet/` and loaded via `importlib.resources`.

**The `master_fact_sheet.txt` is NOT copied.** It stays at the canonical path and continues
to be ingested via the existing `POST /fact-sources/ingest` endpoint, exactly as today.

## Dependencies

No new pip packages. Uses Python stdlib `importlib.resources` (Python ≥ 3.9).

## Steps

### 1. Create `job_agent/resources/fact_sheet/`

```
mkdir -p job_agent/resources/fact_sheet
touch job_agent/resources/__init__.py
touch job_agent/resources/fact_sheet/__init__.py
```

### 2. Copy resource files (read from source, write to destination)

Source directory: `/Users/youseffayyaz/Polito/Resume-CV/fact_sheet/`

Files to copy:

| Source filename | Destination (in `job_agent/resources/fact_sheet/`) |
|-----------------|-----------------------------------------------------|
| `fact_sheet_schema.json` | `fact_sheet_schema.json` |
| `claude_fact_sheet_prompt_pack.md` | `claude_fact_sheet_prompt_pack.md` |
| `claude_tool_calling_spec.md` | `claude_tool_calling_spec.md` |
| `claude_tool_definitions_example.json` | `claude_tool_definitions_example.json` |
| `fact_sheet_renderer_spec.md` | `fact_sheet_renderer_spec.md` |
| `fact_sheet_renderer_prompt.txt` | `fact_sheet_renderer_prompt.txt` |
| `master_fact_sheet_render_template.txt` | `master_fact_sheet_render_template.txt` |

Do NOT copy `master_fact_sheet.txt` — it is the user's canonical source of truth and must
remain untouched at its original location.

### 3. Add package-data entry in `pyproject.toml`

Under `[tool.setuptools.package-data]`:

```toml
[tool.setuptools.package-data]
"job_agent" = ["resources/fact_sheet/*"]
```

### 4. New file: `job_agent/services/resource_loader.py`

```python
"""Load vendored fact sheet resource files via importlib.resources.

All code that needs the canonical schema, prompt pack, renderer spec, etc.
must use these helpers — never read from absolute filesystem paths at runtime.

The master_fact_sheet.txt is intentionally excluded; it is ingested via
POST /fact-sources/ingest, not loaded as a package resource.
"""

from __future__ import annotations

import json
from importlib.resources import files


_RESOURCE_PKG = "job_agent.resources.fact_sheet"


def load_fact_sheet_resource(filename: str) -> str:
    """Return the text content of a vendored fact_sheet resource file."""
    return files(_RESOURCE_PKG).joinpath(filename).read_text(encoding="utf-8")


def load_fact_sheet_schema() -> dict:
    """Return the canonical JSON Schema as a parsed dict."""
    return json.loads(load_fact_sheet_resource("fact_sheet_schema.json"))


def load_tool_definitions() -> list[dict]:
    """Return the Anthropic-format tool definitions as a list."""
    return json.loads(load_fact_sheet_resource("claude_tool_definitions_example.json"))


def load_prompt_pack() -> str:
    """Return the full claude_fact_sheet_prompt_pack.md text."""
    return load_fact_sheet_resource("claude_fact_sheet_prompt_pack.md")


def extract_prompt_section(pack_text: str, prompt_number: int) -> str:
    """
    Extract a numbered prompt block from the prompt pack markdown.
    Looks for markers like '## Prompt 1', '## Prompt 2', etc.
    Returns the text between that marker and the next '## Prompt N' or EOF.
    """
    import re
    pattern = rf"## Prompt {prompt_number}\b(.*?)(?=## Prompt \d|\Z)"
    match = re.search(pattern, pack_text, re.S)
    if not match:
        raise ValueError(f"Prompt {prompt_number} not found in prompt pack")
    return match.group(1).strip()


def load_renderer_spec() -> str:
    """Return the fact_sheet_renderer_spec.md text."""
    return load_fact_sheet_resource("fact_sheet_renderer_spec.md")


def load_renderer_prompt() -> str:
    """Return the fact_sheet_renderer_prompt.txt text."""
    return load_fact_sheet_resource("fact_sheet_renderer_prompt.txt")


def load_render_template() -> str:
    """Return the master_fact_sheet_render_template.txt text (golden shape)."""
    return load_fact_sheet_resource("master_fact_sheet_render_template.txt")
```

## Tests

### `tests/test_resource_loader.py`

```python
def test_load_fact_sheet_schema_returns_valid_jsonschema():
    from job_agent.services.resource_loader import load_fact_sheet_schema
    schema = load_fact_sheet_schema()
    assert isinstance(schema, dict)
    # A JSON Schema always has either "$schema" or "properties" or "type"
    assert any(k in schema for k in ("$schema", "properties", "type", "definitions"))


def test_load_prompt_pack_contains_prompt_1_header():
    from job_agent.services.resource_loader import load_prompt_pack
    pack = load_prompt_pack()
    assert "Prompt 1" in pack or "prompt 1" in pack.lower()


def test_load_renderer_spec_is_nonempty():
    from job_agent.services.resource_loader import load_renderer_spec
    spec = load_renderer_spec()
    assert len(spec) > 100  # at minimum a non-trivial document


def test_extract_prompt_section_returns_nonempty_text():
    from job_agent.services.resource_loader import load_prompt_pack, extract_prompt_section
    pack = load_prompt_pack()
    section = extract_prompt_section(pack, 1)
    assert len(section) > 10


def test_load_render_template_nonempty():
    from job_agent.services.resource_loader import load_render_template
    template = load_render_template()
    assert len(template) > 100
```

## Commit Message
```
chore(resources): vendor fact_sheet schema, prompt pack, and renderer spec into project resources (Phase 1.4.0)
```
