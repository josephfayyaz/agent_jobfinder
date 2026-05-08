"""
LLM prompts for the CV generation pipeline.

All prompts follow one strict rule: end with an unambiguous JSON instruction.
MLX thinking models do not enforce response_format — the JSON contract lives here.

Prompt authorship philosophy (from the original resume prompt template):
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

from job_agent.services.resource_loader import load_prompt_resource


# ── Writer ────────────────────────────────────────────────────────────────────

def resolve_presentation_mode(
    target_seniority: str | None,
    job_seniority: str | None = None,
) -> str:
    """
    Map a seniority label to a presentation_mode ("junior", "mid", "senior").
    Per-job seniority overrides the global target seniority.
    """
    from job_agent.config import get_settings

    raw = (job_seniority or target_seniority or get_settings().target_job_seniority or "").lower()
    if raw in ("intern", "entry", "junior", "graduate", "trainee"):
        return "junior"
    if raw in ("mid", "midlevel", "mid-level", "intermediate"):
        return "mid"
    if raw in ("senior", "staff", "lead", "principal", "head", "director", "vp"):
        return "senior"
    return "junior"


def build_writer_system_prompt() -> str:
    return load_prompt_resource("writer_system.md").strip()


def build_keyword_extraction_system_prompt() -> str:
    return """You are an ATS keyword analyst. Extract exact keywords from job descriptions
that applicant tracking systems and recruiters look for. Return valid JSON only.
No markdown, no extra text."""


def build_keyword_extraction_prompt(job_dict: dict) -> str:
    return f"""JOB: {job_dict.get("title", "N/A")} at {job_dict.get("company", "N/A")}
LOCATION: {job_dict.get("location", "not specified")}

JOB DESCRIPTION:
{str(job_dict.get("description", ""))[:3000]}

Task: Extract the top 12 keywords from this job description that a resume must contain.
These are skills, tools, methodologies, and outcomes explicitly stated or strongly implied.

Rank them by importance:
- Rank 1-4: Must-have (in title, requirements, or mentioned 3+ times)
- Rank 5-8: Important (in requirements or mentioned 2 times)
- Rank 9-12: Nice-to-have (mentioned once, in "preferred" section)

Return valid JSON only:
{{
  "keywords": [
    {{"rank": 1, "term": "...", "exact_phrase": "phrase from JD", "tier": "must|important|nice"}}
  ]
}}"""


def build_compliance_matrix_system_prompt() -> str:
    return load_prompt_resource("compliance_system.md").strip()


def build_compliance_matrix_prompt(
    job_dict: dict,
    draft_content: dict,
    ranked_keywords: list[dict] | None = None,
) -> str:
    description = str(job_dict.get("description", "") or "")[:2000]
    requirements = _extract_requirements_from_description(description)
    if requirements:
        requirements_text = "\n".join(
            f"{index + 1}. {requirement}" for index, requirement in enumerate(requirements)
        )
    else:
        requirements_text = "1. (No explicit requirements found in the provided description.)"

    summary = str(draft_content.get("professional_summary", "") or "")
    skills = ", ".join(str(skill) for skill in (draft_content.get("selected_skills") or [])) or "(none)"
    experiences_text = _format_draft_experiences(draft_content.get("selected_experiences") or [])
    projects_text = _format_draft_projects(draft_content.get("selected_projects") or [])

    keyword_line = ""
    if ranked_keywords:
        must_terms = [
            str(item.get("term", "")).strip()
            for item in ranked_keywords
            if item.get("tier") == "must"
        ]
        must_terms = [term for term in must_terms if term]
        if must_terms:
            keyword_line = f"\nTOP KEYWORDS: {', '.join(must_terms)}\n"

    return f"""JOB: {job_dict.get("title", "N/A")} at {job_dict.get("company", "N/A")}

JOB REQUIREMENTS:
{requirements_text}

DRAFT CONTENT:
Professional Summary: {summary}
Skills: {skills}
Experience bullets:
{experiences_text}
Project bullets:
{projects_text}
{keyword_line}
For each requirement, find the closest matching content in the draft.
Score coverage: "strong" (directly addressed with evidence), "partial"
(mentioned but weak or without metric), "missing" (no evidence in draft).

Return JSON:
{{
  "requirements": [
    {{
      "id": "r1",
      "requirement": "original requirement text",
      "matched_content": "exact bullet or phrase from draft that covers this, or null",
      "coverage": "strong|partial|missing",
      "suggestion": "one-line improvement suggestion if partial or missing, else null"
    }}
  ],
  "strong_count": 0,
  "partial_count": 0,
  "missing_count": 0,
  "coverage_pct": 0.0
}}""".strip()


def build_rejection_prediction_system_prompt() -> str:
    return """You are a talent acquisition analyst reviewing a job application before it is
submitted. Your job is to identify likely rejection factors based on the job
description and the candidate's profile. Be honest but constructive - frame
findings as risks to address, not as certainties. Return valid JSON only."""


def build_rejection_prediction_prompt(job_dict: dict, profile_dict: dict) -> str:
    experiences = profile_dict.get("experiences") or []
    recent_role = "none"
    if experiences and isinstance(experiences[0], dict):
        recent_role = str(experiences[0].get("role_title") or experiences[0].get("title") or "none")

    education = profile_dict.get("education") or []
    education_text = "not specified"
    if education and isinstance(education[0], dict):
        degree = str(education[0].get("degree") or "").strip()
        institution = str(education[0].get("institution") or "").strip()
        combined = f"{degree} {institution}".strip()
        if combined:
            education_text = combined

    skills = ", ".join((profile_dict.get("global_skills") or [])[:20])
    return f"""JOB: {job_dict.get("title", "N/A")} at {job_dict.get("company", "N/A")}
LOCATION: {job_dict.get("location", "not specified")}
SENIORITY REQUIRED: {job_dict.get("seniority") or "not specified"}

JOB DESCRIPTION (excerpt):
{str(job_dict.get("description", "") or "")[:2000]}

CANDIDATE PROFILE SUMMARY:
Name: {profile_dict.get("full_name", "N/A")}
Location: {profile_dict.get("location", "not specified")}
Skills: {skills}
Most recent role: {recent_role}
Education: {education_text}

Analyse the likely rejection risks for this candidate applying to this role.

For each risk:
- Type: "hard_blocker" (almost certain rejection) or "soft_blocker" (likely friction)
- Factor: brief name of the issue
- Evidence: specific text from JD or profile supporting this risk
- Confidence: "high" | "medium" | "low"
- Mitigable: true if the candidate can address it in their application, false if not
- Suggestion: one-line action if mitigable, else null

Return JSON:
{{
  "risks": [
    {{
      "type": "hard_blocker|soft_blocker",
      "factor": "...",
      "evidence": "...",
      "confidence": "high|medium|low",
      "mitigable": true,
      "suggestion": "... or null"
    }}
  ],
  "hard_blocker_count": 0,
  "soft_blocker_count": 0,
  "overall_risk": "low|medium|high",
  "recommendation": "Apply | Apply with preparation | Reconsider - address gaps first | Skip"
}}""".strip()


def build_writer_user_prompt(
    profile: dict,
    track: dict | None,
    job: dict | None,
    *,
    selected_experiences: list | None = None,
    selected_projects: list | None = None,
    presentation_mode: str = "junior",
    target_seniority: str = "junior",
    ranked_keywords: list[dict] | None = None,
    confirmed_facts: list[dict] | None = None,
    verified_facts: list[dict] | None = None,
    truth_constraints: list[str] | None = None,
) -> str:
    profile = profile or {}
    track = track or {}
    job = job or {}

    mode_blocks = {
        "junior": """
══════════════════════════════════
PRESENTATION MODE: JUNIOR / INTERN
══════════════════════════════════
The target is an early-career role. The candidate has real prior experience.
Rules:
1. HEADLINE/SUMMARY: do NOT include "5+ years", "X years of experience",
   "senior engineer", "lead", or "architected" in the headline or summary.
   Lead with role vocabulary + primary stack.
2. Every fact-sheet role is eligible. You may omit AT MOST one role per job
   if it is unambiguously irrelevant. Never omit more than one.
3. PER-ROLE BULLETS: use 2–3 bullets per role. The selected_bullets list
   supplied below is already pre-scored — use it as-is unless a bullet needs
   Tier-1 rephrasing.
4. VERB REGISTER: contributor register. Built, implemented, developed,
   supported, collaborated on, investigated, analyzed, documented.
   Use "led" or "owned" only if the fact sheet explicitly documents it.
5. YEARS PHRASE: you may say "3 years at Org as Role" inside a role block.
   You may NOT aggregate to "5+ years of experience" in the summary.
6. SKILLS: include every stack item the job asks for that the candidate
   truthfully has. Adjacent skills go into inferred_additions.
""",
        "mid": """
══════════════════════════════════
PRESENTATION MODE: MID-LEVEL
══════════════════════════════════
1. HEADLINE/SUMMARY: "X years of experience" is permitted when factual.
   Ownership verbs are allowed when fact-sheet-supported.
2. 3 bullets per role.
3. VERB REGISTER: ownership register permitted where evidence exists.
4. Adjacent skills and tools go into inferred_additions.
""",
        "senior": """
══════════════════════════════════
PRESENTATION MODE: SENIOR / STAFF
══════════════════════════════════
1. HEADLINE/SUMMARY: "5+ years of experience" and leadership framing are
   permitted when the fact sheet documents them.
2. 3–4 bullets per role; foreground scope and impact.
3. VERB REGISTER: leadership register is allowed when justified by evidence.
4. Two-page resume is acceptable for senior and staff roles.
""",
    }
    mode_block = mode_blocks.get(presentation_mode, mode_blocks["junior"])

    def _value(item: dict | object, *keys: str) -> str:
        for key in keys:
            if isinstance(item, dict):
                value = item.get(key)
            else:
                value = getattr(item, key, None)
            if value not in (None, ""):
                return str(value)
        return ""

    if selected_experiences:
        exp_lines = []
        for sel in selected_experiences:
            experience_fact = sel.experience_fact
            exp_lines.append(
                f"Role: {_value(experience_fact, 'role_title', 'title')} at "
                f"{_value(experience_fact, 'organization', 'company')} "
                f"({_value(experience_fact, 'start_date')}–{_value(experience_fact, 'end_date') or 'present'})\n"
                + "\n".join(f"  - {bullet}" for bullet in sel.selected_bullets)
            )
        experience_block = "\n\n".join(exp_lines)
    else:
        experience_block = _format_experiences(profile.get("experiences") or [])

    if selected_projects:
        project_lines = []
        for sel in selected_projects:
            project_fact = sel.project_fact
            header = _value(project_fact, "project_name", "name")
            description = _value(project_fact, "short_resume_line", "description", "summary")
            block = [f"Project: {header}"]
            if description:
                block.append(f"  Summary: {description}")
            block.extend(f"  - {bullet}" for bullet in sel.selected_bullets)
            project_lines.append("\n".join(block))
        project_block = "\n\n".join(project_lines)
    else:
        project_block = _format_projects(profile.get("projects") or [])

    keyword_block = ""
    if ranked_keywords:
        must_terms = [str(item.get("term", "")) for item in ranked_keywords if item.get("tier") == "must"]
        important_terms = [
            str(item.get("term", ""))
            for item in ranked_keywords
            if item.get("tier") == "important"
        ]
        nice_terms = [str(item.get("term", "")) for item in ranked_keywords if item.get("tier") == "nice"]
        keyword_block = f"""
ATS KEYWORDS (ranked by importance — use these terms in bullets and summary):
Must-have: {", ".join(term for term in must_terms if term) or "None"}
Important: {", ".join(term for term in important_terms if term) or "None"}
Nice-to-have: {", ".join(term for term in nice_terms if term) or "None"}
"""

    clarification_block = ""
    if confirmed_facts:
        non_empty = [
            fact
            for fact in confirmed_facts
            if fact.get("confirmed") and str(fact.get("answer") or "").strip()
        ]
        if non_empty:
            rows = "\n".join(
                f"- Gap: {fact.get('gap', '')}\n  Answer: {str(fact.get('answer') or '').strip()}"
                for fact in non_empty
            )
            clarification_block = f"""\
══ CANDIDATE CLARIFICATIONS ════════════════════════════════════════════════════
The candidate answered the following questions about skill gaps identified in the
job description. Treat these as factual confirmations — use them to strengthen
or refine existing bullets where relevant, but do NOT invent experience beyond
what is documented in the fact sheet above.

{rows}
══════════════════════════════════════════════════════════════════════════════"""

    verified_block = ""
    if verified_facts:
        rows = "\n".join(
            f"- [{fact.get('fact_type', 'general')}] {fact.get('gap_label', '')}: "
            f"{str(fact.get('evidence') or '').strip()}"
            for fact in verified_facts
            if str(fact.get("evidence") or "").strip()
        )
        if rows:
            verified_block = f"""\
══ VERIFIED CANDIDATE FACTS (profile memory) ═══════════════════════════════════
The candidate has explicitly saved the following facts from previous job
applications. Treat them as trusted evidence only as written — use them to
strengthen bullets and claims where relevant, but do NOT broaden the claim or
fabricate experience beyond what is stated here or in the profile.

{rows}
══════════════════════════════════════════════════════════════════════════════"""

    json_schema_instruction = """
Return ONLY a JSON object with this exact schema:
{
  "summary": "string",
  "experience": [
    {"role": "string", "org": "string", "dates": "string", "bullets": ["string"]}
  ],
  "projects": [
    {"name": "string", "description": "string", "bullets": ["string"]}
  ],
  "education": [{"degree": "string", "institution": "string", "dates": "string"}],
  "skills": {"languages": [], "frameworks": [], "tools": [], "cloud": [], "other": []},
  "inferred_additions": [
    {
      "id": "add_1",
      "tier": "skill|tool|responsibility|metric",
      "text": "the proposed text",
      "reason": "why this is plausible given the candidate's background",
      "attached_to": "summary|experience[0]|skills|...",
      "confidence": "low|med|high"
    }
  ]
}
Do NOT include any text outside this JSON object.
"""

    truthfulness_block = ""
    if truth_constraints:
        truthfulness_block = "══ TRUTHFULNESS CONSTRAINTS ═══════════════════════════════════════════════════\n"
        truthfulness_block += "\n".join(f"- {constraint}" for constraint in truth_constraints if str(constraint).strip())
        truthfulness_block += "\n"

    return f"""\
Generate a tailored resume for the following candidate, track, and job.

{mode_block}

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
{experience_block}

── PROJECTS ────────────────────────────────────────────────────────────────────
{project_block}

── EDUCATION ───────────────────────────────────────────────────────────────────
{_format_education(profile.get("education") or [])}

── SKILLS ──────────────────────────────────────────────────────────────────────
{", ".join(profile.get("global_skills") or [])}

── CERTIFICATIONS ──────────────────────────────────────────────────────────────
{", ".join(str(c) for c in (profile.get("certifications") or [])) or "None listed"}

── ACHIEVEMENTS ────────────────────────────────────────────────────────────────
{", ".join(str(a) for a in (profile.get("achievements") or [])) or "None listed"}

{keyword_block}

{verified_block}

{clarification_block}

{truthfulness_block}

══ INSTRUCTIONS ════════════════════════════════════════════════════════════════
1. Extract the 5–7 most important requirements from the job description.
2. Respect the resolved presentation mode: {presentation_mode}.
3. The global target seniority is: {target_seniority}.
4. Use the selected experiences and selected projects above when they are provided.
5. Write the summary for THIS exact role and company.
6. Apply the track emphasis: {track.get("emphasis", {})}.
7. Put all adjacent but not explicitly verified additions into inferred_additions.

{json_schema_instruction}
""".strip()


# ── Reviewer ──────────────────────────────────────────────────────────────────

def build_reviewer_system_prompt() -> str:
    return load_prompt_resource("reviewer_system.md").strip()


def build_reviewer_user_prompt(
    profile: dict,
    track: dict,
    job: dict,
    draft: dict,
    presentation_mode: str = "junior",
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

PRESENTATION MODE: {presentation_mode.upper()}
When scoring Career-Level Alignment, verify the headline, summary, and verb
register match the job's seniority target.

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

ADDITIONAL CHECK — PRESENTATION MISMATCH:
If presentation_mode is "junior" and you find any of the following in the
draft, add them to the gaps list with the prefix "[MISMATCH]":
  - Aggregate "X+ years of experience" in headline or summary
  - "Led", "Architected", "Owned" without evidence in the fact sheet
  - The word "student" (the candidate is NOT a student)

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


# ── Bullet Clarify ─────────────────────────────────────────────────────────────

def build_language_extraction_system_prompt() -> str:
    return """You are a resume strategist. Your job is to map a job description's language
onto a candidate's existing resume bullets. You must NEVER invent skills or
experience. You only map what already exists.

Return valid JSON only. No markdown, no extra text."""


def build_language_extraction_prompt(profile_dict: dict, job_dict: dict, draft_content: dict) -> str:
    experiences = draft_content.get("selected_experiences") or []
    projects = draft_content.get("selected_projects") or []
    bullet_lines: list[str] = []
    for exp in experiences:
        title = exp.get("title", "")
        company = exp.get("company", "")
        for bullet in exp.get("bullets") or []:
            bullet_lines.append(f"- Experience | {title} @ {company}: {bullet}")
    for proj in projects:
        name = proj.get("name", "")
        for bullet in proj.get("bullets") or []:
            bullet_lines.append(f"- Project | {name}: {bullet}")
    bullet_text = "\n".join(bullet_lines) or "(no bullets found)"
    skills = ", ".join(profile_dict.get("global_skills") or []) or "(no skills listed)"
    return f"""\
JOB TITLE: {job_dict.get("title", "N/A")} at {job_dict.get("company", "N/A")}

JOB DESCRIPTION:
{str(job_dict.get("description") or "")[:3000]}

CANDIDATE'S CURRENT BULLETS:
{bullet_text}

CANDIDATE'S PROFILE SKILLS:
{skills}

Task:
1. Extract the top 10 skills/outcomes/traits from the job description.
2. Rank them by importance (1=most critical).
3. For each, find the closest existing bullet or skill from the candidate's profile.
4. Mark as "gap" if no reasonable match exists.

Return JSON:
{{
  "language_map": [
    {{
      "rank": 1,
      "jd_term": "...",
      "jd_context": "exact phrase from JD",
      "matched_bullet": "closest existing bullet text or null",
      "match_quality": "strong|partial|gap"
    }}
  ],
  "gap_count": <int>,
  "summary": "one sentence about overall match quality"
}}""".strip()


def build_clarifying_questions_system_prompt() -> str:
    return """You are helping a job applicant truthfully strengthen their resume.
Ask specific yes/no or numeric questions to confirm whether the candidate
has evidence for gaps identified in their profile. Only ask questions whose
positive answer would justify adding or rewriting a bullet.
Do NOT ask open-ended questions. Each question must be answerable with
"yes/no + optional metric" or a number.

Return valid JSON only."""


def build_clarifying_questions_prompt(language_map: list[dict], profile_dict: dict, job_dict: dict) -> str:
    del profile_dict
    gaps = [item for item in (language_map or []) if item.get("match_quality") == "gap"]
    gap_lines = "\n".join(
        f"- {item.get('jd_term', '')}: {item.get('jd_context', '')}"
        for item in gaps
    ) or "(no gaps)"
    return f"""\
JOB: {job_dict.get("title", "N/A")} at {job_dict.get("company", "N/A")}

GAPS IDENTIFIED (skills/outcomes in the JD with no match in profile):
{gap_lines}

Generate at most 3 clarifying questions. Each question must:
- Reference a specific gap
- Be answerable with yes + concrete example OR no
- If answered yes, the answer must provide enough detail to write a bullet

Return JSON:
{{
  "questions": [
    {{
      "id": "q1",
      "gap_term": "...",
      "question": "Have you [specific thing]? If yes, what was the outcome/metric?",
      "context": "why this matters for the role"
    }}
  ]
}}""".strip()


def build_bullet_rewrite_system_prompt(word_limit: int) -> str:
    return f"""You are a resume writer. Rewrite resume bullets using the company's exact
language from the job description. Rules:
- Use ONLY facts the candidate has confirmed. If they said "no", do not use that skill.
- Each bullet must be ≤{word_limit} words.
- Start each bullet with a strong past-tense action verb.
- Include at least one metric or concrete outcome where possible.
- Do NOT fabricate. Do NOT use superlatives without evidence.
- Vary your verbs. Do not start two bullets with the same word.
- Use the company's exact terminology where it maps to a confirmed skill.

Return valid JSON only. No markdown."""


def build_bullet_rewrite_prompt(
    language_map: list[dict],
    answers: list[dict],
    draft_content: dict,
    job_dict: dict,
    word_limit: int,
) -> str:
    del word_limit
    confirmed_lines = []
    denied_lines = []
    for answer in answers or []:
        question_id = answer.get("question_id", "")
        text = answer.get("answer", "")
        if answer.get("confirmed"):
            confirmed_lines.append(f"- {question_id}: {text}")
        else:
            denied_lines.append(f"- USER DOES NOT HAVE: {question_id} — omit this")
    confirmed_text = "\n".join(confirmed_lines) or "(no confirmed additions)"
    denied_text = "\n".join(denied_lines) or "(none)"
    return f"""\
JOB: {job_dict.get("title", "N/A")} at {job_dict.get("company", "N/A")}
COMPANY LANGUAGE MAP:
{_safe_json_excerpt({"language_map": language_map}, max_chars=2400)}

USER-CONFIRMED FACTS:
{confirmed_text}
{denied_text}

CURRENT BULLETS TO IMPROVE:
Experience bullets: {_safe_json_excerpt({"selected_experiences": draft_content.get("selected_experiences", [])}, max_chars=2000)}
Project bullets: {_safe_json_excerpt({"selected_projects": draft_content.get("selected_projects", [])}, max_chars=2000)}

Rewrite only bullets where improvement is possible using confirmed facts.
Keep bullets unchanged if they already use strong company-matching language.

Return JSON:
{{
  "experiences": [
    {{
      "original_title": "...",
      "bullets": ["rewritten bullet 1", "rewritten bullet 2"]
    }}
  ],
  "projects": [
    {{
      "original_name": "...",
      "bullets": ["rewritten bullet"]
    }}
  ],
  "unchanged_count": <int>,
  "rewrite_notes": "brief explanation of what changed and why"
}}""".strip()


def build_cover_letter_system_prompt() -> str:
    return """You are an expert cover letter writer. Your writing style is Spartan, professional, and optimistic.

STYLE RULES (non-negotiable):
- SPARTAN: No filler phrases. Never write: "I am excited to...", "I am passionate about...", "I would be a great fit", "I am writing to express my interest", "I believe I would bring", "I look forward to hearing from you"
- PROFESSIONAL: Formal but warm. Direct. No buzzwords without evidence.
- OPTIMISTIC: Forward-looking and confident. The candidate belongs at this company.
- Do NOT start any paragraph with "I". Vary sentence openings.
- Under 300 words total — every sentence must earn its place.
- Do not re-state CV bullet points verbatim — synthesize, don't copy.

STRUCTURE (3 paragraphs, exactly):
1. OPENING (3-4 sentences):
   - Who the candidate is: name, degree, university, expected graduation date
   - Why THIS specific company — reference something concrete from the company context provided (mission, a product, a research area, a value). NOT generic praise.
   - The role applied for.

2. VALUE (3-5 sentences):
   - 2-3 concrete achievements that directly match this role's requirements.
   - XYZ format where possible: outcome + method + tool.
   - Draw from the most relevant experience for this specific role.

3. CLOSE (2-3 sentences):
   - Clear, specific ask — offer two options to reduce friction: brief call OR reply by email.
   - Optimistic close — confident, not desperate.
   - No clichés.

OUTPUT: Valid JSON only, no text outside the JSON:
{
  "subject": "<email subject line for sending this cover letter>",
  "body": "<full cover letter, plain text, use \\n for paragraph breaks>"
}"""


def build_cover_letter_user_prompt(
    profile: dict,
    track: dict,
    job: dict,
    company_context: str = "",
) -> str:
    """
    Build user prompt for cover letter generation.
    company_context: extracted text from company website (About/Mission pages).
    """
    name = profile.get("full_name", "Candidate")
    brand = profile.get("brand_summary", "")
    education = profile.get("education") or []
    experiences = profile.get("experiences") or []

    grad_date = "TBD"
    for edu in education:
        degree = edu.get("degree", "")
        if "master" in degree.lower():
            grad_date = edu.get("end_date", grad_date)
            break

    experience_blocks: list[str] = []
    for exp in experiences[:3]:
        role = exp.get("role") or exp.get("title", "")
        company = exp.get("company", "")
        bullets = exp.get("bullets") or []
        bullet_lines = "\n".join(f"  • {bullet}" for bullet in bullets[:3])
        experience_blocks.append(f"{role} @ {company}:\n{bullet_lines}")
    exp_text = "\n\n".join(experience_blocks)

    track_title = track.get("title", "")
    track_emphasis = str(track.get("emphasis") or "")

    job_title = job.get("title", "")
    job_company = job.get("company", "")
    job_location = job.get("location", "")
    job_description = (job.get("description") or "")[:2000]
    company_url = job.get("company_url") or job.get("source_url") or ""

    return f"""ROLE: {job_title}
COMPANY: {job_company}
LOCATION: {job_location}
WEBSITE: {company_url}

COMPANY CONTEXT (extracted from their website):
{company_context if company_context else "(Company website unavailable — write based on job description only. Do not fabricate company-specific details.)"}

JOB DESCRIPTION:
{job_description or "(not available)"}

---

CANDIDATE:
Name: {name}
Degree: {education[0].get("degree", "Candidate degree") if education else "Candidate degree"}
Expected graduation: {grad_date}
Resume track: {track_title} (emphasis: {track_emphasis})
Summary: {brand}

Top experiences:
{exp_text or "(no experience data available)"}

---

Write the cover letter for {name} applying to {job_title} at {job_company}.
- Reference specific details from the company context if available.
- Align the candidate's background to the role and company culture.
- Writing style: Spartan professional optimistic (see system prompt rules).
- Output valid JSON only.""".strip()


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


def _extract_requirements_from_description(description: str, max_items: int = 12) -> list[str]:
    """Best-effort extraction of requirement-like lines from a JD description."""
    positive_markers = (
        "responsib",
        "requirement",
        "qualification",
        "experience",
        "knowledge",
        "proficien",
        "ability",
        "assist",
        "support",
        "manage",
        "monitor",
        "prepare",
        "collaborat",
        "participat",
        "analy",
        "report",
        "forecast",
        "budget",
        "reconcil",
        "statement",
        "invoice",
        "cash application",
        "power bi",
        "excel",
        "sql",
        "erp",
        "degree",
        "kpi",
        "you will",
        "you'll",
        "the role",
        "about the role",
    )
    negative_markers = (
        "about us",
        "about the company",
        "who we are",
        "it's more than a job",
        "give back beauty",
        "guided by our motto",
        "small enough to care",
        "people and the planet",
        "headquartered",
        "specializes in",
        "present in more than",
        "recognized leader",
        "our goal is to build brands",
        "privately owned beauty group",
        "member of the gbb group",
    )
    candidates: list[str] = []
    for raw_line in description.splitlines():
        line = raw_line.strip().lstrip("-•*").strip()
        if len(line) >= 8:
            candidates.append(line)

    if not candidates:
        fragments = [fragment.strip() for fragment in description.split(".")]
        candidates.extend(fragment for fragment in fragments if len(fragment) >= 8)

    prioritized: list[str] = []
    fallback: list[str] = []
    for candidate in candidates:
        normalized = candidate.casefold()
        has_positive = any(marker in normalized for marker in positive_markers)
        has_negative = any(marker in normalized for marker in negative_markers)
        if has_positive and not has_negative:
            prioritized.append(candidate)
        elif not has_negative:
            fallback.append(candidate)

    seen: set[str] = set()
    requirements: list[str] = []
    for candidate in prioritized + fallback:
        key = candidate.casefold()
        if key in seen:
            continue
        seen.add(key)
        requirements.append(candidate)
        if len(requirements) >= max_items:
            break
    return requirements


def build_enhancement_prompt(profile: dict, job: dict, draft: dict, reviewer_gaps: list[str]) -> str:
    """Prompt for the mid model to propose expert enhancements."""
    gaps_text = "\n".join(f"  - {gap}" for gap in reviewer_gaps) or "  (none specified)"
    return f"""\
You are a senior {job.get("title", "technology")} professional at {job.get("company", "a top company")} \
reviewing a junior candidate's resume.

Your task: propose 3–5 specific, targeted improvements to this resume that would make it \
more compelling for this exact role. You may ONLY suggest changes that are plausible given \
the candidate's existing experience — do not invent skills or experiences.

For each proposal, ask the candidate a yes/no question to confirm they have the relevant \
experience before the change is applied.

══ TARGET JOB ═════════════════════════════════════════════════════════════
{job.get("title", "N/A")} at {job.get("company", "N/A")}
{str(job.get("description", ""))[:600]}

══ KNOWN GAPS (from reviewer) ═════════════════════════════════════════════
{gaps_text}

══ CURRENT DRAFT ═══════════════════════════════════════════════════════════
Headline: {draft.get("headline", "")}
Summary: {draft.get("professional_summary", "")}
Skills: {", ".join(draft.get("selected_skills") or [])}

══ CANDIDATE BACKGROUND ════════════════════════════════════════════════════
{profile.get("public_brand_summary", "")}

══ OUTPUT FORMAT ═══════════════════════════════════════════════════════════
Return valid JSON only. No markdown, no code fences, no extra text.
{{
  "proposals": [
    {{
      "section": "<headline|summary|skills|experience_bullet>",
      "original_text": "<the exact current text>",
      "proposed_text": "<the improved version>",
      "rationale": "<why this change improves the recruiter/ATS reception>",
      "question_for_user": "<yes/no question: e.g., 'Have you used dbt for pipeline transformation?'>"
    }}
  ]
}}""".strip()


def build_thesis_outreach_system_prompt() -> str:
    return """You are an expert academic email writer. Your task is to write a concise, genuine, and specific outreach email from a master's student seeking a thesis or traineeship position.

TONE RULES:
- Professional but warm
- Specific: reference the research area, not generic praise
- Concise: email body must be under 250 words
- Clear ask: end with a low-friction request

EMAIL STRUCTURE (4 paragraphs):
1. WHO: Name, degree, expected graduation date, and thesis track
2. WHY THEM: Specific alignment with the professor, lab, or company
3. WHAT THE STUDENT BRINGS: 2-3 concrete experiences relevant to the target
4. ASK: Offer a short call or a reply by email

OUTPUT FORMAT — respond with valid JSON only:
{
  "subject": "<email subject line>",
  "body": "<full email body, plain text, newlines as \\n>",
  "key_alignment_points": ["<point 1>", "<point 2>", "<point 3>"]
}

Do not include any explanation outside the JSON object."""


def build_thesis_outreach_user_prompt(profile: dict, target: dict) -> str:
    """Build the user prompt for thesis outreach generation."""
    name = profile.get("full_name", "Candidate")
    location = profile.get("location", "")
    brand = profile.get("public_brand_summary") or profile.get("brand_summary", "")
    experiences = profile.get("experiences", []) or []
    projects = profile.get("projects", []) or []
    education = profile.get("education", []) or []

    grad_date = "TBD"
    for edu in education:
        degree = str(edu.get("degree", "") or edu.get("presentation", ""))
        if "master" in degree.lower():
            grad_date = edu.get("end_date") or grad_date
            break

    experience_sections: list[str] = []
    for exp in experiences[:3]:
        role = exp.get("role") or exp.get("title", "")
        company = exp.get("company") or exp.get("organization", "")
        bullets = exp.get("bullets") or []
        bullet_text = "\n".join(f"  - {bullet}" for bullet in bullets[:2]) or "  - No bullets provided"
        experience_sections.append(f"- {role} @ {company}:\n{bullet_text}")

    project_sections: list[str] = []
    for project in projects[:2]:
        title = project.get("title") or project.get("name", "")
        desc = project.get("description") or project.get("summary", "")
        project_sections.append(f"- {title}: {str(desc)[:200]}")

    target_type = target.get("type", "professor")
    target_name = target.get("name", "")
    institution = target.get("institution", "")
    department = target.get("department", "")
    country = target.get("country", "")
    research_area = target.get("research_area", "")
    notes = target.get("notes", "") or ""

    return f"""STUDENT PROFILE:
Name: {name}
Location: {location}
Degree: {education[0].get("degree", "Candidate degree") if education else "Candidate degree"}
Expected graduation: {grad_date}
Summary: {brand}

Top experiences:
{chr(10).join(experience_sections) or "(none)"}

Key projects:
{chr(10).join(project_sections) or "(none)"}

---

TARGET:
Type: {target_type}
Name: {target_name}
Institution: {institution}{f", {department}" if department else ""}
Country: {country}
Research area: {research_area}
Notes / context: {notes or "(none provided)"}

---

Write a personalized outreach email from {name} to {target_name} at {institution}.
Align the student's background to the research area: {research_area}.
If notes are provided, reference specific details from them.
Output valid JSON only."""


def build_thesis_revision_prompt(original_subject: str, original_body: str, feedback: str) -> str:
    """Prompt to revise an outreach draft based on explicit user feedback."""
    return f"""Revise the following outreach email based on the feedback provided.
Keep what works; fix what is flagged. Maintain the 4-paragraph structure and 250-word limit.

ORIGINAL SUBJECT: {original_subject}

ORIGINAL BODY:
{original_body}

USER FEEDBACK:
{feedback}

Output valid JSON only:
{{
  "subject": "<revised subject>",
  "body": "<revised body, plain text>",
  "key_alignment_points": ["<point 1>", "<point 2>", "<point 3>"]
}}"""
