# Phase Q7 — Provider Validation And Smoke Audit

Status: pending

## Goal

Finish the provider architecture work by aligning validation, smoke checks, and
real workflow expectations.

## Write Scope

- `job_agent/routers/system.py`
- `job_agent/provider_smoke.py`
- `tests/test_provider_resilience.py`
- `tests/test_provider_smoke.py`
- `tests/test_onboarding.py`

## Do Not Touch

- database schema
- frontend theme/UI
- CV rendering

## Exact Changes

### 1. Keep `/providers/validate` lightweight but truthful

Do not make the route run a full onboarding call.

Instead:

- keep the current small live probe
- add a note in the response detail if the provider family still requires
  large-prompt smoke verification

For Gemini and Local Gateway, append:

```python
" Large-prompt workflow behavior should still be verified with provider-smoke."
```

### 2. Add a smoke-aware internal QA path

If there is already a QA or diagnostics surface, add a follow-up action there.
If not, keep this limited to the CLI/module smoke path created in Q3.

### 3. Add realistic provider test matrix

At minimum, verify these cases:

- Gemini: validation passes, large-intake smoke path also passes
- Local Gateway: validation passes, context-too-large smoke path maps clearly
- OpenAI: usage metadata is present in smoke path

## Verification

Run:

```bash
pytest tests/test_provider_resilience.py tests/test_provider_smoke.py tests/test_onboarding.py -q
ruff check job_agent/routers/system.py job_agent/provider_smoke.py tests/test_provider_resilience.py tests/test_provider_smoke.py tests/test_onboarding.py
```

## Completion Rule

This provider-runtime program is only complete when:

- validation is no longer confused with workflow readiness
- smoke checks cover a large structured prompt
- provider failures map to explicit categories

## Completion Handoff

When this phase is complete:

1. Move this spec to `AGENT_SPECS/archive/codex/completed/`
2. Write a completion report in `AGENT_SPECS/completed/`
3. Add a line to `completed_agent_specs.txt`:
   `phase_Q7_provider_validation_and_smoke_audit.md — COMPLETE — <timestamp> — aligned lightweight validation with realistic smoke verification and audit coverage`
