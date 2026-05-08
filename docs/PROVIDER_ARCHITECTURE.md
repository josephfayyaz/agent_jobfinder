# Provider Architecture

This document defines the target provider architecture for Job Agent after
reviewing patterns from `career-ops` and comparing them against the current
FastAPI + SQLite app.

## Why This Exists

The app already supports:

- OpenAI
- Google Gemini
- Anthropic Claude
- Local Gateway (OpenAI-compatible local server such as LM Studio or vLLM)
- Ollama

But provider behavior is still too distributed across:

- `job_agent/llm.py`
- `job_agent/routers/system.py`
- onboarding/provider UI
- intake and workflow error handling

That is manageable today, but it is not yet robust enough for long-term
maintenance across cloud and local providers.

## What To Borrow From career-ops

The useful pattern in `career-ops` is not the exact CLI setup. The useful
pattern is the separation of concerns:

1. Shared task logic lives in common mode files.
2. Provider-specific entrypoints are thin wrappers around that shared logic.
3. Provider behavior is documented explicitly instead of being inferred from
   scattered code.
4. There is a clear distinction between user data and system logic.

For Job Agent, that maps to:

1. Shared workflow contracts:
   - onboarding intake
   - manual JD analysis
   - CV generation
   - CV review/rewrite
   - compliance matrix
2. Thin provider adapters:
   - OpenAI adapter
   - Gemini adapter
   - Claude adapter
   - Local Gateway adapter
   - Ollama adapter
3. Explicit capability registry:
   - JSON mode support
   - system instruction shape
   - token/context constraints
   - retry policy
   - probe/validation strategy
4. Strong separation between:
   - user/runtime state
   - provider system behavior
   - prompt/mode logic

## What Not To Copy From career-ops

Job Agent is not a CLI-first slash-command project.

Do not copy these directly:

- `.gemini/commands/*.toml`
- CLI-specific bootstrap rules
- batch-worker prompt orchestration based on `claude -p`

Instead, use the same conceptual split inside the web app:

- workflow-mode definitions
- provider capability docs
- provider adapters
- standalone probe scripts

## Current Job Agent Structure

Current strengths:

- one LLM router entrypoint in `job_agent/llm.py`
- provider-mode normalization in `job_agent/providers.py`
- onboarding/provider status and validation in `job_agent/routers/system.py`
- prompt logic already centralized for CV generation in `job_agent/services/prompts.py`
- intake prompt packs already exist in `job_agent/services/intake.py`

Current weaknesses:

- provider capability knowledge is embedded in code branches rather than one
  shared registry
- validation probes are much smaller than real onboarding/CV workloads, so a
  provider can pass validation but still fail during actual use
- prompt/input shaping policy is not first-class per provider
- provider error translation is still partly route-specific
- there is no standalone provider smoke/eval path equivalent to
  `career-ops/gemini-eval.mjs`

## Recommended Target Architecture

### 1. Shared Workflow Contracts

Define provider-neutral workflow contracts for:

- onboarding intake
- onboarding question-answer merge
- manual JD scoring
- CV draft generation
- CV review/rewrite
- compliance matrix generation

Each workflow contract should define:

- required input fields
- max recommended input size
- required output JSON schema
- fallback behavior when provider output is incomplete

### 2. Provider Capability Registry

Introduce a single capability table in application code later, for example:

- provider id
- supports native JSON mode
- supports separate system instruction
- recommended max prompt chars for intake
- recommended max prompt chars for JD scoring
- retry style
- health probe style
- structured-output strictness

This should become the source of truth for provider behavior instead of
duplicating assumptions in each branch.

### 3. Provider Adapters

Keep `LLMRouter` as the public entrypoint, but internally split provider logic
into small adapters:

- `openai_adapter`
- `gemini_adapter`
- `claude_adapter`
- `local_gateway_adapter`
- `ollama_adapter`

Each adapter should expose:

- `probe()`
- `generate_json()`
- `classify_error()`
- `usage_payload()`
- `suggest_recovery()`

### 4. Input Shaping Layer

Before calling a provider, every workflow should pass through a workflow-aware
input shaper:

- deduplicate repeated source text
- normalize PDF text
- trim low-value sections first
- preserve head and tail context
- apply provider-specific size limits

This matters most for Gemini and local models.

### 5. Provider Error Taxonomy

Map raw provider failures into stable app-level categories:

- auth
- quota
- rate_limit
- context_too_large
- unsupported_feature
- blocked_content
- empty_output
- malformed_json
- timeout
- unavailable

Routes should translate only these categories into user-facing messages.

### 6. Standalone Provider Smoke Scripts

Add one script per provider family so failures can be reproduced without the
full onboarding flow:

- OpenAI smoke script
- Gemini smoke script
- Claude smoke script
- Local Gateway smoke script
- Ollama smoke script

These should test:

- probe
- small JSON generation
- medium JSON generation
- large intake-like JSON generation

### 7. Prompt/Mode Split

Borrow the `career-ops` idea of shared modes, but implement it in a way that
fits this repo:

- keep Python builders where runtime interpolation is needed
- move long workflow instructions into versioned markdown mode files
- load shared sections for:
  - onboarding intake
  - JD analysis
  - CV generation
  - compliance matrix

This makes prompts easier to diff, test, and compare across providers.

## Provider Family Guidance

See:

- `docs/providers/openai.md`
- `docs/providers/gemini.md`
- `docs/providers/claude.md`
- `docs/providers/local_gateway.md`

## Implementation Priority

1. Provider capability registry
2. Standalone smoke scripts
3. Workflow-specific input shaping
4. Provider error taxonomy
5. Prompt/mode file split
6. Adapter extraction from `job_agent/llm.py`

## Main Recommendation

The right move is not to make Gemini or Claude look like OpenAI.

The right move is:

- one shared workflow contract
- one explicit provider capability model
- one adapter per provider family
- one stable error taxonomy
- one set of smoke tests that simulate real workload sizes

That is the architecture that will make the app robust across cloud and local
providers.
