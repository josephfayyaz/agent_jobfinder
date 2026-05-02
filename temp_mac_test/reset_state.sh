#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/runtime_env.sh"

rm -rf "$JOB_AGENT_HOME"
rm -rf "$SCRIPT_DIR/.logs"
rm -rf "$SCRIPT_DIR/results"
rm -rf "$SCRIPT_DIR/generated/users" "$SCRIPT_DIR/generated/manifest.json" "$SCRIPT_DIR/generated/role_sources.json"

mkdir -p "$JOB_AGENT_HOME" "$SCRIPT_DIR/.logs" "$SCRIPT_DIR/results" "$SCRIPT_DIR/generated/users"

echo "Temp test runtime reset."
echo "Runtime root: $JOB_AGENT_HOME"
