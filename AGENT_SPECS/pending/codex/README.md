# Active Codex Pending Specs

## Active user-facing product tracks

The next user-facing product track is the search-quality and CV-usability pack
defined in:

- `master_plans/codex/phase_S0_search_quality_and_cv_usability_execution_plan.md`
- `master_plans/codex/phase_T0_intake_generalization_execution_plan.md`

Recommended execution order:

1. `phase_S1_strict_discovery_geography_and_queue_scope.md`
2. `phase_S2_jd_ready_default_queue_cap.md`
3. `phase_S3_job_detail_dialog_and_posted_time.md`
4. `phase_S4_profile_review_visibility_and_preference_simplification.md`
5. `phase_S5_jobs_and_drafts_action_ux.md`
6. `phase_T5_intake_regression_corpus_and_diagnostics.md`

## One-line track summary

The active product program now combines:

- `S`: search quality, JD readability, and action usability
- `T`: intake generalization, provenance, and schema-safe multi-source CV ingestion

The `T` pack is intentionally placed before `S4` so the expanded review surface
rests on a stable intake substrate instead of brittle PDF-to-schema inference.

## Completion bookkeeping rule

When any pending spec is completed, the implementing agent must do all of these
in the same change set:

1. Move the finished spec from `pending/codex/` to `archive/codex/completed/`
2. Write a completion report in `AGENT_SPECS/completed/`
3. Append one line to `completed_agent_specs.txt` in this format:
   `phase_QX_....md — COMPLETE — <timestamp> — <one-line outcome>`
4. Keep a blank line before the first `Q`-track entry in `completed_agent_specs.txt`

## Why these tracks exist

The app already works across the main workflow, but two areas still need
structured follow-through:

- the jobs surface still overexposes weak-JD rows and under-exposes the actual JD
- discovery must be user-initiated so fresh workspaces do not silently fill with
  seeded-company jobs
- the onboarding intake is still too brittle for arbitrary CV layouts

The `S` and `T` packs are designed to address those issues without creating a
cross-track refactor collision.

## Future Pending Note

After `S0A` is complete, add a follow-up company-source catalog phase before any
large expansion of seeded companies. That phase should let the user add/import
companies into an explicit catalog, tag them by country/industry/source type,
and select them per discovery run. Do not add more companies to an automatically
active seeded list.

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
- `phase_Q6A_local_provider_adapters.md`
  - extracted local gateway and Ollama generation into a shared local-provider adapter
- `phase_Q6B_openai_claude_adapters.md`
  - extracted OpenAI and Claude request bodies into thin cloud adapters
- `phase_Q6C_gemini_adapter_and_router_cleanup.md`
  - extracted Gemini request execution into an adapter and completed the router cleanup without changing public contracts
- `phase_T1_source_dossier_and_multi_file_provenance.md`
  - persisted ordered per-source onboarding dossiers and clean active-dossier replacement
- `phase_T2_normalized_markdown_intake_layer.md`
  - added deterministic normalized source blocks for provider intake prompts
- `phase_T3_schema_safe_canonical_promotion.md`
  - centralized provider draft promotion before strict canonical schema ingestion
- `phase_T4_review_surface_and_field_provenance.md`
  - added provenance-friendly review payloads and editable key identity fields
