#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/runtime_env.sh"

cd "$REPO_ROOT"

"$PYTHON_BIN" -m job_agent.worker >"$SCRIPT_DIR/.logs/worker.log" 2>&1 &
WORKER_PID=$!

cleanup() {
  kill "$WORKER_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

exec "$PYTHON_BIN" -m uvicorn job_agent.main:app --host 127.0.0.1 --port "$APP_PORT" --reload
