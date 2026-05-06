# Release Specs — Codex Execution Order

## READ THIS FIRST

These specs prepare the Job Agent for public release. They fix real bugs that affect new users.
**Execute them in the numbered order below. Do NOT skip ahead. Do NOT start spec N+1 until spec N has passing tests.**

---

## Execution Sequence

| Spec | File | Priority | Content |
|------|------|----------|---------|
| 01 | `release_spec_01_p0_critical_fixes.md` | P0 BLOCKER | Worker crash loop fix + FactSheet bulk-delete scope fix |
| 02 | `release_spec_02_p1_startup_resilience.md` | P1 HIGH | Lifespan error handling + runtime dir PermissionError + SQLite pragmas |
| 03 | `release_spec_03_p1_frontend_guards.md` | P1 HIGH | apply.js polling try/catch + intake.js null guards + search.js null guards |
| 04 | `release_spec_04_p2_llm_hardening.md` | P2 MEDIUM | LLM truncation error + API key log truncation |
| 05 | `release_spec_05_p2_frontend_polish.md` | P2 MEDIUM | Cache-busting on base.html + skeleton loader aria attributes |

---

## Global Rules (apply to every spec)

1. **Python environment:** `conda run -n ML <command>` only. Never create a virtualenv or pip-install globally.
2. **No Alembic.** SQLite schema changes only via `_safe_add_column()` in `db.py:prepare_database()`.
3. **Starlette TemplateResponse** must use keyword-only arguments: `TemplateResponse(request=request, name="file.html", context={...})`. Positional args crash.
4. **LLMRouter.generate()** raises two exception types. Always catch both: `ProviderUnavailableError` AND `ValueError`.
5. **Run the full test suite after every spec:** `conda run -n ML pytest tests/ -x -q`. All tests must pass before moving on.
6. **After each spec is complete:**
   a. Write a report in `AGENT_SPECS/completed/<spec-name>.md`
   b. Append a completion line to `completed_agent_specs.txt`
   c. Move the spec file from `AGENT_SPECS/pending/claude/` to `AGENT_SPECS/completed/`

---

## Completion Line Format

```
release_spec_01_p0_critical_fixes.md — COMPLETE — 2026-05-04T14:00:00+02:00
```

Use an actual ISO 8601 timestamp (your local time). Append to:
`/Users/youseffayyaz/Local_LLM/completed_agent_specs.txt`

---

## ORM Field Name Reference (Codex gets these wrong — always check)

| Model | Correct field | Wrong (do not use) |
|-------|--------------|---------------------|
| `ExperienceFact` | `.role_title` | ~~`.title`~~ |
| `ExperienceFact` | `.verified_core_facts` | ~~`.bullets`~~ |
| `ExperienceFact` | `.tools_and_tech` | ~~`.tech_stack`~~ |
| `ProjectFact` | `.project_name` | ~~`.name`~~ |
| `ProjectFact` | `.short_resume_line` | ~~`.summary`~~ |
| `CandidateSourceFile` | `.original_name` | ~~`.original_filename`~~ |
| `CandidateSourceFile` | `.mime_type` | ~~`.content_type`~~ |
| `ResumeDraft` | `.review_feedback` (JSONB) | ~~`.review_notes`~~ |
