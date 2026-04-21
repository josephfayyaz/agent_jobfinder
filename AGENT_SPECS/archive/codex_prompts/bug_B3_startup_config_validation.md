# Bug Fix B3 — Startup Config Validation

## Bug

`DEFAULT_CANDIDATE_ID` is not validated at application startup.

If it is empty (unset in `.env`), `_load_context()` in `CVWorkflowService` falls back to
`MasterProfile(id=1)`. If that record also doesn't exist in the DB, the request fails
mid-flight with an unhelpful `ValueError` — the user sees a 500 with no clear cause.

Same issue propagates to `BulletClarifyService` (F1) and all future G-phase services
that call `wf._load_context()`.

Also: `JOBSPY_DISCOVER_QUERIES` defaults to data-engineering focused queries. Since this
system is optimized for MLOps/AI roles in Italy, the defaults should reflect that.

---

## Hard Rules

- No Alembic. No new tables.
- Always conda ML.
- Do not change `_load_context()` behaviour — only add startup warnings.

---

## Fix 1: Add startup config warning in `lifespan()` in `main.py`

In the `lifespan` context manager (already exists — phase D), after `prepare_database()`,
add a warning if `DEFAULT_CANDIDATE_ID` is not set:

```python
if not settings.default_candidate_id.strip():
    logger.warning(
        "DEFAULT_CANDIDATE_ID is not set. CV workflow will fall back to MasterProfile(id=1). "
        "Set DEFAULT_CANDIDATE_ID=<uuid> in .env to use Candidate-based profiles."
    )
```

This is a warning only — do not block startup. The system is usable without it via MasterProfile.

---

## Fix 2: Update default `jobspy_discover_queries` in `config.py`

Change the default query list to be MLOps/AI-focused for Italy:

```python
jobspy_discover_queries: list[str] = Field(
    default=[
        "MLOps Engineer",
        "AI Engineer",
        "Machine Learning Engineer",
        "Data Engineer",
        "Kubernetes Engineer",
    ],
    ...
)
```

---

## Fix 3: Add `ValueError` catch in `BulletClarifyService.start_clarification()`

In `job_agent/services/bullet_clarify.py`, the language extraction LLM call:

```python
language_result = self.router.generate(
    role="small",
    system_prompt=build_language_extraction_system_prompt(),
    user_prompt=build_language_extraction_prompt(profile_dict, job_dict, draft_content),
)
```

Currently only caught higher up. Wrap with:

```python
try:
    language_result = self.router.generate(...)
except (ProviderUnavailableError, ValueError):
    # Return empty clarification — no questions, no rewrite possible
    clarification = BulletClarification(
        draft_id=draft_id,
        status="complete",
        language_map={},
        questions=[],
        rewritten_bullets={},
    )
    self.session.add(clarification)
    self.session.commit()
    return clarification
```

Same pattern for the rewrite call in `submit_answers()`.

---

## Tests to Write

File: `tests/test_bug_b3.py`

1. `test_startup_warning_logged_when_candidate_id_unset`
   - Patch `settings.default_candidate_id` to `""`
   - Call the lifespan startup block (or just the warning check directly)
   - Assert logger.warning was called with the expected message

2. `test_default_jobspy_queries_are_mlops_focused`
   - Assert `settings.jobspy_discover_queries` includes "MLOps Engineer"

3. `test_bullet_clarify_handles_provider_error_gracefully`
   - Mock router to raise `ProviderUnavailableError` in `start_clarification`
   - Assert returns a `BulletClarification` with `status="complete"` (no exception raised)

4. `test_bullet_clarify_handles_json_error_gracefully`
   - Mock router to raise `ValueError("Could not extract valid JSON...")`
   - Assert returns a `BulletClarification` with `status="complete"` (no exception raised)

---

## Acceptance Criteria

- [ ] Startup logs `WARNING` when `DEFAULT_CANDIDATE_ID` is empty
- [ ] Default `jobspy_discover_queries` includes MLOps/AI-focused queries
- [ ] `BulletClarifyService.start_clarification()` catches `ProviderUnavailableError` and `ValueError`
- [ ] `BulletClarifyService.submit_answers()` catches `ProviderUnavailableError` and `ValueError`
- [ ] All 4 tests pass
- [ ] Full suite still passes: `pytest --tb=short -q`
- [ ] Ruff clean
- [ ] Write `AGENT_SPECS/completed/phase_B3_report.md`
- [ ] Append to `completed_agent_specs.txt`
