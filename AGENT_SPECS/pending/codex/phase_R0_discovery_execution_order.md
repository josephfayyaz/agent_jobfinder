# Phase R0 — Discovery Implementation Pack Order

## Purpose

This file is the execution index for the discovery / job-matching rollout that
starts after onboarding and role-suggestion stabilization.

The downstream implementation agent must execute the specs in this exact order.
Do not skip ahead. Do not merge two phases into one unless the later phase
explicitly depends on the earlier change and both can still be validated
cleanly.

## Active release scope

This pack is intentionally narrow.

- Active retrieval source for this phase: `JobSpy` only
- Active AI model/provider for this phase: exactly one configured provider
- Active country scope for this phase: exactly one selected country
- Active role scope for this phase: up to `4` desired roles
- Active queue cap for this phase: at most `80` visible jobs after scoring
- Active default visibility threshold for this phase: `70` fit score

## Explicit non-goals for this pack

Do not implement any of the following in R1-R5:

- Apify integration
- Gmail discovery ingestion changes
- ATS retrieval activation in the user-facing discovery flow
- career-page discovery as a primary user path
- mixed-provider workflows where one provider matches and another writes
- multi-country or EU-wide discovery
- full 20-user discovery audit

Keep extension points for later work, but do not activate them in the release
workflow for this pack.

## Global constraints for every spec in this pack

1. Use the conda environment `ML` for every command, test, and script.
2. Do not create a new virtualenv.
3. Do not bypass `LLMRouter`; all provider-based generation must continue to go
   through `job_agent/llm.py`.
4. Preserve existing runtime data conventions.
5. Use the current single-owner model of the app; do not introduce multi-user
   orchestration.
6. Every completed phase must:
   - write a completion report in `AGENT_SPECS/completed/`
   - append a completion line to `completed_agent_specs.txt`
   - move the spec out of `pending/codex/` only after the phase is actually
     complete and verified

## Execution order

1. `phase_R1_provider_and_search_contract.md`
2. `phase_R2_jobspy_discovery_backend.md`
3. `phase_R3_candidate_fit_scoring.md`
4. `phase_R4_jobs_progress_and_results_ui.md`
5. `phase_R5_validation_and_smoke_audit.md`

## Suggested handoff batches

If the user wants to hand work to GPT-5.3 Codex in batches, use these groups:

1. Batch A:
   - `phase_R1_provider_and_search_contract.md`
   - `phase_R2_jobspy_discovery_backend.md`
2. Batch B:
   - `phase_R3_candidate_fit_scoring.md`
   - `phase_R4_jobs_progress_and_results_ui.md`
3. Batch C:
   - `phase_R5_validation_and_smoke_audit.md`

## Required completion line format

Append completion entries to `completed_agent_specs.txt` in this format:

```text
phase_R1_provider_and_search_contract.md — COMPLETE — 2026-04-29T19:15:00+02:00
```

Do not append anything before the implementation, verification, and report are
finished for that specific phase.
