# API Key Product Rollout — Temporary Spec Pack

## Purpose

This folder is a temporary planning pack for the public-release version of Job Agent
where cloud BYOK is the default path and local LLM remains an optional upgrade.

The product direction is:

- default to **user-owned API keys**
- make billing differences crystal clear
- keep keys **local-only** and stored in the OS keychain
- make model quality and cost understandable to non-technical users
- offer **optional local LLM** later for users with stronger hardware

## Rollout Order

1. `stage_01_billing_truth_and_provider_choice.md`
2. `stage_02_guided_key_setup_and_validation.md`
3. `stage_03_cost_modes_and_budget_guardrails.md`
4. `stage_04_failover_and_credit_exhaustion_handling.md`
5. `stage_05_optional_local_llm_upgrade.md`
6. `stage_06_marketing_help_and_experiments.md`
7. `design_2026-04-24_multi_provider_gmail_resilience.md`

## Product Rules

- Do not promise free API tokens.
- Do not imply that ChatGPT Plus or Claude Pro includes API usage.
- Do not store keys in plaintext YAML or frontend local storage.
- Do not force users into local LLM during onboarding.
- Do explain that users with stronger hardware can later switch to local LLM for near-zero marginal cost.

## Current Files Likely Affected

- `frontend/templates/onboarding.html`
- `frontend/templates/settings.html`
- `frontend/static/onboarding.js`
- `frontend/static/settings.js`
- `job_agent/routers/system.py`
- `job_agent/routers/setup_state.py`
- `job_agent/config.py`
- `job_agent/user_config.py`
- `job_agent/llm.py`
- `job_agent/secrets.py`
- `job_agent/onboard.py`

## Final Product Recommendation

The best version of this product is:

- **Balanced cloud-first onboarding**
- **OpenAI + Claude supported from day one**
- **cheap mode by default**
- **quality mode optional**
- **provider failover available**
- **local LLM shown as an advanced upgrade**

This matches product, privacy, and support reality better than trying to design
around free cloud credits.
