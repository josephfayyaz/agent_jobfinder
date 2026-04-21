# Codex Completion Report — Phase F1

## Phase
Phase F1 — Human-in-the-Loop Bullet Clarify & Rewrite

## Status
COMPLETE

## Completion Timestamp
2026-04-18T12:16:56+02:00

## Files Created
AGENT_SPECS/completed/phase_F1_report.md  (57 lines)
job_agent/services/bullet_clarify.py  (181 lines)
tests/test_bullet_clarify.py  (247 lines)

## Files Modified
job_agent/models.py  — added `BulletClarification` ORM model and `ResumeDraft.clarifications` relationship
job_agent/db.py  — added `bullet_clarifications` table/index bootstrap SQL in `prepare_database()`
job_agent/config.py  — added `bullet_clarify_word_limit` setting
job_agent/services/prompts.py  — added language extraction, clarifying question, and rewrite prompt builders for bullet clarify flow
job_agent/main.py  — added `POST /drafts/{draft_id}/clarify` and `POST /drafts/{draft_id}/clarify/{clarification_id}/answer` endpoints
.env.example  — added `BULLET_CLARIFY_WORD_LIMIT`
completed_agent_specs.txt  — appended F1 completion entry

## DB Changes Applied
Tables created via Base.metadata.create_all():
- `bullet_clarifications` (new ORM model)

Columns added to prepare_database():
- None.

Additional SQL bootstrap in `prepare_database()`:
- `CREATE TABLE IF NOT EXISTS bullet_clarifications (...)`
- `CREATE INDEX IF NOT EXISTS ix_bullet_clarifications_draft_id ON bullet_clarifications(draft_id)`

## Tests Added
test_start_clarification_returns_questions_when_gaps_exist  [tests/test_bullet_clarify.py]
test_start_clarification_skips_questions_when_no_gaps  [tests/test_bullet_clarify.py]
test_submit_answers_runs_rewrite_with_confirmed_facts  [tests/test_bullet_clarify.py]
test_submit_answers_rejects_non_pending_clarification  [tests/test_bullet_clarify.py]
test_enforce_word_limit_truncates_long_bullets  [tests/test_bullet_clarify.py]
test_merge_rewritten_bullets_updates_matching_experiences  [tests/test_bullet_clarify.py]
test_start_clarification_404_for_missing_draft  [tests/test_bullet_clarify.py]
test_api_start_clarify_endpoint_returns_200  [tests/test_bullet_clarify.py]

## Test Run Output
231 passed, 3 warnings in 5.14s

## Ruff Output
All checks passed!

## Deviations From Spec
`prepare_database()` creates `bullet_clarifications.id` as `UUID PRIMARY KEY` without a DB-side `gen_random_uuid()` default to avoid requiring the `pgcrypto` extension at bootstrap. ORM inserts still generate UUIDs via model default (`uuid.uuid4`).

## Issues Encountered
Graphify rebuild command failed in this environment with `ModuleNotFoundError: No module named 'graphify'`, so graph output could not be regenerated in this run.
