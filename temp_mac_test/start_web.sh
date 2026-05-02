#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/runtime_env.sh"

cd "$REPO_ROOT"
exec "$PYTHON_BIN" -m uvicorn job_agent.main:app --host 127.0.0.1 --port "$APP_PORT" --reload
