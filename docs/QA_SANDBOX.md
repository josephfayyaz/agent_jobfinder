# QA Sandbox

This repository now uses `temp_mac_test/` as the only approved repo-local QA
sandbox.

## Why this changed

The older `mac_full_test_data_temp/` harness accumulated too many runtime
databases, generated PDFs, logs, and historical outputs. That made it hard to
know which artifacts were still valid and which runtime state was leaking
between tests.

`temp_mac_test/` replaces it with a smaller and more opinionated layout:

- `generated/users/`
  Synthetic candidate corpus for repeatable onboarding and role-flow tests.
- `.runtime/current/`
  The active disposable SQLite workspace for the current QA run.
- `.logs/`
  App, worker, and audit logs.
- `results/`
  Saved JSON, PDF, and PNG artifacts from active QA work.

## Canonical commands

From repo root:

```bash
bash temp_mac_test/reset_state.sh
bash temp_mac_test/bootstrap.sh
bash temp_mac_test/start_full.sh
```

Then open:

```text
http://127.0.0.1:8000/ui
```

## Rules

- Always run the app and tests in the `ML` environment.
- Keep `temp_mac_test/` disposable. Runtime DBs and logs are not product data.
- Save new QA artifacts only in `temp_mac_test/results/`.
- Do not recreate `mac_full_test_data_temp/`.
