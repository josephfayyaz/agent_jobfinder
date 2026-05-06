"""System, configuration, workspace, and top-level UI routes."""

from __future__ import annotations

from pathlib import Path
import socket

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from job_agent.config import normalize_lm_studio_base_url, reload_settings_from_sources, settings
from job_agent.db import get_db
from job_agent.llm import LLMRouter
from job_agent.providers import normalize_provider_mode, provider_setup_status
from job_agent.services.workspace import (
    DELETE_CONFIRMATION_PHRASE,
    RESET_CONFIRMATION_PHRASE,
    SHARE_REPOSITORY_URL,
    build_workspace_backup,
    open_backups_folder,
    workspace_status,
    wipe_workspace,
)
from job_agent.secrets import SECRET_FIELDS
from job_agent.services.gmail_oauth import GmailOAuthService
from job_agent.services.tracker_integrity import TrackerIntegrityService
from job_agent.search_preferences import (
    LANGUAGE_OPTIONS,
    LEVEL_OPTIONS,
    MAX_DISCOVERY_ROLES,
    normalize_country_list,
    normalize_job_language_preferences,
    normalize_role_list,
    primary_search_country,
    search_preference_recommendations,
)

from job_agent.routers.job_views import _get_dashboard_data, _get_priority_jobs, _get_recent_jobs_with_scores
from job_agent.routers.setup_state import (
    _active_candidate_id,
    _onboarding_complete,
    _setup_gate_enabled,
    _setup_status_payload,
)
from job_agent.routers.templates import templates
from job_agent.routers.ui_context import _ui_context

router = APIRouter()

_PROVIDER_SECRET_FIELDS: dict[str, set[str]] = {
    "openai": {"openai_api_key"},
    "gemini": {"gemini_api_key"},
    "anthropic": {"anthropic_api_key"},
    "lm_studio": set(),
    "ollama": set(),
}
_PROVIDER_CONFIG_FIELDS: dict[str, set[str]] = {
    "openai": {"use_openai_review"},
    "gemini": set(),
    "anthropic": {"use_claude_final_review", "anthropic_model"},
    "lm_studio": {
        "lm_studio_base_url",
        "lm_studio_small_model",
        "lm_studio_writer_model",
        "lm_studio_mid_model",
    },
    "ollama": {
        "ollama_base_url",
        "ollama_fast_model",
        "ollama_writer_model",
    },
}


def _lm_studio_models_data(base_url: str | None = None) -> dict[str, object]:
    target_url = normalize_lm_studio_base_url(base_url or settings.lm_studio_base_url).rstrip("/")
    try:
        response = httpx.get(f"{target_url}/models", timeout=3)
        if response.is_success:
            data = response.json()
            models = [item["id"] for item in data.get("data", []) if isinstance(item, dict) and item.get("id")]
            return {"models": models, "online": True}
    except Exception:
        pass
    return {"models": [], "online": False}


def _ollama_models_data(base_url: str | None = None) -> dict[str, object]:
    target_url = (base_url or getattr(settings, "ollama_base_url", "http://localhost:11434")).rstrip("/")
    try:
        response = httpx.get(f"{target_url}/api/tags", timeout=3)
        if response.is_success:
            data = response.json()
            models = [
                item["name"]
                for item in data.get("models", [])
                if isinstance(item, dict) and item.get("name")
            ]
            return {"models": models, "online": True}
    except Exception:
        pass
    return {"models": [], "online": False}


def _probe_openai_compatible_chat(base_url: str, model: str) -> tuple[bool, str]:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 8,
        "temperature": 0,
    }
    try:
        response = httpx.post(
            f"{base_url.rstrip('/')}/chat/completions",
            json=payload,
            timeout=8,
        )
    except Exception as exc:
        return False, f"Could not reach the local provider chat endpoint: {exc}"

    if response.is_success:
        return True, "chat_ok"

    detail = ""
    try:
        detail = (response.text or "").strip()
    except Exception:
        detail = ""
    if response.status_code == 400:
        if "context" in detail.lower():
            return (
                False,
                "Model returned 400 (context issue). Increase context window in your local provider and retry.",
            )
        return (
            False,
            "Model returned 400 during probe. Ensure the selected chat model is loaded and supports OpenAI-compatible chat completions.",
        )
    return False, f"Model probe failed ({response.status_code}). {detail[:180]}".strip()


def _provider_mode_cleanup(mode: str) -> tuple[dict[str, object], set[str]]:
    inactive_modes = [name for name in _PROVIDER_CONFIG_FIELDS if name != mode]
    updates: dict[str, object] = {}
    clear_secrets: set[str] = set()

    for inactive in inactive_modes:
        clear_secrets.update(_PROVIDER_SECRET_FIELDS.get(inactive, set()))
        for field in _PROVIDER_CONFIG_FIELDS.get(inactive, set()):
            updates[field] = False if field.startswith("use_") else ""

    if mode != "openai":
        updates["use_openai_review"] = False
    if mode != "anthropic":
        updates["use_claude_final_review"] = False

    return updates, clear_secrets


@router.get("/health")
def health() -> dict:
    from job_agent.services.documents import check_pdflatex

    pdf_ok, pdf_path = check_pdflatex()
    db_url = settings.database_url or "sqlite"
    return {
        "status": "ok",
        "db_backend": "sqlite" if db_url.startswith("sqlite") else "postgresql",
        "pdflatex": {"available": pdf_ok, "path": pdf_path},
    }


@router.get("/providers")
def providers() -> dict:
    return LLMRouter().provider_status()


@router.get("/health/ai-status")
def health_ai_status() -> dict[str, object]:
    snapshot = provider_setup_status()
    return {
        "configured": snapshot["configured"],
        "ready": snapshot["ready"],
        "provider_mode": snapshot["mode"],
        "openai_ready": snapshot["openai_ready"],
        "gemini_ready": snapshot["gemini_ready"],
        "anthropic_ready": snapshot["anthropic_ready"],
        "lm_studio_ready": snapshot["lm_studio_ready"],
        "ollama_ready": snapshot["ollama_ready"],
    }


@router.get("/health/connectivity")
def health_connectivity() -> dict[str, bool]:
    try:
        socket.setdefaulttimeout(3.0)
        socket.getaddrinfo("example.com", 443)
        return {"online": True}
    except OSError:
        return {"online": False}


@router.get("/lm-studio/models")
def lm_studio_models(base_url: str | None = None) -> dict[str, object]:
    return _lm_studio_models_data(base_url)


@router.get("/ollama/models")
def ollama_models(base_url: str | None = None) -> dict[str, object]:
    return _ollama_models_data(base_url)


@router.post("/providers/validate")
def validate_provider(payload: dict = Body(...)) -> dict[str, object]:
    raw_mode = str(payload.get("provider_mode") or "openai").strip().lower()
    if raw_mode == "mixed":
        raise HTTPException(
            status_code=422,
            detail="provider_mode must be openai, gemini, anthropic, lm_studio, or ollama.",
        )
    if raw_mode not in {"openai", "gemini", "anthropic", "lm_studio", "ollama", "local"}:
        raise HTTPException(
            status_code=422,
            detail="provider_mode must be openai, gemini, anthropic, lm_studio, or ollama.",
        )
    mode = normalize_provider_mode(raw_mode)
    openai_key = str(payload.get("openai_api_key") or settings.openai_api_key or "")
    gemini_key = str(payload.get("gemini_api_key") or settings.gemini_api_key or "")
    anthropic_key = str(payload.get("anthropic_api_key") or settings.anthropic_api_key or "")
    lm_studio_base_url = normalize_lm_studio_base_url(
        payload.get("lm_studio_base_url") or settings.lm_studio_base_url or ""
    )
    ollama_base_url = str(payload.get("ollama_base_url") or getattr(settings, "ollama_base_url", "") or "")
    openai_model = str(payload.get("openai_review_model") or settings.openai_review_model or "gpt-4o-mini").strip() or "gpt-4o-mini"

    def _validate_openai(api_key: str, model: str) -> tuple[bool, str]:
        if not api_key.strip():
            return False, "Paste an OpenAI API key first."
        try:
            # Use a real (cheap) generation call so quota issues are caught here,
            # not silently later during intake.
            response = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key.strip()}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 1,
                },
                timeout=10,
            )
            if response.is_success:
                return True, f"OpenAI verified with {model}."
            if response.status_code in {401, 403}:
                return False, "OpenAI key is invalid or does not have access."
            if response.status_code == 429:
                return False, "OpenAI quota exceeded — add billing credit at platform.openai.com/settings/organization/billing, then try again."
            return False, f"OpenAI validation failed ({response.status_code})."
        except Exception as exc:
            return False, f"Could not reach OpenAI: {exc}"

    def _validate_anthropic(api_key: str) -> tuple[bool, str]:
        if not api_key.strip():
            return False, "Paste an Anthropic API key first."
        try:
            response = httpx.get(
                "https://api.anthropic.com/v1/models",
                headers={
                    "x-api-key": api_key.strip(),
                    "anthropic-version": "2023-06-01",
                },
                timeout=5,
            )
            if response.is_success:
                return True, "Anthropic key accepted."
            if response.status_code in {401, 403}:
                return False, "Anthropic key is invalid or does not have access."
            return False, f"Anthropic validation failed ({response.status_code})."
        except Exception as exc:
            return False, f"Could not reach Anthropic: {exc}"

    def _validate_gemini(api_key: str) -> tuple[bool, str]:
        if not api_key.strip():
            return False, "Paste a Gemini API key first."
        try:
            response = httpx.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent",
                headers={
                    "x-goog-api-key": api_key.strip(),
                    "Content-Type": "application/json",
                },
                json={
                    "contents": [{"parts": [{"text": "hi"}]}],
                    "generationConfig": {"temperature": 0, "maxOutputTokens": 1},
                },
                timeout=10,
            )
            if response.is_success:
                return True, f"Gemini verified with {settings.gemini_model}."
            if response.status_code in {400, 401, 403}:
                return False, "Gemini key is invalid or does not have access."
            if response.status_code == 429:
                return False, "Gemini quota exceeded or rate limited. Check your Google AI Studio billing or limits."
            return False, f"Gemini validation failed ({response.status_code})."
        except Exception as exc:
            return False, f"Could not reach Gemini: {exc}"

    if mode == "openai":
        ok, detail = _validate_openai(openai_key, openai_model)
        return {"ok": ok, "provider_mode": mode, "detail": detail}
    if mode == "gemini":
        ok, detail = _validate_gemini(gemini_key)
        return {"ok": ok, "provider_mode": mode, "detail": detail}
    if mode == "anthropic":
        ok, detail = _validate_anthropic(anthropic_key)
        return {"ok": ok, "provider_mode": mode, "detail": detail}
    if mode == "ollama":
        data = _ollama_models_data(ollama_base_url.strip() or None)
        ok = bool(data["online"] and data["models"])
        detail = "Ollama is not reachable." if not data["online"] else "Ollama is reachable but no models were found."
        if ok:
            if settings.app_env.strip().lower() == "test":
                return {
                    "ok": True,
                    "provider_mode": mode,
                    "detail": f"Ollama online — {len(data['models'])} models found.",
                    "models": data["models"],
                }
            usable_models = [name for name in data["models"] if "embed" not in str(name).lower()]
            probe_model = usable_models[0] if usable_models else data["models"][0]
            probe_ok, probe_detail = _probe_openai_compatible_chat(f"{ollama_base_url.rstrip('/')}/v1", probe_model)
            ok = probe_ok
            detail = (
                f"Ollama online — {len(data['models'])} models found. Probe passed with '{probe_model}'."
                if probe_ok
                else f"Ollama online, but model probe failed for '{probe_model}'. {probe_detail}"
            )
        return {
            "ok": ok,
            "provider_mode": mode,
            "detail": detail,
            "models": data["models"],
        }
    if mode == "lm_studio":
        data = _lm_studio_models_data(lm_studio_base_url.strip() or None)
        ok = bool(data["online"] and data["models"])
        detail = "LM Studio is not reachable." if not data["online"] else "LM Studio is reachable but no models were found."
        if ok:
            if settings.app_env.strip().lower() == "test":
                return {
                    "ok": True,
                    "provider_mode": mode,
                    "detail": f"LM Studio online — {len(data['models'])} models found.",
                    "models": data["models"],
                }
            usable_models = [name for name in data["models"] if "embed" not in str(name).lower()]
            probe_model = usable_models[0] if usable_models else data["models"][0]
            probe_ok, probe_detail = _probe_openai_compatible_chat(lm_studio_base_url, probe_model)
            ok = probe_ok
            detail = (
                f"LM Studio online — {len(data['models'])} models found. Probe passed with '{probe_model}'."
                if probe_ok
                else f"LM Studio online, but model probe failed for '{probe_model}'. {probe_detail}"
            )
        return {
            "ok": ok,
            "provider_mode": mode,
            "detail": detail,
            "models": data["models"],
        }

    raise HTTPException(
        status_code=422,
        detail="provider_mode must be openai, gemini, anthropic, lm_studio, or ollama.",
    )


@router.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db)) -> dict[str, object]:
    return _get_dashboard_data(db)


@router.get("/setup/status")
def setup_status(db: Session = Depends(get_db)) -> dict[str, object]:
    return _setup_status_payload(db)


@router.get("/onboarding/status")
def onboarding_status(db: Session = Depends(get_db)) -> dict[str, object]:
    setup = _setup_status_payload(db)
    return {
        "configured": _onboarding_complete(),
        "candidate_id_set": bool(settings.default_candidate_id.strip()),
        "setup_complete": setup["complete"],
        "missing_steps": setup["missing_steps"],
    }


@router.get("/search/preferences/recommendations")
def search_preferences_endpoint(
    candidate_id: str | None = None,
    roles: str | None = None,
    countries: str | None = None,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    active_candidate_id = candidate_id or _active_candidate_id(db) or settings.default_candidate_id.strip() or None
    recommendations = search_preference_recommendations(
        db,
        candidate_id=active_candidate_id,
        current_roles=roles or None,
        current_countries=countries or None,
        current_languages=settings.job_search_languages,
    )
    recommendations["selected_languages"] = normalize_job_language_preferences(
        recommendations.get("selected_languages")
    )
    recommendations["countries"] = normalize_country_list(recommendations.get("countries"))
    recommendations["suggested_roles"] = normalize_role_list(recommendations.get("suggested_roles"))
    recommendations["language_options"] = LANGUAGE_OPTIONS
    recommendations["level_options"] = LEVEL_OPTIONS
    return recommendations


@router.get("/settings/current")
def settings_current() -> dict[str, object]:
    from job_agent.user_config import EDITABLE_FIELDS, USER_SETTINGS_PATH

    data: dict[str, object] = {}
    for field in EDITABLE_FIELDS:
        value = getattr(settings, field, None)
        if field in SECRET_FIELDS and value:
            data[field] = "***"
        else:
            data[field] = value
    data["_yaml_exists"] = USER_SETTINGS_PATH.exists()
    data["default_candidate_id"] = settings.default_candidate_id
    return data


@router.post("/settings/save")
def settings_save(updates: dict) -> dict[str, object]:
    from job_agent.config import settings as settings_singleton
    from job_agent.user_config import EDITABLE_FIELDS, USER_SETTINGS_PATH, write_user_settings

    invalid = [key for key in updates if key not in EDITABLE_FIELDS]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Unknown fields: {invalid}")

    sanitized_updates = dict(updates)
    clear_secrets: set[str] = set()
    for key in SECRET_FIELDS:
        value = sanitized_updates.get(key)
        if isinstance(value, str) and not value.strip():
            sanitized_updates.pop(key)

    if "llm_provider_mode" in sanitized_updates:
        raw_mode = str(sanitized_updates["llm_provider_mode"]).strip().lower()
        if raw_mode == "mixed":
            raise HTTPException(
                status_code=422,
                detail="llm_provider_mode must be openai, gemini, anthropic, lm_studio, or ollama.",
            )
        if raw_mode not in {"openai", "gemini", "anthropic", "lm_studio", "ollama", "local"}:
            raise HTTPException(
                status_code=422,
                detail="llm_provider_mode must be openai, gemini, anthropic, lm_studio, or ollama.",
            )
        mode = normalize_provider_mode(raw_mode)
        if mode not in {"openai", "gemini", "anthropic", "lm_studio", "ollama"}:
            raise HTTPException(
                status_code=422,
                detail="llm_provider_mode must be openai, gemini, anthropic, lm_studio, or ollama.",
            )
        sanitized_updates["llm_provider_mode"] = mode
        cleanup_updates, clear_secrets = _provider_mode_cleanup(mode)
        for key, value in cleanup_updates.items():
            sanitized_updates.setdefault(key, value)

    if "lm_studio_base_url" in sanitized_updates and str(sanitized_updates["lm_studio_base_url"] or "").strip():
        sanitized_updates["lm_studio_base_url"] = normalize_lm_studio_base_url(
            sanitized_updates["lm_studio_base_url"]
        )

    if "jobspy_discover_queries" in sanitized_updates:
        queries = normalize_role_list(sanitized_updates["jobspy_discover_queries"])
        if isinstance(queries, list) and len(queries) > MAX_DISCOVERY_ROLES:
            raise HTTPException(
                status_code=422,
                detail=f"Maximum {MAX_DISCOVERY_ROLES} job discovery roles allowed. Remove some before adding more.",
            )
        sanitized_updates["jobspy_discover_queries"] = queries

    if "job_search_countries" in sanitized_updates:
        countries = normalize_country_list(sanitized_updates["job_search_countries"])
        sanitized_updates["job_search_countries"] = countries
        sanitized_updates["jobspy_discover_location"] = primary_search_country(
            countries,
            str(sanitized_updates.get("jobspy_discover_location") or settings.jobspy_discover_location or "Italy"),
        )

    if "job_search_languages" in sanitized_updates:
        languages = normalize_job_language_preferences(sanitized_updates["job_search_languages"])
        if len(languages) > 6:
            raise HTTPException(
                status_code=422,
                detail="Maximum 6 job languages allowed. Remove some before adding more.",
            )
        sanitized_updates["job_search_languages"] = [
            {"name": item["name"], "level": item["level"]}
            for item in languages
        ]

    write_user_settings(sanitized_updates, clear_secrets=clear_secrets)
    reload_settings_from_sources(settings_singleton, path=USER_SETTINGS_PATH)
    return {"status": "saved", "fields_updated": list(sanitized_updates.keys())}


@router.post("/settings/reload")
def settings_reload() -> dict[str, str]:
    from job_agent.config import settings as settings_singleton
    from job_agent.user_config import USER_SETTINGS_PATH

    reload_settings_from_sources(settings_singleton, path=USER_SETTINGS_PATH)
    return {"status": "reloaded"}


@router.post("/gmail/test-connection")
def test_gmail_connection(email: str, app_password: str) -> dict[str, object]:
    import imaplib

    try:
        conn = imaplib.IMAP4_SSL("imap.gmail.com")
        conn.login(email.strip(), app_password.strip())
        conn.logout()
        return {"ok": True, "error": None}
    except imaplib.IMAP4.error as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "error": f"Connection failed: {exc}"}


@router.get("/gmail/status")
def gmail_status() -> dict[str, object]:
    oauth_status = GmailOAuthService(settings).status()
    legacy_configured = bool(settings.gmail_email and settings.gmail_app_password)
    mode = "oauth" if oauth_status["connected"] else ("legacy" if legacy_configured else "none")
    return {
        "configured": bool(oauth_status["connected"] or legacy_configured),
        "oauth_connected": bool(oauth_status["connected"]),
        "mode": mode,
        "email": str(oauth_status["email"] or settings.gmail_email or ""),
        "expires_at": oauth_status["expires_at"],
        "has_client_credentials": oauth_status["has_client_credentials"],
        "auto_sync": settings.gmail_auto_sync,
        "sync_interval_minutes": settings.gmail_sync_interval_minutes,
    }


@router.post("/gmail/oauth/start")
def gmail_oauth_start(request: Request) -> dict[str, object]:
    service = GmailOAuthService(settings)
    try:
        payload = service.start(str(request.base_url).rstrip("/"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, **payload}


@router.get("/gmail/oauth/callback")
def gmail_oauth_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    if error:
        return RedirectResponse(url=f"/ui/settings?gmail_oauth=error&detail={error}#gmail", status_code=302)
    if not code or not state:
        raise HTTPException(status_code=422, detail="Missing OAuth code/state in callback.")
    service = GmailOAuthService(settings)
    try:
        service.complete_callback(code=code, state=state, base_url=str(request.base_url).rstrip("/"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return RedirectResponse(url="/ui/settings?gmail_oauth=connected#gmail", status_code=302)


@router.post("/gmail/oauth/disconnect")
def gmail_oauth_disconnect() -> dict[str, object]:
    service = GmailOAuthService(settings)
    service.disconnect()
    return {"ok": True, "connected": False}


@router.get("/workspace/status")
def workspace_runtime_status() -> dict[str, object]:
    return workspace_status()


@router.get("/workspace/download", include_in_schema=False)
def workspace_download() -> FileResponse:
    bundle_path = build_workspace_backup()
    return FileResponse(
        bundle_path,
        media_type="application/zip",
        filename=bundle_path.name,
    )


@router.post("/workspace/backups/open")
def workspace_backups_open() -> dict[str, object]:
    try:
        path = open_backups_folder()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"status": "opened", "path": str(path)}


@router.post("/workspace/reset")
def workspace_reset(body: dict = Body(...), db: Session = Depends(get_db)) -> dict[str, object]:
    phrase = str(body.get("phrase") or "").strip()
    if phrase != RESET_CONFIRMATION_PHRASE:
        raise HTTPException(status_code=422, detail=f"Type '{RESET_CONFIRMATION_PHRASE}' to reset the workspace.")
    result = wipe_workspace(db, delete_downloads=False)
    reload_settings_from_sources(settings)
    return {"status": "reset", **result}


@router.post("/workspace/delete")
def workspace_delete(body: dict = Body(...), db: Session = Depends(get_db)) -> dict[str, object]:
    phrase = str(body.get("phrase") or "").strip()
    if phrase != DELETE_CONFIRMATION_PHRASE:
        raise HTTPException(status_code=422, detail=f"Type '{DELETE_CONFIRMATION_PHRASE}' to delete all local data.")
    result = wipe_workspace(db, delete_downloads=True)
    reload_settings_from_sources(settings)
    return {"status": "deleted", **result}


@router.get("/exports/csv/download", include_in_schema=False)
def download_csv(db: Session = Depends(get_db)):
    from job_agent.services.exporters import CsvExportService

    export = CsvExportService(db).export_jobs_snapshot()
    csv_path = Path(export.file_path)
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail="CSV file not found.")
    return FileResponse(csv_path, media_type="text/csv", filename=csv_path.name)


@router.get("/system/integrity")
def system_integrity(request: Request, db: Session = Depends(get_db)):
    payload = TrackerIntegrityService(db).evaluate()
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            request=request,
            name="partials/integrity_status.html",
            context={"integrity": payload},
        )
    return payload


@router.post("/system/integrity/repair")
def system_integrity_repair(request: Request, db: Session = Depends(get_db)):
    payload = TrackerIntegrityService(db).repair_safe_issues()
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            request=request,
            name="partials/integrity_status.html",
            context={"integrity": payload},
            headers={"X-Toast-Success": "Safe tracker repairs applied"},
        )
    return payload


# ── UI pages ───────────────────────────────────────────────────────────────────

@router.get("/ui", include_in_schema=False)
def ui_dashboard(request: Request, db: Session = Depends(get_db)):
    if _setup_gate_enabled():
        setup = _setup_status_payload(db)
        if not setup["complete"]:
            return templates.TemplateResponse(
                request=request,
                name="setup_required.html",
                context=_ui_context(request, "Setup Required", setup=setup, next_url="/ui"),
            )
    dash = _get_dashboard_data(db)
    stat_cards = [
        {"label": "New Jobs (24h)", "value": dash["jobs"]["new_24h"], "color": "text-blue-600"},
        {"label": "High Match", "value": dash["jobs"]["high_match"], "color": "text-green-600"},
        {"label": "Pending Approvals", "value": dash["cv"]["pending_approvals"], "color": "text-yellow-600"},
        {
            "label": "Active Applications",
            "value": sum(dash["applications"].values()),
            "color": "text-indigo-600",
        },
    ]
    priority_jobs = _get_priority_jobs(db)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=_ui_context(
            request,
            "Dashboard",
            stat_cards=stat_cards,
            recent_jobs=_get_recent_jobs_with_scores(db, limit=8),
            priority_jobs=priority_jobs,
            system=dash["system"],
            config=dash["config"],
        ),
    )


@router.get("/ui/setup-required", include_in_schema=False)
def ui_setup_required(request: Request, next: str = "/ui", db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request=request,
        name="setup_required.html",
        context=_ui_context(
            request,
            "Setup Required",
            setup=_setup_status_payload(db),
            next_url=next,
        ),
    )


@router.get("/ui/workspace-reset", include_in_schema=False)
def ui_workspace_reset(
    request: Request,
    mode: str = "reset",
    open: int = 0,
):
    mode_value = "delete" if mode == "delete" else "reset"
    workspace = workspace_status()
    return templates.TemplateResponse(
        request=request,
        name="workspace_reset.html",
        context=_ui_context(
            request,
            "Workspace Reset",
            mode=mode_value,
            auto_open_backups=bool(open and mode_value == "reset"),
            backups_dir=workspace["backups_dir"],
            backup_count=workspace["backup_count"],
        ),
    )


@router.get("/ui/help", include_in_schema=False)
def ui_help(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request=request,
        name="help.html",
        context=_ui_context(request, "Help", setup=_setup_status_payload(db)),
    )


@router.get("/ui/about", include_in_schema=False)
def ui_about(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="about.html",
        context=_ui_context(request, "About"),
    )


@router.get("/ui/settings", include_in_schema=False)
def ui_settings(request: Request, db: Session = Depends(get_db)):
    from job_agent.user_config import EDITABLE_FIELDS, USER_SETTINGS_PATH, read_user_settings

    user_yml = read_user_settings()
    lm_models_payload = _lm_studio_models_data()
    workspace = workspace_status()
    current: dict[str, object] = {}
    for field in EDITABLE_FIELDS:
        value = getattr(settings, field, None)
        if field in SECRET_FIELDS and value:
            current[field] = "***"
        else:
            current[field] = value

    provider_mode = normalize_provider_mode(getattr(settings, "llm_provider_mode", "openai"))
    ollama_models_payload = _ollama_models_data()
    search_recommendations = search_preference_recommendations(
        db,
        candidate_id=settings.default_candidate_id.strip() or None,
        current_roles=settings.jobspy_discover_queries,
        current_countries=settings.job_search_countries,
        current_languages=settings.job_search_languages,
    )
    gmail_oauth = GmailOAuthService(settings)
    gmail_state = gmail_oauth.status()
    legacy_gmail_configured = bool(settings.gmail_email and settings.gmail_app_password)

    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context=_ui_context(
            request,
            "Settings",
            current=current,
            lm_models=lm_models_payload["models"],
            lm_online=lm_models_payload["online"],
            ollama_models=ollama_models_payload["models"],
            ollama_online=ollama_models_payload["online"],
            openai_configured=bool(settings.openai_api_key),
            gemini_configured=bool(settings.gemini_api_key),
            anthropic_configured=bool(settings.anthropic_api_key),
            candidate_id=settings.default_candidate_id,
            yaml_exists=USER_SETTINGS_PATH.exists(),
            provider_mode=provider_mode,
            user_yml=user_yml,
            gmail_configured=bool(gmail_state["connected"] or legacy_gmail_configured),
            gmail_oauth_connected=bool(gmail_state["connected"]),
            gmail_oauth_email=str(gmail_state["email"] or ""),
            gmail_oauth_expires_at=gmail_state["expires_at"],
            gmail_has_client_credentials=bool(gmail_state["has_client_credentials"]),
            gmail_legacy_configured=legacy_gmail_configured,
            gmail_oauth_redirect_uri=gmail_oauth.redirect_uri(str(request.base_url)),
            workspace=workspace,
            share_url=SHARE_REPOSITORY_URL,
            reset_phrase=RESET_CONFIRMATION_PHRASE,
            delete_phrase=DELETE_CONFIRMATION_PHRASE,
            language_options=LANGUAGE_OPTIONS,
            language_level_options=LEVEL_OPTIONS,
            search_recommendations=search_recommendations,
        ),
    )
