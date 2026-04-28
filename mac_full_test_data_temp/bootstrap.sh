#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  for candidate in python3.13 python3.12 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      PYTHON_BIN="$candidate"
      break
    fi
  done
fi

if [[ -z "$PYTHON_BIN" ]]; then
  echo "Python 3.12+ is required." >&2
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

echo "Bootstrap complete."
echo "Live repo: $REPO_ROOT"
echo "Disposable runtime: $JOB_AGENT_HOME"
