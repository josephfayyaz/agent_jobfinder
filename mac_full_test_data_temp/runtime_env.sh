#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DOWNLOADS_RUNTIME_ROOT="${HOME}/Downloads/job_agent_full_test_runtime"

export JOB_AGENT_HOME="${JOB_AGENT_HOME:-$DOWNLOADS_RUNTIME_ROOT}"
export DATABASE_URL="sqlite:///$JOB_AGENT_HOME/job_agent.db"
export ARTIFACTS_DIR="$JOB_AGENT_HOME/generated"

PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" && -f "$SCRIPT_DIR/.python-bin" ]]; then
  PYTHON_BIN="$(cat "$SCRIPT_DIR/.python-bin")"
fi
PYTHON_BIN="${PYTHON_BIN:-python3}"

mkdir -p "$JOB_AGENT_HOME" "$SCRIPT_DIR/.logs"
