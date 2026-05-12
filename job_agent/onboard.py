from __future__ import annotations

import json
import re
import socket
from pathlib import Path
from typing import Any

import click
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from job_agent.config import normalize_lm_studio_base_url, reload_settings_from_sources, settings
from job_agent.search_preferences import normalize_country_list, normalize_job_language_preferences
from job_agent.user_config import USER_SETTINGS_PATH, read_user_settings, write_user_settings

load_user_settings_overlay = reload_settings_from_sources

try:
    import questionary
except ImportError:  # pragma: no cover - fallback path for minimal environments
    questionary = None


console = Console()
API_BASE_URL = "http://localhost:8000"
DEFAULT_LM_STUDIO_BASE = "http://localhost:1234/v1"


def _prompt_text(message: str, *, default: str = "", non_interactive: bool = False) -> str:
    if non_interactive:
        return default
    if questionary is not None:
        answer = questionary.text(message, default=default).ask()
        if answer is None:
            raise click.Abort()
        return str(answer).strip()
    return str(click.prompt(message, default=default, show_default=bool(default))).strip()


def _prompt_password(message: str, *, non_interactive: bool = False) -> str:
    if non_interactive:
        return ""
    if questionary is not None:
        answer = questionary.password(message).ask()
        if answer is None:
            raise click.Abort()
        return str(answer).strip()
    return str(click.prompt(message, hide_input=True, default="", show_default=False)).strip()


def _prompt_confirm(
    message: str,
    *,
    default: bool = True,
    non_interactive: bool = False,
) -> bool:
    if non_interactive:
        return default
    if questionary is not None:
        answer = questionary.confirm(message, default=default).ask()
        if answer is None:
            raise click.Abort()
        return bool(answer)
    return bool(click.confirm(message, default=default))


def _prompt_select(
    message: str,
    choices: list[str],
    *,
    default: str,
    non_interactive: bool = False,
) -> str:
    if non_interactive:
        return default
    if questionary is not None:
        answer = questionary.select(message, choices=choices, default=default).ask()
        if answer is None:
            raise click.Abort()
        return str(answer)
    return str(click.prompt(message, type=click.Choice(choices), default=default))


def _prompt_int_range(
    message: str,
    *,
    min_value: int,
    max_value: int,
    default: int,
    non_interactive: bool = False,
) -> int:
    if non_interactive:
        return default
    while True:
        value_text = _prompt_text(message, default=str(default))
        try:
            value = int(value_text)
        except ValueError:
            console.print("[red]Please enter a valid integer.[/red]")
            continue
        if min_value <= value <= max_value:
            return value
        console.print(f"[red]Value must be between {min_value} and {max_value}.[/red]")


def _is_port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1.0)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def _fetch_lm_studio_models(base_url: str) -> tuple[bool, list[str]]:
    try:
        response = httpx.get(f"{normalize_lm_studio_base_url(base_url).rstrip('/')}/models", timeout=3)
        if response.status_code != 200:
            return False, []
        payload = response.json()
    except (httpx.RequestError, ValueError):
        return False, []

    data = payload.get("data", []) if isinstance(payload, dict) else []
    model_ids = [
        str(item.get("id", "")).strip()
        for item in data
        if isinstance(item, dict) and str(item.get("id", "")).strip()
    ]
    return True, model_ids


def _render_prereq_table(
    *,
    sqlite_path: str,
    port_free: bool,
    lm_ok: bool,
) -> None:
    table = Table(title="Step 1 — Prerequisites Check")
    table.add_column("Check", style="bold")
    table.add_column("Command")
    table.add_column("Status")

    table.add_row(
        "SQLite database",
        sqlite_path,
        "[green]PASS[/green]",
    )
    table.add_row(
        "Port 8000 free",
        "TCP connect localhost:8000",
        "[green]PASS[/green]" if port_free else "[yellow]WARN[/yellow]",
    )
    table.add_row(
        "LM Studio",
        "GET http://localhost:1234/v1/models",
        "[green]PASS[/green]" if lm_ok else "[yellow]WARN[/yellow]",
    )
    console.print(table)


def _sqlite_path_label() -> str:
    from job_agent.db import _default_db_url

    db_url = settings.database_url or _default_db_url()
    if db_url.startswith("sqlite:///"):
        return db_url.removeprefix("sqlite:///")
    return db_url


def _run_prerequisites_check(lm_studio_base_url: str) -> tuple[bool, list[str]]:
    port_free = _is_port_free(8000)
    lm_ok, models = _fetch_lm_studio_models(lm_studio_base_url)

    _render_prereq_table(sqlite_path=_sqlite_path_label(), port_free=port_free, lm_ok=lm_ok)

    if not port_free:
        console.print("[yellow]Port 8000 is already in use. Continuing (API may already be running).[/yellow]")
    if not lm_ok:
        console.print("[yellow]LM Studio is not reachable. You can continue with cloud-only settings.[/yellow]")
    return True, models


def _choose_model_name(
    label: str,
    *,
    models: list[str],
    default: str,
    non_interactive: bool,
) -> str:
    selected_default = default or (models[0] if models else "")
    if non_interactive:
        return selected_default
    if models:
        console.print(f"[dim]{label} options:[/dim] {', '.join(models)}")
        selection = _prompt_select(
            f"{label}:",
            choices=models + ["Type manually"],
            default=selected_default if selected_default in models else models[0],
        )
        if selection != "Type manually":
            return selection
    return _prompt_text(f"{label} (type model name):", default=selected_default)


def _server_is_running() -> bool:
    try:
        response = httpx.get(f"{API_BASE_URL}/health", timeout=2)
    except httpx.RequestError:
        return False
    return response.is_success


def _validate_fact_sheet_path(raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if not path.exists():
        raise ValueError(f"File not found: {path}")
    suffix = path.suffix.lower()
    if suffix == ".json":
        json.loads(path.read_text(encoding="utf-8"))
        return path
    if suffix == ".txt":
        if not path.read_text(encoding="utf-8").strip():
            raise ValueError("TXT fact sheet is empty.")
        return path
    raise ValueError("Only .json or .txt fact sheets are supported.")


def _candidate_name_from_json_payload(payload: dict[str, Any], path: Path) -> str:
    person = payload.get("person")
    if isinstance(person, dict):
        full_name = str(person.get("full_name") or "").strip()
        if full_name:
            return full_name
    return path.stem.replace("_", " ").replace("-", " ").title() or "Candidate"


def _ingest_fact_sheet(path: Path) -> str | None:
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        create_response = httpx.post(
            f"{API_BASE_URL}/candidates",
            json={"full_name": _candidate_name_from_json_payload(payload, path)},
            timeout=10,
        )
        create_response.raise_for_status()
        candidate_id = str(create_response.json()["id"])

        ingest_response = httpx.post(
            f"{API_BASE_URL}/candidates/{candidate_id}/fact-sheet-json",
            json=payload,
            timeout=30,
        )
        ingest_response.raise_for_status()
        return candidate_id

    ingest_response = httpx.post(
        f"{API_BASE_URL}/fact-sources/ingest",
        json={"path": str(path)},
        timeout=20,
    )
    ingest_response.raise_for_status()
    return settings.default_candidate_id.strip() or None


def _write_default_candidate_id(candidate_id: str, env_path: Path = Path(".env")) -> None:
    content = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    if "DEFAULT_CANDIDATE_ID" in content:
        content = re.sub(
            r"DEFAULT_CANDIDATE_ID=.*",
            f"DEFAULT_CANDIDATE_ID={candidate_id}",
            content,
        )
    else:
        content += f"\nDEFAULT_CANDIDATE_ID={candidate_id}\n"
    env_path.write_text(content, encoding="utf-8")


def _warn_if_api_key_looks_unusual(provider: str, api_key: str) -> None:
    key = api_key.strip()
    if not key:
        console.print(
            f"[yellow]{provider} API key is blank. You can add it later via job-agent settings set.[/yellow]"
        )
        return

    looks_unusual = len(key) < 12 or " " in key
    if provider == "OpenAI":
        looks_unusual = looks_unusual or not key.startswith(("sk-", "sk-proj-"))
    elif provider == "Anthropic":
        looks_unusual = looks_unusual or not key.startswith("sk-ant-")

    if looks_unusual:
        console.print(
            f"[yellow]{provider} API key format looks unusual. Saving it anyway; you can fix it later if needed.[/yellow]"
        )


def run_onboarding(*, non_interactive: bool = False) -> None:
    from job_agent.preflight import check_and_install_packages

    check_and_install_packages()
    console.print(
        Panel(
            "Job Agent — First-Run Setup\n"
            "This wizard will configure your system in ~5 minutes.\n"
            "Press Ctrl+C at any time to quit without saving.",
            title="Welcome",
        )
    )

    existing_settings = read_user_settings()
    if USER_SETTINGS_PATH.exists() and not non_interactive:
        should_continue = _prompt_confirm(
            "Re-run setup? This will overwrite existing settings.",
            default=False,
        )
        if not should_continue:
            console.print("[yellow]Onboarding cancelled. Existing settings were not changed.[/yellow]")
            return

    lm_studio_base_url = str(existing_settings.get("lm_studio_base_url") or settings.lm_studio_base_url).strip()
    if not lm_studio_base_url:
        lm_studio_base_url = DEFAULT_LM_STUDIO_BASE

    prereq_ok, discovered_models = _run_prerequisites_check(lm_studio_base_url)
    if not prereq_ok:
        raise click.ClickException("Prerequisites check failed.")

    updates: dict[str, object] = {
        "llm_provider_mode": "openai",
        "openai_api_key": "",
        "anthropic_api_key": "",
        "use_openai_review": False,
        "use_claude_final_review": False,
    }
    summary: dict[str, str] = {}

    provider_choices = [
        "OpenAI (recommended)",
        "Anthropic (Claude)",
        "Local LLM (LM Studio)",
        "Local LLM (Ollama)",
    ]
    provider_choice = _prompt_select(
        "Which AI provider will you use?",
        choices=provider_choices,
        default=provider_choices[0],
        non_interactive=non_interactive,
    )
    summary["LLM Provider"] = provider_choice

    if provider_choice == provider_choices[2]:
        lm_ok, refreshed_models = _fetch_lm_studio_models(lm_studio_base_url)
        model_options = refreshed_models if lm_ok else discovered_models
        if not model_options:
            console.print("[yellow]LM Studio model list unavailable. Type model names manually.[/yellow]")

        small_default = str(existing_settings.get("lm_studio_small_model") or settings.lm_studio_small_model)
        writer_default = str(existing_settings.get("lm_studio_writer_model") or settings.lm_studio_writer_model)
        mid_default = str(existing_settings.get("lm_studio_mid_model") or settings.lm_studio_mid_model)

        updates["lm_studio_base_url"] = lm_studio_base_url
        updates["lm_studio_small_model"] = _choose_model_name(
            "Small/review model",
            models=model_options,
            default=small_default,
            non_interactive=non_interactive,
        )
        updates["lm_studio_writer_model"] = _choose_model_name(
            "Writer model",
            models=model_options,
            default=writer_default,
            non_interactive=non_interactive,
        )
        updates["lm_studio_mid_model"] = _choose_model_name(
            "Mid/extraction model",
            models=model_options,
            default=mid_default or str(updates["lm_studio_small_model"]),
            non_interactive=non_interactive,
        )
        summary["Writer model"] = str(updates["lm_studio_writer_model"])
        summary["Small model"] = str(updates["lm_studio_small_model"])
        updates["llm_provider_mode"] = "lm_studio"

    if provider_choice == provider_choices[0]:
        updates["openai_api_key"] = _prompt_password("OpenAI API key:", non_interactive=non_interactive)
        _warn_if_api_key_looks_unusual("OpenAI", str(updates["openai_api_key"]))
        updates["use_openai_review"] = True
        updates["llm_provider_mode"] = "openai"
    elif provider_choice == provider_choices[1]:
        updates["anthropic_api_key"] = _prompt_password("Anthropic API key:", non_interactive=non_interactive)
        _warn_if_api_key_looks_unusual("Anthropic", str(updates["anthropic_api_key"]))
        updates["use_claude_final_review"] = True
        updates["llm_provider_mode"] = "anthropic"
    elif provider_choice == provider_choices[3]:
        ollama_base_default = str(existing_settings.get("ollama_base_url") or settings.ollama_base_url).strip() or "http://localhost:11434"
        updates["ollama_base_url"] = _prompt_text(
            "Ollama base URL:",
            default=ollama_base_default,
            non_interactive=non_interactive,
        )
        updates["ollama_fast_model"] = _prompt_text(
            "Ollama fast model:",
            default=str(existing_settings.get("ollama_fast_model") or settings.ollama_fast_model or ""),
            non_interactive=non_interactive,
        )
        updates["ollama_writer_model"] = _prompt_text(
            "Ollama writer model:",
            default=str(existing_settings.get("ollama_writer_model") or settings.ollama_writer_model or ""),
            non_interactive=non_interactive,
        )
        updates["llm_provider_mode"] = "ollama"
        summary["Fast model"] = str(updates["ollama_fast_model"])
        summary["Writer model"] = str(updates["ollama_writer_model"])
    seniority_default = str(existing_settings.get("target_job_seniority") or settings.target_job_seniority or "junior")
    seniority = _prompt_select(
        "Target job seniority?",
        choices=["intern", "junior", "mid", "senior", "any"],
        default=seniority_default if seniority_default in {"intern", "junior", "mid", "senior", "any"} else "junior",
        non_interactive=non_interactive,
    )
    updates["target_job_seniority"] = seniority
    summary["Seniority"] = seniority

    min_score_default = int(existing_settings.get("match_min_score") or settings.match_min_score)
    min_score = _prompt_int_range(
        "Minimum match score to surface a job? [0-100]",
        min_value=0,
        max_value=100,
        default=min_score_default,
        non_interactive=non_interactive,
    )
    updates["match_min_score"] = min_score

    location_default = str(existing_settings.get("jobspy_discover_location") or settings.jobspy_discover_location or "Italy")
    location = _prompt_text(
        "Primary location to search?",
        default=location_default or "Italy",
        non_interactive=non_interactive,
    )
    updates["jobspy_discover_location"] = location
    summary["Location"] = location

    countries_default = existing_settings.get("job_search_countries") or [location or "Italy"]
    country_default = normalize_country_list(countries_default)[0]
    country = _prompt_text(
        "Target country to search:",
        default=country_default,
        non_interactive=non_interactive,
    ).strip() or "Italy"
    updates["job_search_countries"] = normalize_country_list([country])
    region_default = str(existing_settings.get("job_search_region") or "").strip()
    region = _prompt_text(
        "Optional target region or city within that country:",
        default=region_default,
        non_interactive=non_interactive,
    ).strip()
    updates["job_search_region"] = region
    updates["jobspy_discover_location"] = (
        f"{region}, {updates['job_search_countries'][0]}" if region else updates["job_search_countries"][0]
    )
    summary["Location"] = updates["jobspy_discover_location"]

    default_queries = existing_settings.get("jobspy_discover_queries") or settings.jobspy_discover_queries
    queries_default_text = ", ".join(default_queries) if isinstance(default_queries, list) else ""
    queries_raw = _prompt_text(
        "Job titles to search (comma-separated):",
        default=queries_default_text,
        non_interactive=non_interactive,
    )
    updates["jobspy_discover_queries"] = [q.strip() for q in queries_raw.split(",") if q.strip()]

    languages_default = existing_settings.get("job_search_languages") or [{"name": "English", "level": "professional"}]
    languages_default_text = ", ".join(
        f"{item.get('name')}:{item.get('level')}"
        for item in languages_default
        if isinstance(item, dict) and item.get("name")
    )
    languages_raw = _prompt_text(
        "Job description languages (Language:level, comma-separated):",
        default=languages_default_text,
        non_interactive=non_interactive,
    )
    updates["job_search_languages"] = normalize_job_language_preferences(
        "\n".join(part.strip() for part in languages_raw.split(",") if part.strip())
    )
    updates["job_search_languages"] = [
        {"name": item["name"], "level": item["level"]}
        for item in updates["job_search_languages"]
        if isinstance(item, dict)
    ]
    if updates["job_search_languages"]:
        summary["Job Languages"] = ", ".join(
            f"{item['name']} ({str(item['level']).capitalize()})"
            for item in updates["job_search_languages"]
            if isinstance(item, dict)
        )

    jobspy_default = bool(existing_settings.get("use_jobspy", settings.use_jobspy))
    use_jobspy = _prompt_confirm(
        "Enable automatic JobSpy discovery?",
        default=jobspy_default,
        non_interactive=non_interactive,
    )
    updates["use_jobspy"] = use_jobspy
    summary["JobSpy"] = "enabled" if use_jobspy else "disabled"

    candidate_id: str | None = None
    fact_sheet_default = str(existing_settings.get("fact_sheet_path") or "").strip()
    fact_sheet_input = _prompt_text(
        "Path to your fact sheet (JSON or TXT format)?",
        default=fact_sheet_default,
        non_interactive=non_interactive,
    )
    if fact_sheet_input:
        while True:
            try:
                fact_sheet_path = _validate_fact_sheet_path(fact_sheet_input)
                break
            except (ValueError, json.JSONDecodeError) as exc:
                if non_interactive:
                    console.print(f"[yellow]Skipping fact sheet: {exc}[/yellow]")
                    fact_sheet_path = None
                    break
                console.print(f"[red]{exc}[/red]")
                fact_sheet_input = _prompt_text("Path to your fact sheet (JSON or TXT format)?", default="")
                if not fact_sheet_input:
                    fact_sheet_path = None
                    break
        if fact_sheet_path is not None:
            updates["fact_sheet_path"] = str(fact_sheet_path)
            if _server_is_running():
                try:
                    candidate_id = _ingest_fact_sheet(fact_sheet_path)
                except (httpx.RequestError, httpx.HTTPStatusError, ValueError, json.JSONDecodeError) as exc:
                    console.print(
                        f"[yellow]Fact sheet ingest failed ({exc}). Saved path for ingest on first app boot.[/yellow]"
                    )
                else:
                    if candidate_id:
                        console.print(f"[green]Fact sheet ingested. Candidate ID: {candidate_id}[/green]")
                    else:
                        console.print(
                            "[yellow]Fact sheet ingested via legacy endpoint; candidate ID not returned.[/yellow]"
                        )
            else:
                console.print(
                    "[yellow]API not running. Saved fact sheet path; it can be ingested on first app start.[/yellow]"
                )

    artifacts_default = str(existing_settings.get("artifacts_dir") or settings.artifacts_dir or "generated")
    artifacts_input = _prompt_text(
        "Folder to save generated CVs and cover letters?",
        default=artifacts_default,
        non_interactive=non_interactive,
    )
    if artifacts_input:
        resolved = Path(artifacts_input).expanduser()
        updates["artifacts_dir"] = str(resolved)
        summary["CV Output Folder"] = str(resolved)

    summary["Candidate ID"] = candidate_id or settings.default_candidate_id.strip() or "(not set)"

    table = Table(title="Step 5 — Summary")
    table.add_column("Setting")
    table.add_column("Value")
    for key, value in summary.items():
        table.add_row(key, value)
    console.print(table)

    should_save = _prompt_confirm("Save these settings?", default=True, non_interactive=non_interactive)
    if not should_save:
        console.print("[yellow]Setup cancelled. No changes were saved.[/yellow]")
        return

    if candidate_id:
        updates["default_candidate_id"] = candidate_id

    clear_secrets: set[str] = set()
    if provider_choice == provider_choices[2]:
        clear_secrets.update({"openai_api_key", "anthropic_api_key"})
    elif provider_choice == provider_choices[3]:
        clear_secrets.update({"openai_api_key", "anthropic_api_key"})
    elif provider_choice == provider_choices[0]:
        clear_secrets.add("anthropic_api_key")
    elif provider_choice == provider_choices[1]:
        clear_secrets.add("openai_api_key")

    write_user_settings(updates, clear_secrets=clear_secrets)
    reload_settings_from_sources(settings)
    if candidate_id:
        object.__setattr__(settings, "default_candidate_id", candidate_id)

    console.print(
        Panel(
            "Setup complete!\n\n"
            "Next steps:\n"
            "  Start the app:    python -m job_agent.cli start\n"
            "  Open browser:     http://localhost:8000\n\n"
            "Run this wizard again anytime: python -m job_agent.onboard"
        )
    )


@click.command()
@click.option("--non-interactive", is_flag=True, help="Run with defaults where possible.")
def main(non_interactive: bool) -> None:
    """First-run onboarding wizard."""
    try:
        run_onboarding(non_interactive=non_interactive)
    except click.Abort:
        console.print("[yellow]Setup cancelled. No changes were saved.[/yellow]")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
