## Phase P1 Follow-up — Backup Reset Clarity

Refined the reset/delete UX so users can clearly see what happens to their backups. The app now persists downloaded workspace backups into the local Job Agent backup folder, shows the exact backup path before reset, provides an optional “open backup folder after reset” checkbox, and routes successful resets to a dedicated confirmation screen with `Open Backup Folder` and `Continue to Setup` actions.

### What changed

- `job_agent/services/workspace.py`
  - Changed workspace backup creation to persist ZIP archives in the Job Agent backup folder instead of returning a temp file only.
  - Added backup count to `workspace_status()`.
  - Added `open_backups_folder()` with macOS / Windows / Linux support.

- `job_agent/main.py`
  - Added `POST /workspace/backups/open`.
  - Added `GET /ui/workspace-reset` success screen route.
  - Updated `/workspace/download` to serve the persisted archive from the backup folder.

- `job_agent/templates/settings.html`
  - Added visible backup-folder path and stored-backup count in the backup card.
  - Added visible kept-backup path in the `Start Fresh` danger card.
  - Added `Open backup folder after reset` checkbox.
  - Changed post-reset redirect flow to the dedicated success screen instead of jumping straight back into setup-required.

- `job_agent/templates/workspace_reset.html`
  - Added a dedicated post-reset/post-delete confirmation screen.
  - For reset: shows exact backup path, backup count, `Open Backup Folder`, and `Continue to Setup`.
  - For delete: confirms local data and backups were removed.

- `tests/test_workspace_privacy.py`
  - Added coverage for persistent backup placement, backup-folder open endpoint, and the reset-success page rendering.

### Verification

Ran:

```bash
<python> -m pytest tests/test_workspace_privacy.py -q
<python> -m pytest --tb=short -q
<home>/miniforge3/envs/ML/bin/ruff check
```

Results:

- Workspace/privacy suite: passed
- Full suite: `399 passed, 4 warnings`
- Ruff: clean
