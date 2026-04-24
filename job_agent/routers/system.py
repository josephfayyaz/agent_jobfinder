"""System, configuration, workspace, and top-level UI routes."""

from __future__ import annotations

from pathlib import Path

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from job_agent.config import reload_settings_from_sources, settings
from job_agent.db import get_db
from job_agent.llm import LLMRouter
from job_agent.services.workspace import (
    DELETE_CONFIRMATION_PHRASE,
    RESET_CONFIRMATION_PHRASE,
    SHARE_REPOSITORY_URL,
    build_workspace_backup,
    open_backups_folder,
    workspace_status,
    wipe_workspace,
)
from job_agent.search_preferences import (
    LANGUAGE_OPTIONS,
    LEVEL_OPTIONS,
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


def _lm_studio_models_data(base_url: str | None = None) -> dict[str, object]:
    target_url = (base_url or settings.lm_studio_base_url).rstrip("/")
    try:
        response = httpx.get(f"{target_url}/models", timeout=3)
        if response.is_success:
            data = response.json()
            models = [item["id"] for item in data.get("data", []) if isinstance(item, dict) and item.get("id")]
            return {"models": models, "online": True}
    except Exception:
        pass
    return {"models": [], "online": False}


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


@router.get("/lm-studio/models")
def lm_studio_models(base_url: str | None = None) -> dict[str, object]:
    return _lm_studio_models_data(base_url)


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
        if (field.endswith("api_key") or field == "gmail_app_password") and value:
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
    for key in ("openai_api_key", "anthropic_api_key", "gmail_app_password"):
        value = sanitized_updates.get(key)
        if isinstance(value, str) and not value.strip():
            sanitized_updates.pop(key)

    if "llm_provider_mode" in sanitized_updates:
        mode = str(sanitized_updates["llm_provider_mode"]).strip().lower()
        if mode not in {"openai", "anthropic", "local", "mixed"}:
            raise HTTPException(status_code=422, detail="llm_provider_mode must be openai, anthropic, local, or mixed.")
        sanitized_updates["llm_provider_mode"] = mode

    if "jobspy_discover_queries" in sanitized_updates:
        queries = normalize_role_list(sanitized_updates["jobspy_discover_queries"])
        if isinstance(queries, list) and len(queries) > 5:
            raise HTTPException(
                status_code=422,
                detail="Maximum 5 job discovery roles allowed. Remove some before adding more.",
            )
        sanitized_updates["jobspy_discover_queries"] = queries

    if "job_search_countries" in sanitized_updates:
        countries = normalize_country_list(sanitized_updates["job_search_countries"])
        if len(countries) > 5:
            raise HTTPException(
                status_code=422,
                detail="Maximum 5 target countries allowed. Remove some before adding more.",
            )
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

    write_user_settings(sanitized_updates)
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
    return {
        "configured": bool(settings.gmail_email and settings.gmail_app_password),
        "email": settings.gmail_email or None,
        "auto_sync": settings.gmail_auto_sync,
        "sync_interval_minutes": settings.gmail_sync_interval_minutes,
    }


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


@router.get("/ui/settings", include_in_schema=False)
def ui_settings(request: Request, db: Session = Depends(get_db)):
    from job_agent.user_config import EDITABLE_FIELDS, USER_SETTINGS_PATH, read_user_settings

    user_yml = read_user_settings()
    lm_models_payload = _lm_studio_models_data()
    workspace = workspace_status()
    current: dict[str, object] = {}
    for field in EDITABLE_FIELDS:
        value = getattr(settings, field, None)
        if (field.endswith("api_key") or field == "gmail_app_password") and value:
            current[field] = "***"
        else:
            current[field] = value

    provider_mode = getattr(settings, "llm_provider_mode", "openai").strip().lower() or "openai"
    search_recommendations = search_preference_recommendations(
        db,
        candidate_id=settings.default_candidate_id.strip() or None,
        current_roles=settings.jobspy_discover_queries,
        current_countries=settings.job_search_countries,
        current_languages=settings.job_search_languages,
    )

    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context=_ui_context(
            request,
            "Settings",
            current=current,
            lm_models=lm_models_payload["models"],
            lm_online=lm_models_payload["online"],
            openai_configured=bool(settings.openai_api_key),
            anthropic_configured=bool(settings.anthropic_api_key),
            candidate_id=settings.default_candidate_id,
            yaml_exists=USER_SETTINGS_PATH.exists(),
            provider_mode=provider_mode,
            user_yml=user_yml,
            gmail_configured=bool(settings.gmail_email and settings.gmail_app_password),
            gmail_email=settings.gmail_email or "",
            workspace=workspace,
            share_url=SHARE_REPOSITORY_URL,
            reset_phrase=RESET_CONFIRMATION_PHRASE,
            delete_phrase=DELETE_CONFIRMATION_PHRASE,
            language_options=LANGUAGE_OPTIONS,
            language_level_options=LEVEL_OPTIONS,
            search_recommendations=search_recommendations,
        ),
    )
