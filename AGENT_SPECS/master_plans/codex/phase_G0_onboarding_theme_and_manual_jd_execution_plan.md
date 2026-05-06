# Phase G0 — Onboarding, Theme, And Manual JD Execution Plan

This file anchors the currently approved execution order so the implementation
does not drift across turns. It is intentionally narrow: the priority is the
manual job-description workflow and the setup surfaces that unblock it.

## Locked Scope

The active user path is:

1. User completes onboarding.
2. Candidate and setup data persist correctly.
3. User pastes a manual job description.
4. The app analyzes it and returns a score out of 100.
5. The user creates a CV from that job.
6. The app proposes rewrites/modifications grounded in existing evidence.
7. The user confirms, rejects, or requests rewrites.
8. The user previews the CV.
9. The user approves and downloads the CV.
10. The approved CV is persisted in the downstream approved/history surface.
11. The user can also generate a compliance matrix around that flow.

## Execution Order

### Phase 1 — Onboarding and Global UI Redesign

- Replace the current onboarding sidebar with a one-time welcome dialog.
- Expand the visual redesign from onboarding into the full app shell.
- Establish a tokenized global theme:
  - `Ink` `#0B1220`
  - `Slate` `#162033`
  - `Paper` `#F3EEDF`
  - `Cobalt` `#2F6BFF`
  - `Amber` `#D89B2B`
  - `Teal` `#2AA889`
  - `Rose` `#C85A5A`
- Add an `About` surface with product description and maintainer/repo links.
- Keep `Ollama` separate in the provider UX.
- Rename the LM Studio-first local card to a generic local-runtime concept.

### Phase 2 — Gemini Provider Integration

- Add native Google Gemini API support as a real provider.
- Update:
  - `job_agent/config.py`
  - `job_agent/providers.py`
  - `job_agent/llm.py`
  - provider validation routes
  - onboarding/provider persistence and hydration
  - tests

### Phase 3 — Profile Input Restructure And Validation

- Split the profile step into:
  - first name
  - family name
  - email
- Normalize capitalization on save.
- Restrict names to letters and spaces at this phase.
- Add client and server validation.
- Preserve downstream compatibility via a combined `full_name`.

### Phase 4 — Onboarding Persistence Semantics

- Save data step-by-step as the user progresses.
- Use overwrite semantics on next save when the user navigates back and edits.
- Do not destructively erase saved state just because the user clicked Back.

### Phase 5 — PDF Intake Hardening

- Keep PDF upload as the main user path.
- Strengthen local PDF extraction before the model sees the text.
- Use a public-license Python library if needed.
- Normalize extracted text into cleaner structured text/markdown-like content.
- Store the normalized extracted source used for intake.

### Phase 6 — Manual JD To CV Workflow Debugging

- Trace and stabilize:
  - manual JD submission
  - analysis/scoring out of 100
  - CV generation kickoff
  - rewrite / confirm / reject loops
  - preview
  - approval
  - download
  - approved-draft persistence
  - compliance matrix entry point in this path

### Phase 7 — Verification

- Add targeted tests for:
  - onboarding UI and persistence
  - provider selection and validation
  - Gemini provider integration
  - profile validation
  - PDF extraction behavior
  - manual JD analysis path
  - CV draft approval/download path
  - compliance matrix path where it touches the approved flow

## Notes

- Ignore unrelated product areas unless they directly break the path above.
- Keep commits small and push each completed implementation slice.
- Do not rely on browser-only testing as the primary debugging method; combine
  code tracing, targeted tests, and user validation.
