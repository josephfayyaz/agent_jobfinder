#!/usr/bin/env python3
"""
start_apply — quick CLI to generate a tailored CV from messy job info.

Usage:
    python start_apply/cli.py
    python start_apply/cli.py --input ~/job_info.txt
    python start_apply/cli.py --input ~/job_info.txt --fact-sheet ~/path/to/fact_sheet.txt
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

from job_agent.llm import ProviderUnavailableError

DEFAULT_FACT_SHEET = Path("/Users/youseffayyaz/Polito/Resume-CV/fact_sheet/master_fact_sheet.txt")


def _resolve_fact_sheet_path(path_arg: Path | None) -> Path:
    return path_arg or Path(os.environ.get("FACT_SHEET_PATH", str(DEFAULT_FACT_SHEET)))


def _load_raw_input(input_path: Path | None) -> str:
    if input_path:
        return input_path.read_text(encoding="utf-8")
    print("Paste job info below (title, company, URL, JD, anything you have).")
    print("Press Enter twice then Ctrl+D when done:\n")
    lines: list[str] = []
    try:
        for line in sys.stdin:
            lines.append(line)
    except KeyboardInterrupt:
        print("\nCancelled.")
        raise SystemExit(0) from None
    raw_text = "".join(lines).strip()
    if not raw_text:
        print("No input provided. Exiting.")
        raise SystemExit(1)
    return raw_text


def _count_bullets(cv: dict) -> int:
    total = 0
    for item in cv.get("experience_bullets", []) or []:
        total += len(item.get("bullets", []) or [])
    for item in cv.get("project_bullets", []) or []:
        total += len(item.get("bullets", []) or [])
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a tailored CV from job info.")
    parser.add_argument("--input", type=Path, help="Path to a text file with job info.")
    parser.add_argument("--fact-sheet", type=Path, default=None, help="Path to your fact sheet.")
    args = parser.parse_args()

    fact_sheet_path = _resolve_fact_sheet_path(args.fact_sheet)
    if not fact_sheet_path.exists():
        print(f"ERROR: Fact sheet not found at {fact_sheet_path}")
        print("Set --fact-sheet or FACT_SHEET_PATH env var.")
        raise SystemExit(1)

    raw_text = _load_raw_input(args.input)
    fact_sheet = fact_sheet_path.read_text(encoding="utf-8")

    from start_apply.cv_writer import generate_cv, save_cv
    from start_apply.job_parser import parse_job_info
    from start_apply.questioner import ask_clarifying_questions
    from start_apply.scorer import score_match

    try:
        print("\nProcessing...\n")
        job = parse_job_info(raw_text)
        print(f"\n[1/4] Parsed: {job['title']} at {job['company']} ({job['location']})")

        result = score_match(job, fact_sheet)
        matched_short = ", ".join(result["matched"][:3]) if result["matched"] else "None"
        gaps_short = ", ".join(result["gaps"]) if result["gaps"] else "None"
        print(f"[2/4] Match score: {result['score']}/100")
        print(f"      Matched: {matched_short}")
        print(f"      Gaps: {gaps_short}")
        print(f"      {result['summary']}")

        if result["score"] >= 85:
            print("Strong match. Proceeding to CV generation...")
        if result["score"] < 30:
            print(f"Low match ({result['score']}/100). CV will reflect confirmed facts only.")

        confirmed_facts = []
        if result["gaps"]:
            confirmed_facts = ask_clarifying_questions(result["gaps"], job, fact_sheet)
            print("\n[3/4] Answers recorded. Generating CV...")
        else:
            print("\n[3/4] No clarification needed. Generating CV...")

        cv = generate_cv(job, fact_sheet, result, confirmed_facts)
        output_path = save_cv(cv, job, result["score"])
        bullet_count = _count_bullets(cv)
        print(f"\n[4/4] CV saved to: {output_path}")
        print(
            "\nSummary:\n"
            f"  Score:    {result['score']}/100\n"
            f"  Company:  {job['company']}\n"
            f"  Role:     {job['title']}\n"
            f"  Bullets:  {bullet_count}\n"
            f"  Output:   {output_path}"
        )
    except ProviderUnavailableError:
        print("ERROR: LM Studio is not running. Start LM Studio and load a model, then retry.")
        print("Ensure the writer model is loaded (the larger one) for best results.")
        raise SystemExit(1) from None
    except ValueError as exc:
        print(f"ERROR: LLM returned an unreadable response: {exc}")
        print("Try again — the model may have returned prose instead of JSON.")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
