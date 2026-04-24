#!/usr/bin/env bash
set -e

if [[ "${CONDA_DEFAULT_ENV:-}" != "ML" ]]; then
  eval "$(conda shell.bash hook)"
  conda activate ML
fi

# Quick package preflight (no-op if all packages present)
python -c "from job_agent.preflight import check_and_install_packages; check_and_install_packages()" || exit 1

python -m job_agent.cli start "$@"
