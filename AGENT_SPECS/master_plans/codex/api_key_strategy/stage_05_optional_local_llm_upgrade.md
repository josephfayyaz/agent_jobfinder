# Stage 05 — Optional Local LLM Upgrade Path

## Goal

Preserve local LLM as a strong differentiator, but position it correctly:

- optional
- advanced
- recommended only for users with suitable hardware

## Product Position

Cloud BYOK remains the default.

Local LLM is shown as:

- `Private and low-cost after setup`
- `Best for stronger computers`
- `Optional advanced mode`

## UX Entry Points

Do not put this in the main happy path.

Instead add:

- onboarding link:
  `I want to use my own computer instead`
- settings card:
  `Switch to local LLM`
- help page:
  `Local setup requirements`

## Recommended Guidance

Show rough hardware guidance, not fragile benchmark promises:

- `Basic laptop: use cloud APIs`
- `Modern laptop with enough RAM/GPU headroom: local may work`
- `Power user machine: local is a strong option`

## Setup Flow

Add a local setup checklist:

1. install LM Studio
2. download a compatible small model
3. start local server
4. test provider
5. optionally set local as primary

## Product Rule

Never force users to decide on local setup before they understand the app’s value.

## File Targets

- `frontend/templates/onboarding.html`
- `frontend/templates/settings.html`
- `frontend/templates/help.html`
- `frontend/static/onboarding.js`
- `frontend/static/settings.js`
- `job_agent/routers/system.py`

## Acceptance Criteria

- local LLM remains available
- weak-hardware users are not pressured into it
- strong-hardware users can discover it easily
