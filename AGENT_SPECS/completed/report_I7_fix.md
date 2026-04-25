# Codex Completion Report — I7 Fix

## Phase
I7 Fix — confirmed_facts flow + apply.html XSS

## Status
COMPLETE

## Completion Timestamp
2026-04-23T14:07:28+02:00

## Summary
Fixed the semantic break in the web apply flow by carrying confirmed clarifying answers from `WorkflowTask.payload["confirmed_facts"]` into the writer prompt. The writer now receives a dedicated candidate clarifications block and can use those user-confirmed details to strengthen relevant CV bullets without inventing unsupported experience. Also replaced unsafe `innerHTML` rendering of parser/LLM-provided apply-page text with DOM creation and `textContent`.

## Files Modified
- `job_agent/services/prompts.py` — added `confirmed_facts` to `build_writer_user_prompt()` and inserted the candidate clarifications prompt block.
- `job_agent/services/workflows.py` — filters confirmed, non-empty user answers in `run_cv_workflow()` and passes them to `_generate_draft()`.
- `job_agent/templates/apply.html` — replaced unsafe list/question rendering with `createElement()`, `textContent`, and `appendChild()`.

## Files Added
- `tests/test_i7_confirmed_facts.py` — regression coverage for confirmed-facts pass-through and safe apply-template rendering patterns.

## Verification
- `<python> -m pytest tests/test_i7_confirmed_facts.py -v` → 2 passed
- `<python> -m pytest tests/test_i7_confirmed_facts.py tests/test_web_apply_flow.py --tb=short -q` → 6 passed
- `<python> -m pytest --tb=short -q` → 363 passed, 4 warnings
- `<home>/miniforge3/envs/ML/bin/ruff check job_agent/services/prompts.py job_agent/services/workflows.py tests/test_i7_confirmed_facts.py` → All checks passed
- `<home>/miniforge3/envs/ML/bin/ruff check` → All checks passed

## Notes
The spec's exact focused ruff command included `job_agent/templates/apply.html`; Ruff parses explicit file arguments as Python and therefore cannot lint a Jinja/HTML template. The normal project ruff check passes, and the template safety change is covered by a regression test plus source inspection.
