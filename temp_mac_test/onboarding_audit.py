from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass

import httpx


REPO_ROOT = Path(__file__).resolve().parents[1]
HARNESS_ROOT = REPO_ROOT / "temp_mac_test"
USERS_ROOT = HARNESS_ROOT / "generated" / "users"
AUDIT_ROOT = HARNESS_ROOT / ".audit_runtime"
LOG_ROOT = HARNESS_ROOT / ".logs" / "onboarding_audit"
HOST = "127.0.0.1"
PORT = 8011
LM_STUDIO_BASE_URL = "http://127.0.0.1:1234/v1"
REQUEST_TIMEOUT = 180.0
MAX_INTAKE_ROUNDS = 5


class AuditFailure(RuntimeError):
    pass


@dataclass
class ExpectedProfile:
    slug: str
    full_name: str
    email: str
    target_role: str
    seniority: str
    preferred_countries: list[str]
    languages: list[dict[str, str | None]]
    degree: str
    institution: str
    skills: list[str]
    proof_summary: str
    notes_text: str
    resume_text_path: Path
    user_dir: Path
    profile_notes_for_input: str


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_language_entries(raw_languages: list[object]) -> list[dict[str, str | None]]:
    rows: list[dict[str, str | None]] = []
    for item in raw_languages:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "name": str(item.get("name") or "").strip(),
                "level": str(item.get("level") or "").strip() or None,
            }
        )
    return [row for row in rows if row["name"]]


def _discover_profiles() -> list[ExpectedProfile]:
    profiles: list[ExpectedProfile] = []
    for user_dir in sorted(path for path in USERS_ROOT.iterdir() if path.is_dir()):
        profile_raw = _load_json(user_dir / "candidate_profile.json")
        notes_text = (user_dir / "candidate_notes.txt").read_text(encoding="utf-8").strip()
        education = dict(profile_raw.get("education") or {})
        profile_note_lines = [
            f"Candidate: {str(profile_raw.get('candidate_name') or '').strip()}",
            f"Target role: {str(profile_raw.get('target_role') or '').strip()}",
            f"Role family: {str(profile_raw.get('role_family') or '').strip()}",
            f"Seniority: {str(profile_raw.get('seniority') or '').strip()}",
            "Preferred countries: " + ", ".join(
                str(item).strip() for item in profile_raw.get("preferred_countries") or [] if str(item).strip()
            ),
            "Languages: " + ", ".join(
                f"{str(item.get('name') or '').strip()} {str(item.get('level') or '').strip()}".strip()
                for item in profile_raw.get("job_languages") or []
                if isinstance(item, dict) and str(item.get("name") or "").strip()
            ),
            f"Education degree: {str(education.get('degree') or '').strip()}",
            f"Education institution: {str(education.get('institution') or '').strip()}",
            "Skills: " + ", ".join(str(item).strip() for item in profile_raw.get("skills") or [] if str(item).strip()),
            f"Most relevant proof: {str(profile_raw.get('proof_summary') or '').strip()}",
            f"Testing note: {str(profile_raw.get('testing_note') or '').strip()}",
        ]
        profiles.append(
            ExpectedProfile(
                slug=user_dir.name,
                full_name=str(profile_raw.get("candidate_name") or "").strip(),
                email=str(profile_raw.get("email") or "").strip(),
                target_role=str(profile_raw.get("target_role") or "").strip(),
                seniority=str(profile_raw.get("seniority") or "").strip(),
                preferred_countries=[str(item).strip() for item in profile_raw.get("preferred_countries") or [] if str(item).strip()],
                languages=_parse_language_entries(profile_raw.get("job_languages") or []),
                degree=str(education.get("degree") or "").strip(),
                institution=str(education.get("institution") or "").strip(),
                skills=[str(item).strip() for item in profile_raw.get("skills") or [] if str(item).strip()],
                proof_summary=str(profile_raw.get("proof_summary") or "").strip(),
                notes_text=notes_text,
                resume_text_path=user_dir / "candidate_resume.txt",
                user_dir=user_dir,
                profile_notes_for_input="\n".join(line for line in profile_note_lines if line.strip()),
            )
        )
    return profiles


def _non_embedding_models(models: list[str]) -> list[str]:
    return [name for name in models if "embed" not in name.casefold()]


def _select_chat_model(models: list[str]) -> str:
    candidates = _non_embedding_models(models)
    if not candidates:
        raise AuditFailure("LM Studio returned no non-embedding models.")
    for name in candidates:
        if "gpt-oss" in name.casefold():
            return name
    return candidates[0]


def _flatten_strings(value: object) -> list[str]:
    rows: list[str] = []
    if isinstance(value, str):
        text = value.strip()
        if text:
            rows.append(text)
    elif isinstance(value, list):
        for item in value:
            rows.extend(_flatten_strings(item))
    elif isinstance(value, dict):
        for item in value.values():
            rows.extend(_flatten_strings(item))
    return rows


def _answer_for_question(question: dict, expected: ExpectedProfile) -> object:
    question_id = str(question.get("id") or "").strip().casefold()
    prompt = str(question.get("prompt") or question.get("question") or "").strip()
    text = f"{question_id} {prompt}".casefold()
    kind = str(question.get("kind") or "text").strip().lower()
    options = [str(item).strip() for item in question.get("options") or [] if str(item).strip()]
    option_map = {item.casefold(): item for item in options}

    def choose_option(preferred_terms: list[str], default: str | None = None) -> str:
        for term in preferred_terms:
            for option in options:
                if term in option.casefold():
                    return option
        return default or (options[0] if options else "")

    if "target role" in text or question_id == "target_roles":
        answer = expected.target_role
    elif "preferred countr" in text or "where do you want to work" in text:
        answer = ", ".join(expected.preferred_countries)
    elif "work authorization" in text or "visa" in text or "sponsor" in text:
        if "italy" in text or question_id.endswith("_italy"):
            answer = choose_option(["yes", "eu", "authorized"], "Yes")
        elif "germany" in text or question_id.endswith("_germany"):
            answer = choose_option(["yes", "eu", "authorized"], "Yes")
        else:
            answer = "EU/EEA passport holder. No sponsorship required for Italy or Germany."
    elif "availability" in text or "when can you start" in text or "earliest start" in text:
        answer = choose_option(["immediately", "available"], "Available immediately")
    elif "language" in text:
        answer = ", ".join(
            f"{row['name']} {row['level']}".strip() for row in expected.languages if row.get("name")
        )
    elif "latest education degree" in text or "current or most recent degree" in text:
        answer = expected.degree or "Completed university degree"
    elif "institution" in text or "school" in text or "university" in text or "bootcamp" in text:
        answer = expected.institution or "University"
    elif "education status" in text:
        answer = choose_option(["completed", "graduate", "done"], "Completed")
    elif "recent proof" in text or "most relevant proof" in text or "example project" in text:
        answer = expected.proof_summary
    elif "core skill" in text or "strongest skill" in text or "tech stack" in text or "tools" in text:
        answer = ", ".join(expected.skills[:6])
    elif "seniority" in text:
        answer = choose_option([expected.seniority], expected.seniority.title())
    else:
        answer = (
            f"Target role: {expected.target_role}. Preferred countries: {', '.join(expected.preferred_countries)}. "
            f"Most relevant proof: {expected.proof_summary}. Core skills: {', '.join(expected.skills[:5])}. "
            f"Languages: {', '.join(f'{row['name']} {row['level']}'.strip() for row in expected.languages)}."
        )

    if kind == "multi_select":
        if "countr" in text:
            selected = [option for option in options if option.casefold() in {country.casefold() for country in expected.preferred_countries}]
            return selected or options[:1]
        if "language" in text:
            selected = [option for option in options if any(row["name"].casefold() in option.casefold() for row in expected.languages)]
            return selected or options[:1]
        return [answer] if isinstance(answer, str) and answer else []

    if kind == "single_select" and options:
        if isinstance(answer, str):
            direct = option_map.get(answer.casefold())
            if direct:
                return direct
        return choose_option([str(answer).casefold()] if isinstance(answer, str) else [], options[0])

    return answer


def _wait_for_health(base_url: str, timeout_seconds: float = 60.0) -> None:
    deadline = time.time() + timeout_seconds
    with httpx.Client(timeout=5.0) as client:
        while time.time() < deadline:
            try:
                response = client.get(f"{base_url}/health")
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(0.5)
    raise AuditFailure("App did not become healthy before timeout.")


class AppRuntime:
    def __init__(self, runtime_dir: Path, log_path: Path, python_bin: str) -> None:
        self.runtime_dir = runtime_dir
        self.log_path = log_path
        self.python_bin = python_bin
        self.process: subprocess.Popen[bytes] | None = None

    def start(self) -> None:
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["JOB_AGENT_HOME"] = str(self.runtime_dir)
        env["DATABASE_URL"] = f"sqlite:///{self.runtime_dir / 'job_agent.db'}"
        env["ARTIFACTS_DIR"] = str(self.runtime_dir / "generated")
        log_file = self.log_path.open("ab")
        self.process = subprocess.Popen(
            [
                self.python_bin,
                "-m",
                "uvicorn",
                "job_agent.main:app",
                "--host",
                HOST,
                "--port",
                str(PORT),
            ],
            cwd=str(REPO_ROOT),
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
        try:
            _wait_for_health(f"http://{HOST}:{PORT}")
        except Exception:
            self.stop()
            raise

    def stop(self) -> None:
        if self.process is None:
            return
        if self.process.poll() is None:
            self.process.send_signal(signal.SIGTERM)
            try:
                self.process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self.process = None


def _provider_payload(model_name: str) -> dict[str, object]:
    return {
        "llm_provider_mode": "lm_studio",
        "use_openai_review": False,
        "use_claude_final_review": False,
        "lm_studio_base_url": LM_STUDIO_BASE_URL,
        "lm_studio_small_model": model_name,
        "lm_studio_writer_model": model_name,
        "lm_studio_mid_model": model_name,
    }


def _assert_ok(response: httpx.Response, context: str) -> dict:
    if response.status_code >= 400:
        raise AuditFailure(f"{context} failed: HTTP {response.status_code} {response.text[:500]}")
    try:
        return response.json()
    except Exception as exc:
        raise AuditFailure(f"{context} did not return JSON: {response.text[:500]}") from exc


def _validate_saved_fact_sheet(expected: ExpectedProfile, fact_sheet: dict) -> list[str]:
    errors: list[str] = []
    person = dict(fact_sheet.get("person") or {})
    contact = dict(person.get("contact") or {})
    if person.get("full_name") != expected.full_name:
        errors.append(f"full_name mismatch: expected '{expected.full_name}', got '{person.get('full_name')}'")
    if contact.get("email") != expected.email:
        errors.append(f"email mismatch: expected '{expected.email}', got '{contact.get('email')}'")

    match_profile = dict(fact_sheet.get("match_profile") or {})
    target_roles = [str(item).strip() for item in match_profile.get("target_roles") or [] if str(item).strip()]
    if expected.target_role not in target_roles:
        errors.append(f"target role missing from saved fact sheet: {target_roles}")

    saved_countries = [
        str(item).strip()
        for item in dict(match_profile.get("location_preferences") or {}).get("preferred_countries") or []
        if str(item).strip()
    ]
    missing_countries = [country for country in expected.preferred_countries if country not in saved_countries]
    if missing_countries:
        errors.append(f"preferred countries missing: {missing_countries} from {saved_countries}")

    saved_languages = {
        str(item.get("name") or "").strip(): str(item.get("level") or "").strip() or None
        for item in fact_sheet.get("languages") or []
        if isinstance(item, dict) and str(item.get("name") or "").strip()
    }
    for language in expected.languages:
        if language["name"] not in saved_languages:
            errors.append(f"language missing: {language['name']}")

    education_rows = [item for item in fact_sheet.get("education") or [] if isinstance(item, dict)]
    expected_degree_lower = expected.degree.casefold()
    degree_ok = False
    for item in education_rows:
        degree_text = str(item.get("degree") or "").strip()
        field_text = str(item.get("field") or "").strip()
        institution_text = str(item.get("institution") or "").strip()
        combined = " ".join(part for part in (degree_text, field_text) if part).strip().casefold()
        if institution_text != expected.institution:
            continue
        if expected_degree_lower == degree_text.casefold() or expected_degree_lower == combined:
            degree_ok = True
            break
    if not degree_ok:
        errors.append("education row missing expected degree/institution")

    proof_haystack = " ".join(
        _flatten_strings(fact_sheet.get("experience"))
        + _flatten_strings(fact_sheet.get("projects"))
        + _flatten_strings(fact_sheet.get("evidence_index"))
    ).casefold()
    if expected.proof_summary.casefold() not in proof_haystack:
        errors.append("proof summary not preserved in saved fact sheet")

    saved_skill_terms = {
        skill.casefold()
        for bucket in dict(fact_sheet.get("skills") or {}).values()
        if isinstance(bucket, list)
        for skill in bucket
        if str(skill).strip()
    }
    missing_skills = [skill for skill in expected.skills if skill.casefold() not in saved_skill_terms]
    if missing_skills:
        errors.append(f"skills missing from saved fact sheet: {missing_skills}")

    return errors


def _run_single_profile(expected: ExpectedProfile, python_bin: str, model_name: str) -> dict[str, object]:
    runtime_dir = AUDIT_ROOT / expected.slug
    log_path = LOG_ROOT / f"{expected.slug}.server.log"
    if runtime_dir.exists():
        shutil.rmtree(runtime_dir)
    runtime = AppRuntime(runtime_dir, log_path, python_bin)
    runtime.start()

    base_url = f"http://{HOST}:{PORT}"
    try:
        with httpx.Client(base_url=base_url, timeout=REQUEST_TIMEOUT) as client:
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

            settings_payload = _provider_payload(model_name)
            _assert_ok(client.post("/settings/save", json=settings_payload), f"{expected.slug} save provider settings")

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
            if intake.get("status") not in {"questions_needed", "complete"}:
                raise AuditFailure(f"{expected.slug} unexpected intake start payload: {intake}")

            intake_rounds = 1
            while intake.get("status") == "questions_needed" and intake_rounds <= MAX_INTAKE_ROUNDS:
                questions = list(intake.get("questions") or [])
                if not questions:
                    raise AuditFailure(f"{expected.slug} asked for questions but returned none")
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
                    f"{expected.slug} answer intake round {intake_rounds}",
                )
                intake_rounds += 1

            if intake.get("status") != "complete":
                raise AuditFailure(f"{expected.slug} intake never completed: {intake}")

            recommendations = _assert_ok(
                client.get("/search/preferences/recommendations", params={"candidate_id": candidate_id}),
                f"{expected.slug} search recommendations",
            )
            suggested_roles = [str(item).strip() for item in recommendations.get("suggested_roles") or [] if str(item).strip()]
            if expected.target_role not in suggested_roles:
                raise AuditFailure(
                    f"{expected.slug} recommendations did not include expected target role '{expected.target_role}': {suggested_roles}"
                )

            _assert_ok(
                client.post(
                    "/settings/save",
                    json={
                        "jobspy_discover_queries": [expected.target_role],
                        "job_search_countries": expected.preferred_countries,
                        "jobspy_discover_location": expected.preferred_countries[0] if expected.preferred_countries else "Italy",
                        "target_job_seniority": expected.seniority or "any",
                    },
                ),
                f"{expected.slug} save search focus",
            )

            setup = _assert_ok(client.get("/setup/status"), f"{expected.slug} setup status")
            if not setup.get("complete"):
                raise AuditFailure(f"{expected.slug} setup did not complete: {setup}")

            current_settings = _assert_ok(client.get("/settings/current"), f"{expected.slug} settings current")
            if current_settings.get("llm_provider_mode") != "lm_studio":
                raise AuditFailure(f"{expected.slug} provider mode not persisted: {current_settings.get('llm_provider_mode')}")

            fact_sheet = _assert_ok(
                client.get(f"/candidates/{candidate_id}/fact-sheet-json"),
                f"{expected.slug} fact sheet export",
            )
            validation_errors = _validate_saved_fact_sheet(expected, fact_sheet)
            if validation_errors:
                raise AuditFailure(f"{expected.slug} saved fact sheet invalid: {'; '.join(validation_errors)}")

        runtime.stop()
        runtime.start()
        with httpx.Client(base_url=base_url, timeout=REQUEST_TIMEOUT) as client:
            reloaded_setup = _assert_ok(client.get("/setup/status"), f"{expected.slug} setup status after restart")
            if not reloaded_setup.get("complete"):
                raise AuditFailure(f"{expected.slug} setup was not persistent after restart: {reloaded_setup}")
            reloaded_candidates = _assert_ok(client.get("/candidates"), f"{expected.slug} candidates after restart")
            if len(reloaded_candidates) != 1:
                raise AuditFailure(f"{expected.slug} expected exactly one persisted candidate after restart: {reloaded_candidates}")
            reloaded_candidate = reloaded_candidates[0]
            if reloaded_candidate.get("full_name") != expected.full_name:
                raise AuditFailure(f"{expected.slug} persisted candidate name mismatch after restart")

            candidate_id = str(reloaded_candidate.get("id") or "")
            reloaded_intake = _assert_ok(
                client.get(f"/candidates/{candidate_id}/intake/status"),
                f"{expected.slug} intake status after restart",
            )
            if reloaded_intake.get("status") != "complete":
                raise AuditFailure(f"{expected.slug} intake reopened instead of resuming complete state: {reloaded_intake}")

            reloaded_fact_sheet = _assert_ok(
                client.get(f"/candidates/{candidate_id}/fact-sheet-json"),
                f"{expected.slug} fact sheet after restart",
            )
            validation_errors = _validate_saved_fact_sheet(expected, reloaded_fact_sheet)
            if validation_errors:
                raise AuditFailure(
                    f"{expected.slug} reloaded fact sheet invalid: {'; '.join(validation_errors)}"
                )

        return {
            "slug": expected.slug,
            "candidate_id": candidate_id,
            "log_path": str(log_path),
            "runtime_dir": str(runtime_dir),
        }
    finally:
        runtime.stop()


def main(argv: list[str]) -> int:
    profiles = _discover_profiles()
    if not profiles:
        print("No synthetic user profiles were found.", file=sys.stderr)
        return 1

    selected = profiles
    requested_slugs = {item.strip() for item in argv[1:] if item.strip()}
    if requested_slugs:
        selected = [profile for profile in profiles if profile.slug in requested_slugs]
        missing = sorted(requested_slugs - {profile.slug for profile in selected})
        if missing:
            print(f"Unknown profile slugs: {', '.join(missing)}", file=sys.stderr)
            return 1

    AUDIT_ROOT.mkdir(parents=True, exist_ok=True)
    LOG_ROOT.mkdir(parents=True, exist_ok=True)

    with httpx.Client(timeout=15.0) as client:
        model_response = client.get(f"{LM_STUDIO_BASE_URL}/models")
        model_payload = _assert_ok(model_response, "LM Studio models")
        model_names = [str(item.get("id") or "").strip() for item in model_payload.get("data") or [] if str(item.get("id") or "").strip()]
    model_name = _select_chat_model(model_names)
    python_bin = os.environ.get("PYTHON_BIN") or sys.executable

    results: list[dict[str, object]] = []
    failures: list[str] = []
    start_time = time.time()
    for profile in selected:
        print(f"[audit] onboarding {profile.slug} on port {PORT} using model {model_name}", flush=True)
        try:
            result = _run_single_profile(profile, python_bin=python_bin, model_name=model_name)
            results.append(result)
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
