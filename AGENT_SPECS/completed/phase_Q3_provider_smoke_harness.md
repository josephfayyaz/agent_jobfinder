# Codex Completion Report — Phase Q3 — Provider Smoke Harness

## Phase
Phase Q3 — Provider Smoke Harness

## Status
COMPLETE

## Completion Timestamp
2026-05-08T15:04:57+0200

## Files Created
job_agent/provider_smoke.py  (71 lines)
tests/test_provider_smoke.py  (43 lines)

## Files Modified
job_agent/__main__.py — added guarded `provider-smoke` CLI path while preserving existing CLI delegation

## DB Changes Applied
None.

## Tests Added
test_provider_smoke_probe_returns_ok  [tests/test_provider_smoke.py]
test_provider_smoke_large_intake_prompt_is_much_larger_than_probe  [tests/test_provider_smoke.py]
test_provider_smoke_raises_on_invalid_json  [tests/test_provider_smoke.py]

## Test Run Output
pytest tests/test_provider_smoke.py -q

## Ruff Output
All checks passed.

## Deviations From Spec
None.

## Issues Encountered
Manual smoke execution still depends on a configured working provider, so the automated test suite covers the CLI path with monkeypatched router behavior instead of requiring live credentials.
