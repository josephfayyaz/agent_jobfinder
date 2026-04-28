# Mac Quick Test Harness

This folder does **not** copy the app. It runs the real project from the repo root
and keeps only temporary runtime state here.

Runtime state lives in:

- `mac_test_temp/_state/`
- `mac_test_temp/.logs/`

## Quick start

1. Use a Python 3.12+ environment with the project dependencies available.
2. From this folder run:

```bash
bash bootstrap.sh
bash start_full.sh
```

3. Open:

- `http://127.0.0.1:8000/ui`

## Useful scripts

- `bootstrap.sh`
  - checks Python version
  - installs the real project in editable mode from the repo root
- `start_web.sh`
  - starts only the FastAPI app
- `start_full.sh`
  - starts the API and worker together
- `open_ui.sh`
  - opens the app in the default macOS browser
- `reset_state.sh`
  - deletes temporary app data and logs for a clean retry

## Important

- This harness uses the real source code under the repo root.
- Any code changes in the main project are picked up automatically on the next run.
- No cloned app copy is used here.
