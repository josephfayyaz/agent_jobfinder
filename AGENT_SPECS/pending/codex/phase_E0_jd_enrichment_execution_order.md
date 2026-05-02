# Phase E0 — Job Description Enrichment Execution Order

## Purpose

This pack fixes the current discovery bottleneck confirmed in real browser runs:
the app retrieves contextually plausible jobs, but thin `JobSpy` / LinkedIn job
descriptions cause weak fallback scoring and hide jobs from the default queue.

This is an execution pack, not a brainstorming note. The implementation agent
must follow these phases in order.

## Validated problem statement

The accepted runtime evidence is already recorded in:

- `/Users/youseffayyaz/Local_LLM/job_agent/TEST_HANDOFF.md`

Historical repo-local runtime artifacts for that evidence were intentionally
deleted when the polluted `mac_full_test_data_temp/` sandbox was replaced by
`temp_mac_test/`.

The core failure mode is:

1. discovery retrieves real jobs
2. saved rows often contain thin LinkedIn board text
3. enrichment quality is inconsistent
4. provider scoring falls back too early
5. the default thresholded queue looks empty or misleading

## Active scope

This pack covers only phases `A` through `D` below:

1. `phase_E1_truthful_jd_readiness_and_quality_gate.md`
2. `phase_E2_selective_jobspy_detail_enrichment.md`
3. `phase_E3_structured_extraction_and_source_priority.md`
4. `phase_E4_queue_ui_and_real_validation.md`

## Explicit non-goals

Do not implement any of the following in this pack:

- Apify integration
- Gmail-based job discovery
- new browser-automation-based scraping
- multi-country or EU-wide discovery
- mixed-provider workflows
- fake LM Studio or fake provider test harnesses
- a full 20-user discovery audit

## Global constraints

1. Use only the `ML` environment for commands, tests, and runtime checks.
2. If LM Studio or the selected active model is not actually available, stop and
   ask the user to load it. Do not substitute a fake provider unless the user
   explicitly approves it.
3. Keep the current single active provider model. Matching and later CV work
   must continue to use the same configured provider.
4. Keep `JobSpy` as the active board-discovery source in this pack.
5. Keep the current ATS integrations active; improve source priority and
   enrichment quality, but do not expand to new ATS families in this pack.
6. All provider calls must continue to go through
   `/Users/youseffayyaz/Local_LLM/job_agent/llm.py`.
7. Do not introduce a destructive database reset as part of this pack.
8. Use `apply_patch` for code edits.
9. After each completed phase:
   - write a report in `/Users/youseffayyaz/Local_LLM/AGENT_SPECS/completed/`
   - append a completion line to
     `/Users/youseffayyaz/Local_LLM/completed_agent_specs.txt`
   - move the phase spec from `pending/codex/` to `archive/codex/` only after
     implementation and verification are actually complete

## Success definition for the pack

This pack is complete only when all of the following are true:

1. Weak or missing job descriptions no longer masquerade as trustworthy low-fit
   candidate scores.
2. Discovery preserves a truthful distinction between:
   - retrieved jobs
   - jobs awaiting enrichment
   - jobs ready for provider scoring
3. Structured ATS or company-page descriptions are preferred over thin board
   snippets whenever available.
4. The jobs UI clearly shows why a job is not yet fully scored.
5. A real two-user browser rerun with the configured live provider produces a
   more truthful queue than the current fallback-heavy baseline.

## Required completion line format

Append completion entries to
`/Users/youseffayyaz/Local_LLM/completed_agent_specs.txt` in this format:

```text
phase_E1_truthful_jd_readiness_and_quality_gate.md — COMPLETE — 2026-05-01T18:10:00+02:00
```

Do not append anything until the phase is implemented, tested, and reported.
