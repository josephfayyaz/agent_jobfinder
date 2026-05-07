# Phase K — Provider Controller Deduplication

Status: complete  
Completed: 2026-05-07

## Outcome

The duplicated provider validation and save-payload logic shared by onboarding
and settings was extracted into one global helper:

- `frontend/static/provider_controller.js`

Onboarding and settings now both use the shared helper for:

- provider flags
- validation request payloads
- save-payload defaults
- LM Studio / Ollama single-model assignment
- shared local-model default selection

## Key Files

- `frontend/static/provider_controller.js`
- `frontend/static/onboarding/core.js`
- `frontend/static/onboarding/intake.js`
- `frontend/static/settings/core.js`
- `frontend/static/settings/provider.js`
- `frontend/templates/onboarding.html`
- `frontend/templates/settings.html`

## Notes

- DOM-specific visibility and status rendering stayed local to each screen.
- Backend routes and provider payload contracts were unchanged.

## Verification

- `71 passed` across the combined touched-suite verification pass
- `ruff check job_agent ...` passed
