# AGENT_SPECS — Implementation Handoff Specs

This directory contains precise, self-contained implementation briefs that can be
handed to any coding agent (Codex, Claude Code, Copilot, etc.) for execution.

## Workflow

1. **Claude Code** (architect role): analyzes requirements, designs the solution,
   writes a spec file here with exact file paths and code changes.
2. **Codex** (implementer role): reads the spec, applies the changes, runs tests.
3. **Claude Code** (reviewer role): verifies correctness, approves or requests fixes.

This split saves tokens — Claude Code does planning/review, Codex does mechanical
code changes.

## Spec File Format

Each spec file follows this structure:

```markdown
# Spec: <title>
Status: pending | in_progress | done
Implemented by: <agent name> on <date>

## Context
Why this change is needed.

## Changes

### File: path/to/file.py
#### Change 1: <what>
BEFORE:
```python
old code
```
AFTER:
```python
new code
```

## Verification
Commands to confirm the change works.
```

## Naming Convention
`phase{N}_{step}_{short_description}.md`
Example: `phase1_0_llm_mlx_fix.md`
