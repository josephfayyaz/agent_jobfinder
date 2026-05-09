# OpenAI Provider Contract

## Role

OpenAI is the strict cloud baseline.

Use it as the reference implementation for:

- structured JSON generation
- predictable retries
- usage accounting

## Strengths

- stable JSON output path
- mature auth and usage semantics
- good fallback for onboarding and CV workflows

## Risks

- quota/billing failures
- rate limits
- model drift across versions

## Required Behavior

- validation probe must detect billing/quota, not just auth
- usage must always be captured when available
- JSON output must remain strict for all structured workflows

## Recommended Workflow Use

- onboarding intake: strong fallback
- manual JD analysis: primary-safe
- CV generation: primary-safe
- compliance matrix: primary-safe

## Recovery Policy

- auth failure: stop and ask for valid key
- quota failure: surface billing message
- malformed JSON: retry once with stricter JSON reminder
- timeout: retry once, then fail cleanly
