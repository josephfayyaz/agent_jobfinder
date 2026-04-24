## Phase P1 — Single-Owner Workspace

Implemented the single-owner/privacy-safe workspace layer on top of the existing setup gate. The app now treats one machine as one candidate workspace, stores live runtime data outside the repo in an OS-specific app-data home, exposes a full-workspace backup download, and adds explicit Settings controls for sharing the GitHub source link, starting fresh, or erasing all local data with typed confirmation phrases.

### What changed

- `job_agent/runtime_paths.py`
  - Added cross-platform runtime path resolution for the app-data home, user settings file, SQLite DB, backups, generated artifacts, and legacy repo-local paths.
  - Added non-destructive bootstrap migration from legacy repo-local `job_agent.db`, `config/user_settings.yml`, and `generated/`.

- `job_agent/config.py`
  - Switched runtime settings loading to the new app-data-home settings path.
  - Added full in-memory settings reload (`reload_settings_from_sources`) so deleted/removed YAML values actually clear from the live process.
  - Normalized relative `artifacts_dir` values into the app-data home.

- `job_agent/db.py`
  - Moved the default SQLite path from the repo root into the local Job Agent data home.
  - Ensured parent directories exist before engine creation and bootstrapped runtime-state migration before opening SQLite.

- `job_agent/user_config.py`
  - Moved the live user settings path to the app-data home.
  - Added `delete_user_settings()` for reset/delete flows.

- `job_agent/services/documents.py`
  - Resolved generated CV output through the runtime app-data home when `artifacts_dir` is relative.

- `job_agent/services/exporters.py`
  - Resolved CSV export output through the runtime app-data home when `artifacts_dir` is relative.

- `job_agent/services/intake.py`
  - Resolved uploaded source-file storage through the runtime app-data home when `artifacts_dir` is relative.

- `job_agent/services/workspace.py`
  - Added workspace status reporting, full backup ZIP creation, reset/delete confirmation phrases, DB/data wipe helpers, and legacy-runtime cleanup.
  - Reset preserves downloaded backups; full delete removes them too.

- `job_agent/main.py`
  - Added owner-candidate resolution and changed `POST /candidates` to update the single owner instead of creating parallel profiles.
  - Added `/workspace/status`, `/workspace/download`, `/workspace/reset`, and `/workspace/delete`.
  - Updated settings save/reload to use full reload semantics.
  - Passed workspace/share/danger-zone context into `/ui/settings`.

- `job_agent/templates/settings.html`
  - Upgraded the System section into a single-owner workspace control panel.
  - Added local data-home visibility, GitHub share card, full backup download, and a GitHub-style danger zone with hidden typed-confirmation inputs.

- `job_agent/templates/setup_required.html`
  - Clarified that the setup gate exists to keep the machine bound to one owner workspace.

- `job_agent/templates/onboarding.html`
  - Added privacy messaging explaining that runtime data is stored outside the repo.

- `job_agent/cli.py`
  - Updated settings source display/reload messaging to use the runtime settings path.

- `job_agent/cli_start.py`
  - Updated start preflight to check the runtime settings file path instead of repo-local config.

- `job_agent/onboard.py`
  - Stopped relying on `.env` writes for `DEFAULT_CANDIDATE_ID` during onboarding save; the runtime settings file is now the primary owner-state source.

- `config/user_settings.example.yml`
  - Updated examples/comments to reflect the app-data-home storage model.

- `AGENTS.md`, `CLAUDE.md`, `AGENT_SPECS/MASTER_PLAN.md`
  - Synced docs/roadmap with the single-owner workspace architecture and P1 completion.

- `tests/test_workspace_privacy.py`
  - Added coverage for single-owner candidate upsert, backup archive creation, typed-confirmation validation, reset preserving backups, and full delete removing backups.

### Verification

Ran:

```bash
/Users/youseffayyaz/miniforge3/envs/ML/bin/python -m pytest tests/test_workspace_privacy.py tests/test_onboarding.py -q
/Users/youseffayyaz/miniforge3/envs/ML/bin/python -m pytest --tb=short -q
/Users/youseffayyaz/miniforge3/envs/ML/bin/ruff check
```

Results:

- Focused privacy/onboarding suite: passed
- Full suite: `397 passed, 4 warnings`
- Ruff: clean
