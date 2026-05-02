#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
USER_SLUG="${1:-08_market_research_junior}"
TARGET_DIR="$SCRIPT_DIR/generated/users/$USER_SLUG"

if [[ ! -d "$TARGET_DIR" ]]; then
  echo "Sample not found: $USER_SLUG" >&2
  exit 1
fi

echo "Sample directory: $TARGET_DIR"
ls -1 "$TARGET_DIR"
