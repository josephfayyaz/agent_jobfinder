# UI / UX Rebuild Baseline — 2026-05-02

This document captures the intended direction before a larger frontend redesign.

## Originality guardrail

The redesign must not look like a clone of `career-ops`.

Use these rules:

- keep this app database-backed and app-first, not file-operator-shaped
- avoid external report naming or operator-style panel language
- use app-native labels and screen structure
- prefer direct, practical UX over prompt-operator aesthetics

## Primary user journey

The visible first-class journey should be:

1. Onboarding
2. Jobs
3. CVs
4. Applications
5. Settings

Everything else should become secondary or utility-level navigation.

## Navigation changes

Recommended simplification:

- `Dashboard`
- `Jobs`
- `CVs`
- `Applications`
- `Settings`

Secondary tools can live under a compact utility menu:

- Analytics
- Companies
- Story Bank
- Offer Compass
- Profile Memory
- Thesis

## Page-level redesign targets

### Jobs

The page should visually separate:

- search controls
- manual target intake
- discovery status
- queue filters
- queue list

Do not keep all operational text blocks at the top of the page.

### Draft detail

The page should become a guided review workspace with four zones:

- CV Preview
- Evidence Review
- Fit and Gaps
- Final Actions

### Onboarding

The onboarding flow should emphasize:

- input
- follow-up questions
- extracted-data review
- search-setup confirmation

### Settings

The settings page should stop feeling like one long control wall.

Use sections:

- AI Provider
- Search Preferences
- Integrations
- Advanced Maintenance

## Naming recommendations

To reduce resemblance to external tools, prefer labels like:

- `Private Career Workspace`
- `Profile Readiness`
- `Target Fit Map`
- `Application Gaps`
- `Recommended Improvements`
- `Manual Target`

Avoid externally-associated phrases as primary UI framing.
