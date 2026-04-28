from __future__ import annotations

import io
from pathlib import Path

import pytest

from job_agent.llm import ProviderUnavailableError
from job_agent.models import Candidate, CandidateIntakeDraft, CandidateSourceFile
from job_agent.routers.candidates import _provider_failure_detail
from job_agent.services.intake import FactSheetIntakeService, UploadedFile

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _valid_fact_sheet(full_name: str) -> dict:
    return {
        "person": {"full_name": full_name, "contact": {"email": f"{full_name.lower().replace(' ', '')}@example.com"}},
        "match_profile": {
            "target_roles": ["Data Engineer"],
            "work_authorization": "EU",
            "location_preferences": {"preferred_countries": ["Italy"], "remote_preference": "hybrid"},
            "availability": {"status": "available", "earliest_start_date": "2026-06-01"},
            "employment_preferences": {"full_time": True},
        },
        "experience": [],
        "education": [{"degree": "BSc Computer Science", "institution": "Test University", "status": "Completed"}],
        "skills": {
            "programming_languages": ["Python"],
            "frameworks_and_platforms": [],
            "cloud_and_infra": [],
            "data_and_analytics": [],
            "business_tools": [],
            "methods": [],
        },
        "languages": [{"name": "English", "level": "C1"}],
        "completion_status": "usable_with_gaps",
        "confidence_summary": {"overall_confidence": "medium", "notes": []},
        "missing_information": [],
        "conflicts": [],
        "evidence_index": [],
        "projects": [],
    }


def test_extract_text_from_txt_returns_verbatim():
    from job_agent.services.file_extraction import extract_text_from_txt

    text = extract_text_from_txt(FIXTURES_DIR / "sample_cv.txt")

    assert "Jane Doe" in text


def test_extract_text_auto_dispatches_by_extension(tmp_path):
    from job_agent.services.file_extraction import extract_text_auto

    txt_file = tmp_path / "test.txt"
    txt_file.write_text("hello world", encoding="utf-8")

    assert extract_text_auto(txt_file) == "hello world"


def test_extract_text_auto_raises_on_unknown_extension(tmp_path):
    from job_agent.services.file_extraction import UnsupportedFileType, extract_text_auto

    unknown = tmp_path / "test.xyz"
    unknown.write_bytes(b"data")

    with pytest.raises(UnsupportedFileType):
        extract_text_auto(unknown)


def test_upload_endpoint_stores_source_file_and_extracted_text(client, db_session):
    db_session.add(Candidate(id="test-cand-1", full_name="Test User"))
    db_session.commit()

    sample_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
    response = client.post(
        "/candidates/test-cand-1/sources/upload",
        files=[("files", ("cv.pdf", io.BytesIO(sample_pdf), "application/pdf"))],
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["uploaded"] == 1
    stored = db_session.query(CandidateSourceFile).filter_by(candidate_id="test-cand-1").first()
    assert stored is not None
    assert stored.original_name.endswith(".pdf")


def test_upload_endpoint_rejects_non_pdf_files(client, db_session):
    db_session.add(Candidate(id="test-cand-1b", full_name="Test User"))
    db_session.commit()

    response = client.post(
        "/candidates/test-cand-1b/sources/upload",
        files=[("files", ("avatar.png", io.BytesIO(b"\x89PNG\r\n\x1a\n"), "image/png"))],
    )

    assert response.status_code == 422
    assert "Only PDF or plain-text files are accepted" in response.text


def test_upload_endpoint_accepts_plain_text_files(client, db_session):
    db_session.add(Candidate(id="test-cand-1c", full_name="Test User"))
    db_session.commit()

    response = client.post(
        "/candidates/test-cand-1c/sources/upload",
        files=[("files", ("notes.txt", io.BytesIO(b"Jane Doe\nData Engineer\nPython SQL"), "text/plain"))],
    )

    assert response.status_code == 200, response.text
    stored = db_session.query(CandidateSourceFile).filter_by(candidate_id="test-cand-1c").first()
    assert stored is not None
    assert "Jane Doe" in (stored.extracted_text or "")


def test_start_intake_with_no_files_returns_questions(db_session, monkeypatch):
    db_session.add(Candidate(id="test-cand-2", full_name="Test User 2"))
    db_session.commit()

    class Router:
        def generate(self, **kwargs):
            return {
                "questions": [
                    "What is your target role?",
                    "What country do you want to work in?",
                ]
            }

    service = FactSheetIntakeService(db_session, Router())
    result = service.start_intake("test-cand-2", [])

    assert result.status == "questions_needed"
    assert len(result.questions or []) == 2
    assert result.questions[0]["kind"] == "text"
    assert result.questions[0]["prompt"] == "What is your target role?"
    draft = db_session.query(CandidateIntakeDraft).filter_by(candidate_id="test-cand-2").first()
    assert draft is not None


def test_start_intake_with_files_returns_complete_fact_sheet(db_session):
    db_session.add(Candidate(id="test-cand-3", full_name="Test User 3", email="test3@example.com"))
    db_session.commit()

    class Router:
        def generate(self, **kwargs):
            return {"fact_sheet": _valid_fact_sheet("Test User 3")}

    service = FactSheetIntakeService(db_session, Router())
    result = service.start_intake(
        "test-cand-3",
        [UploadedFile(filename="cv.txt", content=b"Test User 3\nData Engineer", content_type="text/plain")],
    )

    assert result.status == "complete"
    assert result.fact_sheet is not None


def test_structured_fact_sheet_bypasses_llm_and_populates_experience(db_session):
    db_session.add(Candidate(id="test-cand-structured", full_name="Test User Structured", email="structured@example.com"))
    db_session.commit()

    class Router:
        def generate(self, **kwargs):
            raise AssertionError("Structured fact sheets should bypass LLM intake generation")

    structured_text = """MASTER FACT SHEET
==================================================
SECTION: CORE PROFILE
==================================================
FULL_NAME: Test User Structured
PRIMARY_EMAIL: structured@example.com
CURRENT_LOCATION: Turin, Italy
TARGET_ROLE_FAMILIES:
- Data Engineer
FULL_TIME_AVAILABILITY_NOTE:
- Available for full-time work.

==================================================
SECTION: PROFESSIONAL EXPERIENCE
==================================================
ITEM_ID: EXP-001
ROLE_TITLE: Data Engineer
ORGANIZATION: Example Co
LOCATION: Turin, Italy
START_DATE: 2023-01
END_DATE: 2025-01
VERIFIED_CORE_FACTS:
- Built production ETL pipelines in Python and SQL.
- Maintained analytics-ready warehouse tables.
TOOLS_AND_TECH:
- Python
- SQL

==================================================
SECTION: EDUCATION
==================================================
ITEM_ID: EDU-001
DEGREE: MSc
FIELD: Data Science
INSTITUTION: Politecnico di Torino
STATUS: Final stage
"""

    service = FactSheetIntakeService(db_session, Router())
    result = service.start_intake(
        "test-cand-structured",
        [UploadedFile(filename="fact_sheet.txt", content=structured_text.encode("utf-8"), content_type="text/plain")],
    )

    assert result.status == "complete"
    assert result.fact_sheet is not None
    assert result.fact_sheet["experience"]
    assert result.fact_sheet["experience"][0]["role_title"] == "Data Engineer"


def test_answer_questions_loops_until_complete(db_session):
    db_session.add(Candidate(id="test-cand-4", full_name="Test User 4", email="test4@example.com"))
    db_session.add(
        CandidateIntakeDraft(
            id="draft-4",
            candidate_id="test-cand-4",
            pending_questions=["What is your target role?"],
            partial_fact_sheet={},
            iteration=1,
        )
    )
    db_session.commit()

    class Router:
        def generate(self, **kwargs):
            return {"fact_sheet": _valid_fact_sheet("Test User 4")}

    service = FactSheetIntakeService(db_session, Router())
    result = service.answer_questions("test-cand-4", {"What is your target role?": "Data Engineer"})

    assert result.status == "complete"
    assert result.fact_sheet is not None


def test_intake_filters_low_value_questions(db_session):
    db_session.add(Candidate(id="test-cand-lowq", full_name="Test User LowQ"))
    db_session.commit()

    class Router:
        def generate(self, **kwargs):
            return {
                "questions": [
                    {
                        "id": "q1",
                        "prompt": "What month and year did this role start exactly?",
                        "kind": "text",
                    },
                    {
                        "id": "q2",
                        "prompt": "What is your certificate serial number?",
                        "kind": "text",
                    },
                ],
                "partial_fact_sheet": {},
            }

    service = FactSheetIntakeService(db_session, Router())
    result = service.start_intake("test-cand-lowq", [])

    assert result.status == "questions_needed"
    prompts = [str(question.get("prompt", "")).lower() for question in (result.questions or [])]
    assert prompts
    assert all("certificate serial number" not in prompt for prompt in prompts)
    assert all("month and year" not in prompt for prompt in prompts)


def test_intake_never_completes_with_empty_fact_sheet(db_session):
    db_session.add(Candidate(id="test-cand-emptyfact", full_name="Test User Empty"))
    db_session.commit()

    class Router:
        def generate(self, **kwargs):
            return {"fact_sheet": {"person": {"full_name": "Test User Empty", "contact": {"email": "t@example.com"}}}}

    service = FactSheetIntakeService(db_session, Router())
    result = service.start_intake("test-cand-emptyfact", [])

    assert result.status == "questions_needed"
    assert result.questions
    question_ids = {str(question.get("id")) for question in (result.questions or [])}
    assert "latest_education_degree" in question_ids
    assert "core_skills" in question_ids


def test_answer_questions_directly_merges_required_ground_truth(db_session):
    db_session.add(Candidate(id="test-cand-manual", full_name="Test User Manual", email="manual@example.com"))
    db_session.add(
        CandidateIntakeDraft(
            id="draft-manual",
            candidate_id="test-cand-manual",
            pending_questions=[
                {"id": "latest_education_degree", "prompt": "Degree?", "kind": "text", "required": True},
                {"id": "latest_education_institution", "prompt": "Institution?", "kind": "text", "required": True},
                {"id": "latest_education_status", "prompt": "Status?", "kind": "single_select", "options": ["Completed"], "required": True},
                {"id": "core_skills", "prompt": "Skills?", "kind": "text", "required": True},
            ],
            partial_fact_sheet={},
            iteration=1,
        )
    )
    db_session.commit()

    class Router:
        def generate(self, **kwargs):
            return {"fact_sheet": {}}

    service = FactSheetIntakeService(db_session, Router())
    result = service.answer_questions(
        "test-cand-manual",
        {
            "latest_education_degree": "BSc Computer Science",
            "latest_education_institution": "University of Turin",
            "latest_education_status": "Completed",
            "core_skills": "Python, SQL, Git",
        },
    )

    assert result.status == "complete"
    assert result.fact_sheet is not None
    assert result.fact_sheet["education"][0]["degree"] == "BSc Computer Science"
    assert result.fact_sheet["education"][0]["institution"] == "University of Turin"
    assert "Python" in result.fact_sheet["skills"]["programming_languages"]


def test_intake_uses_small_model_not_writer_model(db_session):
    db_session.add(Candidate(id="test-cand-5", full_name="Test User 5"))
    db_session.commit()
    calls = []

    class Router:
        def generate(self, **kwargs):
            calls.append(kwargs)
            return {"questions": ["Test question?"]}

    service = FactSheetIntakeService(db_session, Router())
    service.start_intake("test-cand-5", [])

    assert calls
    assert calls[0]["role"] == "small"


def test_intake_loads_prompt_pack_from_canonical_path():
    from job_agent.services.resource_loader import load_prompt_pack

    pack = load_prompt_pack()

    assert len(pack) > 50
    assert "Prompt 1" in pack


def test_structured_choice_questions_are_normalized(db_session):
    db_session.add(Candidate(id="test-cand-choice", full_name="Test User Choice"))
    db_session.commit()

    class Router:
        def generate(self, **kwargs):
            return {
                "questions": [
                    {
                        "id": "relocate",
                        "prompt": "Are you open to relocation?",
                        "kind": "single_select",
                        "options": ["Yes", "No", "Only within Italy"],
                    }
                ],
                "partial_fact_sheet": {"person": {"full_name": "Test User Choice"}},
            }

    service = FactSheetIntakeService(db_session, Router())
    result = service.start_intake("test-cand-choice", [])

    assert result.status == "questions_needed"
    assert result.questions == [
        {
            "id": "relocate",
            "prompt": "Are you open to relocation?",
            "kind": "single_select",
            "options": ["Yes", "No", "Only within Italy"],
            "allow_free_text": False,
            "required": True,
        }
    ]


def test_intake_deduplicates_and_truncates_large_source_texts(db_session):
    candidate_id = "test-cand-6"
    db_session.add(Candidate(id=candidate_id, full_name="Test User 6"))
    db_session.commit()

    repeated = ("A" * 20_000) + "\nUNIQUE_MARKER_ALPHA\n"
    second = ("B" * 18_000) + "\nUNIQUE_MARKER_BETA\n"
    calls = []

    class Router:
        def generate(self, **kwargs):
            calls.append(kwargs)
            return {"questions": ["What is your target role?"]}

    service = FactSheetIntakeService(db_session, Router())
    service.start_intake(
        candidate_id,
        [
            UploadedFile(filename="one.txt", content=repeated.encode("utf-8"), content_type="text/plain"),
            UploadedFile(filename="dup.txt", content=repeated.encode("utf-8"), content_type="text/plain"),
            UploadedFile(filename="two.txt", content=second.encode("utf-8"), content_type="text/plain"),
        ],
    )

    assert calls
    prompt = calls[0]["user_prompt"]
    assert len(prompt) < 40_000
    assert prompt.count("UNIQUE_MARKER_ALPHA") == 1
    assert prompt.count("UNIQUE_MARKER_BETA") == 1
    assert "[... truncated " in prompt


def test_provider_failure_detail_handles_local_context_limit():
    msg = _provider_failure_detail(
        ProviderUnavailableError(
            "LM Studio request failed: The number of tokens to keep from the initial prompt is greater than the context length. Try to load the model with a larger context length, or provide a shorter input"
        )
    )
    assert "context window" in msg
    assert "duplicate source files" in msg


def test_canonical_minimal_fact_sheet_normalizes_location_objects(db_session):
    from job_agent.services.intake import _canonical_minimal_fact_sheet

    candidate = Candidate(id="test-cand-7", full_name="Test User 7", email="test7@example.com")
    db_session.add(candidate)
    db_session.commit()

    fact_sheet = _canonical_minimal_fact_sheet(
        candidate,
        {
            "experience": [{"organization": "Org", "role_title": "Engineer", "location": {"city": "Turin", "country": "Italy"}}],
            "education": [{"institution": "Uni", "degree": "MSc", "location": {"country": "Italy"}}],
            "languages": [{"language": "English", "level": "C1"}],
            "missing_information": {"portfolio_url": "Need URL"},
            "confidence_summary": {"verified": 5, "inferred": 1, "missing": 1},
            "evidence_index": {"github_url": "MASTER FACT SHEET"},
        },
    )

    assert fact_sheet["experience"][0]["location"] == "Turin, Italy"
    assert fact_sheet["education"][0]["location"] == "Italy"
    assert fact_sheet["languages"][0] == {"name": "English", "level": "C1"}
    assert fact_sheet["missing_information"] == ["portfolio url: Need URL"]
    assert fact_sheet["confidence_summary"]["overall_confidence"] == "high"
    assert fact_sheet["evidence_index"][0]["id"] == "github_url"


def test_canonical_minimal_fact_sheet_normalizes_match_profile_variants(db_session):
    from job_agent.services.intake import _canonical_minimal_fact_sheet

    candidate = Candidate(id="test-cand-8", full_name="Test User 8")
    db_session.add(candidate)
    db_session.commit()

    fact_sheet = _canonical_minimal_fact_sheet(
        candidate,
        {
            "target_role_families": ["Data Engineer"],
            "target_regions": ["Italy", "Germany"],
            "willing_to_relocate": "yes",
            "full_time_availability_note": "Available for full-time work. Thesis collaboration is possible.",
            "primary_domain_interests": ["Data platforms"],
            "match_profile": {"availability": "Full-time"},
        },
    )

    mp = fact_sheet["match_profile"]
    assert mp["target_roles"] == ["Data Engineer"]
    assert mp["preferred_industries"] == ["Data platforms"]
    assert mp["location_preferences"]["preferred_countries"] == ["Italy", "Germany"]
    assert mp["location_preferences"]["willing_to_relocate"] is True
    assert mp["availability"]["status"] == "available"
    assert mp["employment_preferences"]["full_time"] is True
    assert mp["employment_preferences"]["thesis_collaboration"] is True
