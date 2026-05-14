from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from job_agent.llm import ProviderUnavailableError
from job_agent.models import Candidate, CandidateIntakeDraft, CandidateSourceFile
from job_agent.routers.candidates import _provider_failure_detail
from job_agent.services.intake import FactSheetIntakeService, UploadedFile

FIXTURES_DIR = Path(__file__).parent / "fixtures"
INTAKE_CORPUS_DIR = FIXTURES_DIR / "intake_corpus"
ACCOUNTANT_PROFILE_TEXT = """Offer a 10-year background in accounting and finance, with experience ranging from P&L/financial statements, management reports, general ledger, and journal entries to multi-state payroll, accounts payable/receivable, reconciliations, inventory variances allocation, and job costing
Additional cross-training and experience in diverse areas of business operations including staff training and direction, order management, software training, and operational/technical documentation
Effectively identify, develop and execute strategies to boost productivity, efficiency and quality
Dynamic organization, project planning, time management, and multi-tasking abilities
Actively facilitate and contribute to collaborative team environments and welcome increasing responsibilities as well as opportunities for professional development
Readily adapt to new professional settings/industries and adeptly acquire and apply new skills and knowledge toward supporting company goals
PC Literate with technical proficiency in Axapta, MAS90/MAS200, QuickBooks, Microsoft Office Suite (including Excel Spreadsheets), and ADP Payroll (Certified)

Accounts Payable Specialist/Payroll Specialist/Accounting Specialist
Apply sharp organization, analytical and multitasking abilities toward managing accounts payable, general ledger transactions, accounts receivable, daily invoicing, cash posting, and multiple account reconciliations.
Proficiently handle full-cycle accounts payable for over 200 vendors, with accountability ranging from weekly check processing and GL coding to account reconciliation and allocation.
Process bi-weekly payroll for over 100 employees nationwide.

Company Name                                                          2004 - 2005
Corporate Store Accountant
Efficiently managed payables and receivables including reconciliations, payroll and general ledger functions.
Posted, reconciled and allocated inventory variances to general ledger for corporate office as well as 7 multi-state cafes.

Company Name                                                          2001 - 2004
Accounting Manager
Compiled and prepared detailed financial statements, management reports and journal entries.
Developed and produced Excel spreadsheets for P&L, balance sheet, income summary, and trial balance.
"""

EUROPASS_STYLE_CV_TEXT = """Yousef Fayyaz

Date of birth: 18/03/1992
Email: S341999@studenti.polito.it

ABOUT MYSELF

Currently pursuing an MSc in Data Science and Engineering at Politecnico di Torino.

EDUCATION AND TRAINING

Data science and Engineering
Politecnico di Torino [ 24/09/2024 - Current ]
City: Torino | Country: Italy | Website: www.polito.it

Bachelor's Degree of Computer Engineering
Islamic Azad University [ 05/01/2015 - 05/01/2020 ]
City: Tehran | Country: Iran | Website: https://wtb.iau.ir | Field(s) of study: Computer Systems Architecture |
Final grade: 16.12

RECOMMENDATIONS
E-mail: recommender@example.com
"""


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


def _fixture_text(name: str) -> str:
    return (INTAKE_CORPUS_DIR / name).read_text(encoding="utf-8")


def _assert_diagnostic_contract(entry: dict) -> None:
    assert {"stage", "code", "severity", "message"} <= set(entry.keys())
    assert str(entry.get("stage") or "").strip()
    assert str(entry.get("code") or "").strip()
    assert str(entry.get("severity") or "").strip() in {"info", "warning", "error"}
    assert str(entry.get("message") or "").strip()


def test_extract_text_from_txt_returns_verbatim():
    from job_agent.services.file_extraction import extract_text_from_txt

    text = extract_text_from_txt(FIXTURES_DIR / "sample_cv.txt")

    assert "Jane Doe" in text


def test_extract_text_from_pdf_prefers_pdfplumber_and_normalizes_layout(tmp_path, monkeypatch):
    from job_agent.services import file_extraction

    sample = tmp_path / "sample.pdf"
    sample.write_bytes(b"%PDF-1.4")

    monkeypatch.setattr(
        file_extraction,
        "_extract_pdf_text_with_pdfplumber",
        lambda _path: "Jane   Doe\n\n• Python   \n• SQL",
    )
    monkeypatch.setattr(file_extraction, "_extract_pdf_text_with_pdfminer", lambda _path: "fallback")

    text = file_extraction.extract_text_from_pdf(sample)

    assert text == "Jane Doe\n\n- Python\n- SQL"


def test_extract_text_from_pdf_falls_back_to_pdfminer_when_pdfplumber_is_empty(tmp_path, monkeypatch):
    from job_agent.services import file_extraction

    sample = tmp_path / "sample.pdf"
    sample.write_bytes(b"%PDF-1.4")

    monkeypatch.setattr(file_extraction, "_extract_pdf_text_with_pdfplumber", lambda _path: "")
    monkeypatch.setattr(file_extraction, "_extract_pdf_text_with_pdfminer", lambda _path: "Recovered text")

    assert file_extraction.extract_text_from_pdf(sample) == "Recovered text"


def test_extract_text_from_pdf_raises_truthful_error_when_no_readable_text_is_found(tmp_path, monkeypatch):
    from job_agent.services import file_extraction

    sample = tmp_path / "sample.pdf"
    sample.write_bytes(b"%PDF-1.4")

    monkeypatch.setattr(file_extraction, "_extract_pdf_text_with_pdfplumber", lambda _path: "")
    monkeypatch.setattr(file_extraction, "_extract_pdf_text_with_pdfminer", lambda _path: "")

    with pytest.raises(ValueError, match="Could not extract readable text from PDF"):
        file_extraction.extract_text_from_pdf(sample)


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


def test_upload_endpoint_can_replace_existing_candidate_sources(client, db_session, tmp_path):
    candidate = Candidate(id="test-cand-replace", full_name="Replace User", email="replace@example.com")
    db_session.add(candidate)
    existing_path = tmp_path / "old.txt"
    existing_path.write_text("old content", encoding="utf-8")
    db_session.add(
        CandidateSourceFile(
            id="old-source",
            candidate_id=candidate.id,
            original_name="old.txt",
            mime_type="text/plain",
            stored_path=str(existing_path),
            extracted_text="old content",
        )
    )
    db_session.commit()

    response = client.post(
        f"/candidates/{candidate.id}/sources/upload",
        files=[("files", ("new.txt", io.BytesIO(b"new content"), "text/plain"))],
        data={"replace_existing": "1"},
    )

    assert response.status_code == 200, response.text
    stored = db_session.query(CandidateSourceFile).filter_by(candidate_id=candidate.id).all()
    assert len(stored) == 1
    assert stored[0].original_name == "new.txt"
    assert not existing_path.exists()
    assert response.json()["uploaded"] == 1


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


def test_start_intake_parses_freeform_profile_notes_into_experience_and_skills(db_session):
    db_session.add(Candidate(id="test-cand-freeform", full_name="Freeform User"))
    db_session.commit()

    class Router:
        def generate(self, **kwargs):
            return {
                "questions": [
                    "What country do you want to work in?",
                ]
            }

    service = FactSheetIntakeService(db_session, Router())
    result = service.start_intake("test-cand-freeform", [], profile_notes=ACCOUNTANT_PROFILE_TEXT)

    assert result.status == "questions_needed"
    assert result.fact_sheet is not None
    assert any(
        "Accounts Payable Specialist" in str(item.get("role_title") or "")
        for item in (result.fact_sheet.get("experience") or [])
    )
    assert any(
        "Accounting Manager" in str(item.get("role_title") or "")
        for item in (result.fact_sheet.get("experience") or [])
    )
    raw_skills = result.fact_sheet.get("skills", {})
    if isinstance(raw_skills, dict):
        skills = [
            item
            for bucket in raw_skills.values()
            if isinstance(bucket, list)
            for item in bucket
        ]
    else:
        skills = list(raw_skills or [])
    assert any("QuickBooks" in item for item in skills)


def test_start_intake_recovers_contact_and_education_from_source_text(db_session):
    db_session.add(Candidate(id="test-cand-source-hints", full_name="Yousef Fayyaz"))
    db_session.commit()

    class Router:
        def generate(self, **kwargs):
            return {
                "questions": [
                    "What country do you want to work in?",
                ]
            }

    service = FactSheetIntakeService(db_session, Router())
    result = service.start_intake(
        "test-cand-source-hints",
        [
            UploadedFile(
                filename="cv.txt",
                content=EUROPASS_STYLE_CV_TEXT.encode("utf-8"),
                content_type="text/plain",
            )
        ],
    )

    assert result.status == "questions_needed"
    assert result.fact_sheet is not None
    assert result.fact_sheet["person"]["contact"]["email"] == "S341999@studenti.polito.it"
    education = result.fact_sheet["education"]
    assert any(
        item["degree"] == "MSc"
        and item["field"] == "Data Science and Engineering"
        and item["institution"] == "Politecnico di Torino"
        for item in education
    )
    assert any(
        item["degree"] == "Bachelor's Degree"
        and item["field"] == "Computer Systems Architecture"
        and item["institution"] == "Islamic Azad University"
        for item in education
    )


def test_start_intake_records_conflict_when_source_email_disagrees_with_ai(db_session):
    db_session.add(Candidate(id="test-cand-source-conflict", full_name="Yousef Fayyaz"))
    db_session.commit()

    class Router:
        def generate(self, **kwargs):
            fact_sheet = _valid_fact_sheet("Yousef Fayyaz")
            fact_sheet["person"]["contact"]["email"] = "ai@example.com"
            return {"fact_sheet": fact_sheet}

    service = FactSheetIntakeService(db_session, Router())
    result = service.start_intake(
        "test-cand-source-conflict",
        [
            UploadedFile(
                filename="cv.txt",
                content=EUROPASS_STYLE_CV_TEXT.encode("utf-8"),
                content_type="text/plain",
            )
        ],
    )

    assert result.status == "complete"
    assert result.fact_sheet is not None
    assert result.fact_sheet["person"]["contact"]["email"] == "ai@example.com"
    assert any(
        item["field"] == "person.contact.email"
        and item["source_a"] == "ai@example.com"
        and item["source_b"] == "S341999@studenti.polito.it"
        for item in result.fact_sheet["conflicts"]
    )


def test_canonical_minimal_fact_sheet_accepts_legacy_lm_shape():
    from job_agent.services.intake import _canonical_minimal_fact_sheet

    candidate = Candidate(id="test-cand-legacy", full_name="Ari Leone", email="ari@example.test")
    raw = {
        "candidate_name": "Ari Leone",
        "email": "ari@example.test",
        "target_role": "Junior Data Engineer",
        "location_preferences": ["Italy", "Germany"],
        "languages": [{"language": "English", "proficiency": "C1"}],
        "education": [
            {
                "degree": "BSc Computer Engineering",
                "institution": "Politecnico di Torino",
                "field_of_study": "Computer Engineering",
                "status": "completed",
            }
        ],
        "professional_experience": [
            {
                "description": "Built ETL coursework pipelines and a capstone analytics warehouse.",
                "skills": ["Python", "SQL", "Git", "Pandas", "PostgreSQL"],
            }
        ],
        "confidence_summary": {
            "overall": "high",
            "education": "high",
            "experience": "high",
            "skills": "high",
            "languages": "high",
        },
        "missing_information": {},
        "conflicts": [],
        "evidence_index": {"education": [{"source": "uploaded_document", "field": "degree"}]},
    }

    canonical = _canonical_minimal_fact_sheet(candidate, raw)

    assert canonical["person"]["full_name"] == "Ari Leone"
    assert canonical["person"]["contact"]["email"] == "ari@example.test"
    assert canonical["match_profile"]["target_roles"] == ["Junior Data Engineer"]
    assert canonical["match_profile"]["location_preferences"]["preferred_countries"] == ["Italy", "Germany"]
    assert canonical["languages"] == [{"name": "English", "level": "C1"}]
    assert canonical["education"][0]["field"] == "Computer Engineering"
    assert canonical["confidence_summary"]["overall_confidence"] == "high"
    assert canonical["missing_information"] == []
    assert "Python" in canonical["skills"]["programming_languages"]


def test_answer_questions_prompt_includes_uploaded_source_text(db_session):
    db_session.add(Candidate(id="test-cand-source", full_name="Source User"))
    db_session.add(
        CandidateSourceFile(
            id="src-1",
            candidate_id="test-cand-source",
            original_name="resume.txt",
            mime_type="text/plain",
            stored_path="/tmp/resume.txt",
            extracted_text="Resume evidence: Built ETL workflows with Python and SQL.",
        )
    )
    db_session.add(
        CandidateIntakeDraft(
            id="draft-source",
            candidate_id="test-cand-source",
            partial_fact_sheet={},
            pending_questions=[
                {"id": "availability", "prompt": "When can you start?", "kind": "text", "required": True}
            ],
            iteration=1,
        )
    )
    db_session.commit()

    calls = []

    class Router:
        def generate(self, **kwargs):
            calls.append(kwargs)
            return {
                "fact_sheet": _valid_fact_sheet("Source User"),
            }

    service = FactSheetIntakeService(db_session, Router())
    result = service.answer_questions("test-cand-source", {"availability": "Immediately"})

    assert result.status == "complete"
    assert calls
    assert "Resume evidence: Built ETL workflows with Python and SQL." in calls[0]["user_prompt"]


def test_canonical_minimal_fact_sheet_flattens_work_authorization_mapping():
    from job_agent.services.intake import _canonical_minimal_fact_sheet

    candidate = Candidate(id="test-cand-auth", full_name="Auth User", email="auth@example.test")
    canonical = _canonical_minimal_fact_sheet(
        candidate,
        {
            "person": {"full_name": "Auth User", "contact": {"email": "auth@example.test"}},
            "work_authorization": {"Italy": "Yes", "Germany": "No"},
        },
    )

    assert canonical["match_profile"]["work_authorization"] == "Italy: Yes; Germany: No"


def test_direct_answers_capture_country_specific_work_authorization():
    from job_agent.services.intake import _apply_direct_answers_to_partial_fact_sheet

    updated = _apply_direct_answers_to_partial_fact_sheet(
        {},
        {
            "work_authorization_italy": "Yes",
            "work_authorization_germany": "No",
        },
    )

    assert updated["match_profile"]["work_authorization"] == "Italy: Yes; Germany: No"


def test_canonical_minimal_fact_sheet_flattens_work_authorization_list():
    from job_agent.services.intake import _canonical_minimal_fact_sheet

    candidate = Candidate(id="test-cand-auth-list", full_name="Auth User", email="auth@example.test")
    canonical = _canonical_minimal_fact_sheet(
        candidate,
        {
            "person": {"full_name": "Auth User", "contact": {"email": "auth@example.test"}},
            "match_profile": {
                "work_authorization": ["Work Visa for Italy", "EU Blue Card for Germany"],
            },
        },
    )

    assert canonical["match_profile"]["work_authorization"] == "Work Visa for Italy; EU Blue Card for Germany"


def test_canonical_minimal_fact_sheet_normalizes_person_current_location_string():
    from job_agent.services.intake import _canonical_minimal_fact_sheet

    candidate = Candidate(id="test-cand-loc", full_name="Loc User", email="loc@example.test")
    canonical = _canonical_minimal_fact_sheet(
        candidate,
        {
            "person": {
                "full_name": "Loc User",
                "contact": {"email": "loc@example.test"},
                "current_location": "Turin, Italy",
            },
        },
    )

    assert canonical["person"]["current_location"] == {"city": "Turin", "country": "Italy"}


def test_canonical_minimal_fact_sheet_normalizes_legacy_project_keys():
    from job_agent.services.intake import _canonical_minimal_fact_sheet

    candidate = Candidate(id="test-cand-proj", full_name="Proj User", email="proj@example.test")
    canonical = _canonical_minimal_fact_sheet(
        candidate,
        {
            "projects": [
                {
                    "title": "ETL Coursework Pipelines",
                    "description": "Built ETL pipelines for coursework.",
                    "evidence_id": "evidence_2",
                }
            ]
        },
    )

    assert canonical["projects"] == [
        {
            "name": "ETL Coursework Pipelines",
            "summary": "Built ETL pipelines for coursework.",
            "tools": [],
            "link": None,
        }
    ]


def test_canonical_minimal_fact_sheet_normalizes_legacy_experience_keys():
    from job_agent.services.intake import _canonical_minimal_fact_sheet

    candidate = Candidate(id="test-cand-exp", full_name="Exp User", email="exp@example.test")
    canonical = _canonical_minimal_fact_sheet(
        candidate,
        {
            "target_role": "Research Assistant",
            "experience": [
                {
                    "role": "Research Assistant",
                    "institution": "University of Milan",
                    "description": "Supported experiments and literature synthesis for an academic lab.",
                    "skills": ["Scientific writing", "Statistics"],
                }
            ],
        },
    )

    assert canonical["experience"] == [
        {
            "role_title": "Research Assistant",
            "organization": "University of Milan",
            "location": None,
            "start_date": None,
            "end_date": None,
            "current": None,
            "role_family": None,
            "responsibilities": ["Supported experiments and literature synthesis for an academic lab."],
            "tools": ["Scientific writing", "Statistics"],
            "achievements": [],
            "evidence_refs": [],
            "verification_status": "partial",
        }
    ]


def test_start_intake_applies_structured_profile_notes_overlay(db_session):
    db_session.add(Candidate(id="test-cand-notes", full_name="Notes User", email="notes@example.test"))
    db_session.commit()

    class Router:
        def generate(self, **kwargs):
            return {
                "fact_sheet": {
                    "education": [{"degree": "BSc", "institution": "Test University"}],
                    "skills": {"programming_languages": ["Python"]},
                }
            }

    service = FactSheetIntakeService(db_session, Router())
    result = service.start_intake(
        "test-cand-notes",
        [],
        profile_notes=(
            "Target role: Junior Data Engineer\n"
            "Preferred countries: Italy, Germany\n"
            "Languages: English C1\n"
            "Most relevant proof: Built ETL coursework pipelines."
        ),
    )

    assert result.fact_sheet is not None
    assert result.fact_sheet["match_profile"]["target_roles"] == ["Junior Data Engineer"]
    assert result.fact_sheet["match_profile"]["location_preferences"]["preferred_countries"] == ["Italy", "Germany"]
    assert result.fact_sheet["languages"] == [{"name": "English", "level": "C1"}]
    assert result.fact_sheet["projects"][0]["name"] == "Profile note evidence"


def test_start_intake_profile_notes_overlay_preserves_skills_and_education(db_session):
    db_session.add(Candidate(id="test-cand-notes-rich", full_name="Notes Rich", email="notes.rich@example.test"))
    db_session.commit()

    class Router:
        def generate(self, **kwargs):
            return {
                "fact_sheet": {
                    "completion_status": "partial",
                    "skills": {"programming_languages": ["Python"]},
                }
            }

    service = FactSheetIntakeService(db_session, Router())
    result = service.start_intake(
        "test-cand-notes-rich",
        [],
        profile_notes=(
            "Target role: Backend Software Engineer\n"
            "Preferred countries: Italy, Spain\n"
            "Languages: English C1\n"
            "Education degree: BSc Software Engineering\n"
            "Education institution: Sapienza University of Rome\n"
            "Skills: Python, FastAPI, PostgreSQL, Docker, Redis\n"
            "Most relevant proof: Built service APIs and background workers."
        ),
    )

    assert result.fact_sheet is not None
    assert result.fact_sheet["completion_status"] == "usable_with_gaps"
    assert result.fact_sheet["education"][0]["degree"] == "BSc Software Engineering"
    assert result.fact_sheet["education"][0]["institution"] == "Sapienza University of Rome"
    saved_skills = {
        skill
        for values in result.fact_sheet["skills"].values()
        for skill in values
    }
    assert {"Python", "FastAPI", "PostgreSQL", "Docker", "Redis"} <= saved_skills


def test_canonical_minimal_fact_sheet_normalizes_numeric_confidence_summary():
    from job_agent.services.intake import _canonical_minimal_fact_sheet

    candidate = Candidate(id="test-cand-confidence", full_name="Confidence User", email="confidence@example.test")
    canonical = _canonical_minimal_fact_sheet(
        candidate,
        {
            "confidence_summary": {
                "overall_confidence": 0.95,
                "notes": ["strong source grounding"],
            }
        },
    )

    assert canonical["confidence_summary"] == {
        "overall_confidence": "high",
        "notes": ["strong source grounding"],
    }


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


def test_start_intake_can_reset_existing_draft_state(db_session):
    db_session.add(Candidate(id="test-cand-reset", full_name="Reset User", email="reset@example.com"))
    db_session.add(
        CandidateIntakeDraft(
            id="draft-reset",
            candidate_id="test-cand-reset",
            partial_fact_sheet={"person": {"full_name": "Old User"}},
            pending_questions=[{"id": "q1", "prompt": "Old question", "kind": "text", "required": True}],
            last_answers={"q1": "old"},
            iteration=3,
        )
    )
    db_session.commit()

    class Router:
        def generate(self, **kwargs):
            return {"questions": [{"id": "q2", "prompt": "New question", "kind": "text", "required": True}]}

    service = FactSheetIntakeService(db_session, Router())
    result = service.start_intake("test-cand-reset", [], profile_notes="Target role: Analyst", reset_existing_draft=True)

    assert result.status == "questions_needed"
    draft = db_session.query(CandidateIntakeDraft).filter_by(candidate_id="test-cand-reset").first()
    assert draft is not None
    assert draft.iteration == 1
    assert draft.last_answers is None
    assert draft.pending_questions[0]["id"] == "q2"


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
    assert "[... truncated " in prompt or "[... block truncated ...]" in prompt


def test_intake_shaping_is_smaller_for_gemini_than_openai():
    from job_agent.services.provider_input import shape_text_blocks_for_workflow

    blocks = [("A" * 9000) + " ALPHA ", ("B" * 9000) + " BETA "]
    gemini_blocks = shape_text_blocks_for_workflow(blocks, workflow="intake", provider_mode="gemini")
    openai_blocks = shape_text_blocks_for_workflow(blocks, workflow="intake", provider_mode="openai")

    assert len(gemini_blocks) == len(openai_blocks) == 2
    assert sum(len(item) for item in gemini_blocks) < sum(len(item) for item in openai_blocks)
    assert any("[... block truncated ...]" in item for item in gemini_blocks)


def test_intake_shaping_respects_total_provider_budget_for_many_blocks():
    from job_agent.providers import provider_prompt_char_limit
    from job_agent.services.provider_input import shape_text_blocks_for_workflow

    blocks = [f"{index}-" + ("X" * 1200) for index in range(30)]
    shaped = shape_text_blocks_for_workflow(blocks, workflow="intake", provider_mode="gemini")

    assert shaped
    assert sum(len(item) for item in shaped) <= provider_prompt_char_limit("intake", "gemini")


def test_provider_failure_detail_handles_local_context_limit():
    msg = _provider_failure_detail(
        ProviderUnavailableError(
            "LM Studio request failed: prompt exceeded context",
            provider="lm_studio",
            category="context_too_large",
            retryable=True,
        )
    )
    assert "context window" in msg
    assert "duplicate source files" in msg


def test_provider_failure_detail_handles_gemini_input_too_large():
    msg = _provider_failure_detail(
        ProviderUnavailableError(
            "Gemini prompt too large",
            provider="gemini",
            category="context_too_large",
            retryable=True,
        )
    )
    assert "too large" in msg.lower()
    assert "upload fewer pdfs" in msg.lower()


def test_provider_failure_detail_prefers_error_category_for_gemini_context_issue():
    msg = _provider_failure_detail(
        ProviderUnavailableError(
            "Gemini prompt too large",
            provider="gemini",
            category="context_too_large",
            retryable=True,
        )
    )
    assert "gemini" in msg.lower()
    assert "too large" in msg.lower()


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


def test_start_intake_builds_ordered_multi_file_source_dossier(db_session, monkeypatch):
    import job_agent.services.intake as intake

    db_session.add(Candidate(id="test-cand-dossier", full_name="Dossier User"))
    db_session.commit()

    def fake_extract(path):
        return "EDUCATION\n- MSc Data Science\nPython" if "first" in path.name else "EXPERIENCE\n- Built SQL pipelines"

    prompts: list[str] = []

    class Router:
        def generate(self, **kwargs):
            prompts.append(kwargs["user_prompt"])
            return {"questions": ["Which country do you want to work in?"]}

    monkeypatch.setattr(intake, "extract_text_auto", fake_extract)
    service = FactSheetIntakeService(db_session, Router())
    result = service.start_intake(
        "test-cand-dossier",
        [
            UploadedFile(filename="first.pdf", content=b"pdf-one", content_type="application/pdf"),
            UploadedFile(filename="second.pdf", content=b"pdf-two", content_type="application/pdf"),
        ],
    )

    assert result.status == "questions_needed"
    draft = db_session.query(CandidateIntakeDraft).filter_by(candidate_id="test-cand-dossier").one()
    entries = draft.source_dossier["entries"]
    assert [entry["label"] for entry in entries] == ["first.pdf", "second.pdf"]
    assert entries[0]["source_type"] == "pdf"
    assert "## Education" in entries[0]["normalized_text"]
    assert "- MSc Data Science" in entries[0]["normalized_text"]
    assert "# Source: first.pdf" in prompts[0]
    assert "# Source: second.pdf" in prompts[0]


def test_start_intake_keeps_pdf_and_notes_as_distinct_sources(db_session, monkeypatch):
    import job_agent.services.intake as intake

    db_session.add(Candidate(id="test-cand-notes-dossier", full_name="Notes User"))
    db_session.commit()

    class Router:
        def generate(self, **_kwargs):
            return {"questions": ["What role are you targeting?"]}

    monkeypatch.setattr(intake, "extract_text_auto", lambda _path: "SKILLS\nPython\nSQL")
    service = FactSheetIntakeService(db_session, Router())
    service.start_intake(
        "test-cand-notes-dossier",
        [UploadedFile(filename="cv.pdf", content=b"pdf", content_type="application/pdf")],
        profile_notes="Target role: Data Engineer",
    )

    draft = db_session.query(CandidateIntakeDraft).filter_by(candidate_id="test-cand-notes-dossier").one()
    entries = draft.source_dossier["entries"]
    assert [entry["label"] for entry in entries] == ["cv.pdf", "Manual profile notes"]
    assert entries[1]["source_type"] == "notes"
    assert "Target role: Data Engineer" in entries[1]["raw_text"]


@pytest.mark.parametrize(
    "fixture_name",
    [
        "clean_single_column_cv.txt",
        "two_column_cv.txt",
        "icon_heavy_section_light_cv.txt",
        "multi_page_cv.txt",
    ],
)
def test_intake_layout_regression_corpus_reaches_question_stage(db_session, fixture_name):
    candidate_id = f"test-cand-layout-{fixture_name.replace('.', '-').replace('_', '-')}"
    db_session.add(Candidate(id=candidate_id, full_name="Layout User"))
    db_session.commit()

    class Router:
        def generate(self, **_kwargs):
            return {"questions": [{"id": "target_roles", "prompt": "What role are you targeting?", "kind": "text"}]}

    service = FactSheetIntakeService(db_session, Router())
    result = service.start_intake(
        candidate_id,
        [
            UploadedFile(
                filename=fixture_name,
                content=_fixture_text(fixture_name).encode("utf-8"),
                content_type="text/plain",
            )
        ],
    )

    assert result.status == "questions_needed"
    draft = db_session.query(CandidateIntakeDraft).filter_by(candidate_id=candidate_id).one()
    assert draft.source_dossier is not None
    entries = draft.source_dossier["entries"]
    assert len(entries) == 1
    assert entries[0]["label"] == fixture_name
    assert str(entries[0]["normalized_text"]).strip()
    assert isinstance(draft.source_dossier.get("diagnostics"), list)


def test_intake_mixed_uploaded_text_and_manual_notes_are_both_in_prompt_and_dossier(db_session):
    candidate_id = "test-cand-mixed-source-corpus"
    db_session.add(Candidate(id=candidate_id, full_name="Mixed Source User"))
    db_session.commit()

    prompts: list[str] = []

    class Router:
        def generate(self, **kwargs):
            prompts.append(kwargs["user_prompt"])
            return {"questions": [{"id": "target_roles", "prompt": "What role are you targeting?", "kind": "text"}]}

    service = FactSheetIntakeService(db_session, Router())
    result = service.start_intake(
        candidate_id,
        [
            UploadedFile(
                filename="two_column_cv.txt",
                content=_fixture_text("two_column_cv.txt").encode("utf-8"),
                content_type="text/plain",
            )
        ],
        profile_notes=_fixture_text("mixed_notes.txt"),
    )

    assert result.status == "questions_needed"
    assert prompts
    assert "# Source: two_column_cv.txt" in prompts[0]
    assert "# Source: Manual profile notes" in prompts[0]
    draft = db_session.query(CandidateIntakeDraft).filter_by(candidate_id=candidate_id).one()
    labels = [entry["label"] for entry in draft.source_dossier["entries"]]
    assert labels == ["two_column_cv.txt", "Manual profile notes"]
    assert "Target role: Embedded Software Engineer" in draft.source_dossier["entries"][1]["raw_text"]


def test_intake_diagnostics_capture_extraction_failure_without_private_text(db_session, monkeypatch):
    import job_agent.services.intake as intake

    candidate_id = "test-cand-diag-extraction"
    db_session.add(Candidate(id=candidate_id, full_name="Diagnostics User"))
    db_session.commit()

    monkeypatch.setattr(intake, "extract_text_auto", lambda _path: (_ for _ in ()).throw(RuntimeError("private raw text leak")))

    class Router:
        def generate(self, **_kwargs):
            return {"questions": ["What role are you targeting?"]}

    service = FactSheetIntakeService(db_session, Router())
    result = service.start_intake(
        candidate_id,
        [UploadedFile(filename="broken.pdf", content=b"%PDF-1.4", content_type="application/pdf")],
    )

    assert result.status == "questions_needed"
    draft = db_session.query(CandidateIntakeDraft).filter_by(candidate_id=candidate_id).one()
    diagnostics = draft.source_dossier["diagnostics"]
    extraction = next(item for item in diagnostics if item["stage"] == "extraction")
    _assert_diagnostic_contract(extraction)
    assert extraction["code"] == "source_text_unavailable"
    serialized = json.dumps(extraction)
    assert "Traceback" not in serialized
    assert "private raw text leak" not in serialized


def test_intake_diagnostics_capture_normalization_failure_without_source_leak(db_session, monkeypatch):
    import job_agent.services.intake as intake

    candidate_id = "test-cand-diag-normalization"
    db_session.add(Candidate(id=candidate_id, full_name="Normalization User"))
    db_session.commit()

    monkeypatch.setattr(
        intake,
        "_normalize_source_markdown",
        lambda _text: (_ for _ in ()).throw(ValueError("secret@example.com should never leak")),
    )

    class Router:
        def generate(self, **_kwargs):
            return {"questions": ["What role are you targeting?"]}

    service = FactSheetIntakeService(db_session, Router())
    result = service.start_intake(
        candidate_id,
        [UploadedFile(filename="messy.txt", content=b"messy text", content_type="text/plain")],
    )

    assert result.status == "questions_needed"
    draft = db_session.query(CandidateIntakeDraft).filter_by(candidate_id=candidate_id).one()
    diagnostics = draft.source_dossier["diagnostics"]
    normalization = next(item for item in diagnostics if item["stage"] == "normalization")
    _assert_diagnostic_contract(normalization)
    assert normalization["code"] == "source_normalization_failed"
    serialized = json.dumps(normalization)
    assert "Traceback" not in serialized
    assert "secret@example.com" not in serialized


def test_intake_diagnostics_capture_provider_draft_shape_failure(db_session):
    candidate_id = "test-cand-diag-provider-shape"
    db_session.add(Candidate(id=candidate_id, full_name="Provider Shape User"))
    db_session.commit()

    class Router:
        def generate(self, **_kwargs):
            return "provider returned plain text instead of json"

    service = FactSheetIntakeService(db_session, Router())
    with pytest.raises(ValueError) as excinfo:
        service.start_intake(candidate_id, [])

    assert "invalid intake response" in str(excinfo.value).lower()
    draft = db_session.query(CandidateIntakeDraft).filter_by(candidate_id=candidate_id).one()
    diagnostics = draft.source_dossier["diagnostics"]
    provider_failure = next(item for item in diagnostics if item["stage"] == "provider_draft_shape")
    _assert_diagnostic_contract(provider_failure)
    assert provider_failure["code"] == "provider_response_unparseable"
    assert "Traceback" not in json.dumps(provider_failure)


def test_intake_diagnostics_capture_schema_promotion_failure(db_session, monkeypatch):
    import job_agent.services.intake as intake

    candidate_id = "test-cand-diag-schema"
    db_session.add(Candidate(id=candidate_id, full_name="Schema User", email="schema@example.com"))
    db_session.commit()

    class Router:
        def generate(self, **_kwargs):
            return {"fact_sheet": _valid_fact_sheet("Schema User")}

    def _raise_schema_error(*_args, **_kwargs):
        raise ValueError("SECRET_PROFILE_TEXT should never be surfaced")

    monkeypatch.setattr(intake.FactSheetJsonIngestionService, "ingest_json", _raise_schema_error)

    service = FactSheetIntakeService(db_session, Router())
    with pytest.raises(ValueError) as excinfo:
        service.start_intake(candidate_id, [])

    assert "inconsistent" in str(excinfo.value).lower()
    assert "SECRET_PROFILE_TEXT" not in str(excinfo.value)
    draft = db_session.query(CandidateIntakeDraft).filter_by(candidate_id=candidate_id).one()
    diagnostics = draft.source_dossier["diagnostics"]
    schema_failure = next(item for item in diagnostics if item["stage"] == "schema_promotion")
    _assert_diagnostic_contract(schema_failure)
    assert schema_failure["code"] == "schema_ingest_failed"
    serialized = json.dumps(schema_failure)
    assert "SECRET_PROFILE_TEXT" not in serialized
    assert "Traceback" not in serialized


def test_rerunning_intake_replaces_active_source_dossier(db_session, monkeypatch):
    import job_agent.services.intake as intake

    db_session.add(Candidate(id="test-cand-rerun-dossier", full_name="Rerun User"))
    db_session.commit()

    class Router:
        def generate(self, **_kwargs):
            return {"questions": ["What role are you targeting?"]}

    monkeypatch.setattr(intake, "extract_text_auto", lambda path: f"text from {path.name}")
    service = FactSheetIntakeService(db_session, Router())
    service.start_intake(
        "test-cand-rerun-dossier",
        [UploadedFile(filename="old.pdf", content=b"old", content_type="application/pdf")],
        reset_existing_draft=True,
    )
    service.start_intake(
        "test-cand-rerun-dossier",
        [UploadedFile(filename="new.pdf", content=b"new", content_type="application/pdf")],
        reset_existing_draft=True,
    )

    draft = db_session.query(CandidateIntakeDraft).filter_by(candidate_id="test-cand-rerun-dossier").one()
    labels = [entry["label"] for entry in draft.source_dossier["entries"]]
    assert labels == ["new.pdf"]
    assert "old.pdf" not in str(draft.source_dossier)


def test_promoting_malformed_optional_fields_records_draft_issues(db_session):
    db_session.add(Candidate(id="test-cand-promotion", full_name="Promotion User"))
    db_session.commit()

    class Router:
        def generate(self, **_kwargs):
            payload = _valid_fact_sheet("Promotion User")
            payload["person"]["current_location"] = "Turin, Italy"
            payload["match_profile"]["work_authorization"] = {"Italy": "student permit"}
            payload["projects"] = "not a project list"
            return {"fact_sheet": payload}

    service = FactSheetIntakeService(db_session, Router())
    result = service.start_intake("test-cand-promotion", [])

    assert result.status == "complete"
    assert result.fact_sheet["person"]["current_location"] == {"city": "Turin", "country": "Italy"}
    assert result.fact_sheet["match_profile"]["work_authorization"] == "Italy: student permit"
    assert result.fact_sheet["projects"] == []
    draft = db_session.query(CandidateIntakeDraft).filter_by(candidate_id="test-cand-promotion").one()
    assert any(issue["field"] == "projects" for issue in draft.source_dossier["draft_issues"])


def test_onboarding_review_payload_includes_field_provenance(client, db_session):
    candidate = Candidate(id="test-cand-review-provenance", full_name="Review User", email="review@example.com")
    db_session.add(candidate)
    draft = CandidateIntakeDraft(
        id="review-draft",
        candidate_id=candidate.id,
        partial_fact_sheet=None,
        source_dossier={
            "version": 1,
            "candidate_id": candidate.id,
            "entries": [
                {
                    "source_id": "source-1",
                    "label": "cv.pdf",
                    "source_type": "pdf",
                    "order": 1,
                        "raw_text": "Review User\nreviewuser@example.com\nTurin, Italy",
                        "normalized_text": "Review User\nreviewuser@example.com\nTurin, Italy",
                    "normalized_preview": "Review User",
                    "warnings": [],
                }
            ],
            "draft_issues": [],
            "field_provenance": {},
        },
        iteration=1,
    )
    db_session.add(draft)
    db_session.commit()

    payload = _valid_fact_sheet("Review User")
    payload["person"]["current_location"] = {"city": "Turin", "country": "Italy"}
    post = client.post(f"/candidates/{candidate.id}/fact-sheet-json", json=payload)
    assert post.status_code == 200, post.text

    response = client.get(f"/candidates/{candidate.id}/onboarding-review")

    assert response.status_code == 200, response.text
    review = response.json()["review"]
    assert review["fields"]["person.full_name"]["value"] == "Review User"
    assert review["fields"]["person.full_name"]["source_hint"] == "cv.pdf"
    assert review["fields"]["person.contact.email"]["source_hint"] == "cv.pdf"
    assert review["fields"]["match_profile.location_preferences.preferred_countries"]["value"] == ["Italy"]
    assert review["sources"][0]["label"] == "cv.pdf"


def test_review_save_overwrites_active_draft_state(client, db_session):
    candidate = Candidate(id="test-cand-review-save", full_name="Before User", email="before@example.com")
    db_session.add(candidate)
    db_session.add(
        CandidateIntakeDraft(
            id="review-save-draft",
            candidate_id=candidate.id,
            partial_fact_sheet=_valid_fact_sheet("Before User"),
            source_dossier={"version": 1, "entries": [], "draft_issues": []},
            iteration=1,
        )
    )
    db_session.commit()

    payload = _valid_fact_sheet("After User")
    payload["person"]["contact"]["email"] = "after@example.com"
    payload["match_profile"]["location_preferences"]["preferred_countries"] = ["Germany"]
    payload["match_profile"]["location_preferences"]["preferred_cities"] = ["Berlin"]
    response = client.post(f"/candidates/{candidate.id}/fact-sheet-json", json=payload)

    assert response.status_code == 200, response.text
    draft = db_session.query(CandidateIntakeDraft).filter_by(candidate_id=candidate.id).one()
    assert draft.partial_fact_sheet["person"]["full_name"] == "After User"
    assert draft.partial_fact_sheet["person"]["contact"]["email"] == "after@example.com"
    assert draft.partial_fact_sheet["match_profile"]["location_preferences"]["preferred_countries"] == ["Germany"]
    assert draft.partial_fact_sheet["match_profile"]["location_preferences"]["preferred_cities"] == ["Berlin"]
