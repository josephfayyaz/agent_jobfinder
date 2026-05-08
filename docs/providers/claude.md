# Claude Provider Contract

## Role

Claude is the high-quality cloud reasoning provider.

Use it where:

- structured judgment quality matters
- review/rewrite nuance matters
- fallback quality is more important than cost

## Strengths

- strong review and rewrite quality
- reliable long-form reasoning
- good fit for final review and compliance reasoning

## Risks

- cost can become non-trivial
- response shape and usage metadata may differ from OpenAI
- large prompts still require disciplined truncation

## Required Behavior

- usage capture should be normalized into app-level metrics
- review workflows should preserve deterministic JSON contract
- large-document workflows should not assume unlimited context

## Recommended Workflow Use

- onboarding intake: optional fallback
- manual JD analysis: strong fit
- CV generation review/rewrite: very strong fit
- compliance matrix: very strong fit

## Recovery Policy

- auth: fail fast
- rate limit: retry once if safe
- malformed JSON: retry once with stricter output reminder
- timeout: fail with provider-specific detail
