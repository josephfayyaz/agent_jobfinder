from __future__ import annotations

import io
from pathlib import Path

import pytest

from job_agent.models import Candidate, CandidateIntakeDraft, CandidateSourceFile
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
        "education": [],
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

    response = client.post(
        "/candidates/test-cand-1/sources/upload",
        files=[("files", ("cv.txt", io.BytesIO(b"Jane Doe\nData Engineer"), "text/plain"))],
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["uploaded"] == 1
    stored = db_session.query(CandidateSourceFile).filter_by(candidate_id="test-cand-1").first()
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
