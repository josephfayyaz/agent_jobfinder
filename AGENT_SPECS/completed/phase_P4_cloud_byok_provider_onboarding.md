# Phase P4r — Cloud BYOK Provider Onboarding

## Status

Completed and verified on 2026-04-25.

## What changed

- Kept the shared provider-mode normalization layer in place across router, setup, and UI code.
- Fixed provider-status semantics so `configured` now means at least one provider is set up, while `ready` still means the currently selected provider mode is usable.
- Updated `/health/ai-status` to expose the corrected `configured` vs `ready` distinction for the base warning banner.
- Preserved setup-gate behavior: onboarding still requires the selected provider mode to be ready before the workspace is considered complete.
- Refined onboarding step 1 so the UI is clearly cloud-first:
  - OpenAI remains the recommended default
  - Claude is shown as an equally supported cloud option
  - LM Studio and Ollama are visually grouped as advanced local options
- Added regression coverage for:
  - provider-status normalization and readiness
  - `/health/ai-status`
  - `/setup/status` provider readiness across supported modes

## Files touched

- `job_agent/providers.py`
- `job_agent/routers/system.py`
- `job_agent/routers/setup_state.py`
- `frontend/templates/onboarding.html`
- `tests/test_provider_resilience.py`
- `tests/test_onboarding.py`

## Verification

- `pytest tests/test_provider_resilience.py tests/test_onboarding.py --tb=short -q`
- `pytest --tb=short -q`
- `ruff check`

Result:

- `455 passed, 3 warnings`
- `ruff check` clean

## Notes

- Remaining warnings come from the existing `duckduckgo_search` deprecation warning in `job_agent/services/company_resolver.py`.
- The provider banner behavior now aligns better with the product wording: no banner when a provider is configured anywhere, but setup still blocks until the selected mode is actually ready.
