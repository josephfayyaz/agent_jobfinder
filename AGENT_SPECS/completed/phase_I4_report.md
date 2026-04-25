# Codex Completion Report — Phase I4

## Phase
PHASE I4 — CV Output Folder Selection + Company/Date Naming

## Status
COMPLETE

## Completion Timestamp
2026-04-23T00:29:16+02:00

## Summary
Implemented configurable CV/cover-letter output folder support and company/date-based artifact naming. Generated resume TeX filenames now follow `<Company>_<Date>_<DraftID8>.tex`, resulting PDFs inherit the same stem, and generated cover letters are now persisted as `<Company>_<Date>_<DraftID8>_cover.txt`. The output folder is now exposed in onboarding and the web settings page, and persisted through the existing settings save flow.

## Files Added
- `tests/test_cv_output_folder.py` — coverage for filename format, auto-creation of artifact directory, and `/settings/save` acceptance of `artifacts_dir`
- `AGENT_SPECS/completed/phase_I4_report.md`

## Files Modified
- `job_agent/config.py` — clarified `artifacts_dir` setting description, added YAML overlay mapping, and converted overlay value to `Path`
- `job_agent/user_config.py` — added `artifacts_dir` to editable settings fields
- `config/user_settings.example.yml` — documented output folder setting and default
- `job_agent/services/documents.py` — added safe filename/stem helpers and switched TeX naming to `<Company>_<Date>_<DraftID8>.tex`
- `job_agent/services/cover_letter.py` — persisted generated cover letters to `_cover.txt` artifacts using the same stem convention
- `job_agent/onboard.py` — added onboarding prompt to set CV output folder
- `job_agent/templates/settings.html` — added System-section `CV Output Folder` input and wired system save action for `artifacts_dir`
- `tests/test_cover_letter.py` — ensured cover-letter generation test writes into a temp artifact directory and asserts `_cover.txt` save
- `completed_agent_specs.txt` — appended I4 completion entry

## Behavior Changes
- Users can configure `artifacts_dir` via YAML settings, onboarding wizard, and web settings UI
- Resume artifact naming is now company/date/draft-based for easier lookup
- Cover letters are now saved as text artifacts in the configured output folder
- Runtime settings save endpoint now accepts and persists `artifacts_dir`

## Verification
- `<python> -m pytest tests/test_cv_output_folder.py tests/test_documents.py tests/test_cover_letter.py tests/test_onboarding.py tests/test_settings_ui.py tests/test_user_settings.py tests/test_workflows.py tests/test_candidate_workflow.py --tb=short -q` → 35 passed in 1.12s
- `<python> -m pytest --tb=short -q` → 349 passed in 3.87s
- `<python> -m ruff check` → All checks passed
