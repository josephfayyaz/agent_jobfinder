#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

export JOB_AGENT_HOME="$SCRIPT_DIR/_state"
mkdir -p "$JOB_AGENT_HOME" "$SCRIPT_DIR/.logs"

cd "$REPO_ROOT"
exec uvicorn job_agent.main:app --host 127.0.0.1 --port 8000 --reload
