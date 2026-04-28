# Mac Full Test Harness

This folder is now the full local test environment for the live repo.

Two things live here:

1. The generated test corpus
2. The launcher scripts for running the real application code against a disposable runtime

## What this fixes

- The app runs from the real source tree under the repo root
- Any bug fix in the main project is used immediately on the next run
- Runtime state is isolated from your real workspace
- The temporary DB, settings, uploads, and generated files live under:

`~/Downloads/job_agent_full_test_runtime`

That folder is disposable. Delete it whenever you want.

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

- `reset_state.sh` wipes the Downloads runtime used by this harness
- It also clears the older `mac_test_temp` runtime so stale candidate data cannot leak into tests
- It does **not** copy the app; it runs the real repo directly

## Test corpus

- `build_dataset.py`
  - creates 20 synthetic candidate packs
  - writes both `.txt` and `.pdf` CV inputs
  - writes matching profile JSON and synthetic target-job briefs
- `generated/manifest.json`
  - quick index of all candidate packs
- `generated/role_sources.json`
  - public occupation references used as role-family seeds

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
