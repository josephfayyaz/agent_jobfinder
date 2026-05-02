from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import shutil
import sys
import time

import httpx

from onboarding_audit import (
    AUDIT_ROOT,
    HOST,
    LM_STUDIO_BASE_URL,
    LOG_ROOT,
    PORT,
    REQUEST_TIMEOUT,
    AppRuntime,
    AuditFailure,
    ExpectedProfile,
    _answer_for_question,
    _assert_ok,
    _discover_profiles,
    _provider_payload,
    _select_chat_model,
)


ROLE_AUDIT_ROOT = AUDIT_ROOT.parent / ".role_audit_runtime"
ROLE_LOG_ROOT = LOG_ROOT.parent / "role_suggestion_audit"
MAX_DISCOVERY_ROLES = 4

EXPECTED_ROLE_SUGGESTIONS: dict[str, list[str]] = {
    "Junior Data Engineer": ["Junior Data Engineer", "Analytics Engineer", "ETL Developer", "BI Engineer"],
    "Analytics Engineer": ["Analytics Engineer", "Data Engineer", "BI Developer", "Analytics Developer"],
    "Backend Software Engineer": ["Backend Software Engineer", "Backend Engineer", "API Engineer", "Platform Engineer"],
    "QA Automation Engineer": ["QA Automation Engineer", "Test Automation Engineer", "Software QA Engineer", "QA Analyst"],
    "Product Designer": ["Product Designer", "UX Designer", "UI/UX Designer", "Interaction Designer"],
    "Junior Accountant": ["Junior Accountant", "Accounting Assistant", "Accounts Payable Specialist", "Accounts Receivable Specialist"],
    "Financial Analyst": ["Financial Analyst", "FP&A Analyst", "Reporting Analyst", "Business Finance Analyst"],
    "Market Research Analyst": ["Market Research Analyst", "Consumer Insights Analyst", "Research Analyst", "Marketing Analyst"],
    "HR Operations Specialist": ["HR Operations Specialist", "People Operations Coordinator", "HR Coordinator", "Talent Operations Specialist"],
    "Architect": ["Architect", "Project Architect", "Architectural Designer", "Design Architect"],
    "Civil Engineer": ["Civil Engineer", "Site Engineer", "Construction Engineer", "Structural Design Engineer"],
    "Mechanical Engineer": ["Mechanical Engineer", "Design Engineer", "Product Development Engineer", "Test Engineer"],
    "Materials Engineer": ["Materials Engineer", "Materials Scientist", "Failure Analysis Engineer", "Materials Lab Engineer"],
    "Industrial Engineer": ["Industrial Engineer", "Process Improvement Engineer", "Operations Engineer", "Continuous Improvement Engineer"],
    "Laboratory Analyst": ["Laboratory Analyst", "QC Analyst", "Analytical Chemist", "Quality Control Specialist"],
    "Supply Chain Analyst": ["Supply Chain Analyst", "Demand Planner", "Inventory Analyst", "Operations Analyst"],
    "Business Analyst": ["Business Analyst", "Process Analyst", "Requirements Analyst", "Operations Analyst"],
    "Research Assistant": ["Research Assistant", "Research Associate", "Laboratory Research Assistant", "Scientific Research Assistant"],
    "Project Manager": ["Project Manager", "Delivery Manager", "Implementation Project Manager", "Program Coordinator"],
    "Data Scientist": ["Data Scientist", "Machine Learning Engineer", "Applied Data Scientist", "Experimentation Scientist"],
}

CUSTOM_ROLE_BY_SLUG = {
    "01_junior_data_engineer_english_only": "Data Platform Analyst",
}


def _require_ml_python(python_bin: str) -> None:
    normalized = str(python_bin)
    if "/envs/ML/bin/python" not in normalized:
        raise AuditFailure(f"Role audit must run with the ML environment, got: {normalized}")


def _bootstrap_candidate(client: httpx.Client, expected: ExpectedProfile, model_name: str) -> str:
    validation = _assert_ok(
        client.post(
            "/providers/validate",
            json={
                "provider_mode": "lm_studio",
                "lm_studio_base_url": LM_STUDIO_BASE_URL,
            },
        ),
        f"{expected.slug} provider validation",
    )
    if not validation.get("ok"):
        raise AuditFailure(f"{expected.slug} provider validation reported not ok: {validation}")

    _assert_ok(client.post("/settings/save", json=_provider_payload(model_name)), f"{expected.slug} save provider settings")

    candidate = _assert_ok(
        client.post("/candidates", json={"full_name": expected.full_name, "email": expected.email}),
        f"{expected.slug} create candidate",
    )
    candidate_id = str(candidate.get("id") or "")
    if not candidate_id:
        raise AuditFailure(f"{expected.slug} candidate creation returned no id")

    with expected.resume_text_path.open("rb") as handle:
        upload = _assert_ok(
            client.post(
                f"/candidates/{candidate_id}/sources/upload",
                files={"files": (expected.resume_text_path.name, handle, "text/plain")},
            ),
            f"{expected.slug} upload resume",
        )
    if int(upload.get("uploaded") or 0) != 1:
        raise AuditFailure(f"{expected.slug} upload did not store exactly one resume: {upload}")

    intake = _assert_ok(
        client.post(
            f"/candidates/{candidate_id}/intake/start",
            data={"profile_notes": expected.profile_notes_for_input},
        ),
        f"{expected.slug} start intake",
    )
    rounds = 0
    while intake.get("status") == "questions_needed":
        rounds += 1
        if rounds > 5:
            raise AuditFailure(f"{expected.slug} intake exceeded question rounds: {intake}")
        questions = list(intake.get("questions") or [])
        answers: dict[str, object] = {}
        for index, raw_question in enumerate(questions, start=1):
            question = raw_question if isinstance(raw_question, dict) else {"id": f"q{index}", "prompt": str(raw_question)}
            question_id = str(question.get("id") or f"q{index}")
            answers[question_id] = _answer_for_question(question, expected)
        intake = _assert_ok(
            client.post(
                f"/candidates/{candidate_id}/intake/answer",
                json={"answers": answers},
            ),
            f"{expected.slug} answer intake round {rounds}",
        )
    if intake.get("status") != "complete":
        raise AuditFailure(f"{expected.slug} onboarding did not complete before role audit: {intake}")
    return candidate_id


def _save_roles(client: httpx.Client, expected: ExpectedProfile, roles: list[str]) -> None:
    payload = {
        "jobspy_discover_queries": roles,
        "job_search_countries": expected.preferred_countries,
        "jobspy_discover_location": expected.preferred_countries[0] if expected.preferred_countries else "Italy",
        "target_job_seniority": expected.seniority or "any",
    }
    _assert_ok(client.post("/settings/save", json=payload), f"{expected.slug} save discovery roles")


def _current_roles(client: httpx.Client) -> list[str]:
    current = _assert_ok(client.get("/settings/current"), "settings current")
    return [str(item).strip() for item in current.get("jobspy_discover_queries") or [] if str(item).strip()]


def _verify_suggestions(expected: ExpectedProfile, suggestions: list[str]) -> None:
    expected_roles = EXPECTED_ROLE_SUGGESTIONS.get(expected.target_role)
    if expected_roles is None:
        raise AuditFailure(f"No expected role suggestion fixture defined for {expected.target_role}")
    if suggestions != expected_roles:
        raise AuditFailure(
            f"{expected.slug} contextual suggestions mismatch. expected={expected_roles} actual={suggestions}"
        )
    if len(suggestions) > MAX_DISCOVERY_ROLES:
        raise AuditFailure(f"{expected.slug} returned more than {MAX_DISCOVERY_ROLES} suggestions: {suggestions}")


def _run_single_profile(expected: ExpectedProfile, python_bin: str, model_name: str) -> dict[str, object]:
    runtime_dir = ROLE_AUDIT_ROOT / expected.slug
    log_path = ROLE_LOG_ROOT / f"{expected.slug}.server.log"
    if runtime_dir.exists():
        shutil.rmtree(runtime_dir)
    runtime = AppRuntime(runtime_dir, log_path, python_bin)
    runtime.start()
    base_url = f"http://{HOST}:{PORT}"
    try:
        with httpx.Client(base_url=base_url, timeout=REQUEST_TIMEOUT) as client:
            candidate_id = _bootstrap_candidate(client, expected, model_name)
            recommendations = _assert_ok(
                client.get("/search/preferences/recommendations", params={"candidate_id": candidate_id}),
                f"{expected.slug} initial search recommendations",
            )
            suggested_roles = [str(item).strip() for item in recommendations.get("suggested_roles") or [] if str(item).strip()]
            _verify_suggestions(expected, suggested_roles)

            selected_roles = suggested_roles[:2]
            custom_role = CUSTOM_ROLE_BY_SLUG.get(expected.slug)
            if custom_role:
                selected_roles.append(custom_role)
            _save_roles(client, expected, selected_roles)
            if _current_roles(client) != selected_roles:
                raise AuditFailure(f"{expected.slug} saved roles were not persisted immediately")

            if expected.slug == "01_junior_data_engineer_english_only":
                response = client.post(
                    "/settings/save",
                    json={"jobspy_discover_queries": ["A", "B", "C", "D", "E"]},
                )
                if response.status_code != 422:
                    raise AuditFailure(f"{expected.slug} max-role rejection failed: {response.status_code} {response.text[:300]}")

        runtime.stop()
        runtime.start()

        with httpx.Client(base_url=base_url, timeout=REQUEST_TIMEOUT) as client:
            if _current_roles(client) != selected_roles:
                raise AuditFailure(f"{expected.slug} selected roles did not persist after restart")

            edited_roles = [suggested_roles[0], suggested_roles[-1]]
            if custom_role:
                edited_roles = [suggested_roles[0], custom_role]
            _save_roles(client, expected, edited_roles)
            if _current_roles(client) != edited_roles:
                raise AuditFailure(f"{expected.slug} edited roles were not saved")

        runtime.stop()
        runtime.start()

        with httpx.Client(base_url=base_url, timeout=REQUEST_TIMEOUT) as client:
            if _current_roles(client) != edited_roles:
                raise AuditFailure(f"{expected.slug} edited roles did not persist after restart")

            fact_sheet = _assert_ok(
                client.get(f"/candidates/{candidate_id}/fact-sheet-json"),
                f"{expected.slug} export fact sheet before role refresh test",
            )
            refreshed_role = suggested_roles[1] if len(suggested_roles) > 1 else suggested_roles[0]
            updated_fact_sheet = copy.deepcopy(fact_sheet)
            match_profile = dict(updated_fact_sheet.get("match_profile") or {})
            match_profile["target_roles"] = [refreshed_role]
            updated_fact_sheet["match_profile"] = match_profile
            _assert_ok(
                client.post(f"/candidates/{candidate_id}/fact-sheet-json", json=updated_fact_sheet),
                f"{expected.slug} update fact sheet target roles",
            )
            refreshed = _assert_ok(
                client.get("/search/preferences/recommendations", params={"candidate_id": candidate_id}),
                f"{expected.slug} refreshed recommendations after fact sheet update",
            )
            refreshed_roles = [str(item).strip() for item in refreshed.get("suggested_roles") or [] if str(item).strip()]
            if not refreshed_roles or refreshed_roles[0] != refreshed_role:
                raise AuditFailure(
                    f"{expected.slug} suggestions did not refresh from updated fact sheet. expected first={refreshed_role} actual={refreshed_roles}"
                )
            if len(refreshed_roles) > MAX_DISCOVERY_ROLES:
                raise AuditFailure(f"{expected.slug} refreshed suggestions exceeded role limit: {refreshed_roles}")

        return {
            "slug": expected.slug,
            "candidate_id": candidate_id,
            "selected_roles": selected_roles,
            "edited_roles": edited_roles,
            "log_path": str(log_path),
        }
    finally:
        runtime.stop()


def main(argv: list[str]) -> int:
    profiles = _discover_profiles()
    requested_slugs = {item.strip() for item in argv[1:] if item.strip()}
    if requested_slugs:
        profiles = [profile for profile in profiles if profile.slug in requested_slugs]
        missing = sorted(requested_slugs - {profile.slug for profile in profiles})
        if missing:
            print(f"Unknown profile slugs: {', '.join(missing)}", file=sys.stderr)
            return 1

    ROLE_AUDIT_ROOT.mkdir(parents=True, exist_ok=True)
    ROLE_LOG_ROOT.mkdir(parents=True, exist_ok=True)

    with httpx.Client(timeout=15.0) as client:
        models = _assert_ok(client.get(f"{LM_STUDIO_BASE_URL}/models"), "LM Studio models")
    model_names = [str(item.get("id") or "").strip() for item in models.get("data") or [] if str(item.get("id") or "").strip()]
    model_name = _select_chat_model(model_names)
    python_bin = os.environ.get("PYTHON_BIN") or sys.executable
    _require_ml_python(python_bin)

    results: list[dict[str, object]] = []
    failures: list[str] = []
    start_time = time.time()
    for profile in profiles:
        print(f"[role-audit] {profile.slug} using {model_name}", flush=True)
        try:
            results.append(_run_single_profile(profile, python_bin, model_name))
            print(f"[pass] {profile.slug}", flush=True)
        except Exception as exc:
            failures.append(f"{profile.slug}: {exc}")
            print(f"[fail] {profile.slug}: {exc}", flush=True)

    duration = time.time() - start_time
    print(json.dumps({"passed": len(results), "failed": len(failures), "seconds": round(duration, 1)}, indent=2))
    if failures:
        print("\nFailures:")
        for row in failures:
            print(f"- {row}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
