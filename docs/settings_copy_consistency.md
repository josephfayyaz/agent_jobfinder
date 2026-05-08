# Settings Copy Consistency

This pass reviewed and aligned user-facing copy across provider and settings surfaces.

## Purpose

After the settings hardening passes (specs 016–019), the backend contract no longer
exposes URLs, model names, secrets, or local paths.  This pass ensures the rendered
HTML surfaces reflect the same principle in their placeholder and label copy.

## Surfaces reviewed

- `/ui/settings` (legacy Jinja renderer — `settings.html` + partials)
- `/ui/onboarding` (legacy onboarding renderer — `onboarding.html` + `step_provider.html`)
- `/settings/current` (public JSON endpoint)
- `/api/vue/settings` (Vue-safe JSON endpoint)
- `/app/settings` (Vue SPA bridge)
- `/app/onboarding` (Vue SPA bridge)
- `frontend/static/onboarding/hydrate.js` (onboarding hydration script)
- `job_agent/cli.py` (`job-agent settings show` terminal output)

## Safe vocabulary used

```
Configured
Not configured
Available
Unavailable
Local provider configured
Remote provider configured
Leave blank to keep the current setting
Leave blank to use the current saved address
Leave blank to use the default local address
No Secret Values Rendered
No Local Paths Rendered
```

## Copy changed

### `frontend/templates/partials/settings/provider_section.html`

- Removed model name `gpt-oss-20b` from local provider hint copy
- Label: `Local Gateway URL` → `Local Gateway Address`
- Placeholder: `http://localhost:1234/v1` → `Leave blank to use the current saved address`
- Placeholder: `Enter the loaded local model name` → `Leave blank to keep the current setting`
- Label: `Ollama URL` → `Ollama Address`
- Placeholder: `http://localhost:11434` → `Leave blank to use the current saved address`
- Placeholder: `Enter the local model name` → `Leave blank to keep the current setting`

### `frontend/templates/partials/onboarding/step_provider.html`

- Label: `Gateway URL` → `Gateway Address`
- Cleared `value="http://localhost:1234/v1"` → `value=""` (JS fallback handles default)
- Placeholder: `http://localhost:1234/v1` → `Leave blank to use the default local address`
- Label: `Ollama URL` → `Ollama Address`
- Cleared `value="http://localhost:11434"` → `value=""` (JS fallback handles default)
- Placeholder: `http://localhost:11434` → `Leave blank to use the default local address`
- Placeholder: `sk-...` → `Enter your API key`
- Placeholder: `AIza...` → `Enter your API key`
- Placeholder: `sk-ant-...` → `Enter your API key`

## Copy left unchanged

- `frontend/static/settings/provider.js` — internal JS fallback defaults
  (`"http://localhost:1234/v1"` and `"http://localhost:11434"` are default values
  sent to the backend when fields are left blank, never rendered as copy)
- `frontend/static/onboarding/intake.js` — same pattern
- `frontend/static/onboarding/hydrate.js` — already uses `"Configured"` placeholder
- `job_agent/cli.py` — terminal output; `localhost:8000` is expected UX for a CLI tool
- Vue `SettingsPage.vue` and `OnboardingPage.vue` — already fully safe read-only shells

## No contracts expanded

No fields were added to `/settings/current`, `/api/vue/settings`, or any backend endpoint.

## No secrets or paths exposed

No secret values, masked secrets, API keys, model names, local filesystem paths,
base URLs, or provider endpoints are rendered to users on any of the reviewed surfaces.
