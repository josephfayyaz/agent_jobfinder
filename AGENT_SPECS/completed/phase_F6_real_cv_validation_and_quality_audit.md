# Phase F6 — Real CV Validation And Quality Audit

Status: COMPLETE  
Completed: 2026-05-01

## Scope completed

- Ran the required F6 regression suite in the `ML` environment.
- Performed live CV workflow validation against the real app and the real LM Studio `openai/gpt-oss-20b` model.
- Saved runtime CV artifacts under `mac_full_test_data_temp/results/`.
- Debugged real runtime failures discovered during F6.
- Proved persisted draft review state survives restart and remains bound to the original candidate.

## Code fixes made during F6

### 1. Settings overlay bug

Problem:
- Runtime YAML reload ignored:
  - `jobspy_detail_enrichment_enabled`
  - `jobspy_detail_enrichment_limit`

Fix:
- Added both keys to the YAML overlay mapping in `job_agent/config.py`.

Regression:
- `tests/test_user_settings.py::test_yaml_overlay_loads_jobspy_detail_enrichment_fields`

### 2. Draft route UUID bug

Problem:
- `GET /drafts/{id}` and `POST /drafts/{id}/approve` could 500 because UUID path params were passed to SQLAlchemy as raw strings.

Fix:
- Added UUID coercion in `job_agent/routers/drafts.py`.

Regression:
- `tests/test_api.py::test_get_draft_accepts_uuid_string_path`
- `tests/test_api.py::test_approve_draft_accepts_uuid_string_path`

### 3. Draft candidate persistence bug

Problem:
- Saved drafts did not store `candidate_id`.
- Preview/rerender/clarification logic reloaded the current default candidate instead of the candidate used when the draft was created.
- After switching candidate and restarting the app, old drafts could be re-evaluated against the wrong person.

Fix:
- Added nullable `candidate_id` to `resume_drafts`.
- Added additive migration in `job_agent/db.py`.
- `CVWorkflowService.queue_cv_workflow()` now snapshots `candidate_id` into task payload.
- `CVWorkflowService.run_cv_workflow()` now loads context from payload `candidate_id` and persists it on the created draft.
- Draft preview/rerender/clarification paths now reload context from `draft.candidate_id`.

Regression:
- `tests/test_candidate_workflow.py::test_load_context_uses_explicit_candidate_id_over_changed_default`
- `tests/test_candidate_workflow.py::test_queue_cv_workflow_persists_candidate_id_snapshot`
- `tests/test_candidate_workflow.py::test_run_cv_workflow_uses_candidate_dict_when_candidate_set`
- `tests/test_api.py::test_preview_state_uses_draft_candidate_after_default_candidate_switch`

## Validation run

Interpreter:
- `/Users/youseffayyaz/miniforge3/envs/ML/bin/python`

Passed:

```bash
/Users/youseffayyaz/miniforge3/envs/ML/bin/python -m pytest tests/test_candidate_workflow.py tests/test_api.py tests/test_ui_draft_detail.py tests/test_bullet_clarify.py -q
# 85 passed

/Users/youseffayyaz/miniforge3/envs/ML/bin/python -m pytest tests/test_documents.py tests/test_workflows.py tests/test_candidate_workflow.py tests/test_api.py -q
# 91 passed

/Users/youseffayyaz/miniforge3/envs/ML/bin/python -m ruff check \
  job_agent/models.py job_agent/db.py job_agent/schemas.py \
  job_agent/services/workflows.py job_agent/routers/drafts.py \
  job_agent/services/bullet_clarify.py job_agent/config.py \
  tests/test_documents.py tests/test_workflows.py \
  tests/test_candidate_workflow.py tests/test_api.py tests/test_user_settings.py
# All checks passed
```

## Live runtime artifacts

Existing F6 audit outputs retained:
- `mac_full_test_data_temp/results/f6_yousef_discovered_report.json`
- `mac_full_test_data_temp/results/f6_rina_manual_report.json`
- `mac_full_test_data_temp/results/f6_farah_sparse_control_report.json`
- `mac_full_test_data_temp/results/f6_cv_runtime_validation_summary.json`

Post-fix persistence proof artifacts:
- `mac_full_test_data_temp/results/f6_rina_manual_postfix_report.json`
- `mac_full_test_data_temp/results/f6_candidate_binding_before_restart.json`
- `mac_full_test_data_temp/results/f6_candidate_binding_after_restart.json`

## Live conclusions

- Rich profiles can now produce materially stronger CVs than sparse profiles.
- Sparse profiles still remain truthful and do not invent unsupported work history.
- Manual JD flow works end-to-end with the live provider.
- Persisted drafts now remain tied to the original candidate even after candidate switching and app restart.

## Remaining product recommendations from F6

- Tighten preview gating for rich profiles: several Rina and Yousef bullets still score well while carrying `needs_user_confirmation` or `adjacent_inference`.
- Strengthen JD requirement filtering: `recommended_improvements` still contains some heading/boilerplate pollution.
- Consider blocking final approval when pending preview confirmations exceed a stricter threshold, or require explicit user acknowledgment before final PDF export.
