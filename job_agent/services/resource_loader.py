"""Load vendored fact sheet resource files via importlib.resources.

All code that needs the canonical schema, prompt pack, renderer spec, etc.
must use these helpers — never read from absolute filesystem paths at runtime.

The master_fact_sheet.txt is intentionally excluded; it is ingested via
POST /fact-sources/ingest, not loaded as a package resource.
"""

from __future__ import annotations

import json
import re
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

