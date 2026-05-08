# Local Gateway Provider Contract

## Role

Local Gateway is the OpenAI-compatible local provider family:

- LM Studio
- vLLM
- other OpenAI-compatible local servers

Ollama remains separate because the runtime behavior is different enough to
justify its own adapter path.

## Strengths

- privacy-first
- no cloud billing
- flexible model selection

## Risks

- context-window mismatch
- incomplete JSON compliance
- model-specific quirks
- server responds but loaded model is wrong for the workflow

## Required Behavior

- validation must check more than transport reachability
- validation should verify:
  - chat/instruct compatibility
  - minimum context expectations
  - model presence for required roles
- structured workflows must expect imperfect JSON
- retries should include prompt reduction for context issues

## Recommended Workflow Use

- onboarding intake: allowed, but only with strong truncation and truthful error messages
- manual JD analysis: strong fit with good models
- CV generation: strong fit with larger models
- compliance matrix: acceptable with good models

## Recovery Policy

- context failure: show actionable model/context guidance
- malformed JSON: retry once with reduced prompt and stricter reminder
- empty output: fail with model-specific message
- model not loaded: fail with server/model guidance

## Design Rule

Do not treat all OpenAI-compatible local servers as equivalent.

The app should eventually track at least:

- server family
- configured models
- max reliable context
- JSON compliance behavior
- known quirks
