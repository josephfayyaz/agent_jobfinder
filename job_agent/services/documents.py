from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from job_agent.config import settings
from job_agent.runtime_paths import resolve_artifacts_dir

_logger = logging.getLogger(__name__)

_PDFLATEX_SEARCH_PATHS = [
    "/usr/local/texlive/2024/bin/universal-darwin/pdflatex",
    "/usr/local/texlive/2023/bin/universal-darwin/pdflatex",
    "/Library/TeX/texbin/pdflatex",
    "/opt/homebrew/bin/pdflatex",
    "pdflatex",
]


def latex_escape(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    output = value
    for raw, escaped in replacements.items():
        output = output.replace(raw, escaped)
    return output


def ensure_artifacts_dir() -> Path:
    artifacts_dir = resolve_artifacts_dir(settings.artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return artifacts_dir


def _safe_filename(text: str) -> str:
    """Convert user-provided labels to filesystem-safe strings."""
    cleaned = re.sub(r"[^\w\s-]", "", text or "Unknown")
    compact = re.sub(r"[\s]+", "_", cleaned.strip())
    return compact[:30] or "Unknown"


def build_artifact_stem(company: str | None, draft_id: str) -> str:
    company_slug = _safe_filename(company or "Unknown")
    date_str = date.today().strftime("%Y-%m-%d")
    return f"{company_slug}_{date_str}_{draft_id[:8]}"


def render_resume_tex(profile: dict, job: dict, track: dict, content: dict, draft_id: str) -> str:
    artifact_dir = ensure_artifacts_dir()
    stem = build_artifact_stem(job.get("company", "Unknown"), draft_id)
    tex_path = artifact_dir / f"{stem}.tex"

    experiences = content.get("selected_experiences", [])
    projects = content.get("selected_projects", [])
    skills = content.get("selected_skills", [])

    experience_lines = []
    for experience in experiences:
        experience_lines.append(
            rf"\textbf{{{latex_escape(experience.get('title', 'Experience'))}}} --- "
            rf"{latex_escape(experience.get('company', 'Company'))} \\"
        )
        for bullet in experience.get("bullets", []):
            experience_lines.append(rf"\item {latex_escape(bullet)}")
        experience_lines.append("")

    project_lines = []
    for project in projects:
        project_lines.append(rf"\textbf{{{latex_escape(project.get('name', 'Project'))}}} \\")
        for bullet in project.get("bullets", []):
            project_lines.append(rf"\item {latex_escape(bullet)}")
        project_lines.append("")

    contact_parts = [
        latex_escape(profile.get("email", "")),
        latex_escape(profile.get("phone", "")),
    ]
    if profile.get("linkedin_url"):
        contact_parts.append(rf"\href{{{profile['linkedin_url']}}}{{LinkedIn}}")
    if profile.get("github_url"):
        contact_parts.append(rf"\href{{{profile['github_url']}}}{{GitHub}}")
    contact_line = r" \quad ".join(part for part in contact_parts if part)

    tex = rf"""
\documentclass[11pt,a4paper]{{article}}
\usepackage[T1]{{fontenc}}
\usepackage[utf8]{{inputenc}}
\usepackage[left=0.75in,right=0.75in,top=0.75in,bottom=0.75in]{{geometry}}
\usepackage{{setspace}}
\setstretch{{1.15}}
\usepackage[sfdefault,light]{{roboto}}
\usepackage[hidelinks]{{hyperref}}
\usepackage{{enumitem}}
\setlist[itemize]{{noitemsep, topsep=2pt, leftmargin=*}}
\newcommand{{\namesize}}{{\fontsize{{18pt}}{{22pt}}\selectfont}}
\newcommand{{\sectionsize}}{{\fontsize{{14pt}}{{18pt}}\selectfont}}
\newcommand{{\subsize}}{{\fontsize{{10pt}}{{12pt}}\selectfont}}
\renewcommand{{\section}}[1]{{%
  {{\sectionsize\bfseries #1}}\vspace{{2pt}}\hrule\vspace{{6pt}}%
}}
\pagestyle{{empty}}
\begin{{document}}
\begin{{center}}
{{\namesize\bfseries {latex_escape(profile.get('full_name', 'Candidate') or 'Candidate')}}} \\
{{\subsize {contact_line}}}
\end{{center}}

\section{{Target Role}}
{latex_escape(job.get('title', 'Unknown Role'))} at {latex_escape(job.get('company', 'Unknown Company'))}

\section{{Profile}}
{latex_escape(content.get('professional_summary', track.get('baseline_summary', '')))}

\section{{Selected Skills}}
{latex_escape(", ".join(skills))}

\section{{Experience}}
\begin{{itemize}}
{chr(10).join(experience_lines)}
\end{{itemize}}

\section{{Projects}}
\begin{{itemize}}
{chr(10).join(project_lines)}
\end{{itemize}}

\section{{Tailoring Notes}}
\begin{{itemize}}
{chr(10).join(rf"\item {latex_escape(note)}" for note in content.get("tailoring_notes", []))}
\end{{itemize}}
\end{{document}}
""".strip()

    tex_path.write_text(tex, encoding="utf-8")
    return str(tex_path)


def _find_pdflatex() -> str:
    """Return the first available pdflatex binary path, or raise if none found."""
    for candidate in _PDFLATEX_SEARCH_PATHS:
        if candidate == "pdflatex":
            if shutil.which("pdflatex"):
                return "pdflatex"
        elif Path(candidate).is_file():
            return candidate
    raise FileNotFoundError(
        "pdflatex not found. Install BasicTeX: brew install --cask basictex"
    )


def check_pdflatex() -> tuple[bool, str | None]:
    """
    Check if pdflatex is available on the system.
    Returns (available: bool, path: str | None).
    """
    try:
        path = _find_pdflatex()
    except FileNotFoundError:
        return (False, None)
    return (path is not None, path)


def compile_pdf(tex_path: str) -> str:
    """Compile a .tex file to .pdf and return the PDF path."""
    tex_path = Path(tex_path).resolve()
    if not tex_path.exists():
        raise FileNotFoundError(f"TeX source not found: {tex_path}")

    pdflatex = _find_pdflatex()
    pdf_output = tex_path.with_suffix(".pdf")

    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = [
            pdflatex,
            "-interaction=nonstopmode",
            "-halt-on-error",
            f"-output-directory={tmpdir}",
            str(tex_path),
        ]
        retried_after_roboto_install = False
        for _pass in range(2):
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                combined_output = f"{result.stdout}\n{result.stderr}"
                if (
                    not retried_after_roboto_install
                    and "roboto.sty" in combined_output
                    and "not found" in combined_output.lower()
                ):
                    tlmgr = shutil.which("tlmgr")
                    if tlmgr is not None:
                        install_result = subprocess.run(
                            [tlmgr, "install", "roboto"],
                            capture_output=True,
                            text=True,
                        )
                        if install_result.returncode == 0:
                            retried_after_roboto_install = True
                            _logger.info("Installed roboto LaTeX package via tlmgr; retrying pdflatex")
                            result = subprocess.run(cmd, capture_output=True, text=True)
                            if result.returncode == 0:
                                continue
                _logger.error("pdflatex failed:\n%s", result.stdout[-2000:])
                raise RuntimeError(
                    f"pdflatex compilation failed (pass {_pass + 1}). "
                    "Check the .tex file for syntax errors."
                )

        tmp_pdf = Path(tmpdir) / tex_path.with_suffix(".pdf").name
        shutil.copy(tmp_pdf, pdf_output)
        _logger.info("PDF compiled: %s", pdf_output)

    return str(pdf_output)
