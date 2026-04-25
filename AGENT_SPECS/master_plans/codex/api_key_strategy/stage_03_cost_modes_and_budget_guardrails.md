# Stage 03 — Cost Modes + Budget Guardrails

## Goal

Make the product affordable and predictable for normal users.

## Product Decision

Expose **modes**, not raw model complexity first.

Modes:

- `Economy`
- `Balanced`
- `Premium`

Optional advanced view:

- exact provider/model mapping

## Recommended Defaults

### Economy
- cheapest supported model
- use for parsing, scoring, fit-gap analysis, keyword extraction

### Balanced
- cheap model for analysis
- better model for CV writing and cover letter generation

### Premium
- stronger writer and reviewer models
- slower and more expensive

## Budget Controls

Add user settings:

- `monthly_budget_soft_cap`
- `stop_after_soft_cap`
- `auto_switch_to_economy`
- `disable_premium_when_low_credit`

## UI Requirements

In settings, show:

- current cost mode
- estimated monthly usage examples
- soft cap input
- explanation text

Example copy:

- `Light search: 20 drafts / month`
- `Active search: 60 drafts / month`
- `Heavy search: 120 drafts / month`

## Runtime Behavior

Before expensive actions:

- estimate cost class
- if user is near cap:
  - warn
  - suggest switching mode
  - optionally auto-switch

## File Targets

- `job_agent/config.py`
- `job_agent/user_config.py`
- `job_agent/llm.py`
- `job_agent/services/workflows.py`
- `frontend/templates/settings.html`
- `frontend/static/settings.js`

## Acceptance Criteria

- user can pick a simple cost mode
- user can set a monthly soft cap
- app can automatically downgrade quality when budget is tight
- premium usage never surprises the user
