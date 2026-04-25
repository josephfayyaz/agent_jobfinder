# Stage 04 — Failover + Credit Exhaustion Handling

## Goal

Keep the workflow usable when one provider runs out of credits, rate limits, or fails.

## Product Behavior

If user has both OpenAI and Claude configured:

- primary provider handles default flow
- backup provider handles fallback

## Failover Rules

### Retry classes

- `invalid_key`: do not retry elsewhere automatically until user confirms
- `billing_missing`: offer switch to other provider
- `credits_exhausted`: auto-offer switch to backup provider
- `temporary_outage`: retry once, then fail over
- `rate_limited`: retry with backoff or use fallback provider

## UX Requirements

Show clear toast/banner messages:

- `OpenAI credits appear exhausted. Switched to Claude.`
- `Claude is unavailable right now. Try again or switch provider.`
- `No backup provider is configured.`

## Settings Controls

Add:

- `primary_provider`
- `fallback_provider`
- `allow_automatic_failover`
- `allow_failover_for_premium_tasks_only`

## Logging

Record:

- provider used
- fallback trigger reason
- task type
- whether user had to intervene

## File Targets

- `job_agent/llm.py`
- `job_agent/services/workflows.py`
- `job_agent/routers/system.py`
- `frontend/templates/settings.html`
- `frontend/static/settings.js`

## Acceptance Criteria

- mixed-provider users can continue work if one provider fails
- failover is visible, not silent
- invalid credential errors are not hidden behind useless retries
