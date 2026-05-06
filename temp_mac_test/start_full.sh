#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/runtime_env.sh"

cd "$REPO_ROOT"

"$PYTHON_BIN" -m job_agent.worker >"$SCRIPT_DIR/.logs/worker.log" 2>&1 &
WORKER_PID=$!
echo "$WORKER_PID" >"$QA_PID_DIR/worker.pid"

APP_URL="${APP_URL:-http://127.0.0.1:${APP_PORT}/onboarding/}"
AUTO_OPEN_BROWSER="${AUTO_OPEN_BROWSER:-1}"

maybe_open_browser() {
  if [[ "$AUTO_OPEN_BROWSER" != "1" ]]; then
    return 0
  fi

  (
    "$PYTHON_BIN" - "$APP_URL" <<'PY'
import shutil
import subprocess
import sys
import time
import urllib.request

url = sys.argv[1]
deadline = time.time() + 45

while time.time() < deadline:
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            if response.status < 500:
                break
    except Exception:
        time.sleep(0.5)
else:
    raise SystemExit(0)

for command in (["open", url], ["xdg-open", url]):
    if shutil.which(command[0]):
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        break
PY
  ) >/dev/null 2>&1 &
}

cleanup() {
  kill "$WORKER_PID" >/dev/null 2>&1 || true
  rm -f "$QA_PID_DIR/worker.pid" "$QA_PID_DIR/app.pid"
}
trap cleanup EXIT INT TERM

echo "$$" >"$QA_PID_DIR/app.pid"
maybe_open_browser
exec "$PYTHON_BIN" -m uvicorn job_agent.main:app --host 127.0.0.1 --port "$APP_PORT" --reload
