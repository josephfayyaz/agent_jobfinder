# AGENT_SPECS

This directory is the shared handoff area for implementation prompts, completion
reports, and longer-term planning documents.

## Structure

### `pending/`
Specs that are still active and have not been fully implemented or validated yet.

- `pending/claude/` — pending specs authored by Claude
- `pending/codex/` — pending specs authored by Codex

### `archive/`
Specs that are no longer active.

- `archive/<agent>/completed/` — implemented specs kept for reference
- `archive/<agent>/superseded/` — replaced or obsolete specs that should not be
  used for new work without review

### `completed/`
Implementation reports only. This folder is intentionally unified and does not
split reports by author.

### `master_plans/`
Longer-horizon planning documents and execution-order packs.

- `master_plans/claude/` — Claude-created roadmap and planning docs
- `master_plans/codex/` — Codex-created strategy packs and future-phase plans

## Working Rules

1. New implementation specs go into `pending/<agent>/`.
2. After a spec is implemented and verified, move the prompt into
   `archive/<agent>/completed/` and write the report into `completed/`.
3. If a spec is replaced, move it into `archive/<agent>/superseded/`.
4. Keep roadmap, execution-order, and strategy material under `master_plans/`,
   not mixed into the active prompt folders.
5. If a pending folder is intentionally empty, keep a placeholder such as
   `.gitkeep` so the structure stays visible in git.
6. Every completed implementation must also update `completed_agent_specs.txt`.
7. `completed_agent_specs.txt` entries should use one line per completed spec:
   `spec_filename.md — COMPLETE — <timestamp> — <one-line outcome>`
8. When multiple specs belong to one execution track, insert a blank line before
   the first entry of that track in `completed_agent_specs.txt` so later agents
   can visually separate the groups.
9. Completion reports must follow `completed/REPORT_TEMPLATE.md` unless the spec
   explicitly tightens the reporting requirements further.

## Current Intent

- `pending/` should stay small, current, and actionable.
- `archive/` is the historical record for prompts.
- `completed/` is the historical record for reports.
- `master_plans/` is where future planning and execution-order packs belong.
