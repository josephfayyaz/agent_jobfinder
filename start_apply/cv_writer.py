from __future__ import annotations

from datetime import datetime
from pathlib import Path

from job_agent.config import settings
from job_agent.llm import LLMRouter


_SYSTEM_PROMPT = """You are a professional resume writer. Write a tailored CV section using only
confirmed facts. Rules:
- Use the company's exact language from the job description.
- Each bullet must be ≤ 22 words.
- Start each bullet with a strong past-tense action verb.
- Include at least one metric per bullet where possible.
- NEVER fabricate skills or outcomes. If the user said "no" to a question, omit that skill.
- Vary your verbs. Do not start two bullets with the same word.
Return valid JSON only."""


def enforce_bullet_word_limit(cv: dict, limit: int = 22) -> dict:
    for section in ("experience_bullets", "project_bullets"):
        for item in cv.get(section, []) or []:
            fixed = []
            for bullet in item.get("bullets", []) or []:
                words = str(bullet).split()
                if len(words) > limit:
                    bullet = " ".join(words[:limit])
                fixed.append(str(bullet))
            item["bullets"] = fixed
    return cv


def generate_cv(
    job: dict,
    fact_sheet: str,
    score_result: dict,
    confirmed_facts: list[dict],
    router: LLMRouter | None = None,
) -> dict:
    router = router or LLMRouter()
    req_text = "\n".join(f"- {item}" for item in (job.get("requirements") or []))
    confirmed_lines: list[str] = []
    denied_lines: list[str] = []
    for answer in confirmed_facts:
        gap = str(answer.get("gap") or answer.get("question_id") or "unknown_gap")
        if answer.get("confirmed"):
            confirmed_lines.append(f"- {gap}: {answer.get('answer', '')}")
        else:
            denied_lines.append(f"- {gap}: NOT CONFIRMED — omit this skill")
    if not confirmed_lines:
        confirmed_lines.append("- (none)")
    if not denied_lines:
        denied_lines.append("- (none)")

    user_prompt = f"""JOB: {job.get("title", "Unknown")} at {job.get("company", "Unknown")}
LOCATION: {job.get("location", "Unknown")}
SENIORITY: {job.get("seniority", "unknown")}

JOB REQUIREMENTS:
{req_text}

CANDIDATE FACT SHEET:
{fact_sheet[:4000]}

CONFIRMED ADDITIONAL FACTS (from clarifying questions):
{chr(10).join(confirmed_lines)}
{chr(10).join(denied_lines)}

MATCH ANALYSIS:
{score_result.get("summary", "")}
Matched: {score_result.get("matched", [])}

Generate a tailored CV. Return JSON:
{{
  "headline": "job title variant matching the role",
  "professional_summary": "3-4 sentence summary using company language, ≤80 words",
  "key_skills": ["skill1", "skill2", ...],
  "experience_bullets": [
    {{
      "role": "role title from fact sheet",
      "company": "company from fact sheet",
      "bullets": ["bullet 1", "bullet 2", ...]
    }}
  ],
  "project_bullets": [
    {{
      "name": "project name",
      "bullets": ["bullet"]
    }}
  ],
  "tailoring_notes": ["note about why this CV matches the role"]
}}"""
    data = router.generate(
        role="writer",
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )
    cv = {
        "headline": str(data.get("headline") or job.get("title") or "Tailored CV"),
        "professional_summary": str(data.get("professional_summary") or ""),
        "key_skills": list(data.get("key_skills") or []),
        "experience_bullets": list(data.get("experience_bullets") or []),
        "project_bullets": list(data.get("project_bullets") or []),
        "tailoring_notes": list(data.get("tailoring_notes") or []),
    }
    return enforce_bullet_word_limit(cv, limit=settings.bullet_clarify_word_limit)


def save_cv(cv: dict, job: dict, score: int, output_dir: Path | None = None) -> Path:
    output_dir = output_dir or Path("start_apply/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    company = str(job.get("company") or "company")
    slug_chars = []
    for ch in company.lower():
        if ch.isalnum():
            slug_chars.append(ch)
        elif ch in {" ", "-", "_"}:
            slug_chars.append("_")
    company_slug = "".join(slug_chars).strip("_") or "company"
    while "__" in company_slug:
        company_slug = company_slug.replace("__", "_")

    date_str = datetime.now().strftime("%Y-%m-%d")
    file_path = output_dir / f"{company_slug}_{date_str}.md"

    lines = [
        f"# CV — {job.get('title', 'Unknown Role')} at {company}",
        f"**Generated:** {datetime.now().isoformat(timespec='minutes')}",
        f"**Match Score:** {score}/100",
        f"**Location:** {job.get('location', 'Unknown')}",
        "",
        "---",
        "",
        f"## {cv.get('headline', '')}",
        "",
        cv.get("professional_summary", ""),
        "",
        "---",
        "",
        "## Key Skills",
    ]
    for skill in cv.get("key_skills", []):
        lines.append(f"- {skill}")

    lines.extend(["", "---", "", "## Experience"])
    for role in cv.get("experience_bullets", []):
        lines.append(f"### {role.get('role', '')} at {role.get('company', '')}")
        for bullet in role.get("bullets", []):
            lines.append(f"- {bullet}")

    lines.extend(["", "---", "", "## Projects"])
    for project in cv.get("project_bullets", []):
        lines.append(f"### {project.get('name', '')}")
        for bullet in project.get("bullets", []):
            lines.append(f"- {bullet}")

    lines.extend(["", "---", "", "## Tailoring Notes"])
    for note in cv.get("tailoring_notes", []):
        lines.append(f"- {note}")

    lines.extend(["", "---", "*Generated by start_apply CLI. Verify all facts before submitting.*", ""])
    file_path.write_text("\n".join(lines), encoding="utf-8")
    return file_path
