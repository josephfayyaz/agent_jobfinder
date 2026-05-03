from __future__ import annotations

import json
from pathlib import Path

from job_agent.services.fact_sheet_json import FactSheetJsonIngestionService
from job_agent.services.profile_readiness import READINESS_READY, evaluate_profile_readiness


QA_PROFILE_DIR = Path(__file__).resolve().parents[1] / "examples" / "qa_profiles"


def test_qa_profiles_ingest_and_export_as_ready(db_session):
    profile_paths = sorted(QA_PROFILE_DIR.glob("*_profile.json"))
    assert len(profile_paths) == 5

    service = FactSheetJsonIngestionService(db_session)
    for profile_path in profile_paths:
        payload = json.loads(profile_path.read_text(encoding="utf-8"))
        result = service.ingest_json(candidate_id=None, fact_sheet=payload, source_name=profile_path.stem)
        exported = service.export_json(result.candidate_id)
        readiness = evaluate_profile_readiness(exported)

        assert exported["person"]["full_name"] == payload["person"]["full_name"]
        assert readiness["status"] == READINESS_READY
        assert readiness["ready_for_final_cv"] is True
        assert readiness["counts"]["experiences"] >= 2
        assert readiness["counts"]["skills"] >= 6
        assert readiness["counts"]["evidence_blocks"] >= 3
