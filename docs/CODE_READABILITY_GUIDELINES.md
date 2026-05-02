# Code Readability Guidelines

These are the project rules for making the code easier for humans and AI
systems to extend.

## 1. Prefer names over comments

If a function or variable is unclear, rename it before adding explanatory
comments.

## 2. Use comments for intent, not narration

Good comments explain:

- why a guard exists
- why a field is snapshotted
- why a fallback is safe
- why a route blocks a workflow

Bad comments explain line-by-line what obvious code already says.

## 3. Add module docstrings to high-traffic files

Especially for:

- large routers
- workflow orchestration services
- rendering services
- large frontend controllers

## 4. Add function docstrings to non-trivial flows

Functions should explain:

- the ownership boundary
- important inputs/outputs
- any persistence or truthfulness guarantees

## 5. Keep architecture notes in docs

Use short docs for:

- onboarding
- discovery
- CV generation
- draft review
- QA sandbox usage

## 6. Avoid comment spam

The goal is cleaner extension, not maximum comment count. A small number of
high-signal comments is better than explaining every statement.
