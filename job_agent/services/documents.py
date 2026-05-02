from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unicodedata

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

_ROBOTO_PACKAGE_LINE = r"\usepackage[sfdefault,light]{roboto}"
_ENUMITEM_PACKAGE_LINE = r"\usepackage{enumitem}"
_SETLIST_LINE = r"\setlist[itemize]{noitemsep, topsep=2pt, leftmargin=*}"


def _latex_font_package() -> str:
    """Prefer Roboto when installed; otherwise use the default LaTeX font stack."""
    kpsewhich = shutil.which("kpsewhich")
    if kpsewhich:
        try:
            result = subprocess.run(
                [kpsewhich, "roboto.sty"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return r"\usepackage[sfdefault,light]{roboto}"
        except Exception:
            pass
    return ""


def _prepare_tex_for_compilation(tex_path: Path, output_dir: Path) -> Path:
    """Copy the TeX source to the temp dir and swap fonts if Roboto is unavailable."""
    target = output_dir / tex_path.name
    source = tex_path.read_text(encoding="utf-8")
    fallback_font = _latex_font_package()
    if fallback_font != _ROBOTO_PACKAGE_LINE and _ROBOTO_PACKAGE_LINE in source:
        source = source.replace(_ROBOTO_PACKAGE_LINE, fallback_font)
    if _ENUMITEM_PACKAGE_LINE in source:
        source = source.replace(_ENUMITEM_PACKAGE_LINE, "")
    if _SETLIST_LINE in source:
        source = source.replace(_SETLIST_LINE, "")
    source = re.sub(r"\\begin\{itemize\}\s*\\end\{itemize\}", r"\\vspace{0.25em}", source, flags=re.S)
    target.write_text(source, encoding="utf-8")
    return target


def latex_escape(value: str) -> str:
    value = _sanitize_pdflatex_text(value)
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


def _sanitize_pdflatex_text(value: str) -> str:
    """Strip characters that frequently break pdflatex (emoji/private-use/control)."""
    cleaned = []
    for char in str(value or ""):
        category = unicodedata.category(char)
        if category.startswith("C") and char not in {"\n", "\t"}:
            continue
        if category == "So":
            continue
        cleaned.append(char)
    text = "".join(cleaned)
    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "-",
        "\u00a0": " ",
    }
    for raw, replacement in replacements.items():
        text = text.replace(raw, replacement)
    return text


def _render_mode_from_context(job: dict, track: dict) -> str:
    raw = " ".join(
        [
            str(settings.target_job_seniority or ""),
            str(job.get("seniority") or ""),
            str(job.get("title") or ""),
            str(track.get("title") or ""),
        ]
    ).lower()
    if any(token in raw for token in ("senior", "staff", "lead", "principal", "head", "director", "vp")):
        return "senior"
    if any(token in raw for token in ("mid", "intermediate")):
        return "mid"
    return "junior"


def _layout_limits(mode: str) -> dict[str, int]:
    if mode == "senior":
        return {"max_experiences": 6, "max_projects": 3, "max_skills": 18, "exp_bullets": 4, "project_bullets": 3}
    if mode == "mid":
        return {"max_experiences": 4, "max_projects": 2, "max_skills": 14, "exp_bullets": 3, "project_bullets": 2}
    return {"max_experiences": 3, "max_projects": 1, "max_skills": 10, "exp_bullets": 2, "project_bullets": 2}


def ensure_artifacts_dir() -> Path:
    artifacts_dir = resolve_artifacts_dir(settings.artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return artifacts_dir


def _safe_filename(text: str) -> str:
    """Convert user-provided labels to filesystem-safe strings."""
    cleaned = re.sub(r"[^\w\s-]", "", text or "Unknown")
    compact = re.sub(r"[\s]+", "_", cleaned.strip())
    return compact[:30] or "Unknown"


def build_artifact_stem(company: str | None, candidate_name: str | None, draft_id: str) -> str:
    company_slug = _safe_filename(company or "Unknown")
    candidate_slug = _safe_filename(candidate_name or "Candidate")
    date_str = date.today().strftime("%Y-%m-%d")
    return f"{date_str}_{company_slug}_{candidate_slug}_{draft_id[:8]}"


def render_resume_tex(profile: dict, job: dict, track: dict, content: dict, draft_id: str) -> str:
    artifact_dir = ensure_artifacts_dir()
    stem = build_artifact_stem(job.get("company", "Unknown"), profile.get("full_name", "Candidate"), draft_id)
    tex_path = artifact_dir / f"{stem}.tex"

    mode = _render_mode_from_context(job, track)
    limits = _layout_limits(mode)
    experiences = list(content.get("selected_experiences", []))[: limits["max_experiences"]]
    projects = list(content.get("selected_projects", []))[: limits["max_projects"]]
    skills = list(content.get("selected_skills", []))[: limits["max_skills"]]

    experience_blocks: list[str] = []
    for experience in experiences:
        title = latex_escape(experience.get("title", "Experience"))
        company = latex_escape(experience.get("company", "Company"))
        location = latex_escape(experience.get("location", ""))
        dates = latex_escape(experience.get("dates", ""))
        bullet_lines = "\n".join(
            rf"\item {latex_escape(str(bullet))}"
            for bullet in (experience.get("bullets") or [])[: limits["exp_bullets"]]
            if str(bullet).strip()
        )
        header_lines = [rf"\textbf{{{title}}}"]
        if company:
            company_line = rf"\textit{{{company}}}"
            if location:
                company_line += rf" \hfill {location}"
            header_lines.append(company_line)
        if dates:
            header_lines[0] += rf" \hfill {dates}"
        block = "\n".join(header_lines)
        if bullet_lines:
            block += f"\n\\begin{{itemize}}\n{bullet_lines}\n\\end{{itemize}}"
        experience_blocks.append(block)

    project_blocks: list[str] = []
    for project in projects:
        name = latex_escape(project.get("name", "Project"))
        description = latex_escape(project.get("description", ""))
        bullets = "\n".join(
            rf"\item {latex_escape(str(bullet))}"
            for bullet in (project.get("bullets") or [])[: limits["project_bullets"]]
            if str(bullet).strip()
        )
        header = rf"\textbf{{{name}}}"
        if description:
            header += rf" \\ {description}"
        if bullets:
            header += f"\n\\begin{{itemize}}\n{bullets}\n\\end{{itemize}}"
        project_blocks.append(header)

    contact_parts = [latex_escape(profile.get("location", "")), latex_escape(profile.get("email", "")), latex_escape(profile.get("phone", ""))]
    if profile.get("linkedin_url"):
        contact_parts.append(rf"\href{{{profile['linkedin_url']}}}{{LinkedIn}}")
    if profile.get("github_url"):
        contact_parts.append(rf"\href{{{profile['github_url']}}}{{GitHub}}")
    contact_line = r" \quad ".join(part for part in contact_parts if part)

    headline = latex_escape(content.get("headline") or job.get("title") or track.get("title") or "")
    summary_source = str(content.get("professional_summary") or track.get("baseline_summary", ""))
    if mode == "junior":
        summary_words = summary_source.split()
        if len(summary_words) > 55:
            summary_source = " ".join(summary_words[:55]) + "..."
    summary = latex_escape(summary_source)
    experience_section = "\n\n".join(block for block in experience_blocks if block.strip())
    project_section = "\n\n".join(block for block in project_blocks if block.strip())
    project_section_title = "Projects"
    if project_blocks and all(
        str(project.get("name", "") or "").strip().casefold() in {"profile note evidence", "profile evidence"}
        for project in projects
    ):
        project_section_title = "Relevant Evidence"
    experience_block_tex = ""
    if experience_section:
        experience_block_tex = f"\\section{{Professional Experience}}\n{experience_section}\n"
    project_block_tex = ""
    if project_section:
        project_block_tex = f"\\section{{{project_section_title}}}\n{project_section}\n"
    education_lines = []
    for item in profile.get("education") or []:
        degree = latex_escape(item.get("degree", ""))
        institution = latex_escape(item.get("institution", ""))
        field = latex_escape(item.get("field", ""))
        status = latex_escape(item.get("status", "") or item.get("year", ""))
        line = rf"\textbf{{{degree}}}"
        if field:
            line += rf", {field}"
        if institution:
            line += rf" \\ \textit{{{institution}}}"
        if status:
            line += rf" \hfill {status}"
        education_lines.append(line)
    education_section = "\n\n".join(education_lines) or latex_escape("Education details available on request.")
    skills_text = latex_escape(", ".join(str(skill) for skill in skills if str(skill).strip()))
    skills_section = skills_text or latex_escape("Skills available on request.")
    language_items = list(profile.get("languages") or [])
    language_line = ", ".join(
        f"{str(item.get('name') or '').strip()} ({str(item.get('level') or '').strip()})"
        for item in language_items
        if isinstance(item, dict) and str(item.get("name") or "").strip()
    )
    languages_block_tex = ""
    if language_line:
        languages_block_tex = f"\\section{{Languages}}\n{latex_escape(language_line)}\n"
    line_stretch = "1.15" if mode == "senior" else "1.06"
    font_size = "11pt" if mode == "senior" else "10pt"

    tex = rf"""
\documentclass[{font_size},a4paper]{{article}}
\usepackage[T1]{{fontenc}}
\usepackage[utf8]{{inputenc}}
\usepackage[left=0.75in,right=0.75in,top=0.75in,bottom=0.75in]{{geometry}}
\usepackage{{setspace}}
\setstretch{{{line_stretch}}}
{_latex_font_package()}
\usepackage[hidelinks]{{hyperref}}
\newcommand{{\namesize}}{{\fontsize{{19pt}}{{23pt}}\selectfont}}
\newcommand{{\headlinesize}}{{\fontsize{{11pt}}{{13pt}}\selectfont}}
\newcommand{{\sectionsize}}{{\fontsize{{12.5pt}}{{15pt}}\selectfont}}
\newcommand{{\subsize}}{{\fontsize{{10pt}}{{12pt}}\selectfont}}
\renewcommand{{\section}}[1]{{%
  \vspace{{6pt}}{{\sectionsize\bfseries #1}}\vspace{{2pt}}\hrule\vspace{{5pt}}%
}}
\pagestyle{{empty}}
\setlength{{\parindent}}{{0pt}}
\begin{{document}}
\begin{{center}}
{{\namesize\bfseries {latex_escape(profile.get('full_name', 'Candidate') or 'Candidate')}}} \\
{{\headlinesize\textit{{{headline}}}}} \\
{{\subsize {contact_line}}}
\end{{center}}

\section{{Professional Summary}}
{summary}

\section{{Core Skills}}
{skills_section}

{experience_block_tex}

{project_block_tex}

\section{{Education}}
{education_section}

{languages_block_tex}
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
        tmpdir_path = Path(tmpdir)
        compile_target = _prepare_tex_for_compilation(tex_path, tmpdir_path)
        cmd = [
            pdflatex,
            "-interaction=nonstopmode",
            "-halt-on-error",
            f"-output-directory={tmpdir}",
            str(compile_target),
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
                snippet = (combined_output or result.stdout or result.stderr)[-2000:]
                _logger.error("pdflatex failed:\n%s", snippet)
                readable_reason = "Check the .tex file for syntax errors."
                lowered = combined_output.lower()
                if "roboto.sty" in lowered and "not found" in lowered:
                    readable_reason = "The Roboto LaTeX package is not installed."
                elif "emergency stop" in lowered:
                    readable_reason = "LaTeX stopped on a package or syntax error."
                raise RuntimeError(
                    f"pdflatex compilation failed (pass {_pass + 1}). "
                    f"{readable_reason}"
                )

        tmp_pdf = Path(tmpdir) / tex_path.with_suffix(".pdf").name
        shutil.copy(tmp_pdf, pdf_output)
        _logger.info("PDF compiled: %s", pdf_output)

    return str(pdf_output)
