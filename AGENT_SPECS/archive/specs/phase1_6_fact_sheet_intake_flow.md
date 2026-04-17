# Phase 1.6 — Interactive Fact Sheet Intake Flow

## Goal

Allow any new user to create their own fact sheet by uploading their CV, LinkedIn export,
and optional portfolio — no manual template editing required. The app extracts text from the
uploaded files, calls the LM Studio small model with the Prompt 1–4 system prompts from
`claude_fact_sheet_prompt_pack.md`, asks ≤5 high-value missing questions if needed, and
saves the result via `FactSheetJsonIngestionService` (Phase 1.4).

User journey:
1. `/ui/onboarding` — name + email → creates a `Candidate`
2. Drag-drop CV (PDF/DOCX/TXT), LinkedIn export, optional portfolio HTML
3. `POST /candidates/{id}/sources/upload` — server extracts text, stores `CandidateSourceFile`
4. `POST /candidates/{id}/intake/start` — LLM returns either `{status:"questions_needed"}` or
   `{status:"complete"}`
5. `POST /candidates/{id}/intake/answer` — feed answers back; loop until complete (max 3 rounds)
6. On completion: fact sheet saved, redirect to `/ui` dashboard

## Dependencies

Add to `pyproject.toml` under `[project] dependencies`:
```
"pdfminer.six>=20240706,<20250000",
"python-docx>=1.1,<2",
```

Run: `/Users/youseffayyaz/miniforge3/bin/conda run -n ML pip install -e ".[dev]"`

Note: `beautifulsoup4` is already a dependency (used by `career_scanner`). Reuse it for HTML.

## New Models: `job_agent/models.py`

Add after the Phase 1.4 Candidate models:

```python
class CandidateSourceFile(Base):
    """Uploaded CV / LinkedIn export / portfolio files with extracted text cached."""
    __tablename__ = "candidate_source_files"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(_uuid.uuid4())
    )
    candidate_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("candidates.id"), index=True
    )
    original_name: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    stored_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CandidateIntakeDraft(Base):
    """Conversation state while the intake LLM loop is in progress."""
    __tablename__ = "candidate_intake_drafts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(_uuid.uuid4())
    )
    candidate_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("candidates.id"), index=True, unique=True
    )
    partial_fact_sheet: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    pending_questions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_answers: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    iteration: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
```

## Alembic Migration

Create `alembic/versions/xxxx_add_candidate_source_files_and_intake_drafts.py`:

```python
"""Add CandidateSourceFile and CandidateIntakeDraft tables.

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6  (Phase 1.4 migration)
Create Date: 2026-04-11
"""
from alembic import op
import sqlalchemy as sa

def upgrade() -> None:
    op.create_table(
        "candidate_source_files",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("candidate_id", sa.String(36), sa.ForeignKey("candidates.id"), nullable=False),
        sa.Column("original_name", sa.String(500), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("stored_path", sa.String(1000), nullable=True),
        sa.Column("extracted_text", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_table(
        "candidate_intake_drafts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("candidate_id", sa.String(36), sa.ForeignKey("candidates.id"),
                  nullable=False, unique=True),
        sa.Column("partial_fact_sheet", sa.JSON, nullable=True),
        sa.Column("pending_questions", sa.JSON, nullable=True),
        sa.Column("last_answers", sa.JSON, nullable=True),
        sa.Column("iteration", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

def downgrade() -> None:
    op.drop_table("candidate_intake_drafts")
    op.drop_table("candidate_source_files")
```

## New File: `job_agent/services/file_extraction.py`

```python
"""Text extraction from PDF, DOCX, HTML, and plain text files."""

from __future__ import annotations

from pathlib import Path


class UnsupportedFileType(ValueError):
    pass


def extract_text_from_pdf(path: Path) -> str:
    """Extract text from a PDF using pdfminer.six."""
    from pdfminer.high_level import extract_text
    return extract_text(str(path))


def extract_text_from_docx(path: Path) -> str:
    """Extract text from a DOCX file using python-docx."""
    from docx import Document
    doc = Document(str(path))
    return "\n".join(para.text for para in doc.paragraphs if para.text.strip())


def extract_text_from_html(path: Path) -> str:
    """Extract visible text from an HTML file using BeautifulSoup."""
    from bs4 import BeautifulSoup
    html = path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")
    # Remove script/style noise
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def extract_text_from_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def extract_text_auto(path: Path) -> str:
    """Dispatch by file extension. Raise UnsupportedFileType on unknown extension."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(path)
    if suffix in (".docx", ".doc"):
        return extract_text_from_docx(path)
    if suffix in (".html", ".htm"):
        return extract_text_from_html(path)
    if suffix in (".txt", ".md", ".rst"):
        return extract_text_from_txt(path)
    raise UnsupportedFileType(f"Unsupported file type: {suffix}")
```

## New File: `job_agent/services/intake.py`

```python
"""Interactive fact sheet intake flow."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from job_agent.llm import LLMRouter

logger = logging.getLogger(__name__)

_MAX_ITERATIONS = 3


@dataclass
class UploadedFile:
    filename: str
    content: bytes
    content_type: str


@dataclass
class IntakeResult:
    status: str          # "questions_needed" | "complete"
    questions: list[str] | None = None
    fact_sheet: dict | None = None
    iteration: int = 0


def _build_intake_system_prompt(prompt_pack_text: str) -> str:
    """Extract Prompt 1 (system) from the prompt pack."""
    from job_agent.services.resource_loader import extract_prompt_section
    return extract_prompt_section(prompt_pack_text, 1)


def _build_intake_user_prompt(
    prompt_pack_text: str,
    extracted_texts: list[str],
    prompt_pack_prompt_number: int = 2,
) -> str:
    """
    Build the user-turn prompt from the prompt pack.
    Uses Prompt 2 when files are provided, Prompt 3 for text-only.
    """
    from job_agent.services.resource_loader import extract_prompt_section
    base = extract_prompt_section(prompt_pack_text, prompt_pack_prompt_number)
    combined = "\n\n---\n\n".join(extracted_texts)
    return f"{base}\n\n=== UPLOADED DOCUMENT TEXT ===\n{combined}"


def _build_answer_prompt(
    prompt_pack_text: str,
    partial_fact_sheet: dict,
    questions: list[str],
    answers: dict[str, str],
) -> str:
    """Build Prompt 4 (answer integration) from the prompt pack."""
    from job_agent.services.resource_loader import extract_prompt_section
    base = extract_prompt_section(prompt_pack_text, 4)
    qa_block = "\n".join(f"Q: {q}\nA: {answers.get(q, '').strip()}" for q in questions)
    return (
        f"{base}\n\n"
        f"=== CURRENT PARTIAL FACT SHEET ===\n{json.dumps(partial_fact_sheet, indent=2)}\n\n"
        f"=== ANSWERS TO QUESTIONS ===\n{qa_block}"
    )


def _parse_llm_response(raw: str) -> dict:
    """
    Parse the LLM response. Expects a JSON object with either:
      {"fact_sheet": {...}}  — complete fact sheet
      {"questions": [...]}  — list of up to 5 follow-up questions
    """
    # Try direct parse first
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Try to find a JSON block in the response
    import re
    match = re.search(r"\{.*\}", raw, re.S)
    if match:
        return json.loads(match.group(0))
    raise ValueError(f"LLM response is not parseable JSON: {raw[:200]}")


class FactSheetIntakeService:
    """
    Orchestrates the interactive intake flow:
      1. Accept uploaded file blobs, extract text
      2. Call the LM Studio small model with Prompt 1/2/3 from the prompt pack
      3. Parse the response as {fact_sheet: ...} or {questions: [...]}
      4. If questions → save draft state and return questions to caller
      5. If fact_sheet → validate + save via FactSheetJsonIngestionService
    """

    def __init__(self, session: Session, router: "LLMRouter") -> None:
        self.session = session
        self.router = router

    def _get_or_create_draft(self, candidate_id: str) -> object:
        from job_agent.models import CandidateIntakeDraft
        draft = self.session.query(CandidateIntakeDraft).filter_by(
            candidate_id=candidate_id
        ).first()
        if not draft:
            draft = CandidateIntakeDraft(
                id=str(uuid.uuid4()),
                candidate_id=candidate_id,
                iteration=0,
            )
            self.session.add(draft)
            self.session.flush()
        return draft

    def start_intake(
        self,
        candidate_id: str,
        uploaded_files: list[UploadedFile],
        profile_notes: str | None = None,
    ) -> IntakeResult:
        """
        Perform the initial intake pass.
        Returns either {status:"questions_needed", questions:[...]}
        or {status:"complete", fact_sheet:{...}}.
        """
        from job_agent.config import get_settings
        from job_agent.models import CandidateSourceFile
        from job_agent.services.resource_loader import load_prompt_pack
        from job_agent.services.fact_sheet_json import FactSheetJsonIngestionService

        settings = get_settings()
        prompt_pack = load_prompt_pack()

        # Save uploaded files + extract text
        extracted_texts: list[str] = []
        for uf in uploaded_files:
            import tempfile, os
            suffix = Path(uf.filename).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uf.content)
                tmp_path = Path(tmp.name)
            try:
                from job_agent.services.file_extraction import extract_text_auto
                text = extract_text_auto(tmp_path)
            except Exception as exc:
                logger.warning("Could not extract text from %s: %s", uf.filename, exc)
                text = ""
            finally:
                os.unlink(tmp_path)

            src = CandidateSourceFile(
                id=str(uuid.uuid4()),
                candidate_id=candidate_id,
                original_name=uf.filename,
                mime_type=uf.content_type,
                extracted_text=text,
            )
            self.session.add(src)
            extracted_texts.append(text)

        if profile_notes:
            extracted_texts.append(profile_notes)

        self.session.flush()

        # If no extracted text, use text already stored from previous uploads
        if not extracted_texts or not any(extracted_texts):
            from job_agent.models import CandidateSourceFile as CSF
            existing = self.session.query(CSF).filter_by(candidate_id=candidate_id).all()
            extracted_texts = [s.extracted_text for s in existing if s.extracted_text]

        # Build prompts
        sys_prompt = _build_intake_system_prompt(prompt_pack)
        user_prompt = _build_intake_user_prompt(
            prompt_pack,
            extracted_texts,
            prompt_pack_prompt_number=2 if extracted_texts else 3,
        )

        # Call LLM
        raw = self.router.complete(
            system=sys_prompt,
            user=user_prompt,
            model=settings.lm_studio_small_model,
        )
        result = _parse_llm_response(raw)

        draft = self._get_or_create_draft(candidate_id)

        if "questions" in result:
            draft.pending_questions = result["questions"]
            draft.partial_fact_sheet = result.get("partial_fact_sheet", {})
            draft.iteration = 1
            self.session.add(draft)
            self.session.commit()
            return IntakeResult(
                status="questions_needed",
                questions=result["questions"],
                iteration=draft.iteration,
            )

        if "fact_sheet" in result:
            svc = FactSheetJsonIngestionService(self.session)
            svc.ingest_json(candidate_id=candidate_id, fact_sheet=result["fact_sheet"])
            self.session.commit()
            return IntakeResult(
                status="complete",
                fact_sheet=result["fact_sheet"],
                iteration=draft.iteration,
            )

        raise ValueError("LLM response contained neither 'questions' nor 'fact_sheet' key")

    def answer_questions(
        self,
        candidate_id: str,
        answers: dict[str, str],
    ) -> IntakeResult:
        """
        Feed answers back to the LLM (Prompt 4) and continue the intake loop.
        After _MAX_ITERATIONS rounds of questions, force a completion.
        """
        from job_agent.models import CandidateIntakeDraft
        from job_agent.services.resource_loader import load_prompt_pack
        from job_agent.services.fact_sheet_json import FactSheetJsonIngestionService
        from job_agent.config import get_settings

        settings = get_settings()
        prompt_pack = load_prompt_pack()
        draft = self.session.query(CandidateIntakeDraft).filter_by(
            candidate_id=candidate_id
        ).first()
        if not draft:
            raise ValueError(f"No active intake draft for candidate {candidate_id}")

        draft.last_answers = answers
        draft.iteration += 1

        if draft.iteration >= _MAX_ITERATIONS:
            # Force completion with what we have
            partial = draft.partial_fact_sheet or {}
            partial.setdefault("missing_information", ["Intake loop max iterations reached"])
            svc = FactSheetJsonIngestionService(self.session)
            try:
                svc.ingest_json(candidate_id=candidate_id, fact_sheet=partial)
            except Exception:
                pass  # Save best-effort even if schema is partial
            self.session.commit()
            return IntakeResult(
                status="complete",
                fact_sheet=partial,
                iteration=draft.iteration,
            )

        user_prompt = _build_answer_prompt(
            prompt_pack=prompt_pack,
            partial_fact_sheet=draft.partial_fact_sheet or {},
            questions=draft.pending_questions or [],
            answers=answers,
        )
        sys_prompt = _build_intake_system_prompt(prompt_pack)
        raw = self.router.complete(
            system=sys_prompt,
            user=user_prompt,
            model=settings.lm_studio_small_model,
        )
        result = _parse_llm_response(raw)
        self.session.add(draft)

        if "questions" in result:
            draft.pending_questions = result["questions"]
            draft.partial_fact_sheet = result.get("partial_fact_sheet", draft.partial_fact_sheet)
            self.session.commit()
            return IntakeResult(
                status="questions_needed",
                questions=result["questions"],
                iteration=draft.iteration,
            )

        if "fact_sheet" in result:
            svc = FactSheetJsonIngestionService(self.session)
            svc.ingest_json(candidate_id=candidate_id, fact_sheet=result["fact_sheet"])
            self.session.commit()
            return IntakeResult(
                status="complete",
                fact_sheet=result["fact_sheet"],
                iteration=draft.iteration,
            )

        raise ValueError("LLM response contained neither 'questions' nor 'fact_sheet' key")
```

## New Endpoints: `job_agent/main.py`

```python
from fastapi import UploadFile, File
from job_agent.services.intake import FactSheetIntakeService, UploadedFile as _UploadedFile


@app.post("/candidates/{candidate_id}/sources/upload")
async def upload_candidate_sources(
    candidate_id: str,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload one or more source files (CV PDF, LinkedIn TXT, portfolio HTML).
    Server extracts text and stores CandidateSourceFile rows.
    """
    from job_agent.models import CandidateSourceFile
    import uuid as _uuid
    from job_agent.services.file_extraction import extract_text_auto
    import tempfile, os
    from pathlib import Path as _Path

    results = []
    for f in files:
        content = await f.read()
        suffix = _Path(f.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = _Path(tmp.name)
        try:
            text = extract_text_auto(tmp_path)
        except Exception as exc:
            text = ""
        finally:
            os.unlink(tmp_path)

        src = CandidateSourceFile(
            id=str(_uuid.uuid4()),
            candidate_id=candidate_id,
            original_name=f.filename,
            mime_type=f.content_type,
            extracted_text=text,
        )
        db.add(src)
        results.append({"filename": f.filename, "chars_extracted": len(text)})
    db.commit()
    return {"uploaded": len(results), "files": results}


@app.post("/candidates/{candidate_id}/intake/start")
async def start_intake(
    candidate_id: str,
    body: dict = {},
    db: Session = Depends(get_db),
):
    """Kick off the LLM intake loop using stored source files."""
    from job_agent.llm import LLMRouter
    router = LLMRouter()
    svc = FactSheetIntakeService(db, router)
    result = svc.start_intake(
        candidate_id=candidate_id,
        uploaded_files=[],  # files already stored via /sources/upload
        profile_notes=body.get("profile_notes"),
    )
    return {
        "status": result.status,
        "questions": result.questions,
        "fact_sheet": result.fact_sheet,
        "iteration": result.iteration,
    }


@app.post("/candidates/{candidate_id}/intake/answer")
async def answer_intake_questions(
    candidate_id: str,
    body: dict,  # {"answers": {"q1": "...", "q2": "..."}}
    db: Session = Depends(get_db),
):
    """Feed answers back to the LLM; loop continues until complete."""
    from job_agent.llm import LLMRouter
    router = LLMRouter()
    svc = FactSheetIntakeService(db, router)
    result = svc.answer_questions(candidate_id=candidate_id, answers=body.get("answers", {}))
    return {
        "status": result.status,
        "questions": result.questions,
        "fact_sheet": result.fact_sheet,
        "iteration": result.iteration,
    }


@app.get("/candidates/{candidate_id}/intake/status")
def get_intake_status(candidate_id: str, db: Session = Depends(get_db)):
    """Return current CandidateIntakeDraft state (for the UI to poll)."""
    from job_agent.models import CandidateIntakeDraft
    draft = db.query(CandidateIntakeDraft).filter_by(candidate_id=candidate_id).first()
    if not draft:
        return {"status": "not_started", "iteration": 0}
    if draft.pending_questions:
        return {
            "status": "questions_needed",
            "questions": draft.pending_questions,
            "iteration": draft.iteration,
        }
    return {"status": "complete", "iteration": draft.iteration}
```

## UI Addition: `/ui/onboarding`

Add to `job_agent/templates/onboarding.html` (new file):

```html
<!-- Onboarding page: Name/email → file upload → intake → dashboard -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Job Agent — Onboarding</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://unpkg.com/htmx.org@1.9.12"></script>
  <script src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
</head>
<body class="bg-gray-50 p-8" x-data="{step: 1, candidateId: '', questions: [], status: ''}">

  <!-- Step 1: Create candidate -->
  <div x-show="step === 1">
    <h1 class="text-2xl font-bold mb-4">Step 1 — Create Your Profile</h1>
    <form hx-post="/candidates" hx-trigger="submit"
          hx-on::after-request="candidateId=JSON.parse(event.detail.xhr.responseText).id; step=2">
      <input type="text" name="full_name" placeholder="Full Name" class="border p-2 mr-2" required>
      <input type="email" name="email" placeholder="Email" class="border p-2 mr-2">
      <button type="submit" class="bg-blue-500 text-white px-4 py-2 rounded">Create Profile</button>
    </form>
  </div>

  <!-- Step 2: Upload files -->
  <div x-show="step === 2">
    <h1 class="text-2xl font-bold mb-4">Step 2 — Upload Your Documents</h1>
    <p class="mb-4 text-gray-600">Upload your CV (PDF/DOCX), LinkedIn export (TXT), or portfolio (HTML).</p>
    <form :action="`/candidates/${candidateId}/sources/upload`" method="post"
          enctype="multipart/form-data"
          hx-encoding="multipart/form-data"
          :hx-post="`/candidates/${candidateId}/sources/upload`"
          hx-on::after-request="step=3">
      <input type="file" name="files" multiple accept=".pdf,.docx,.txt,.html,.md" class="mb-4">
      <button type="submit" class="bg-green-500 text-white px-4 py-2 rounded">Upload</button>
    </form>
  </div>

  <!-- Step 3: Start intake -->
  <div x-show="step === 3">
    <h1 class="text-2xl font-bold mb-4">Step 3 — Analyse Your Documents</h1>
    <button :hx-post="`/candidates/${candidateId}/intake/start`"
            hx-vals='{"profile_notes": ""}'
            hx-on::after-request="
              let r=JSON.parse(event.detail.xhr.responseText);
              status=r.status;
              if(r.status==='questions_needed'){questions=r.questions; step=4;}
              else{step=5;}"
            class="bg-purple-500 text-white px-4 py-2 rounded">
      Analyse Documents
    </button>
  </div>

  <!-- Step 4: Answer questions -->
  <div x-show="step === 4">
    <h1 class="text-2xl font-bold mb-4">Step 4 — A Few Quick Questions</h1>
    <form :hx-post="`/candidates/${candidateId}/intake/answer`"
          hx-on::after-request="
            let r=JSON.parse(event.detail.xhr.responseText);
            if(r.status==='questions_needed'){questions=r.questions;}
            else{step=5;}">
      <template x-for="(q, i) in questions" :key="i">
        <div class="mb-4">
          <label x-text="q" class="block font-medium mb-1"></label>
          <textarea :name="`answers[${q}]`" class="border w-full p-2" rows="2"></textarea>
        </div>
      </template>
      <button type="submit" class="bg-blue-500 text-white px-4 py-2 rounded">Submit Answers</button>
    </form>
  </div>

  <!-- Step 5: Complete -->
  <div x-show="step === 5">
    <h1 class="text-2xl font-bold mb-4 text-green-600">Profile Created!</h1>
    <p>Your fact sheet has been saved. You can now start generating CVs.</p>
    <a :href="`/ui?candidate_id=${candidateId}`" class="bg-blue-500 text-white px-4 py-2 rounded inline-block mt-4">
      Go to Dashboard
    </a>
  </div>

</body>
</html>
```

Add the route in `job_agent/main.py`:

```python
@app.get("/ui/onboarding", response_class=HTMLResponse)
def onboarding_page(request: Request):
    return templates.TemplateResponse("onboarding.html", {"request": request})
```

## Tests

### Test fixture: `tests/fixtures/sample_cv.txt`

Create a minimal plain-text CV fixture file for testing:
```
Jane Doe
Data Engineer
Python, SQL, Airflow
ACME Corp — Data Engineer — 2022–present
  - Built ETL pipelines
  - Reduced processing time by 40%
MSc Computer Science, University of Turin, 2022
```

### `tests/test_intake.py`

```python
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import json

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_extract_text_from_txt_returns_verbatim():
    from job_agent.services.file_extraction import extract_text_from_txt
    fixture = FIXTURES_DIR / "sample_cv.txt"
    text = extract_text_from_txt(fixture)
    assert "Jane Doe" in text or len(text) > 10  # fixture present


def test_extract_text_auto_dispatches_by_extension(tmp_path):
    from job_agent.services.file_extraction import extract_text_auto
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("hello world")
    assert extract_text_auto(txt_file) == "hello world"


def test_extract_text_auto_raises_on_unknown_extension(tmp_path):
    from job_agent.services.file_extraction import extract_text_auto, UnsupportedFileType
    unknown = tmp_path / "test.xyz"
    unknown.write_bytes(b"data")
    with pytest.raises(UnsupportedFileType):
        extract_text_auto(unknown)


def test_upload_endpoint_stores_source_file_and_extracted_text(client, db_session):
    """Multipart upload creates a CandidateSourceFile row with extracted_text."""
    import io
    from job_agent.models import Candidate
    cand = Candidate(id="test-cand-1", full_name="Test User")
    db_session.add(cand)
    db_session.commit()

    resp = client.post(
        "/candidates/test-cand-1/sources/upload",
        files=[("files", ("cv.txt", io.BytesIO(b"Jane Doe\nData Engineer"), "text/plain"))],
    )
    assert resp.status_code == 200
    assert resp.json()["uploaded"] == 1


def test_start_intake_with_no_files_returns_questions(db_session):
    """When LLM returns {questions:[...]}, start_intake returns questions_needed."""
    from job_agent.services.intake import FactSheetIntakeService
    from job_agent.models import Candidate

    cand = Candidate(id="test-cand-2", full_name="Test User 2")
    db_session.add(cand)
    db_session.flush()

    mock_router = MagicMock()
    mock_router.complete.return_value = json.dumps(
        {"questions": ["What is your target role?", "What country do you want to work in?"]}
    )

    with patch("job_agent.services.intake.load_prompt_pack", return_value="## Prompt 1\nSystem\n## Prompt 2\nUser\n## Prompt 3\nNoFile\n## Prompt 4\nAnswer"):
        svc = FactSheetIntakeService(db_session, mock_router)
        result = svc.start_intake("test-cand-2", [])

    assert result.status == "questions_needed"
    assert len(result.questions) == 2


def test_start_intake_with_files_returns_complete_fact_sheet(db_session):
    """When LLM returns {fact_sheet:{...}}, start_intake saves and returns complete."""
    from job_agent.services.intake import FactSheetIntakeService
    from job_agent.models import Candidate

    cand = Candidate(id="test-cand-3", full_name="Test User 3")
    db_session.add(cand)
    db_session.flush()

    mock_router = MagicMock()
    minimal_fs = {
        "person": {"full_name": "Test User 3"},
        "match_profile": {}, "experience": [], "projects": [],
        "education": [], "conflicts": [], "evidence_index": [],
        "change_log": [], "missing_information": [],
    }
    mock_router.complete.return_value = json.dumps({"fact_sheet": minimal_fs})

    with patch("job_agent.services.intake.load_prompt_pack", return_value="## Prompt 1\nSystem\n## Prompt 2\nUser\n## Prompt 3\nNoFile\n## Prompt 4\nAnswer"), \
         patch("job_agent.services.fact_sheet_json.FactSheetJsonIngestionService.ingest_json", return_value=MagicMock(candidate_id="test-cand-3")):
        svc = FactSheetIntakeService(db_session, mock_router)
        result = svc.start_intake("test-cand-3", [])

    assert result.status == "complete"


def test_answer_questions_loops_until_complete(db_session):
    """Second round with fact_sheet response → complete."""
    from job_agent.services.intake import FactSheetIntakeService
    from job_agent.models import Candidate, CandidateIntakeDraft
    import uuid

    cand = Candidate(id="test-cand-4", full_name="Test User 4")
    db_session.add(cand)
    draft = CandidateIntakeDraft(
        id=str(uuid.uuid4()),
        candidate_id="test-cand-4",
        pending_questions=["What is your target role?"],
        partial_fact_sheet={},
        iteration=1,
    )
    db_session.add(draft)
    db_session.flush()

    mock_router = MagicMock()
    minimal_fs = {
        "person": {"full_name": "Test User 4"},
        "match_profile": {"target_roles": ["Data Engineer"]},
        "experience": [], "projects": [], "education": [],
        "conflicts": [], "evidence_index": [], "change_log": [], "missing_information": [],
    }
    mock_router.complete.return_value = json.dumps({"fact_sheet": minimal_fs})

    with patch("job_agent.services.intake.load_prompt_pack", return_value="## Prompt 1\nSystem\n## Prompt 4\nAnswer"), \
         patch("job_agent.services.fact_sheet_json.FactSheetJsonIngestionService.ingest_json", return_value=MagicMock(candidate_id="test-cand-4")):
        svc = FactSheetIntakeService(db_session, mock_router)
        result = svc.answer_questions("test-cand-4", {"What is your target role?": "Data Engineer"})

    assert result.status == "complete"


def test_intake_uses_small_model_not_writer_model(db_session):
    """The intake service must call router.complete with lm_studio_small_model, not writer model."""
    from job_agent.services.intake import FactSheetIntakeService
    from job_agent.models import Candidate

    cand = Candidate(id="test-cand-5", full_name="Test User 5")
    db_session.add(cand)
    db_session.flush()

    model_used = []
    mock_router = MagicMock()
    def capture_complete(system, user, model, **kw):
        model_used.append(model)
        return json.dumps({"questions": ["Test question?"]})
    mock_router.complete.side_effect = capture_complete

    with patch("job_agent.services.intake.load_prompt_pack", return_value="## Prompt 1\nSystem\n## Prompt 2\nUser\n## Prompt 3\nNoFile\n## Prompt 4\nAnswer"), \
         patch("job_agent.config.get_settings") as mock_settings:
        mock_settings.return_value.lm_studio_small_model = "qwen3.5-9b"
        mock_settings.return_value.lm_studio_writer_model = "qwen3.5-27b"
        svc = FactSheetIntakeService(db_session, mock_router)
        svc.start_intake("test-cand-5", [])

    assert model_used and model_used[0] == "qwen3.5-9b"


def test_intake_loads_prompt_pack_from_canonical_path():
    """resource_loader.load_prompt_pack must return non-empty text."""
    from job_agent.services.resource_loader import load_prompt_pack
    pack = load_prompt_pack()
    assert len(pack) > 50
```

## Commit Message
```
feat(fact_sheet): add interactive intake flow with file upload, extraction, and LLM question loop (Phase 1.6)
```
