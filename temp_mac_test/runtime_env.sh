#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RUNTIME_ROOT="${SCRIPT_DIR}/.runtime/current"

export JOB_AGENT_HOME="${JOB_AGENT_HOME:-$RUNTIME_ROOT}"
export DATABASE_URL="sqlite:///$JOB_AGENT_HOME/job_agent.db"
export ARTIFACTS_DIR="$JOB_AGENT_HOME/generated"
export APP_PORT="${APP_PORT:-8000}"
export QA_RESULTS_DIR="${QA_RESULTS_DIR:-$SCRIPT_DIR/results}"
export QA_PID_DIR="${QA_PID_DIR:-$SCRIPT_DIR/.pids}"

PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" && -f "$SCRIPT_DIR/.python-bin" ]]; then
  PYTHON_BIN="$(cat "$SCRIPT_DIR/.python-bin")"
fi
PYTHON_BIN="${PYTHON_BIN:-/Users/youseffayyaz/miniforge3/envs/ML/bin/python}"

mkdir -p "$JOB_AGENT_HOME" "$SCRIPT_DIR/.logs" "$QA_RESULTS_DIR" "$QA_PID_DIR"
