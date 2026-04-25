# Stage 01 — Billing Truth + Provider Choice

## Goal

Make the first-run experience honest and friction-light:

- user understands that web subscriptions and API billing are separate
- user selects a preferred cloud provider early
- local LLM is shown as an optional later upgrade, not a startup requirement

## Why This Stage Comes First

Most confusion will happen before a key is even pasted.
If users misunderstand billing, they will blame the product for a provider policy.

## User Experience

Add a dedicated onboarding step:

### Card 1 — OpenAI
- short description
- `Best for:` broad compatibility
- `You need:` an OpenAI API key with billing/credits
- CTA: `Use OpenAI`

### Card 2 — Claude
- short description
- `Best for:` stronger writing quality
- `You need:` a Claude API key with billing/credits
- CTA: `Use Claude`

### Card 3 — Both
- short description
- `Best for:` fallback if one runs out or fails
- CTA: `Use Both`

### Optional card — Local LLM later
- copy:
  `Have a strong computer? You can later switch to local LLM for private, low-cost usage.`
- CTA:
  `Show local setup later`

## Mandatory Copy

Show this message plainly:

`ChatGPT and Claude subscriptions do not automatically include API usage.`

Follow with:

- `You pay the provider directly.`
- `Your key stays on your machine.`
- `You can change providers any time in Settings.`

## Implementation Targets

- `frontend/templates/onboarding.html`
- `frontend/static/onboarding.js`
- `job_agent/onboard.py`
- `job_agent/routers/setup_state.py`
- `job_agent/routers/system.py`

## Data Model

Persist:

- `llm_provider_mode`
- `preferred_writer_provider`
- `preferred_small_provider`
- `provider_setup_completed`
- `provider_setup_mode` with values:
  - `openai`
  - `anthropic`
  - `mixed`
  - `local_later`

## Acceptance Criteria

- onboarding clearly explains billing separation
- user can choose OpenAI, Claude, or both
- local LLM is optional and not blocking
- setup status reflects cloud-ready vs local-ready accurately
- user can continue later only after choosing a provider mode
