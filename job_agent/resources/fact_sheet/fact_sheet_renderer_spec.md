# Fact Sheet Renderer Spec

This document defines how to render the canonical JSON fact sheet into a stable human-readable `master_fact_sheet.txt`.

Goal:

- keep the rendered output recruiter-readable
- keep section names stable across versions
- preserve verified facts, gaps, and conflicts
- make the text suitable for resume generation, cover letters, and manual review

Use this with:

- `fact_sheet_schema.json`
- `claude_fact_sheet_prompt_pack.md`

## Rendering Rules

1. The rendered file is plain text only.
2. The file starts with `MASTER FACT SHEET`.
3. Section order must be deterministic.
4. Null or unknown values should be omitted or marked as `VERIFY` only when the field is important.
5. Verified facts should appear before inferred phrasing.
6. Conflicts and missing information must always be surfaced.
7. Do not fabricate polished bullets when the JSON does not support them.
8. Keep the style dense and operational, not narrative.
9. Use uppercase labels for stable machine and human scanning.

## Stable Section Order

Render sections in this order:

1. `MASTER FACT SHEET`
2. `PURPOSE`
3. `CORE PROFILE`
4. `MATCH PROFILE`
5. `EDUCATION`
6. `EXPERIENCE`
7. `RESEARCH`
8. `PROJECTS`
9. `SKILLS`
10. `LANGUAGES`
11. `MISSING INFORMATION`
12. `CONFLICTS`
13. `CONFIDENCE SUMMARY`
14. `EVIDENCE INDEX`
15. `CHANGE LOG`

## Exact Renderer Prompt

Use this prompt with Claude if you want the model to generate the plain-text fact sheet from JSON.

```text
You are a deterministic fact-sheet renderer.

Convert the provided canonical fact-sheet JSON into a human-readable plain-text master fact sheet.

Rules:
- Output plain text only.
- Do not output Markdown.
- Do not invent new facts.
- Do not summarize away important details.
- Preserve missing fields and conflicts explicitly.
- Use the exact section order and heading style required below.
- Keep labels uppercase.
- Keep content concise, recruiter-useful, and stable across rerenders.
- If a field is absent or null, omit it unless it is strategically important; in that case write VERIFY.
- Prefer direct facts over polished prose.
- If an item has `verification_status`, include it when useful.

Required structure:

MASTER FACT SHEET

PURPOSE:
[1-2 lines]

==================================================
SECTION: CORE PROFILE
==================================================
FULL_NAME: ...
PREFERRED_NAME: ...
CURRENT_LOCATION: ...
PRIMARY_EMAIL: ...
PHONE: ...
LINKEDIN: ...
GITHUB: ...
HEADLINE: ...

==================================================
SECTION: MATCH PROFILE
==================================================
TARGET_ROLES:
- ...
EXCLUDED_ROLES:
- ...
PREFERRED_INDUSTRIES:
- ...
LOCATION_PREFERENCES:
- ...
WORK_AUTHORIZATION: ...
AVAILABILITY: ...
EMPLOYMENT_PREFERENCES:
- ...
SENIORITY_ESTIMATE: ...

==================================================
SECTION: EDUCATION
==================================================
[one block per item]

==================================================
SECTION: EXPERIENCE
==================================================
[one block per item]

==================================================
SECTION: RESEARCH
==================================================
[one block per item]

==================================================
SECTION: PROJECTS
==================================================
[one block per item]

==================================================
SECTION: SKILLS
==================================================
PROGRAMMING_LANGUAGES:
- ...
FRAMEWORKS_AND_PLATFORMS:
- ...
CLOUD_AND_INFRA:
- ...
DATA_AND_ANALYTICS:
- ...
BUSINESS_TOOLS:
- ...
METHODS:
- ...

==================================================
SECTION: LANGUAGES
==================================================
- English: C2

==================================================
SECTION: MISSING INFORMATION
==================================================
- ...

==================================================
SECTION: CONFLICTS
==================================================
- FIELD: ...
  SOURCE_A: ...
  SOURCE_B: ...
  NOTE: ...

==================================================
SECTION: CONFIDENCE SUMMARY
==================================================
COMPLETION_STATUS: ...
OVERALL_CONFIDENCE: ...
NOTES:
- ...

==================================================
SECTION: EVIDENCE INDEX
==================================================
- ID: ...
  SOURCE_TYPE: ...
  SOURCE_NAME: ...
  SUMMARY: ...

==================================================
SECTION: CHANGE LOG
==================================================
- ...
```

## Field Mapping Rules

Use these mappings when rendering:

- `person.full_name` -> `FULL_NAME`
- `person.preferred_name` -> `PREFERRED_NAME`
- `person.current_location.city + country` -> `CURRENT_LOCATION`
- `person.contact.email` -> `PRIMARY_EMAIL`
- `person.contact.phone` -> `PHONE`
- `person.contact.linkedin_url` -> `LINKEDIN`
- `person.contact.github_url` -> `GITHUB`
- `person.headline` -> `HEADLINE`
- `match_profile.target_roles` -> `TARGET_ROLES`
- `match_profile.location_preferences.*` -> `LOCATION_PREFERENCES`
- `match_profile.work_authorization` -> `WORK_AUTHORIZATION`
- `match_profile.availability.*` -> `AVAILABILITY`
- `completion_status` -> `COMPLETION_STATUS`
- `confidence_summary.overall_confidence` -> `OVERALL_CONFIDENCE`

## Experience Item Render Format

Each experience item should render like this:

```text
ITEM_ID: EXP-001
ROLE_TITLE: Example Role
ORGANIZATION: Example Corp
LOCATION: Turin, Italy
START_DATE: 2023-01
END_DATE: 2025-02
CURRENT: No
ROLE_FAMILY: Example Role Family
VERIFICATION_STATUS: verified
RESPONSIBILITIES:
- Built ETL workflows ...
- Maintained reporting pipelines ...
ACHIEVEMENTS:
- Improved forecast accuracy by 28%.
TOOLS:
- Python
- Power BI
- Docker
EVIDENCE_REFS:
- EV-001
- EV-003
```

## Education Item Render Format

```text
ITEM_ID: EDU-001
DEGREE: Master of Science
FIELD: Data Science and Engineering
INSTITUTION: Example University
LOCATION: Turin, Italy
START_DATE: 2024-09
END_DATE: VERIFY
STATUS: Final stage
NOTES:
- Only thesis and internship remain.
```

## Missing Information Policy

Always render a `MISSING INFORMATION` section even if it is short.

Examples:

- Work authorization not confirmed
- Preferred name not confirmed
- Degree completion date not confirmed
- Portfolio URL missing

This is important because downstream resume generation often fails on hidden missing data.

## Conflict Rendering Policy

If conflicts exist, do not hide them.

Render each conflict explicitly:

```text
- FIELD: work_location
  SOURCE_A: CV says Turin, Italy
  SOURCE_B: form answer says Milan, Italy
  NOTE: needs user confirmation
```

## Change Log Policy

Render `CHANGE LOG` only when updates exist. It should be a short operational log, for example:

- Added new research assistant role from uploaded April 2026 CV
- Updated language level for Italian from A2 to B1
- Flagged conflicting end date for an imported role

## Practical Recommendation

Keep the rendered text stable across reruns. That matters because users, recruiters, and later prompts will start treating the text version as a trusted reference. If the renderer is too creative, your application will drift and matching quality will become harder to debug.
