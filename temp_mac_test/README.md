# Temp Mac Test Harness

This folder is the canonical disposable QA sandbox for the live repo source.

It contains:

1. A generated synthetic candidate corpus under `generated/users/`
2. Launcher scripts that run the real application code from the repo root
3. An isolated runtime under `.runtime/current/`
4. Saved QA outputs under `results/`

## Ground Rules

- Tests must run against the real source tree in this repository
- Tests must use the real configured provider for the run
- Do not stub or fake LM Studio unless the user explicitly approves that fallback first
- Runtime state should stay isolated from the main workspace

## Clean test flow

From this folder run:

```bash
bash reset_state.sh
bash bootstrap.sh
bash start_full.sh
```

Then open:

`http://127.0.0.1:8000/ui`

## Important

- `reset_state.sh` wipes the disposable runtime used by this harness
- It also clears generated corpus, logs, and prior QA outputs from this folder
- It does **not** copy the app; it runs the real repo directly
- Live browser-backed results and audit outputs should be written to `results/`

## Test corpus

- `build_dataset.py`
  - creates 20 synthetic candidate packs
  - writes both `.txt` and `.pdf` CV inputs
  - writes matching profile JSON and synthetic target-job briefs
- `generated/manifest.json`
  - quick index of all candidate packs
- `generated/role_sources.json`
  - public occupation references used as role-family seeds

## Canonical runtime layout

- `generated/users/`
  Synthetic test corpus
- `.runtime/current/`
  SQLite DB, generated PDFs, and live app state for the current QA run
- `.logs/`
  App, worker, and audit logs
- `results/`
  Saved JSON/PDF/PNG artifacts from manual or automated QA

## Useful sample

The market-research sample you mentioned is:

`generated/users/08_market_research_junior/`

Quick lookup:

```bash
bash show_sample.sh 08_market_research_junior
```

The candidate content is synthetic by design. The role families and baseline
requirement themes are grounded in public occupation references so the test
corpus covers realistic variation without shipping any personal CV data.

## Historical note

The older `mac_full_test_data_temp/` sandbox was intentionally deleted to
eliminate polluted runtime state. `temp_mac_test/` is now the only approved
repo-local QA harness.
