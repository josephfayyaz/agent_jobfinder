# Spec C7 — Deep Company Brief

## Goal

Generate a lightweight but useful company brief only for shortlisted or high-fit jobs.

## Product Rule

Company research is valuable, but too expensive to run on every discovered job.

## Build

1. Trigger policy
   - only available on shortlist
   - or on jobs above a high-fit threshold

2. Brief sections
   - company mission / product
   - likely team context
   - hiring clues from recent openings
   - role-specific talking points
   - red flags / open questions

3. Source order
   - company website first
   - job description
   - company watchlist context
   - only then optional LLM synthesis

4. Cache
   - cache by company + job id
   - allow manual refresh

## UX

This should feel like:
- “help me interview smarter”
not:
- “long generic AI research report”

## Success Metric

- increased shortlist-to-application confidence
- fewer blind applications to poorly understood companies
