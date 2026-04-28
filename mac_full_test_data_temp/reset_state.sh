#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/runtime_env.sh"

rm -rf "$JOB_AGENT_HOME"
rm -rf "$SCRIPT_DIR/.logs"

# Remove older repo-local temporary state so it cannot leak into testing.
rm -rf "$REPO_ROOT/mac_test_temp/_state" "$REPO_ROOT/mac_test_temp/.logs"

mkdir -p "$JOB_AGENT_HOME" "$SCRIPT_DIR/.logs"

echo "Full-test runtime reset."
echo "Downloads runtime: $JOB_AGENT_HOME"
