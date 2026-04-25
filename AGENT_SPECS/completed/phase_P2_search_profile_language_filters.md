# Phase P2 — Search Profile + Language-Aware Discovery

## What changed

P2 upgrades onboarding and discovery from a single free-text location field to a real search profile:

- `job_search_countries` and `job_search_languages` are now first-class settings.
- The web onboarding flow now auto-suggests:
  - target countries
  - detected job-ready languages from the candidate fact sheet
  - role suggestions from the parsed profile
  - recommended discovery channels from roles + target countries
- Settings → Job Discovery now lets the user edit:
  - target countries
  - desired roles
  - allowed job-description languages with proficiency labels
- The Jobs list now filters out jobs whose detected description language is outside the user’s selected set, while `Show all` remains the escape hatch.
- Job rows now show detected description-language badges.
- CLI settings output and CLI onboarding were extended to understand the new search-profile fields.

## Key files

- `job_agent/search_preferences.py`
  - normalization for countries / roles / job-language preferences
  - lightweight language detection for job descriptions
  - candidate-driven search recommendations
- `job_agent/config.py`
  - new settings fields + parsing / overlay support
- `job_agent/main.py`
  - `/search/preferences/recommendations`
  - settings validation for new search-profile fields
  - default job-list language filtering
  - discovery location now follows the first selected country
- `job_agent/services/jobspy_service.py`
  - skips clearly out-of-language jobs during JobSpy discovery
- `job_agent/templates/onboarding.html`
  - smarter Step 5 with countries, job languages, detected role chips, and discovery-channel suggestions
- `job_agent/templates/settings.html`
  - richer Job Discovery section with language rows and source suggestions
- `job_agent/templates/jobs.html`
  - active filter visibility
- `job_agent/templates/partials/job_row.html`
  - detected job-language badges

## UX decisions

- UI language and job-description language remain separate concepts.
- The app does **not** force users to build a manual company list during onboarding.
  Instead, it asks for the higher-signal filters first: role, country, and readable job languages.
- Job-language defaults are inferred from the uploaded profile when possible, so most users do not need to enter them manually.
- Lower-confidence profile languages are not auto-selected by default; they remain editable suggestions.

## Verification

Commands run:

```bash
<python> -m pytest tests/test_search_profile_preferences.py tests/test_onboarding.py tests/test_settings_ui.py tests/test_setup_gate.py --tb=short -q
<python> -m pytest tests/test_seed_companies.py tests/test_search_profile_preferences.py --tb=short -q
<python> -m pytest --tb=short -q
<home>/miniforge3/envs/ML/bin/ruff check
```

Results:

- Full suite: `403 passed, 4 warnings`
- Ruff: clean

Warnings are the existing `duckduckgo_search` rename warning from `company_resolver.py`, not a P2 regression.

## Follow-up recommendation

The next high-value step should not be “seed more static companies.” It should be:

1. learn companies from the jobs the user keeps / applies to
2. propose company watchlist additions from those real signals
3. only then expand automatic company discovery

That keeps onboarding fast and makes company recommendations evidence-driven instead of generic.
