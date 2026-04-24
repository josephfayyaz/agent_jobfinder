## Summary

<!-- What does this PR change and why? -->

## Type of change

- [ ] Frontend only (`frontend/templates/`, `frontend/static/`)
- [ ] Backend / API / worker / DB
- [ ] Tests
- [ ] Configuration / tooling

## Frontend checklist (if applicable)

- [ ] Templates render correctly in the desktop browser layout
- [ ] Shared page behavior lives in `frontend/static/*.js`, not large inline `<script>` blocks
- [ ] Italian translations added/updated where applicable
- [ ] HTMX targets and swap strategies tested manually
- [ ] No changes to `job_agent/` Python code
- [ ] No changes to `tests/` files

## Backend checklist (if applicable)

- [ ] New/changed endpoints covered by tests
- [ ] Runtime paths stay outside the repo unless explicitly overridden
- [ ] ORM field names match `CLAUDE.md` reference notes
- [ ] `ruff check` passes
- [ ] `pytest` passes

## Testing

<!-- How did you verify this works? -->
