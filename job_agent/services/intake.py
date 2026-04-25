from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
import uuid

from sqlalchemy.orm import Session

from job_agent.config import settings
from job_agent.llm import LLMRouter
from job_agent.models import Candidate, CandidateIntakeDraft, CandidateSourceFile
from job_agent.runtime_paths import resolve_artifacts_dir
from job_agent.services.fact_sheet_json import FactSheetJsonIngestionService
from job_agent.services.file_extraction import extract_text_auto
from job_agent.services.resource_loader import extract_prompt_section, load_prompt_pack

logger = logging.getLogger(__name__)

_MAX_ITERATIONS = 3


@dataclass
class UploadedFile:
    filename: str
    content: bytes
    content_type: str | None = None


@dataclass
class IntakeResult:
    status: str
    questions: list[str] | None = None
    fact_sheet: dict | None = None
    iteration: int = 0


def _parse_llm_response(raw: object) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            import re

            match = re.search(r"\{.*\}", raw, re.S)
            if match:
                return json.loads(match.group(0))
    raise ValueError(f"Intake LLM response is not parseable JSON: {str(raw)[:200]}")


def _build_intake_system_prompt(prompt_pack_text: str) -> str:
    return (
        extract_prompt_section(prompt_pack_text, 1).strip()
        + "\n\nReturn JSON only. Use either {\"questions\": [...], \"partial_fact_sheet\": {...}} "
        + "or {\"fact_sheet\": {...}}."
    )


def _build_intake_user_prompt(
    prompt_pack_text: str,
    extracted_texts: list[str],
    profile_notes: str | None = None,
    existing_fact_sheet: dict | None = None,
) -> str:
    prompt_number = 2 if extracted_texts else 3
    base = extract_prompt_section(prompt_pack_text, prompt_number).strip()
    if prompt_number == 2:
        base = base.replace("{{uploaded_files}}", str(len(extracted_texts)))
        base = base.replace("{{profile_notes}}", profile_notes or "")
        base = base.replace(
            "{{existing_fact_sheet_or_null}}",
            json.dumps(existing_fact_sheet, indent=2) if existing_fact_sheet else "null",
        )
        combined = "\n\n---\n\n".join(text for text in extracted_texts if text.strip())
        return f"{base}\n\n=== UPLOADED DOCUMENT TEXT ===\n{combined}"

    note_block = f"\n\nPROFILE NOTES:\n{profile_notes}" if profile_notes else ""
    return f"{base}{note_block}"


def _build_answer_prompt(
    prompt_pack_text: str,
    partial_fact_sheet: dict,
    questions: list[str],
    answers: dict[str, str],
) -> str:
    base = extract_prompt_section(prompt_pack_text, 4).strip()
    qa_block = "\n".join(f"Q: {question}\nA: {answers.get(question, '').strip()}" for question in questions)
    return (
        base.replace("{{existing_fact_sheet}}", json.dumps(partial_fact_sheet, indent=2))
        .replace("{{new_inputs}}", qa_block)
        + "\n\nReturn JSON only as {\"questions\": [...], \"partial_fact_sheet\": {...}} "
        + "or {\"fact_sheet\": {...}}."
    )


def _canonical_minimal_fact_sheet(candidate: Candidate, partial: dict | None = None) -> dict:
    partial = dict(partial or {})
    person = dict(partial.get("person", {}))
    contact = dict(person.get("contact", {}))
    if candidate.full_name and not person.get("full_name"):
        person["full_name"] = candidate.full_name
    if candidate.email and not contact.get("email"):
        contact["email"] = candidate.email
    if contact:
        person["contact"] = contact

    missing_information = list(partial.get("missing_information", []))
    return {
        "person": person,
        "match_profile": dict(partial.get("match_profile", {})),
        "experience": list(partial.get("experience", [])),
        "education": list(partial.get("education", [])),
        "skills": dict(partial.get("skills", {})),
        "languages": list(partial.get("languages", [])),
        "completion_status": partial.get("completion_status", "usable_with_gaps"),
        "confidence_summary": dict(partial.get("confidence_summary", {})),
        "missing_information": missing_information,
        "conflicts": list(partial.get("conflicts", [])),
        "evidence_index": list(partial.get("evidence_index", [])),
        "projects": list(partial.get("projects", [])),
        "change_log": list(partial.get("change_log", [])),
    }


def _ensure_candidate(session: Session, candidate_id: str) -> Candidate:
    candidate = session.get(Candidate, candidate_id)
    if candidate is None:
        raise ValueError(f"Candidate {candidate_id} not found")
    return candidate


def _safe_extract_text(path: Path, filename: str) -> str:
    try:
        return extract_text_auto(path)
    except Exception as exc:
        logger.warning("Could not extract text from %s: %s", filename, exc)
        return ""


def store_uploaded_files(
    session: Session,
    candidate_id: str,
    uploaded_files: list[UploadedFile],
) -> list[CandidateSourceFile]:
    candidate = _ensure_candidate(session, candidate_id)
    base_dir = resolve_artifacts_dir(settings.artifacts_dir) / "candidate_sources" / candidate.id
    base_dir.mkdir(parents=True, exist_ok=True)

    stored_rows: list[CandidateSourceFile] = []
    for uploaded_file in uploaded_files:
        file_id = str(uuid.uuid4())
        safe_name = Path(uploaded_file.filename or f"{file_id}.bin").name
        stored_path = base_dir / f"{file_id}_{safe_name}"
        extracted_text = ""
        final_path: str | None = None
        try:
            stored_path.write_bytes(uploaded_file.content)
            final_path = str(stored_path)
            extracted_text = _safe_extract_text(stored_path, safe_name)
        except Exception as exc:
            logger.warning("Could not persist uploaded file %s: %s", safe_name, exc)

        row = CandidateSourceFile(
            id=file_id,
            candidate_id=candidate.id,
            original_name=safe_name,
            mime_type=uploaded_file.content_type,
            stored_path=final_path,
            extracted_text=extracted_text,
        )
        session.add(row)
        stored_rows.append(row)

    session.flush()
    return stored_rows


class FactSheetIntakeService:
    def __init__(self, session: Session, router) -> None:
        self.session = session
        self.router = router

    def _get_or_create_draft(self, candidate_id: str) -> CandidateIntakeDraft:
        draft = self.session.query(CandidateIntakeDraft).filter_by(candidate_id=candidate_id).first()
        if draft is None:
            draft = CandidateIntakeDraft(id=str(uuid.uuid4()), candidate_id=candidate_id, iteration=0)
            self.session.add(draft)
            self.session.flush()
        return draft

    def start_intake(
        self,
        candidate_id: str,
        uploaded_files: list[UploadedFile],
        profile_notes: str | None = None,
    ) -> IntakeResult:
        candidate = _ensure_candidate(self.session, candidate_id)
        prompt_pack = load_prompt_pack()
        draft = self._get_or_create_draft(candidate_id)
        stored_rows = store_uploaded_files(self.session, candidate_id, uploaded_files) if uploaded_files else []

        extracted_texts = [row.extracted_text or "" for row in stored_rows if row.extracted_text]
        if not extracted_texts:
            existing_rows = (
                self.session.query(CandidateSourceFile)
                .filter_by(candidate_id=candidate_id)
                .order_by(CandidateSourceFile.created_at.asc())
                .all()
            )
            extracted_texts = [row.extracted_text or "" for row in existing_rows if row.extracted_text]

        system_prompt = _build_intake_system_prompt(prompt_pack)
        user_prompt = _build_intake_user_prompt(
            prompt_pack,
            extracted_texts,
            profile_notes=profile_notes,
            existing_fact_sheet=draft.partial_fact_sheet,
        )
        generate_fn = self.router.generate_with_retry if isinstance(self.router, LLMRouter) else self.router.generate
        result = _parse_llm_response(
            generate_fn(
                role="small",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,
            )
        )
        return self._apply_intake_result(candidate, draft, result, next_iteration=1)

    def answer_questions(self, candidate_id: str, answers: dict[str, str]) -> IntakeResult:
        candidate = _ensure_candidate(self.session, candidate_id)
        draft = self.session.query(CandidateIntakeDraft).filter_by(candidate_id=candidate_id).first()
        if draft is None:
            raise ValueError(f"No active intake draft for candidate {candidate_id}")

        draft.last_answers = dict(answers)
        next_iteration = draft.iteration + 1
        if next_iteration >= _MAX_ITERATIONS:
            partial = _canonical_minimal_fact_sheet(candidate, draft.partial_fact_sheet)
            missing = list(partial.get("missing_information", []))
            if "Intake loop max iterations reached" not in missing:
                missing.append("Intake loop max iterations reached")
            partial["missing_information"] = missing
            FactSheetJsonIngestionService(self.session).ingest_json(candidate_id=candidate_id, fact_sheet=partial)
            draft.partial_fact_sheet = partial
            draft.pending_questions = None
            draft.iteration = next_iteration
            self.session.add(draft)
            self.session.commit()
            return IntakeResult(status="complete", fact_sheet=partial, iteration=next_iteration)

        prompt_pack = load_prompt_pack()
        system_prompt = _build_intake_system_prompt(prompt_pack)
        user_prompt = _build_answer_prompt(
            prompt_pack,
            partial_fact_sheet=draft.partial_fact_sheet or {},
            questions=list(draft.pending_questions or []),
            answers=answers,
        )
        generate_fn = self.router.generate_with_retry if isinstance(self.router, LLMRouter) else self.router.generate
        result = _parse_llm_response(
            generate_fn(
                role="small",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,
            )
        )
        return self._apply_intake_result(candidate, draft, result, next_iteration=next_iteration)

    def _apply_intake_result(
        self,
        candidate: Candidate,
        draft: CandidateIntakeDraft,
        result: dict,
        *,
        next_iteration: int,
    ) -> IntakeResult:
        questions = [str(question) for question in result.get("questions", [])][:5]
        partial_fact_sheet = result.get("partial_fact_sheet") or draft.partial_fact_sheet or {}
        if questions:
            draft.pending_questions = questions
            draft.partial_fact_sheet = partial_fact_sheet
            draft.iteration = next_iteration
            self.session.add(draft)
            self.session.commit()
            return IntakeResult(
                status="questions_needed",
                questions=questions,
                fact_sheet=partial_fact_sheet,
                iteration=next_iteration,
            )

        fact_sheet = result.get("fact_sheet")
        if fact_sheet is None:
            raise ValueError("LLM response contained neither 'questions' nor 'fact_sheet'")

        canonical = _canonical_minimal_fact_sheet(candidate, fact_sheet)
        FactSheetJsonIngestionService(self.session).ingest_json(candidate_id=candidate.id, fact_sheet=canonical)
        draft.partial_fact_sheet = canonical
        draft.pending_questions = None
        draft.iteration = next_iteration
        self.session.add(draft)
        self.session.commit()
        return IntakeResult(status="complete", fact_sheet=canonical, iteration=next_iteration)
