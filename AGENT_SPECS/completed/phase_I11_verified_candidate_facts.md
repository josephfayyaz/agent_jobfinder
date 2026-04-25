# Codex Completion Report — Phase I11

## Phase
Phase I11 — Verified Candidate Facts (Profile Memory Layer)

## Status
COMPLETE

## Completion Timestamp
2026-04-23T14:54:07+02:00

## Summary
Implemented a separate verified profile-memory layer for user-confirmed facts from the web apply flow. The curated fact sheet and `MasterProfile` remain untouched. Confirmed answers saved from draft detail are stored as `VerifiedCandidateFact` rows, can be reviewed/deactivated from `/ui/verified-facts`, and are loaded into future CV writer prompts through a bounded `VERIFIED CANDIDATE FACTS` block.

## Robustness Decisions
- Duplicate active facts with the same candidate scope, gap label, and evidence are not inserted again.
- Optional `source_job_id` is derived server-side from `source_draft_id` when saving from draft detail.
- Invalid source IDs return clear 4xx responses instead of uncaught errors.
- Fact types are normalized to a small whitelist and unknown types fall back to `general`.
- Prompt loading includes active facts only and is capped at 50 records to avoid long-running prompt bloat.
- Candidate scoping supports both candidate-linked facts and single-user/global facts without hiding older global memory.

## Files Added
- `job_agent/templates/verified_facts.html`
- `tests/test_verified_candidate_facts.py`

## Files Modified
- `job_agent/models.py` — added `VerifiedCandidateFact`.
- `job_agent/main.py` — added verified-facts API endpoints, `/ui/verified-facts`, and draft-detail context for saved apply answers.
- `job_agent/services/workflows.py` — stores session confirmed facts on the draft and loads active profile-memory facts for future writer prompts.
- `job_agent/services/prompts.py` — added `verified_facts` parameter and prompt block.
- `job_agent/templates/draft_detail.html` — added “Answers from This Application” promotion UI.
- `job_agent/templates/base.html` — added Profile Memory navigation.
- `completed_agent_specs.txt` — appended completion entry.

## Verification
- `<python> -m pytest tests/test_verified_candidate_facts.py -v` → 10 passed
- `<python> -m pytest --tb=short -q` → 373 passed, 4 warnings
- `<home>/miniforge3/envs/ML/bin/ruff check` → All checks passed

## Notes
The remaining warnings are unrelated `duckduckgo_search` rename warnings from `job_agent/services/company_resolver.py`.
