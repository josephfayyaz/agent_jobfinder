from __future__ import annotations

from job_agent.llm import LLMRouter


_SYSTEM_PROMPT = """Generate specific yes/no clarifying questions to find out if the candidate has
evidence for skill gaps. Each question must be answerable with "yes + metric"
or "no". Ask only if a positive answer would justify a resume bullet.
Return valid JSON only."""


def ask_clarifying_questions(
    gaps: list[str],
    job: dict,
    fact_sheet: str,
    router: LLMRouter | None = None,
    input_fn=input,
    print_fn=print,
) -> list[dict]:
    if not gaps:
        return []
    router = router or LLMRouter()
    user_prompt = f"""JOB: {job.get("title", "Unknown")} at {job.get("company", "Unknown")}
GAPS (skills in JD with no match in fact sheet): {gaps}
FACT SHEET EXCERPT: {fact_sheet[:2000]}

Generate at most 3 clarifying questions.
Return JSON:
{{
  "questions": [
    {{
      "id": "q1",
      "gap": "...",
      "question": "Have you [specific thing]? If yes, give a brief result or metric.",
      "why": "This matters because [JD context]"
    }}
  ]
}}"""
    data = router.generate(
        role="small",
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )
    questions = list(data.get("questions") or [])[:3]
    answers: list[dict] = []
    total = len(questions)
    for idx, question in enumerate(questions, start=1):
        gap = str(question.get("gap") or "")
        question_text = str(question.get("question") or "")
        why = str(question.get("why") or "")
        print_fn(f"\n[Question {idx}/{total}]")
        print_fn(f"Gap: {gap}")
        print_fn(f"Question: {question_text}")
        print_fn(f"Why it matters: {why}")
        response = input_fn("Your answer (or press Enter to skip): ").strip()
        answers.append(
            {
                "question_id": str(question.get("id") or f"q{idx}"),
                "gap": gap,
                "answer": response,
                "confirmed": bool(response),
            }
        )
    return answers
