# Phase F0 — CV Quality Execution Order

## Purpose

This pack upgrades the CV workflow from "truthful but often too weak" to a
general-use, domain-neutral, reviewable system that can produce stronger CVs
for users in any field when the profile evidence is rich enough.

The validated current state is:

1. discovery and fit scoring now work meaningfully enough to feed CV testing
2. sparse profiles no longer produce hallucinated work history
3. CV output for thin profiles is truthful, but often visually underfilled and
   not competitive enough for real application use
4. the system still lacks:
   - a CV readiness gate
   - a manual JD-first workflow
   - structured requirement-to-evidence mapping
   - a real pre-PDF preview/edit step
   - a stronger domain-neutral rendering path

This is an execution pack, not a brainstorming note.

## Validated problem statement

The accepted runtime evidence is already recorded in:

- `/Users/youseffayyaz/Local_LLM/job_agent/TEST_HANDOFF.md`

Historical repo-local runtime artifacts for that evidence were intentionally
deleted when the polluted `mac_full_test_data_temp/` sandbox was replaced by
`temp_mac_test/`.

The core CV failure mode is:

1. user evidence may be sparse or partially structured
2. the app can now avoid hallucination, but not yet guide the user through
   readiness, review, and targeted improvement strongly enough
3. the CV generator still needs a domain-neutral evidence mapping layer and a
   better preview/rendering workflow

## Active scope

This pack covers only phases `F1` through `F6`:

1. `phase_F1_profile_readiness_and_onboarding_review_gate.md`
2. `phase_F2_manual_jd_intake_and_requirement_extraction.md`
3. `phase_F3_evidence_mapping_gap_model_and_cv_scoring.md`
4. `phase_F4_cv_preview_edit_and_safe_paraphrase_controls.md`
5. `phase_F5_domain_neutral_pdf_renderer_and_output_contract.md`
6. `phase_F6_real_cv_validation_and_quality_audit.md`

## Explicit non-goals

Do not implement any of the following in this pack:

- cover-letter automation beyond what already exists
- application auto-submit
- Gmail reply automation
- Apify integration
- new job discovery sources
- mixed-provider workflows
- fake LM Studio or fake provider test harnesses
- role-family assumptions that only fit tech users

## Global constraints

1. Use only the `ML` environment for commands, tests, and runtime checks.
2. If LM Studio or the selected active model is not actually available, stop
   and ask the user to load it. Do not substitute a fake provider unless the
   user explicitly approves it.
3. Keep the current single active provider model. Matching, CV drafting,
   reviewing, and polishing must continue to use the same configured provider.
4. Treat the candidate profile and structured fact sheet as the source of truth.
   The CV is an output artifact, not the canonical data model.
5. The implementation must stay general-use and domain-neutral. Do not hardwire
   tech assumptions such as GitHub, Python, cloud infrastructure, or portfolio
   projects as if they apply to all users.
6. All provider calls must continue to go through
   `/Users/youseffayyaz/Local_LLM/job_agent/llm.py`.
7. Use `apply_patch` for code edits.
8. Do not silently weaken the truthfulness guardrails added in the previous CV
   validation work.
9. Borrow ideas from external tools only at the workflow level. Do not ship a
   CV experience that looks like a re-skinned copy of `career-ops` in naming,
   page structure, section titles, report labels, or operator-facing jargon.
10. Prefer app-native labels and flows for end users. For example, use labels
    such as `Profile Readiness`, `Target Fit Map`, `Evidence Alignment`,
    `Application Gaps`, and `Recommended Improvements` rather than copying
    external terminology.
11. After each completed phase:
   - write a report in `/Users/youseffayyaz/Local_LLM/AGENT_SPECS/completed/`
   - append a completion line to
     `/Users/youseffayyaz/Local_LLM/completed_agent_specs.txt`
   - move the phase spec from `pending/codex/` to `archive/codex/` only after
     implementation and verification are actually complete

## Originality guardrails

The implementation should clearly feel like this product, not a clone of an
external repo.

Required differentiation points:

1. The user flow must stay app-first and database-backed, not file-operator
   driven.
2. UI section names, button text, and panel titles must be app-native and not
   copied from another repository's prompt pack or report style.
3. The CV preview should behave like an interactive review screen, not a
   markdown-ops report.
4. The final PDF renderer may improve visually, but should not copy another
   project's exact template, section ordering, or typography contract.
5. Domain-neutral behavior is required; avoid visible tech-first defaults in
   headings, examples, and section assumptions.

## Success definition for the pack

This pack is complete only when all of the following are true:

1. The app can accept either:
   - a discovered job
   - or a manually pasted job description / URL
   and run the same CV workflow.
2. The app can distinguish between:
   - profile ready for strong CV generation
   - usable with warnings
   - insufficient profile evidence
3. The app produces an explicit requirement-to-evidence map with 4-level gap
   classification.
4. The app exposes a pre-PDF preview/edit step.
5. Safe paraphrasing is allowed, but unsupported facts remain blocked.
6. Final output naming, persistence, and preview behavior are stable enough for
   real user review.
7. A real multi-user browser/runtime rerun with rich-enough profiles produces a
   more competitive and still truthful CV output than the current baseline.

## Required completion line format

Append completion entries to
`/Users/youseffayyaz/Local_LLM/completed_agent_specs.txt` in this format:

```text
phase_F1_profile_readiness_and_onboarding_review_gate.md — COMPLETE — 2026-05-01T21:10:00+02:00
```

Do not append anything until the phase is implemented, tested, and reported.
