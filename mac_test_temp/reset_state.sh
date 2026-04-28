#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
rm -rf "$SCRIPT_DIR/_state" "$SCRIPT_DIR/.logs"
mkdir -p "$SCRIPT_DIR/_state" "$SCRIPT_DIR/.logs"
echo "mac_test_temp state reset."
