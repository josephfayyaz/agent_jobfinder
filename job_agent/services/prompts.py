"""
LLM prompts for the CV generation pipeline.

All prompts follow one strict rule: end with an unambiguous JSON instruction.
MLX thinking models do not enforce response_format — the JSON contract lives here.

Prompt authorship philosophy (from Yousef's Resume_prompt_template):
  - Source of truth is the fact sheet. Never invent facts, metrics, or skills.
  - Optimize for both ATS parsing and 6-second recruiter skim.
  - XYZ bullet format: [action verb] + [scope/context] + [tools] + [outcome].
  - ATS-safe layout only: single column, no tables, no graphics, no icons.
  - If a modern style preference conflicts with ATS safety, choose ATS safety.

Scoring rubric (used in both writer instructions and reviewer evaluation):
  Role Fit         25 pts  headline + summary directly address the target role
  Evidence Quality 25 pts  bullets are quantified, XYZ format, real outcomes
  Keyword Coverage 20 pts  key JD terms appear naturally (not stuffed)
  Clarity          15 pts  concise, professional, no empty buzzwords
  ATS Safety       15 pts  no tables/graphics, standard titles, clean parsing
  ─────────────────────────────────────────────────────────────────
  Total           100 pts
  pass   >= 85    accept as-is
  revise  60–84   targeted edits
  rewrite  < 60   full rewrite or cloud escalation
"""

from __future__ import annotations


# ── Writer ────────────────────────────────────────────────────────────────────

def build_writer_system_prompt() -> str:
    return """\
You are an elite resume strategist, ATS compliance specialist, and senior technical recruiter \
specialising in data engineering, AI/ML, cloud/MLOps, and analytics roles at European and global \
tech companies.

ABSOLUTE RULES — never break these:
1. Treat the candidate fact sheet as the sole source of truth. Never invent facts, metrics, \
dates, titles, supervisors, skills, publications, or outcomes.
2. Quantify only verified facts. Prefer omission over speculation.
3. If ATS safety conflicts with visual preference, always choose ATS safety.
4. Avoid generic buzzwords ("passionate", "hardworking", "team player") unless backed by evidence.

ATS LAYOUT (non-negotiable):
- Single-column layout only.
- No tables, text boxes, graphics, icons, photos, skill bars, or decorative elements.
- No content in page headers or footers.
- Use only standard section titles: Summary, Experience, Projects, Education, Skills, Certifications.
- Contact info may be centred in the document body; never in a header/footer.

BULLET FORMAT — XYZ pattern:
Write each bullet as: [Strong past-tense action verb] + [scope/context] + [tools/method] + [quantified outcome]
Example: "Reduced pipeline latency by 40% by migrating batch ETL to streaming using Apache Kafka."
- One line where possible, two lines maximum.
- Always start with a past-tense action verb.
- Max 4 bullets per experience. Max 3 bullets per project.

SECTION ORDER — default (industry roles):
  Header → Summary → Core Skills → Experience → Projects → Education → Certifications

SECTION ORDER — research / AI roles (apply when role involves research, academia, or ML systems):
  Header → Summary → Core Skills → Selected Research Projects → Research Experience → \
Professional Experience → Education

SCORING RUBRIC you will be judged against (so optimise for it):
  Role Fit         25 pts — headline + summary directly address the target role and company
  Evidence Quality 25 pts — bullets are quantified, XYZ format, concrete outcomes
  Keyword Coverage 20 pts — key JD terms appear naturally in summary, bullets, skills
  Clarity          15 pts — concise, no empty buzzwords, parallel structure
  ATS Safety       15 pts — no tables/graphics, standard titles, single column

OUTPUT FORMAT — return valid JSON only. No markdown, no code fences, no explanation text.
{
  "headline": "<target role title matching the job>",
  "professional_summary": "<3–4 sentences: years of experience, core competency, target role, key value>",
  "selected_experiences": [
    {"title": "", "company": "", "location": "", "bullets": ["<XYZ bullet>", ...]}
  ],
  "selected_projects": [
    {"name": "", "repo_url": "", "bullets": ["<XYZ bullet>", ...]}
  ],
  "selected_skills": ["<8–12 skills that appear in BOTH profile AND job description>"],
  "tailoring_notes": ["<key tailoring decisions made and why>"]
}"""


def build_writer_user_prompt(profile: dict, track: dict, job: dict) -> str:
    return f"""\
Generate a tailored resume for the following candidate, track, and job.

══ TARGET JOB ══════════════════════════════════════════════════════════════════
Company:       {job.get("company", "N/A")}
Title:         {job.get("title", "N/A")}
Location:      {job.get("location") or job.get("city", "N/A")}
Remote Policy: {job.get("remote_policy", "N/A")}
Role Hint:     {job.get("role_track_hint", "N/A")}

Job Description:
{job.get("description", "N/A")}

══ RESUME TRACK ════════════════════════════════════════════════════════════════
Track:    {track.get("title", "N/A")}
Family:   {track.get("role_family", "N/A")}
Baseline: {track.get("baseline_summary", "")}
Emphasis: {track.get("emphasis", {})}
Keywords: {", ".join(track.get("target_keywords", []))}

══ CANDIDATE PROFILE ═══════════════════════════════════════════════════════════
Name:     {profile.get("full_name", "N/A")}
Location: {profile.get("location", "N/A")}
Email:    {profile.get("email", "N/A")}
LinkedIn: {profile.get("linkedin_url", "")}
GitHub:   {profile.get("github_url", "")}

Brand Summary:
{profile.get("public_brand_summary", "")}

── EXPERIENCES ─────────────────────────────────────────────────────────────────
{_format_experiences(profile.get("experiences") or [])}

── PROJECTS ────────────────────────────────────────────────────────────────────
{_format_projects(profile.get("projects") or [])}

── EDUCATION ───────────────────────────────────────────────────────────────────
{_format_education(profile.get("education") or [])}

── SKILLS ──────────────────────────────────────────────────────────────────────
{", ".join(profile.get("global_skills") or [])}

── CERTIFICATIONS ──────────────────────────────────────────────────────────────
{", ".join(str(c) for c in (profile.get("certifications") or [])) or "None listed"}

── ACHIEVEMENTS ────────────────────────────────────────────────────────────────
{", ".join(str(a) for a in (profile.get("achievements") or [])) or "None listed"}

══ INSTRUCTIONS ════════════════════════════════════════════════════════════════
1. Extract the 5–7 most important requirements from the job description.
2. Select the 2–3 most relevant experiences and 1–2 most relevant projects.
3. Write 3–4 XYZ-format bullets per experience (quantified where facts support it).
4. Write the summary for THIS exact role and company (3–4 sentences max).
5. Select 8–12 skills present in BOTH the profile AND the job description.
6. Apply the track emphasis: {track.get("emphasis", {})}.
7. Return valid JSON only — no markdown, no code fences, no extra text.
""".strip()


# ── Reviewer ──────────────────────────────────────────────────────────────────

def build_reviewer_system_prompt() -> str:
    return """\
You are a strict resume reviewer and ATS compliance auditor acting as a senior recruiter \
at the target company.

Score the resume against this weighted rubric (total 100 points):

  Role Fit         25 pts  Does the headline and summary speak directly to the job and company?
  Evidence Quality 25 pts  Are achievements quantified? Do bullets use the XYZ format?
  Keyword Coverage 20 pts  Do the key JD terms appear naturally in summary, bullets, and skills?
  Clarity          15 pts  Is writing professional, concise, free of buzzwords without evidence?
  ATS Safety       15 pts  No tables, graphics, columns, or non-standard section titles?

Decision thresholds:
  pass    score >= 85  — ready for submission
  revise  60 <= score < 85  — fixable with targeted edits
  rewrite score < 60   — fundamental restructuring needed

Be honest and aggressive. A score of 70 means real problems remain.

OUTPUT FORMAT — return valid JSON only. No markdown, no code fences, no explanation text.
{
  "score": <0–100 integer>,
  "role_fit_score":  <0–25>,
  "evidence_score":  <0–25>,
  "keyword_score":   <0–20>,
  "clarity_score":   <0–15>,
  "ats_score":       <0–15>,
  "decision":        "pass" | "revise" | "rewrite",
  "strengths":       ["<what the resume does well>"],
  "gaps":            ["<what is missing or weak>"],
  "must_fix":        ["<specific, actionable changes required>"],
  "keyword_coverage": ["<JD keywords found in the resume>"],
  "revised_summary": "<improved 3–4 sentence professional summary>"
}"""


def build_reviewer_user_prompt(
    profile: dict, track: dict, job: dict, draft: dict
) -> str:
    return f"""\
Review the following resume draft for the target job and provide a structured critique.

══ TARGET JOB ══════════════════════════════════════════════════════════════════
Company:  {job.get("company", "N/A")}
Title:    {job.get("title", "N/A")}
Location: {job.get("location") or job.get("city", "N/A")}

Job Description:
{job.get("description", "N/A")}

══ RESUME TRACK ════════════════════════════════════════════════════════════════
Track:    {track.get("title", "N/A")}
Keywords: {", ".join(track.get("target_keywords", []))}
Emphasis: {track.get("emphasis", {})}

══ CANDIDATE BACKGROUND (for fact-checking) ════════════════════════════════════
Brand Summary: {profile.get("public_brand_summary", "")}
Skills on file: {", ".join((profile.get("global_skills") or [])[:20])}

══ RESUME DRAFT ════════════════════════════════════════════════════════════════
Headline:    {draft.get("headline", "")}

Summary:
{draft.get("professional_summary", "")}

Selected Skills:
{", ".join(draft.get("selected_skills") or [])}

Experiences:
{_format_draft_experiences(draft.get("selected_experiences") or [])}

Projects:
{_format_draft_projects(draft.get("selected_projects") or [])}

Tailoring Notes:
{chr(10).join(f"- {n}" for n in (draft.get("tailoring_notes") or []))}

══ INSTRUCTIONS ════════════════════════════════════════════════════════════════
1. Score each rubric dimension independently before computing the total.
2. Check every factual claim against the candidate background — flag invented facts in must_fix.
3. Be specific in must_fix: name the exact bullet or section that needs changing.
4. revised_summary must improve on the draft summary, not just rephrase it.
5. Return valid JSON only — no markdown, no code fences, no extra text.
""".strip()


# ── Reviser ───────────────────────────────────────────────────────────────────

def build_revision_prompt(job: dict, draft: dict, feedback: dict) -> str:
    must_fix = "\n".join(f"  - {item}" for item in (feedback.get("must_fix") or []))
    gaps = "\n".join(f"  - {g}" for g in (feedback.get("gaps") or []))
    return f"""\
Revise this resume draft using the reviewer feedback below. Fix every item in must_fix.
Return valid JSON only with the same keys as the original draft. No markdown, no extra text.

══ TARGET JOB ══════════════════════════════════════════════════════════════════
Company: {job.get("company", "N/A")}
Title:   {job.get("title", "N/A")}

Job Description (excerpt for keyword alignment):
{str(job.get("description", ""))[:800]}

══ CURRENT DRAFT ═══════════════════════════════════════════════════════════════
{_safe_json_excerpt(draft)}

══ REVIEWER FEEDBACK ═══════════════════════════════════════════════════════════
Score:   {feedback.get("score", "N/A")} / 100
Decision: {feedback.get("decision", "N/A")}

Must Fix:
{must_fix or "  (none listed)"}

Gaps to Address:
{gaps or "  (none listed)"}

Improved Summary Suggested by Reviewer:
{feedback.get("revised_summary", "")}

══ INSTRUCTIONS ════════════════════════════════════════════════════════════════
1. Apply every must_fix item.
2. Use the reviewer's revised_summary as the starting point for the new summary.
3. Improve keyword density naturally — do not keyword-stuff.
4. Keep all facts verified against the original draft. Do not invent new facts.
5. Return valid JSON only — same structure as the current draft.
""".strip()


# ── Private formatters ────────────────────────────────────────────────────────

def _format_experiences(experiences: list[dict]) -> str:
    """Format experience list into readable text for the writer prompt."""
    if not experiences:
        return "(no experiences on file)"
    lines = []
    for exp in experiences:
        title = exp.get("title", "Untitled")
        company = exp.get("company", "")
        location = exp.get("location", "")
        header = f"[{title} — {company}" + (f", {location}" if location else "") + "]"
        lines.append(header)
        if exp.get("summary"):
            lines.append(f"  Summary: {exp['summary']}")
        for bullet in exp.get("bullets") or []:
            lines.append(f"  • {bullet}")
        skills = exp.get("skills") or []
        if skills:
            lines.append(f"  Skills: {', '.join(skills)}")
        lines.append("")
    return "\n".join(lines).strip()


def _format_projects(projects: list[dict]) -> str:
    """Format project list into readable text for the writer prompt."""
    if not projects:
        return "(no projects on file)"
    lines = []
    for proj in projects:
        name = proj.get("name", "Untitled")
        repo = proj.get("repo_url", "")
        header = f"[{name}" + (f" | {repo}" if repo else "") + "]"
        lines.append(header)
        if proj.get("summary"):
            lines.append(f"  Summary: {proj['summary']}")
        for bullet in proj.get("bullets") or []:
            lines.append(f"  • {bullet}")
        skills = proj.get("skills") or []
        if skills:
            lines.append(f"  Skills: {', '.join(skills)}")
        lines.append("")
    return "\n".join(lines).strip()


def _format_education(education: list[dict]) -> str:
    """Format education list into readable text for the writer prompt."""
    if not education:
        return "(no education on file)"
    lines = []
    for edu in education:
        presentation = edu.get("presentation")
        if presentation:
            lines.append(f"• {presentation}")
        else:
            degree = edu.get("degree", "")
            field = edu.get("field", "")
            institution = edu.get("institution", "")
            status = edu.get("status", "")
            parts = filter(None, [degree, field, institution, status])
            lines.append(f"• {', '.join(parts)}")
    return "\n".join(lines)


def _format_draft_experiences(experiences: list[dict]) -> str:
    """Format draft experiences (from writer output) for the reviewer prompt."""
    if not experiences:
        return "(none selected)"
    lines = []
    for exp in experiences:
        title = exp.get("title", "")
        company = exp.get("company", "")
        lines.append(f"  [{title} — {company}]")
        for bullet in exp.get("bullets") or []:
            lines.append(f"    • {bullet}")
    return "\n".join(lines)


def _format_draft_projects(projects: list[dict]) -> str:
    """Format draft projects (from writer output) for the reviewer prompt."""
    if not projects:
        return "(none selected)"
    lines = []
    for proj in projects:
        name = proj.get("name", "")
        lines.append(f"  [{name}]")
        for bullet in proj.get("bullets") or []:
            lines.append(f"    • {bullet}")
    return "\n".join(lines)


def _safe_json_excerpt(data: dict, max_chars: int = 1500) -> str:
    """Render a dict as a compact JSON string, truncated if too long."""
    import json
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if len(text) > max_chars:
        return text[:max_chars] + "\n  ... (truncated)"
    return text
