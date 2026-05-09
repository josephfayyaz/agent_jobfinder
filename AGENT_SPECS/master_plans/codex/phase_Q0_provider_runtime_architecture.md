# Phase Q0 — Provider Runtime Architecture Inspired By career-ops

## Goal

Make the provider layer robust across:

- OpenAI
- Google Gemini
- Anthropic Claude
- Local Gateway
- Ollama

without pretending they are interchangeable.

## Why This Phase Exists

The current app has a good unified router, but provider behavior is still too
implicit. Recent Gemini intake bugs showed the main gap:

- lightweight provider validation succeeded
- real onboarding intake still failed

That means the app needs a provider runtime architecture, not just provider
selection UI.

## What We Borrow From career-ops

Borrow:

- shared logic separated from provider entrypoints
- explicit provider-facing docs
- thin provider wrappers
- clear system-vs-user boundaries

Do not borrow:

- CLI-first slash-command structure
- direct dependency on Gemini CLI or Claude Code command files

## Deliverables

### 1. Capability Registry

Add one source of truth for provider capabilities:

- native JSON mode
- separate system instruction support
- expected usage metadata
- recommended prompt limits by workflow
- retry strategy
- validation probe strategy

### 2. Error Taxonomy

Normalize provider failures into app-level categories:

- auth
- quota
- rate_limit
- context_too_large
- unsupported_feature
- blocked_content
- malformed_json
- empty_output
- timeout
- unavailable

### 3. Smoke Scripts

Add standalone provider smoke scripts that test:

- validation probe
- small structured call
- medium structured call
- large intake-like structured call

### 4. Workflow Input Shaper

Add provider-aware shaping before generation:

- dedup duplicated source text
- clip low-value sections first
- preserve high-signal head/tail context
- apply per-provider safe size limits

### 5. Prompt/Mode Split

Refactor large workflow instructions into markdown mode files while keeping
Python interpolation where needed.

Target workflows:

- onboarding intake
- manual JD scoring
- CV generation
- compliance matrix

### 6. Adapter Split

Keep `LLMRouter` public, but move provider branches into adapters:

- openai
- gemini
- claude
- local_gateway
- ollama

## Guardrails

- Do not break the current `LLMRouter.generate()` contract while doing this.
- Do not force cloud providers into one fake OpenAI schema.
- Do not treat provider validation as sufficient proof of workflow readiness.
- Do not merge provider-specific prompt rules into user-facing workflow logic.

## Suggested Order

1. Capability registry
2. Error taxonomy
3. Smoke scripts
4. Input shaping
5. Adapter split
6. Prompt/mode file split

## Success Criteria

- a provider can be verified with a realistic smoke path, not only a tiny probe
- onboarding intake, JD scoring, CV generation, and compliance matrix each have
  explicit provider-safe limits
- Gemini, Claude, OpenAI, and Local Gateway failures are diagnosable without
  reading raw transport traces
- future local agents have a clear architecture target instead of scattered
  provider-specific patches
