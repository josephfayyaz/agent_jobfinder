# Phase K Local LLM Handoff Report

## Purpose

This report is a handoff for Claude review.

The goal is not to re-argue the feature itself. The goal is to explain why the
current local-agent flow did not complete Phase K reliably, what was already
fixed in `localagent`, what was actually observed with the local models, and
what changes are most likely to make local LLM implementation viable.

## Target Task

Original task under test:

- [phase_K_provider_controller_deduplication.md](/Users/youseffayyaz/Local_LLM/AGENT_SPECS/pending/claude/phase_K_provider_controller_deduplication.md)

Target repo:

- `/Users/youseffayyaz/Local_LLM`

Supporting tool repo:

- `/Users/youseffayyaz/Documents/Local_Agents/localagent`

## Executive Summary

The current failure is not just "the model is weak" and not just "the spec is
bad."

It is a combination of:

1. `localagent` integration issues that were real and were partially fixed.
2. A spec that was too broad for a local Aider-driven model in one pass.
3. Missing structure in the task format for local-model execution.
4. Local model behavior that tends to narrate plans instead of writing edits.

The local LLM path is still worth pursuing, but only with a stricter execution
format and smaller tasks.

## What Was Already Fixed In localagent

Several issues in `localagent` were identified and corrected during testing.

### 1. Binary snapshot crash in worktree sandbox

Problem:

- untracked binary files caused `UnicodeDecodeError` during sandbox baseline
  capture

Fix:

- snapshot logic switched from text reads to raw bytes

Relevant file:

- [worktree.py](/Users/youseffayyaz/Documents/Local_Agents/localagent/localagent/coding/worktree.py)

### 2. Aider executable lookup

Problem:

- `localagent` tried to run bare `aider`
- active shell environment was often `ML`, while `aider` lived in `agent`

Fix:

- added explicit `environment.aider_bin`
- runtime now resolves configured path first

Relevant files:

- [agent.py](/Users/youseffayyaz/Documents/Local_Agents/localagent/localagent/coding/agent.py)
- [config.py](/Users/youseffayyaz/Documents/Local_Agents/localagent/localagent/config.py)

### 3. Runtime env vs project command env split

Problem:

- `localagent` runtime and project `pytest` checks were being forced into the
  same conda env
- this broke project checks when dependencies lived in `ML`

Fix:

- split into:
  - `default_env`: `agent`
  - `command_env`: `ML`

Relevant files:

- [env.py](/Users/youseffayyaz/Documents/Local_Agents/localagent/localagent/env.py)
- [policy.py](/Users/youseffayyaz/Documents/Local_Agents/localagent/localagent/policy.py)
- [config.yaml](/Users/youseffayyaz/.agentlocal/config.yaml)

### 4. Browser tabs opening unexpectedly

Problem:

- Aider opened browser-related flows during runs

Fix:

- Aider invocation now sets:
  - `--no-browser`
  - `--no-gui`
  - `AIDER_BROWSER=false`
  - `AIDER_GUI=false`

### 5. Baseline-aware test handling

Problem:

- target repo already had failing tests
- `localagent` treated any failing post-run check as a new regression

Fix:

- checks now compare current failures against the sandbox baseline
- pre-existing failures are tolerated if preserved

### 6. Aider model-name normalization

Problem:

- Aider needed OpenAI-compatible local models passed as `openai/<model-id>`
- raw model IDs caused LiteLLM provider errors
- Aider could still exit `0`, which made `localagent` misread the failure as a
  harmless no-op

Fix:

- `localagent` now normalizes raw local model IDs to `openai/...`
- `localagent` now treats LiteLLM provider text errors as real failures even
  when subprocess exit code is zero

### 7. Spec-run context trimming

Problem:

- spec-driven runs were loading too much text from `CLAUDE.md`, `AGENTS.md`,
  and the task bundle
- local models were getting overloaded before writing edits

Fix:

- task bundle context is now prioritized
- project spec context is truncated for spec-file runs

## What Was Observed In The Target Repo

The strongest real duplication for Phase K is narrower than the original
feature framing.

Observed live duplication:

- onboarding `validateAndSaveProvider()` in:
  - [frontend/static/onboarding/intake.js](/Users/youseffayyaz/Local_LLM/frontend/static/onboarding/intake.js)
- settings `validateProviderForm()` in:
  - [frontend/static/settings/provider.js](/Users/youseffayyaz/Local_LLM/frontend/static/settings/provider.js)

Shared concerns between those two flows:

- build `/providers/validate` payload
- call `/providers/validate`
- build common provider flags
- default local base URLs
- shape save payload for LM Studio / Ollama
- call `/settings/save`

Observed logic that is not obviously worth centralizing in this phase:

- onboarding panel toggling in:
  - [frontend/static/onboarding/core.js](/Users/youseffayyaz/Local_LLM/frontend/static/onboarding/core.js)
- settings provider panel visibility in:
  - [frontend/static/settings/provider.js](/Users/youseffayyaz/Local_LLM/frontend/static/settings/provider.js)

Observed logic that already exists and should not be moved casually:

- `chooseLocalModelDefaults()` already exists in onboarding core
- `nonEmbeddingModels()` already exists in onboarding core

Conclusion:

Phase K should be smaller and more concrete. The right seam is provider
validation/save flow, not a broad "provider controller" abstraction.

## Model Tests And Results

### A. Previous Qwen-based path

Earlier runs using the Qwen-based local configuration produced no changes.

Important caveat:

- some of those early no-op results were caused by real `localagent` issues,
  especially the Aider model-name normalization problem

So those early no-op results were not a clean model-only test.

### B. Current OSS model actually reachable

Observed live local endpoint:

- base URL: `http://127.0.0.1:8080/v1`
- model id returned by `/v1/models`:
  - `mlx-community/gpt-oss-20b-MXFP4-Q8`

### C. Raw chat-completions probe

Probe:

- asked the model to "Reply with exactly: OK"

Observed behavior:

- it did not follow the instruction cleanly
- it began explaining the instruction instead of simply returning `OK`

Interpretation:

- raw instruction following is weaker than ideal for agentic edit control

### D. Direct Aider smoke test against OSS model

Test shape:

- restricted Aider to the relevant frontend files
- direct prompt requested:
  - create `frontend/static/provider_controller.js`
  - wire shared validation/save logic only
  - avoid backend changes

Observed behavior:

- the model engaged with the codebase
- it narrated a plan for several minutes
- it did not produce actual file edits before being stopped

Interpretation:

- better than the previous immediate no-op behavior
- still not reliable enough for autonomous implementation

### E. Full localagent spec-autonomous run against OSS model

Observed behavior:

- `localagent` engaged with the model
- the Aider subprocess remained alive for multiple minutes
- no file changes were produced before the run was stopped

Interpretation:

- the stack is no longer failing instantly
- but the local model is still not converging to actual edits for this task

## Why The Current Flow Is Still Failing

### 1. The task is still too large for this model/backend shape

Even after narrowing the spec, the model still needs to:

- infer safe extraction boundaries
- create a new shared file
- update multiple frontend files
- preserve behavior
- avoid over-centralization

That is still a medium-sized refactor, not a tiny patch.

### 2. The spec format is too prose-heavy for local-model execution

The current spec is better than before, but it is still written for a stronger
review-and-reason model. It is not yet optimized for a local editor model.

### 3. localagent does not pass an explicit file allowlist into Aider from the spec

Directly giving Aider only the small file set helped somewhat.

Current `localagent` gap:

- the spec can mention write scope
- but `localagent` does not yet turn that into a concrete Aider file list

This is important for local models.

### 4. localagent does not distinguish "planning forever" from "editing"

Observed failure mode:

- model stays active
- no diffs appear
- run consumes time but not progress

This is a workflow problem, not just a model problem.

## Main Recommendations

### Recommendation 1

Split Phase K into smaller local-LLM-safe phases.

Recommended split:

- K1: extract only provider flags + validation payload + base save payload helper
- K2: wire onboarding to it
- K3: wire settings to it
- K4: add structural tests and template include

### Recommendation 2

Adopt a structured task format for local LLM runs.

Instead of long prose-first specs, use a compact execution spec with explicit:

- target files
- read-only files
- exact required edits
- exact forbidden edits
- test commands
- done conditions
- stop conditions

### Recommendation 3

Teach `localagent` to pass target files directly to Aider.

This is probably the single most useful tooling improvement left for local
model execution.

Desired behavior:

- parse target files from the task spec
- invoke Aider with only those files
- avoid broad repo scanning for small refactors

### Recommendation 4

Add a progress watchdog to `localagent`.

Desired behavior:

- if Aider runs for N minutes without producing edits or a concrete completion
  state, terminate and report "planning stall"

### Recommendation 5

Treat local LLMs as patch workers, not architecture deciders.

What local models appear more likely to succeed at:

- changing one file
- applying one narrow transformation
- adding one test file
- wiring one explicit script include

What they appear less likely to succeed at:

- designing the right extraction boundary
- centralizing logic safely across multiple files in one step
- self-policing abstraction scope

### Recommendation 6

Keep Claude as the planning/review layer and the local model as the patch layer.

Proposed division:

- Claude:
  - review architecture
  - shrink/refine specs
  - define exact file-level deltas
  - suggest sequencing
- local LLM:
  - execute one small bounded patch at a time

## Specific Questions For Claude Review

Claude should review this workflow with these questions in mind:

1. Is Phase K still too broad for a local Aider-driven model?
2. What is the smallest viable K1 spec that preserves usefulness?
3. Which exact logic should stay local in onboarding/settings rather than be
   centralized?
4. Should `chooseLocalModelDefaults()` remain in onboarding/settings core for
   now instead of moving into a shared controller?
5. What task-spec structure would Claude recommend for local LLM execution?
6. What `localagent` changes would most improve small-model implementation
   success?

## Suggested Decision

Do not ask the local model to complete the current Phase K spec as one task.

Instead:

1. have Claude review this report
2. have Claude rewrite Phase K as a smaller K1 local-LLM-safe patch
3. run the local model only on that smaller patch

## Supporting Files

Key Phase K files:

- [phase_K_provider_controller_deduplication.md](/Users/youseffayyaz/Local_LLM/AGENT_SPECS/pending/claude/phase_K_provider_controller_deduplication.md)
- [frontend/static/onboarding/core.js](/Users/youseffayyaz/Local_LLM/frontend/static/onboarding/core.js)
- [frontend/static/onboarding/intake.js](/Users/youseffayyaz/Local_LLM/frontend/static/onboarding/intake.js)
- [frontend/static/settings/provider.js](/Users/youseffayyaz/Local_LLM/frontend/static/settings/provider.js)
- [frontend/templates/onboarding.html](/Users/youseffayyaz/Local_LLM/frontend/templates/onboarding.html)
- [frontend/templates/settings.html](/Users/youseffayyaz/Local_LLM/frontend/templates/settings.html)

Key `localagent` files:

- [agent.py](/Users/youseffayyaz/Documents/Local_Agents/localagent/localagent/coding/agent.py)
- [context.py](/Users/youseffayyaz/Documents/Local_Agents/localagent/localagent/coding/context.py)
- [taskbundle.py](/Users/youseffayyaz/Documents/Local_Agents/localagent/localagent/coding/taskbundle.py)
- [config.py](/Users/youseffayyaz/Documents/Local_Agents/localagent/localagent/config.py)
- [config.yaml](/Users/youseffayyaz/.agentlocal/config.yaml)
