from __future__ import annotations

from pathlib import Path
import sys
from unittest.mock import MagicMock

import pytest

from start_apply.cv_writer import enforce_bullet_word_limit, save_cv
from start_apply.job_parser import parse_job_info
from start_apply.scorer import score_match


def test_parse_job_info_returns_structured_dict():
    router = MagicMock()
    router.generate.return_value = {
        "title": "MLOps Engineer",
        "company": "ACME",
        "location": "Milan",
        "url": "https://example.com/job",
        "description": "Job desc",
        "requirements": ["Python", "Kubernetes"],
        "nice_to_have": ["Terraform"],
        "seniority": "mid",
    }

    out = parse_job_info("raw text", router=router)

    assert {"title", "company", "description"} <= out.keys()
    assert out["title"] == "MLOps Engineer"


def test_score_match_returns_score_and_gaps():
    router = MagicMock()
    router.generate.return_value = {
        "score": 76,
        "matched": ["Python", "Docker"],
        "gaps": ["Kubernetes"],
        "summary": "Good fit with one gap.",
    }

    out = score_match({"title": "AI Engineer", "company": "ACME", "requirements": []}, "fact", router=router)

    assert isinstance(out["score"], int)
    assert 0 <= out["score"] <= 100
    assert isinstance(out["gaps"], list)


def test_enforce_bullet_word_limit():
    long_bullet = " ".join(f"w{i}" for i in range(1, 31))
    cv = {
        "experience_bullets": [{"role": "X", "company": "Y", "bullets": [long_bullet]}],
        "project_bullets": [],
    }

    out = enforce_bullet_word_limit(cv, limit=22)
    words = out["experience_bullets"][0]["bullets"][0].split()

    assert len(words) <= 22
    assert words[-1] == "w22"


def test_save_cv_creates_file(tmp_path: Path):
    cv = {
        "headline": "AI Engineer",
        "professional_summary": "Summary",
        "key_skills": ["Python"],
        "experience_bullets": [{"role": "Engineer", "company": "ACME", "bullets": ["Built pipelines."]}],
        "project_bullets": [{"name": "Project A", "bullets": ["Implemented tooling."]}],
        "tailoring_notes": ["Matches role language."],
    }
    job = {"title": "AI Engineer", "company": "ACME", "location": "Milan"}

    output = save_cv(cv, job, 80, output_dir=tmp_path)

    assert output.exists()
    assert output.suffix == ".md"


def test_cli_exits_gracefully_when_no_fact_sheet(monkeypatch, tmp_path: Path):
    from start_apply import cli

    missing = tmp_path / "missing_fact_sheet.txt"
    monkeypatch.setattr(sys, "argv", ["cli.py", "--fact-sheet", str(missing)])

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 1
