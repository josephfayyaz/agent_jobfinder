# Phase R5 — Validation And Smoke Audit

## Goal

Verify the R1-R4 discovery rollout end to end in the `ML` environment with a
repeatable smoke audit that proves the release workflow is working before the
larger 20-user audit is attempted later.

This phase is intentionally not the final 20-user audit. It prepares and
verifies the discovery system at a smaller but meaningful scale.

## Scope

Validate all of the following:

- one-provider whole-workflow contract still holds
- one-country search contract works
- JobSpy-only discovery path works
- multi-role fan-out works
- candidate-fit thresholding works
- default visible cap works
- progress reporting works
- zero-result and failure states are readable

## Read these files first

1. All files changed in R1-R4
2. `job_agent/TEST_HANDOFF.md`
3. `mac_full_test_data_temp/bootstrap.sh`
4. `mac_full_test_data_temp/onboarding_audit.py`
5. `mac_full_test_data_temp/role_suggestion_audit.py`

## Implementation instructions

### Part 1: Discovery smoke harness

Add a small discovery smoke harness under `mac_full_test_data_temp/`.

Recommended new files:

- `mac_full_test_data_temp/discovery_smoke_audit.py`
- `mac_full_test_data_temp/run_discovery_smoke_audit.sh`

Required traits:

- must require `ML` python
- must start from clean disposable runtime state
- must use the active local app endpoints rather than mocking the whole flow
- must cover at least `3` representative synthetic profiles

Suggested profile mix:

1. English-only technical profile
2. multilingual profile with weak local-language proficiency
3. non-technical profile

### Part 2: Verification targets

The smoke audit must verify:

1. provider validation/setup works
2. one-country discovery setting persists
3. desired roles persist
4. discovery task starts and reaches terminal state
5. zero-result runs are reported correctly if they happen
6. successful runs produce a visible summary payload
7. visible jobs are thresholded and capped correctly
8. no run silently “succeeds” when JobSpy is disabled or unavailable

### Part 3: TEST_HANDOFF update

Update `job_agent/TEST_HANDOFF.md` at the end of the phase so it reflects:

- that the discovery spec pack has been implemented up to the smoke-audit level
- what was verified
- what still remains for the later 20-user audit

### Part 4: Full regression

Run a focused regression set in `ML`. At minimum include the tests touched by
R1-R4 plus the new smoke-audit harness command.

If one of your design choices required deviating from these specs, document it
clearly in the completion report.

## Acceptance criteria

1. A repeatable discovery smoke audit exists under `mac_full_test_data_temp/`.
2. The smoke audit validates at least 3 representative profiles.
3. `TEST_HANDOFF.md` is current.
4. Regression commands pass in `ML`.

## Minimum validation commands

Run these in `ML` and include exact outputs in the report:

```bash
CONDA_BASE="$(conda info --base 2>/dev/null)"
"$CONDA_BASE/envs/ML/bin/python" -m pytest tests/test_onboarding.py tests/test_search_profile_preferences.py tests/test_jobspy_scheduler.py tests/test_api.py tests/test_e2e_full_journey.py --tb=short -q
```

And run the new harness:

```bash
bash mac_full_test_data_temp/run_discovery_smoke_audit.sh
```

If the smoke audit needs profile arguments, document the exact invocation.

## Completion report

When complete, write:

- `AGENT_SPECS/completed/phase_R5_validation_and_smoke_audit.md`

Use `AGENT_SPECS/completed/REPORT_TEMPLATE.md`.

Then append this phase to `completed_agent_specs.txt` using the required format
from `phase_R0_discovery_execution_order.md`.
