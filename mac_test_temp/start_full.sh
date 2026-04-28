#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" && -f "$SCRIPT_DIR/.python-bin" ]]; then
  PYTHON_BIN="$(cat "$SCRIPT_DIR/.python-bin")"
fi
PYTHON_BIN="${PYTHON_BIN:-python3}"

export JOB_AGENT_HOME="$SCRIPT_DIR/_state"
mkdir -p "$JOB_AGENT_HOME" "$SCRIPT_DIR/.logs"

cd "$REPO_ROOT"

"$PYTHON_BIN" -m job_agent.worker >"$SCRIPT_DIR/.logs/worker.log" 2>&1 &
WORKER_PID=$!

cleanup() {
  kill "$WORKER_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

exec "$PYTHON_BIN" -m uvicorn job_agent.main:app --host 127.0.0.1 --port 8000 --reload
