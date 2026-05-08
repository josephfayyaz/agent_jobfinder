# Active Codex Pending Specs

The current active program is the provider-runtime hardening track derived from
`docs/PROVIDER_ARCHITECTURE.md`.

## Active execution order

1. `phase_Q6A_local_provider_adapters.md`
2. `phase_Q6B_openai_claude_adapters.md`
3. `phase_Q6C_gemini_adapter_and_router_cleanup.md`
4. `phase_Q7_provider_validation_and_smoke_audit.md`

## One-line track summary

This provider-runtime track turns provider handling from scattered branch logic
into a documented, testable runtime architecture with capability contracts,
error taxonomy, smoke verification, workflow-aware input shaping, prompt
resource splits, adapter extraction, and a final validation audit.

Because the original `Q6` adapter split was too broad for weaker coding
agents, it is now decomposed into `Q6A`, `Q6B`, and `Q6C`.

## Completion bookkeeping rule

When any `Q` spec is completed, the implementing agent must do all of these in
the same change set:

1. Move the finished spec from `pending/codex/` to `archive/codex/completed/`
2. Write a completion report in `AGENT_SPECS/completed/`
3. Append one line to `completed_agent_specs.txt` in this format:
   `phase_QX_....md — COMPLETE — <timestamp> — <one-line outcome>`
4. Keep a blank line before the first `Q`-track entry in `completed_agent_specs.txt`

## Why this track exists

The app already works across OpenAI, Gemini, Claude, Local Gateway, and
Ollama, but the runtime behavior is still too implicit. The recent Gemini
intake issue proved that lightweight provider validation is not enough.

These specs turn provider handling into:

- explicit capability contracts
- explicit error taxonomy
- realistic smoke verification
- shared workflow-aware input shaping
- adapter-based router internals

## Recently completed

- `phase_G1_pdf_intake_hardening.md`
  - implemented in the onboarding intake flow with stronger local PDF extraction
    and normalized source text before AI intake
- `phase_Q1_provider_capability_registry.md`
  - added provider capability contracts and prompt-limit helpers
- `phase_Q2_provider_error_taxonomy.md`
  - normalized provider failures into app-level error categories
- `phase_Q3_provider_smoke_harness.md`
  - added standalone provider smoke CLI and realistic prompt cases
- `phase_Q4_workflow_input_shaping.md`
  - applied shared provider-aware prompt shaping to intake, scoring, CV workflow, and compliance matrix
- `phase_Q5_prompt_mode_split.md`
  - moved core system prompts into versioned prompt resources and kept prompt builders compatible
