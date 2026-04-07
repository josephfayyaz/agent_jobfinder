def build_writer_system_prompt() -> str:
    return (
        "You are a resume tailoring assistant. Produce concise, ATS-safe resume content as JSON only. "
        "Do not invent facts. Emphasize quantified achievements and direct job fit."
    )


def build_writer_user_prompt(profile: dict, track: dict, job: dict) -> str:
    return f"""
Return JSON with the keys:
- headline
- professional_summary
- selected_experiences
- selected_projects
- selected_skills
- tailoring_notes

Candidate profile:
{profile}

Resume track:
{track}

Target job:
{job}

Constraints:
- Use only facts supported by the candidate profile.
- Select the most relevant experiences and projects.
- Keep wording concise and professional.
- Make the draft suitable for a junior or internship application.
""".strip()


def build_reviewer_system_prompt() -> str:
    return (
        "You review a tailored resume against a job description. Return JSON only. "
        "Score aggressively and focus on evidence, keyword coverage, clarity, and truthfulness."
    )


def build_reviewer_user_prompt(profile: dict, track: dict, job: dict, draft: dict) -> str:
    return f"""
Return JSON with the keys:
- score
- decision
- strengths
- gaps
- must_fix
- keyword_coverage
- revised_summary

Candidate profile:
{profile}

Resume track:
{track}

Target job:
{job}

Draft resume:
{draft}

Scoring rubric:
- role_fit
- evidence
- keyword_coverage
- clarity
- ats_safety

Decision rules:
- pass if score >= 85
- revise if 75 <= score < 85
- rewrite if score < 75
""".strip()


def build_revision_prompt(job: dict, draft: dict, feedback: dict) -> str:
    return f"""
Revise this draft resume content using the review feedback. Return JSON only with the same keys as the draft.

Job:
{job}

Existing draft:
{draft}

Feedback:
{feedback}
""".strip()
