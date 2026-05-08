# Active Codex Pending Specs

The current active program is the provider-runtime hardening track derived from
`docs/PROVIDER_ARCHITECTURE.md`.

## Active execution order

1. `phase_Q1_provider_capability_registry.md`
2. `phase_Q2_provider_error_taxonomy.md`
3. `phase_Q3_provider_smoke_harness.md`
4. `phase_Q4_workflow_input_shaping.md`
5. `phase_Q5_prompt_mode_split.md`
6. `phase_Q6_adapter_split_and_router_cleanup.md`
7. `phase_Q7_provider_validation_and_smoke_audit.md`

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
