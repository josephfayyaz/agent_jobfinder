from __future__ import annotations

from pathlib import Path

from job_agent.config import settings


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
    settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
    return settings.artifacts_dir


def render_resume_tex(profile: dict, job: dict, track: dict, content: dict, draft_id: str) -> str:
    artifact_dir = ensure_artifacts_dir()
    tex_path = artifact_dir / f"{draft_id}.tex"

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
\documentclass[10pt]{{article}}
\usepackage[margin=0.7in]{{geometry}}
\usepackage[hidelinks]{{hyperref}}
\usepackage{{enumitem}}
\setlist[itemize]{{nosep,leftmargin=*}}
\pagestyle{{empty}}
\begin{{document}}
\begin{{center}}
{{\LARGE \textbf{{{latex_escape(profile.get('full_name', 'Candidate') or 'Candidate')}}}}} \\
{contact_line}
\end{{center}}

\section*{{Target Role}}
{latex_escape(job.get('title', 'Unknown Role'))} at {latex_escape(job.get('company', 'Unknown Company'))}

\section*{{Profile}}
{latex_escape(content.get('professional_summary', track.get('baseline_summary', '')))}

\section*{{Selected Skills}}
{latex_escape(", ".join(skills))}

\section*{{Experience}}
\begin{{itemize}}
{chr(10).join(experience_lines)}
\end{{itemize}}

\section*{{Projects}}
\begin{{itemize}}
{chr(10).join(project_lines)}
\end{{itemize}}

\section*{{Tailoring Notes}}
\begin{{itemize}}
{chr(10).join(rf"\item {latex_escape(note)}" for note in content.get("tailoring_notes", []))}
\end{{itemize}}
\end{{document}}
""".strip()

    tex_path.write_text(tex, encoding="utf-8")
    return str(tex_path)
