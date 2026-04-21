#!/usr/bin/env bash
set -e

if [[ "${CONDA_DEFAULT_ENV:-}" != "ML" ]]; then
  eval "$(conda shell.bash hook)"
  conda activate ML
fi

python -m job_agent.cli start "$@"
