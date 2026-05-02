# Phase F5 — Domain-Neutral PDF Renderer And Output Contract

## Goal

Upgrade the final CV output path so the app can produce stronger polished PDFs
for rich profiles without reintroducing hallucination or tech bias.

After this phase:

- the renderer supports better final visual quality
- output remains ATS-safe
- section logic works across multiple domains
- file naming and persistence are consistent

The final result should be recognizably this app's CV output, not a visual copy
of another repository's template.

## Files likely in scope

- `job_agent/services/documents.py`
- add an HTML renderer path if needed
- `frontend/templates/` or dedicated CV export templates if needed
- `job_agent/services/workflows.py`
- `job_agent/config.py`
- `tests/test_documents.py`
- add output-contract tests if needed

## Exact implementation requirements

### 1. Output contract

The final saved CV artifact contract must include:

- candidate-aware filename
- company-aware filename
- date in filename
- predictable output path

The current company/date behavior should be preserved or improved, not weakened.

### 2. Domain-neutral section assembly

The renderer must not assume all good CVs look like software-engineering CVs.

Required behavior:

- omit empty sections cleanly
- allow role-relevant sections to rise or fall in prominence
- support evidence-only profiles without visual awkwardness
- preserve ATS-safe single-column output by default
- use section titles and ordering that fit this app's own presentation logic
  rather than mimicking an external template verbatim

### 3. Stronger final rendering path

Improve the final rendering path so rich profiles can reach a more polished
standard than the current sparse-profile-safe baseline.

Acceptable approaches:

- improve the current LaTeX renderer substantially
- or add a stronger HTML-to-PDF export path while preserving ATS safety

If a new HTML renderer path is introduced, it must use original styling,
spacing, headings, and grouping decisions. Do not clone another open-source CV
template closely enough that it looks derivative.

### 4. Preview and PDF consistency

The final PDF should closely match what the user approved in the pre-PDF
preview state.

Do not allow major hidden changes between preview and final export.

## Non-goals

Do not do any of the following in F5:

- redesign the whole product UI
- add Canva integration in this phase unless explicitly required by an existing
  spec dependency
- add new discovery logic

## Acceptance criteria

1. Rich profiles can produce visibly stronger output than the current truthful
   sparse-profile baseline.
2. Empty sections are omitted cleanly.
3. Output filenames include company and date consistently.
4. Final PDFs remain ATS-safe and text-selectable.
5. The renderer stays domain-neutral.
6. The output does not materially resemble `career-ops` in headings, template
   structure, or overall visual contract.

## Validation requirements

Run in `ML`:

```bash
/Users/youseffayyaz/miniforge3/envs/ML/bin/python -m pytest tests/test_documents.py tests/test_workflows.py -q
```

Add tests for:

- filename contract
- empty-section omission
- section ordering / presence
- preview-to-PDF consistency where testable

## Completion report

Write:

- `AGENT_SPECS/completed/phase_F5_domain_neutral_pdf_renderer_and_output_contract.md`

Then append this phase to
`/Users/youseffayyaz/Local_LLM/completed_agent_specs.txt`.
