from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sys
import time
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy.exc import SQLAlchemyError

from job_agent.db import SessionLocal
from job_agent.models import WorkflowTask
from job_agent.services.workflows import CVWorkflowService


BASE_URL = "http://127.0.0.1:8000"
POLL_SECONDS = 2.0
POLL_TIMEOUT_SECONDS = 180.0
PROFILE_DIR = Path(__file__).resolve().parents[1] / "examples" / "qa_profiles"
PROCESS_TASKS_LOCALLY = True

SYNTHETIC_JOBS: dict[str, str] = {
    "consultant_profile": """Title: Junior Consultant
Company: Axis Advisory
Location: Milan, Italy

About the role
We are looking for a junior consultant who can support transformation projects, map processes, analyze KPIs, interview stakeholders, and prepare executive-ready presentations.

Requirements
- MSc or BSc in engineering, economics, or a related field
- Strong Excel and PowerPoint skills
- Good analytical mindset and problem-solving ability
- Experience with SQL or BI tools is a plus
- Fluent English
""",
    "tech_profile": """Title: Junior Data Engineer
Company: Iconsulting
Location: Casalecchio di Reno (Bologna), Italy

About the role
You will help build modern data pipelines, work with relational and non-relational databases, and support real delivery projects in a collaborative data team.

Requirements
- Degree in computer science, engineering, or STEM
- Basic SQL and Python
- Curiosity, analytical mindset, and willingness to learn
- Good English
- Interest in data platforms and analytics engineering
""",
    "finance_profile": """Title: Financial Analyst
Company: Meridian Capital Services
Location: Rome, Italy

About the role
Support budgeting, forecasting, variance analysis, management reporting, and monthly performance reviews with business stakeholders.

Requirements
- Degree in finance, economics, or business
- Strong Excel and financial-modeling fundamentals
- Experience with accounting close, reporting, or FP&A
- Knowledge of SAP or ERP systems is a plus
- Fluent English
""",
    "sales_profile": """Title: Business Development Representative
Company: Orbit Cloud
Location: Milan, Italy

About the role
Own outbound prospecting, qualify inbound leads, maintain CRM hygiene, collaborate with account executives, and support pipeline reporting.

Requirements
- B2B sales or commercial coordination experience
- Familiarity with Salesforce, HubSpot, or equivalent CRM tools
- Strong communication and discovery skills
- English proficiency
""",
    "operations_profile": """Title: Operations Analyst
Company: Verde Operations Group
Location: Bologna, Italy

About the role
Track service KPIs, maintain issue logs, improve cross-functional workflows, and prepare weekly reporting for operations leadership.

Requirements
- Degree in management, economics, operations, or related field
- Strong Excel and reporting skills
- Experience with process documentation and continuous improvement
- SQL or BI knowledge is a plus
- Fluent English
""",
}


@dataclass
class MatrixProfile:
    slug: str
    path: Path
    payload: dict[str, Any]


def _api(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    json_body: dict[str, Any] | None = None,
) -> httpx.Response:
    response = client.request(method, f"{BASE_URL}{path}", json=json_body, timeout=120.0)
    response.raise_for_status()
    return response


def _load_profiles() -> list[MatrixProfile]:
    profiles: list[MatrixProfile] = []
    for path in sorted(PROFILE_DIR.glob("*_profile.json")):
        profiles.append(
            MatrixProfile(
                slug=path.stem,
                path=path,
                payload=json.loads(path.read_text(encoding="utf-8")),
            )
        )
    if len(profiles) != 5:
        raise RuntimeError(f"Expected 5 QA profiles, found {len(profiles)} in {PROFILE_DIR}")
    return profiles


def _set_active_candidate(client: httpx.Client, candidate_id: str, profile: MatrixProfile) -> None:
    match_profile = profile.payload.get("match_profile", {})
    location_preferences = match_profile.get("location_preferences", {})
    countries = location_preferences.get("preferred_countries") or ["Italy"]
    roles = match_profile.get("target_roles") or []
    _api(
        client,
        "POST",
        "/settings/save",
        json_body={
            "default_candidate_id": candidate_id,
            "jobspy_discover_queries": roles,
            "job_search_countries": countries,
        },
    )


def _resolve_owner_candidate(client: httpx.Client) -> str:
    current = _api(client, "GET", "/settings/current").json()
    candidate_id = str(current.get("default_candidate_id") or "").strip()
    if candidate_id:
        return candidate_id
    created = _api(
        client,
        "POST",
        "/candidates",
        json_body={
            "full_name": "QA Matrix Seed Candidate",
            "email": "qa-matrix-seed@example.test",
        },
    ).json()
    return str(created["id"])


def _poll_task(client: httpx.Client, task_id: str) -> dict[str, Any]:
    deadline = time.time() + POLL_TIMEOUT_SECONDS
    while time.time() < deadline:
        task = _api(client, "GET", f"/tasks/{task_id}").json()
        status = str(task.get("status") or "").lower()
        if status in {"completed", "failed"}:
            return task
        time.sleep(POLL_SECONDS)
    raise TimeoutError(f"Timed out waiting for task {task_id}")


def _process_task_locally(task_id: str) -> None:
    try:
        with SessionLocal() as session:
            task = session.get(WorkflowTask, UUID(task_id))
            if task is None or str(task.status or "").lower() != "pending":
                return
            service = CVWorkflowService(session)
            service.process_next_task()
    except SQLAlchemyError:
        raise
    except Exception:
        raise


def _draft_metrics(draft: dict[str, Any]) -> dict[str, Any]:
    content = draft.get("content") or {}
    selected_experiences = content.get("selected_experiences") or []
    selected_projects = content.get("selected_projects") or []
    selected_skills = content.get("selected_skills") or []

    experience_bullets = 0
    for item in selected_experiences:
        bullets = item.get("bullets") or item.get("responsibilities") or []
        experience_bullets += sum(1 for bullet in bullets if str(bullet).strip())

    project_bullets = 0
    for item in selected_projects:
        bullets = item.get("bullets") or item.get("key_results") or []
        if bullets:
            project_bullets += sum(1 for bullet in bullets if str(bullet).strip())
        elif str(item.get("summary") or "").strip():
            project_bullets += 1

    summary_present = bool(str(content.get("professional_summary") or "").strip())
    empty_core_sections = [
        name
        for name, present in (
            ("summary", summary_present),
            ("skills", bool(selected_skills)),
            ("experience", bool(selected_experiences)),
            ("projects", bool(selected_projects)),
        )
        if not present
    ]

    return {
        "summary_present": summary_present,
        "selected_skills": len([item for item in selected_skills if str(item).strip()]),
        "selected_experiences": len(selected_experiences),
        "selected_projects": len(selected_projects),
        "experience_bullets": experience_bullets,
        "project_bullets": project_bullets,
        "empty_core_sections": empty_core_sections,
    }


def run_matrix() -> dict[str, Any]:
    profiles = _load_profiles()
    results: list[dict[str, Any]] = []

    with httpx.Client() as client:
        health = _api(client, "GET", "/health").json()
        providers = _api(client, "GET", "/providers").json()
        owner_candidate_id = _resolve_owner_candidate(client)

        for profile in profiles:
            _api(
                client,
                "POST",
                f"/candidates/{owner_candidate_id}/fact-sheet-json",
                json_body=profile.payload,
            )
            _set_active_candidate(client, owner_candidate_id, profile)

            readiness = _api(client, "GET", f"/candidates/{owner_candidate_id}/readiness").json()["readiness"]
            manual_review = _api(
                client,
                "POST",
                "/ui/jobs/manual-target/analyze",
                json_body={"text": SYNTHETIC_JOBS[profile.slug]},
            ).json()
            job_create = _api(
                client,
                "POST",
                "/jobs/from-text",
                json_body={"text": SYNTHETIC_JOBS[profile.slug]},
            ).json()
            draft_task = _api(
                client,
                "POST",
                "/drafts/generate",
                json_body={
                    "job_id": job_create["job_id"],
                    "track_slug": None,
                    "force_cloud_review": False,
                },
            ).json()

            if PROCESS_TASKS_LOCALLY:
                _process_task_locally(draft_task["task_id"])
            task = _poll_task(client, draft_task["task_id"])
            task_result = task.get("result") or {}
            draft_payload: dict[str, Any] | None = None
            metrics: dict[str, Any] | None = None
            if str(task.get("status") or "").lower() == "completed" and task_result.get("draft_id"):
                draft_payload = _api(client, "GET", f"/drafts/{task_result['draft_id']}").json()
                metrics = _draft_metrics(draft_payload)

            results.append(
                {
                    "profile": profile.slug,
                    "candidate_id": owner_candidate_id,
                    "readiness": readiness,
                    "manual_review_score": manual_review.get("score"),
                    "manual_review_summary": manual_review.get("summary"),
                    "job_id": job_create["job_id"],
                    "task_id": draft_task["task_id"],
                    "task_status": task.get("status"),
                    "task_error": task.get("error_message"),
                    "draft_id": task_result.get("draft_id"),
                    "draft_metrics": metrics,
                }
            )

    return {
        "health": health,
        "providers": providers,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "results": results,
    }


def main() -> int:
    try:
        report = run_matrix()
    except Exception as exc:
        print(json.dumps({"status": "error", "detail": str(exc)}, indent=2))
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
