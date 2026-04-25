# Codex Completion Report — Phase I1 Follow-Up

## Phase
PHASE I1 — Human-in-the-Loop Bullet Rewrite Web UI (apply + save-for-future workflow)

## Status
COMPLETE

## Completion Timestamp
2026-04-22T23:16:00+02:00

## Scope
This follow-up completed the missing user-facing workflow after the initial I1 release:
- applying an accepted rewrite back into the live draft content
- refreshing the draft artifacts after apply
- saving approved wording into the fact-sheet bullet bank for future drafts

## Files Modified
- `job_agent/models.py` — extended `BulletClarification` with draft-target metadata and `promoted_to_fact_sheet`
- `job_agent/db.py` — added no-Alembic bootstrap for the new clarification columns
- `job_agent/services/bullet_clarify.py` — stored exact bullet target metadata during rewrite generation
- `job_agent/main.py` — applied accepted rewrites into `draft.content`, refreshed artifacts, and added a promote endpoint that persists approved bullets into the fact-sheet track bank
- `job_agent/templates/draft_detail.html` — updated the sidebar flow to compare old/new wording, apply to the current draft, and explicitly save for future drafts
- `tests/test_bullet_clarify_ui.py` — added coverage for apply-to-draft and save-for-future behavior
- `completed_agent_specs.txt` — appended follow-up completion entry

## DB Changes Applied
Columns added in `prepare_database()`:
- `bullet_clarifications.promoted_to_fact_sheet`
- `bullet_clarifications.target_section`
- `bullet_clarifications.target_item_index`
- `bullet_clarifications.target_bullet_index`

## Verification
- `<python> -m pytest tests/test_bullet_clarify_ui.py tests/test_bullet_clarify.py --tb=short -q` → 13 passed in 0.91s
- `<python> -m pytest --tb=short -q` → 340 passed in 3.52s
- `<home>/miniforge3/envs/ML/bin/ruff check` → All checks passed

## Outcome
The browser flow now matches the intended review model:
1. generate a rewrite suggestion for a specific bullet
2. compare original vs suggested wording
3. apply the rewrite to the active draft only after explicit user approval
4. regenerate the draft artifact in the background
5. optionally save the approved wording into the fact-sheet bullet bank for future drafts
