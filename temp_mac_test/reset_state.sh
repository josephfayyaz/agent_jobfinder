#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/runtime_env.sh"

for pid_file in "$QA_PID_DIR/app.pid" "$QA_PID_DIR/worker.pid"; do
  if [[ -f "$pid_file" ]]; then
    pid="$(cat "$pid_file" 2>/dev/null || true)"
    if [[ -n "${pid:-}" ]] && kill -0 "$pid" >/dev/null 2>&1; then
      kill "$pid" >/dev/null 2>&1 || true
      sleep 1
      kill -9 "$pid" >/dev/null 2>&1 || true
    fi
  fi
done

rm -rf "$JOB_AGENT_HOME"
rm -rf "$SCRIPT_DIR/.logs"
rm -rf "$QA_PID_DIR"
rm -rf "$SCRIPT_DIR/results"
rm -rf "$SCRIPT_DIR/generated/users" "$SCRIPT_DIR/generated/manifest.json" "$SCRIPT_DIR/generated/role_sources.json"

mkdir -p "$JOB_AGENT_HOME" "$SCRIPT_DIR/.logs" "$SCRIPT_DIR/results" "$SCRIPT_DIR/generated/users" "$QA_PID_DIR"

echo "Temp test runtime reset."
echo "Runtime root: $JOB_AGENT_HOME"
