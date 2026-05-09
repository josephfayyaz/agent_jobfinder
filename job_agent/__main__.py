from __future__ import annotations

import argparse
import json
import sys

from job_agent.cli import cli
from job_agent.provider_smoke import SMOKE_CASES, run_provider_smoke


def _run_provider_smoke(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m job_agent provider-smoke")
    parser.add_argument("--case", choices=sorted(SMOKE_CASES.keys()), required=True)
    parser.add_argument("--role", default="small")
    args = parser.parse_args(argv)
    result = run_provider_smoke(case=args.case, role=args.role)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "provider-smoke":
        return _run_provider_smoke(args[1:])
    cli()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
