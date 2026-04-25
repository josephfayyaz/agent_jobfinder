# Career-Ops Adaptation Pack

## Purpose

This temporary folder translates the strongest ideas from `career-ops` into a
product-specific roadmap for Job Agent.

This is **not** a copy-paste migration plan.

The goal is to answer:

- which ideas are genuinely strong
- which ones fit Job Agent
- which ones should be rejected
- how to implement them in a local-first web application instead of an AI CLI repo

## Core Product Position

Job Agent should become:

- a **guided local-first application**
- for **single-user private job search**
- with **cloud BYOK by default**
- with **optional local LLM later**
- and with a strong **human-in-the-loop filter-first workflow**

Career-ops is valuable mainly as a source of:

- workflow discipline
- opportunity filtering logic
- scan architecture ideas
- tracker integrity patterns

It should **not** define your UI model, credential model, or product style.

## Files

- `decision_matrix.md`
- `adapted_product_blueprint.md`
- `implementation_phases.md`
- `recommended_experiments.md`
- `spec_C3_discovery_pipeline_upgrade.md`
- `spec_C4_shortlist_centric_apply_flow.md`
- `spec_C6_interview_story_bank.md`
- `spec_C7_deep_company_brief.md`
- `spec_C8_offer_evaluation.md`

## Summary Judgment

### Must import
- stronger filter-first mindset
- scan pipeline discipline
- legitimacy / freshness / confidence signals
- tracker integrity checks
- deep personalization from structured profile context

### Must reject
- repo-as-interface
- AI CLI as the primary UX
- file-heavy manual setup for normal users
- provider model tied to Claude Code rather than your app

### Product rule

Job Agent should feel like:

`private recruiting software for one person`

not:

`a prompt repo for technical operators`
