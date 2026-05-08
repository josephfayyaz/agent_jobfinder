# Claude Review Request — Local LLM Workflow For Phase K

## Your Role

Review the attached Phase K local-LLM handoff report and recommend how to make
this feature implementable by a local LLM through Aider and `localagent`.

Primary report:

- [phase_K_local_llm_handoff_report.md](/Users/youseffayyaz/Local_LLM/AGENT_SPECS/pending/claude/phase_K_local_llm_handoff_report.md)

Current phase spec:

- [phase_K_provider_controller_deduplication.md](/Users/youseffayyaz/Local_LLM/AGENT_SPECS/pending/claude/phase_K_provider_controller_deduplication.md)

## Current Situation

- The current Phase K spec is narrower than before but still does not complete
  reliably through the local LLM flow.
- `localagent` has already been improved substantially.
- The local OSS model engages with the repo but tends to narrate a plan instead
  of producing edits.
- The target outcome is still to use a local LLM for implementation, not to
  default to cloud implementation.

## What I Need From You

Please review the report and provide:

1. A judgement on whether the current Phase K task is still too broad for a
   local LLM.
2. A recommended decomposition into smaller local-LLM-safe phases.
3. A concrete recommended K1 implementation scope.
4. A recommended task-spec format for local LLM execution.
5. Recommendations for `localagent` changes that would most improve local model
   success.
6. Any Aider strategy suggestions that are specific to local models:
   - file scoping
   - prompt structure
   - pre-edit audit vs edit pass
   - stall detection
   - whether to avoid broad repo-map scans

## Constraints

- Keep the implementation local-model-friendly.
- Prefer small bounded patches over broad refactors.
- Do not assume a cloud model will be used for implementation.
- Do not suggest a full frontend redesign.
- Preserve backend contracts.

## Files Most Relevant To Review

- [frontend/static/onboarding/core.js](/Users/youseffayyaz/Local_LLM/frontend/static/onboarding/core.js)
- [frontend/static/onboarding/intake.js](/Users/youseffayyaz/Local_LLM/frontend/static/onboarding/intake.js)
- [frontend/static/settings/provider.js](/Users/youseffayyaz/Local_LLM/frontend/static/settings/provider.js)
- [frontend/templates/onboarding.html](/Users/youseffayyaz/Local_LLM/frontend/templates/onboarding.html)
- [frontend/templates/settings.html](/Users/youseffayyaz/Local_LLM/frontend/templates/settings.html)

## Preferred Output

Please respond with:

1. `Assessment`
2. `Why the current local-LLM flow is failing`
3. `Recommended K1 scope`
4. `Suggested rewritten K1 spec`
5. `Recommended localagent changes`
6. `Recommended Aider invocation strategy`
