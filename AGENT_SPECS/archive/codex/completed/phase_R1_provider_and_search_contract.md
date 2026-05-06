# Phase R1 — Provider And Search Contract

## Goal

Stabilize the contract for the whole discovery-and-drafting workflow before any
new retrieval or scoring logic is added.

After this phase:

- the app uses exactly one active AI provider for the whole workflow
- the post-onboarding search profile supports exactly one country
- job-search languages with proficiency are captured and remain editable
- the persisted settings shape is consistent enough for later discovery phases

This is a contract phase. Keep it narrow. Do not implement JobSpy workflow
changes here.

## Required outcome

1. One provider is active for the whole workflow:
   - intake
   - fit scoring
   - readiness analysis
   - CV drafting
2. Search profile is constrained to:
   - one country only
   - up to 4 desired roles
   - one seniority target
   - editable spoken/job languages with proficiency
3. The current provider and search profile remain editable in Settings.
4. Provider changes in Settings apply to future AI work immediately.

## Non-goals

Do not do any of the following in R1:

- add or change JobSpy orchestration
- add discovery tasks or worker task kinds
- add Apify, Gmail, or ATS retrieval
- add progress bars
- add candidate fit scoring logic

## Read these files first

1. `job_agent/config.py`
2. `job_agent/llm.py`
3. `job_agent/routers/system.py`
4. `job_agent/routers/setup_state.py`
5. `job_agent/routers/ui_context.py`
6. `frontend/templates/onboarding.html`
7. `frontend/static/onboarding.js`
8. `frontend/templates/settings.html`
9. `frontend/static/settings.js`
10. `job_agent/search_preferences.py`
11. `tests/test_search_profile_preferences.py`
12. `tests/test_onboarding.py`

## Implementation instructions

### Part 1: Provider contract

Audit the active generation paths and make sure the product behavior matches
this rule:

- if `llm_provider_mode` is `lm_studio`, all AI workflow steps use LM Studio
- if `llm_provider_mode` is `ollama`, all AI workflow steps use Ollama
- if `llm_provider_mode` is `openai`, all AI workflow steps use OpenAI
- if `llm_provider_mode` is `anthropic`, all AI workflow steps use Anthropic

Do not introduce any phase-splitting logic such as:

- local for matching + cloud for drafting
- cloud for scoring + local for writing

If any current code path violates this rule, fix it now.

### Part 2: One-country search contract

The release workflow is now one-country only.

Use this compatibility rule:

- prefer keeping `job_search_countries` as the persisted settings field if that
  reduces blast radius
- normalize it to exactly one item everywhere in the user-facing workflow
- do not create a second parallel source of truth unless absolutely necessary

Required behavior:

- onboarding step 5 allows selecting or typing exactly one country
- Settings → Job Discovery allows editing exactly one country
- saving more than one country from UI or API must normalize or reject
  consistently
- `jobspy_discover_location` continues to derive from that one country

### Part 3: Language proficiency capture

The app must capture and persist job-search language preferences with
proficiency levels.

Required behavior:

- onboarding suggests languages from the candidate profile
- user can edit languages and proficiency levels
- settings page can edit the same fields later
- saved languages are reused by later discovery / scoring phases

Important:

- do not make language a hard exclusion rule in this phase
- this phase only establishes the persisted contract and the editing UX

### Part 4: UI copy and active provider clarity

Update onboarding/settings copy so the user understands:

- one active provider powers the whole workflow
- changing provider changes future AI behavior globally
- one country is currently supported for search

Do not add broad redesign work. Keep the existing UI style.

## Acceptance criteria

1. Saving search settings results in exactly one selected country.
2. The provider mode remains a single workflow-wide source of truth.
3. Languages and proficiency levels save and reload correctly.
4. Existing role-suggestion behavior remains intact.
5. No current onboarding or settings persistence tests regress.

## Required tests

Add or update targeted tests for:

- one-country normalization / rejection semantics
- provider mode remaining global across future workflow entry points
- onboarding persistence of language proficiency
- settings persistence of language proficiency

Minimum commands to run in `ML`:

```bash
CONDA_BASE="$(conda info --base 2>/dev/null)"
"$CONDA_BASE/envs/ML/bin/python" -m pytest tests/test_onboarding.py tests/test_search_profile_preferences.py --tb=short -q
```

If you touch more provider code, also run:

```bash
CONDA_BASE="$(conda info --base 2>/dev/null)"
"$CONDA_BASE/envs/ML/bin/python" -m pytest tests/test_provider_resilience.py tests/test_onboarding.py tests/test_search_profile_preferences.py --tb=short -q
```

## Completion report

When complete, write:

- `AGENT_SPECS/completed/phase_R1_provider_and_search_contract.md`

Use `AGENT_SPECS/completed/REPORT_TEMPLATE.md`.

Then append this phase to `completed_agent_specs.txt` using the required format
from `phase_R0_discovery_execution_order.md`.
