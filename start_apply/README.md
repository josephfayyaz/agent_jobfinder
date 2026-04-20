# start_apply — Quick CV Generator CLI

Generate a tailored CV from messy job info in under 2 minutes.

## Requirements
- LM Studio running at localhost:1234
- Writer model loaded (qwen3.5-27b or similar)
- conda ML environment activated

## Usage

    conda activate ML

    # Paste mode (interactive)
    python start_apply/cli.py

    # File mode
    python start_apply/cli.py --input ~/Downloads/job_info.txt

    # Custom fact sheet
    python start_apply/cli.py --input ~/job.txt --fact-sheet ~/path/fact_sheet.txt

## Output
CVs are saved to start_apply/output/{company}_{date}.md
