#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PYTHON_BIN="${PYTHON_BIN:-}"
DEFAULT_ML_PYTHON="/Users/youseffayyaz/miniforge3/envs/ML/bin/python"
if [[ -z "$PYTHON_BIN" && -x "$DEFAULT_ML_PYTHON" ]]; then
  PYTHON_BIN="$DEFAULT_ML_PYTHON"
fi

if [[ -z "$PYTHON_BIN" ]]; then
  echo "The ML environment python was not found at $DEFAULT_ML_PYTHON." >&2
  exit 1
fi

"$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 12):
    raise SystemExit("Python 3.12+ is required for Job Agent.")
print("Using Python", sys.version.split()[0])
PY

printf '%s\n' "$PYTHON_BIN" >"$SCRIPT_DIR/.python-bin"

# shellcheck disable=SC1091
source "$SCRIPT_DIR/runtime_env.sh"

cd "$REPO_ROOT"
"$PYTHON_BIN" -m pip install -e ".[dev]"
"$PYTHON_BIN" "$SCRIPT_DIR/build_dataset.py"
"SCRIPT_DIR_ENV=$SCRIPT_DIR" "$PYTHON_BIN" - <<'PY'
from __future__ import annotations
import json
from datetime import datetime, timezone
import os
from pathlib import Path

root = Path(os.environ["SCRIPT_DIR_ENV"]).resolve()
manifest = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "python_bin": str(root.joinpath(".python-bin").read_text(encoding="utf-8").strip()),
    "runtime_root": str(root / ".runtime" / "current"),
    "results_root": str(root / "results"),
    "dataset_manifest": str(root / "generated" / "manifest.json"),
}
(root / "current_runtime_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
PY

echo "Bootstrap complete."
echo "Live repo: $REPO_ROOT"
echo "Disposable runtime: $JOB_AGENT_HOME"
echo "Dataset manifest: $SCRIPT_DIR/generated/manifest.json"
