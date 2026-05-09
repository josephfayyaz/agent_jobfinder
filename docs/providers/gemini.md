# Gemini Provider Contract

## Role

Gemini is a cloud provider with strong speed and cost characteristics, but it
must be treated as a distinct provider family, not an OpenAI clone.

## Strengths

- fast structured generation
- good cost profile
- useful fallback for onboarding and JD analysis

## Risks

- validation can pass while larger workflow prompts still fail
- prompt-size sensitivity is more visible during onboarding intake
- JSON mode support can vary by model/version
- blocked content and empty candidate responses must be handled explicitly

## Required Behavior

- provider validation is necessary but not sufficient
- all intake-like workflows must support provider-aware prompt trimming
- JSON-mode failures must retry once without native JSON mode
- blocked prompt responses must map to a clear app-level category

## Recommended Workflow Use

- onboarding intake: allowed, but only with input shaping and size fallback
- manual JD analysis: strong fit
- CV generation: good fit if structured-output fallback is reliable
- compliance matrix: good fit

## Recovery Policy

- invalid auth: stop immediately
- size/context issue: trim prompt and retry once
- JSON mode unsupported: retry once without native JSON mode
- blocked content: explain clearly and stop
- empty output: retry once, then fail with explicit provider detail

## Design Rule

Gemini should always be tested with:

1. tiny validation probe
2. medium structured JSON call
3. large onboarding-intake-like call

If step 3 is not covered, the integration is not production-safe.
