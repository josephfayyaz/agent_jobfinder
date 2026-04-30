# Codex Completion Report — Phase R1 Provider And Search Contract

## Phase
Phase R1 — Provider And Search Contract

## Status
COMPLETE

## Completion Timestamp
2026-04-29T23:37:54+02:00

## Files Created
None.

## Files Modified
job_agent/providers.py — removed active mixed-provider mode and normalized legacy mixed values to a single-provider default.
job_agent/llm.py — removed mixed-mode generation branch so router generation stays single-provider.
job_agent/routers/system.py — rejected mixed provider mode in validation/save, constrained provider mode values, and normalized one-country save behavior.
job_agent/config.py — updated provider mode contract description to single-provider modes only.
job_agent/search_preferences.py — normalized country lists to exactly one country.
job_agent/services/workflows.py — removed cloud split review/rewrite paths and routed review/rewrite through single active provider calls.
job_agent/onboard.py — removed mixed onboarding option and constrained onboarding search country input to one country.
config/user_settings.example.yml — updated provider mode options and added one-country scope note.
frontend/templates/dashboard.html — updated provider guidance copy to single active provider behavior.
frontend/templates/settings.html — removed mixed provider UI option and clarified one-country + language proficiency copy.
frontend/templates/onboarding.html — clarified single-provider behavior and added onboarding language/proficiency editing UI.
frontend/static/onboarding.js — added onboarding language/proficiency row editing, single-country save behavior, and payload persistence.
frontend/static/settings.js — added language proficiency select handling and single-country save normalization.
tests/test_search_profile_preferences.py — updated country expectations to one-country normalization and added one-country save test.
tests/test_onboarding.py — updated onboarding UI language expectations and added onboarding-style language proficiency persistence test.
tests/test_provider_resilience.py — removed mixed readiness case, added mixed rejection tests, and added workflow provider-contract test.

## DB Changes Applied
None.

## Tests Added
test_settings_save_keeps_only_first_country_when_multiple_provided  [tests/test_search_profile_preferences.py]
test_onboarding_style_language_payload_persists_proficiency_levels  [tests/test_onboarding.py]
test_settings_save_rejects_mixed_mode  [tests/test_provider_resilience.py]
test_validate_provider_rejects_mixed_mode  [tests/test_provider_resilience.py]
test_workflow_review_uses_router_generate_for_active_provider  [tests/test_provider_resilience.py]

## Test Run Output
33 passed in 1.09s

## Ruff Output
All checks passed!

## Deviations From Spec
None.

## Issues Encountered
None.
