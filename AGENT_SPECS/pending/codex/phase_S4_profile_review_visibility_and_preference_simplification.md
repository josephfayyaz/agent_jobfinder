# Phase S4 — Profile Review Visibility and Preference Simplification

## Dependency note

Do not start this phase until `T1` through `T4` are complete.

This phase is the user-facing simplification layer on top of the intake
generalization work. Without the `T` substrate, it would expose more fields
without making their source and stability trustworthy enough.

## Goal

Make the onboarding review step honest about which person/preference fields the
system will actually carry forward, while keeping onboarding simpler.

## Why this phase exists

The current canonical fact sheet supports more identity and preference fields
than the onboarding review UI exposes. That creates a trust problem: some
fields can be inferred or persisted without the user clearly reviewing them.

## Fields that currently matter in the canonical fact sheet

### Person / contact

- `person.full_name`
- `person.preferred_name`
- `person.headline`
- `person.current_location`
- `person.contact.email`
- `person.contact.phone`
- `person.contact.linkedin_url`
- `person.contact.github_url`
- `person.contact.portfolio_url`

### Match profile

- `match_profile.location_preferences.preferred_cities`
- `match_profile.location_preferences.preferred_countries`
- `match_profile.location_preferences.remote_preference`
- `match_profile.location_preferences.hybrid_preference`
- `match_profile.location_preferences.onsite_preference`
- `match_profile.location_preferences.willing_to_relocate`
- `match_profile.work_authorization`
- `match_profile.availability.*`

## User decision for now

- do not ask remote / hybrid / onsite preference in onboarding
- do not ask availability-to-start in onboarding
- assume immediate availability for now
- keep future support possible in the schema and backend

## Required behavior after this phase

1. The onboarding review step must expose the important persisted identity fields:
   - full name
   - email
   - phone
   - current location
   - LinkedIn
   - GitHub
   - headline
   - work authorization
2. It must expose job-search geography preferences clearly:
   - target country
   - optional region/city
3. It must not add new remote/hybrid/onsite or availability questions yet.
4. If those fields exist in canonical JSON, they may stay stored but should not
   drive onboarding complexity.

## Files to inspect first

- `/Users/youseffayyaz/Local_LLM/frontend/static/onboarding/review.js`
- `/Users/youseffayyaz/Local_LLM/frontend/templates/partials/onboarding/step_review.html`
- `/Users/youseffayyaz/Local_LLM/job_agent/resources/fact_sheet/fact_sheet_schema.json`
- `/Users/youseffayyaz/Local_LLM/job_agent/services/intake.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/services/fact_sheet_json.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/routers/candidates.py`

## Exact implementation requirements

### 1. Expand review visibility

Update the rendered review editor to include the persisted person/contact fields
listed above.

At minimum the user must be able to see and edit:

- name
- email
- phone
- current location
- LinkedIn
- GitHub
- headline
- work authorization

### 2. Keep the UI simple

Do not add sections for:

- remote policy preference
- hybrid preference
- onsite preference
- availability/start-date

If those fields already exist in the canonical object, preserve them without
surfacing new mandatory questions.

### 3. Save semantics

Saving the profile review must overwrite the canonical fact sheet cleanly and
must not silently drop the new visible person/contact fields.

## Do not touch

- discovery queue behavior
- draft-detail UI
- provider configuration

## Tests required

1. review UI renders the expanded identity fields
2. save payload includes the expanded visible fields
3. save path preserves canonical fact sheet validity
4. remote/availability questions are not added to onboarding

## Browser validation required

1. Finish intake.
2. Open review step.
3. Confirm the expanded identity block is visible.
4. Edit at least one field and save.
5. Confirm the next step uses the updated values.
