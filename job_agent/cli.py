from __future__ import annotations

import sys
import time
from urllib.parse import urlparse
import webbrowser

import click
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from job_agent.user_config import USER_SETTINGS_PATH

try:
    import questionary
except ImportError:  # pragma: no cover - optional fallback for minimal envs
    questionary = None


console = Console()
BASE_URL = "http://localhost:8000"


def _interactive() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def _api(method: str, path: str, **kwargs) -> httpx.Response:
    timeout = kwargs.pop("timeout", 30)
    try:
        response = httpx.request(method, f"{BASE_URL}{path}", timeout=timeout, **kwargs)
        response.raise_for_status()
        return response
    except httpx.ConnectError:
        console.print("[red]Cannot reach server at localhost:8000.[/red]")
        console.print("Run [bold]job-agent start[/bold] first.")
        raise SystemExit(1) from None
    except httpx.RequestError as exc:
        console.print(f"[red]Request failed:[/red] {exc}")
        raise SystemExit(1) from None
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:200] if exc.response.text else ""
        console.print(f"[red]API error {exc.response.status_code}:[/red] {body}")
        raise SystemExit(1) from None


def _prompt_text(message: str, *, default: str = "") -> str:
    if not _interactive():
        return default
    if questionary is not None:
        answer = questionary.text(message, default=default).ask()
        if answer is None:
            raise click.Abort()
        return str(answer).strip()
    return str(click.prompt(message, default=default, show_default=bool(default))).strip()


def _prompt_confirm(message: str, *, default: bool = True) -> bool:
    if not _interactive():
        return default
    if questionary is not None:
        answer = questionary.confirm(message, default=default).ask()
        if answer is None:
            raise click.Abort()
        return bool(answer)
    return bool(click.confirm(message, default=default))


def _prompt_select(message: str, choices: list[str], *, default: str | None = None) -> str:
    selected_default = default if default in choices else choices[0]
    if not _interactive():
        return selected_default
    if questionary is not None:
        answer = questionary.select(message, choices=choices, default=selected_default).ask()
        if answer is None:
            raise click.Abort()
        return str(answer)
    return str(click.prompt(message, type=click.Choice(choices), default=selected_default))


def _format_timestamp(value: object) -> str:
    if not value:
        return "Never"
    text = str(value).replace("T", " ")
    return text[:16]


def _looks_like_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _coerce_setting_value(value: str) -> object:
    lowered = value.strip().lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        return int(value)
    except ValueError:
        return value


def _poll_task(task_id: str, *, timeout_seconds: int = 120, interval_seconds: int = 2) -> dict[str, object] | None:
    deadline = time.time() + timeout_seconds
    with console.status(f"[bold blue]Waiting for task {task_id}...[/bold blue]"):
        while time.time() < deadline:
            task = _api("GET", f"/tasks/{task_id}").json()
            if task.get("status") in {"completed", "failed"}:
                return task
            time.sleep(interval_seconds)
    return None


def _render_settings_tables(current: dict[str, object]) -> None:
    provider_table = Table(title="LLM Provider")
    provider_table.add_column("Setting")
    provider_table.add_column("Value")
    provider_table.add_row("lm_studio_base_url", str(current.get("lm_studio_base_url") or ""))
    provider_table.add_row("lm_studio_small_model", str(current.get("lm_studio_small_model") or ""))
    provider_table.add_row("lm_studio_writer_model", str(current.get("lm_studio_writer_model") or ""))
    provider_table.add_row(
        "openai_api_key",
        "(set)" if current.get("openai_api_key") == "***" else "(not set)",
    )
    provider_table.add_row(
        "anthropic_api_key",
        "(set)" if current.get("anthropic_api_key") == "***" else "(not set)",
    )

    discovery_table = Table(title="Job Discovery")
    discovery_table.add_column("Setting")
    discovery_table.add_column("Value")
    discovery_table.add_row("target_job_seniority", str(current.get("target_job_seniority") or ""))
    discovery_table.add_row("match_min_score", str(current.get("match_min_score") or ""))
    discovery_table.add_row("use_jobspy", str(current.get("use_jobspy") or False).lower())
    discovery_table.add_row("job_search_countries", ", ".join(current.get("job_search_countries") or []))
    discovery_table.add_row(
        "job_search_languages",
        ", ".join(
            f"{item.get('name')} ({item.get('label') or item.get('level')})"
            for item in (current.get("job_search_languages") or [])
            if isinstance(item, dict)
        ),
    )
    discovery_table.add_row("default_candidate_id", str(current.get("default_candidate_id") or "(not set)"))

    cv_table = Table(title="CV Thresholds")
    cv_table.add_column("Setting")
    cv_table.add_column("Value")
    cv_table.add_row("cv_pass_score", str(current.get("cv_pass_score") or ""))
    cv_table.add_row("cv_revise_score", str(current.get("cv_revise_score") or ""))
    cv_table.add_row("bullet_clarify_word_limit", str(current.get("bullet_clarify_word_limit") or ""))

    console.print(provider_table)
    console.print(discovery_table)
    console.print(cv_table)
    source = str(USER_SETTINGS_PATH) if current.get("_yaml_exists") else f"{USER_SETTINGS_PATH} (missing)"
    console.print(f"[dim]Source: {source}[/dim]")


def _render_jobs_table(jobs: list[dict[str, object]], *, title: str = "Jobs") -> None:
    table = Table(title=title)
    table.add_column("ID")
    table.add_column("Title")
    table.add_column("Company")
    table.add_column("Location")
    table.add_column("Status")

    for job in jobs:
        table.add_row(
            str(job.get("id") or ""),
            str(job.get("title") or ""),
            str(job.get("company") or ""),
            str(job.get("location") or job.get("city") or ""),
            str(job.get("status") or ""),
        )
    console.print(table)


def _run_status() -> None:
    health_payload = _api("GET", "/health").json()
    onboarding_payload = _api("GET", "/onboarding/status").json()
    providers_payload = _api("GET", "/providers").json()
    settings_payload = _api("GET", "/settings/current").json()
    lm_models_payload = _api("GET", "/lm-studio/models").json()
    jobs = _api("GET", "/jobs", params={"show_all": True}).json()
    drafts = _api("GET", "/drafts").json()
    applications = _api("GET", "/applications").json()

    api_online = health_payload.get("status") == "ok"
    lm_online = bool(lm_models_payload.get("online"))
    model_count = len(lm_models_payload.get("models", []))
    candidate_id = settings_payload.get("default_candidate_id") or "(not set)"

    status_table = Table(title="Job Agent Status", show_header=False)
    status_table.add_column("Item", style="bold")
    status_table.add_column("Value")
    status_table.add_row("API server", "✓ online (localhost:8000)" if api_online else "✗ offline")
    status_table.add_row("Database", "✓ connected" if api_online else "✗ unavailable")
    lm_value = "✓ online" if lm_online else "✗ offline"
    if lm_online:
        lm_value += f" — {model_count} models loaded"
    status_table.add_row("LM Studio", lm_value)
    status_table.add_row("Candidate ID", str(candidate_id))
    status_table.add_row(
        "Onboarding",
        "✓ configured" if onboarding_payload.get("configured") else "✗ not configured",
    )
    console.print(status_table)
    console.print(
        Panel(
            f"Jobs tracked: [bold]{len(jobs)}[/bold] | "
            f"Drafts: [bold]{len(drafts)}[/bold] | "
            f"Applications: [bold]{len(applications)}[/bold]"
        )
    )
    provider_summary = []
    if providers_payload.get("openai", {}).get("enabled"):
        provider_summary.append("OpenAI enabled")
    if providers_payload.get("anthropic", {}).get("enabled"):
        provider_summary.append("Anthropic enabled")
    if provider_summary:
        console.print("[dim]" + " | ".join(provider_summary) + "[/dim]")


def _run_settings_show() -> None:
    current = _api("GET", "/settings/current").json()
    _render_settings_tables(current)


@click.group()
def cli():
    """Job Agent — local-first job search + CV optimization."""


@cli.command("start")
def start():
    """Start the full stack: database, API server, worker, browser."""
    from job_agent.cli_start import start as start_stack

    start_stack()


@cli.command("onboard")
@click.option("--non-interactive", is_flag=True, help="Run onboarding with defaults where possible.")
def onboard(non_interactive: bool):
    """Run first-run onboarding wizard."""
    from job_agent.onboard import run_onboarding

    try:
        run_onboarding(non_interactive=non_interactive)
    except click.Abort:
        console.print("[yellow]Setup cancelled. No changes were saved.[/yellow]")
        raise SystemExit(1) from None


@cli.command("status")
def status():
    """Show API, provider, onboarding, and pipeline status."""
    _run_status()


@cli.command("apply")
def apply():
    """Paste a job URL or description, then optionally queue a draft."""
    value = _prompt_text("Enter a job URL or paste job description text:")
    if not value:
        console.print("[yellow]No job input provided.[/yellow]")
        return

    if _looks_like_url(value):
        job_response = _api("POST", "/jobs/add", json={"url": value}).json()
    else:
        job_response = _api("POST", "/jobs/from-text", json={"text": value}).json()

    job_id = str(job_response.get("job_id") or "")
    console.print(
        f"[green]✓ Added job[/green] {job_response.get('title', 'Unknown Role')} @ "
        f"{job_response.get('company', 'Unknown Company')} [{job_id}]"
    )

    fit_payload = _api("GET", f"/jobs/{job_id}/track-fit").json()
    recommended_tracks = fit_payload.get("recommended_tracks", [])
    if recommended_tracks:
        top = recommended_tracks[0]
        console.print(
            f"Top match: [bold]{top.get('title') or top.get('slug')}[/bold] "
            f"({top.get('score', 0)}%)"
        )

    if not _prompt_confirm("Generate CV draft for this job?", default=True):
        return

    generate_payload = _api("POST", "/drafts/generate", json={"job_id": job_id}).json()
    task_id = str(generate_payload.get("task_id") or "")
    console.print(f"[cyan]→ Queued draft generation task {task_id}[/cyan]")

    task = _poll_task(task_id)
    if task is None:
        console.print("[yellow]Task is still pending. Keep the worker running and check again later.[/yellow]")
        return
    if task.get("status") == "failed":
        console.print(f"[red]Draft generation failed:[/red] {task.get('error_message') or 'unknown error'}")
        return

    result = task.get("result") or {}
    draft_id = str(result.get("draft_id") or "")
    score = result.get("score")
    console.print(f"[green]✓ Draft ready[/green] [{draft_id}] score={score}")

    if draft_id and _prompt_confirm("Open draft in browser?", default=True):
        webbrowser.open(f"{BASE_URL}/ui/drafts/{draft_id}")


@cli.group("companies")
def companies():
    """Manage watched companies over HTTP."""


@companies.command("list")
def companies_list():
    """List watched companies."""
    sources = _api("GET", "/career-pages", params={"limit": 100}).json()

    table = Table(title=f"Watched Companies ({len(sources)} total)")
    table.add_column("ID")
    table.add_column("Company")
    table.add_column("ATS")
    table.add_column("Last Scan")
    table.add_column("New Jobs")
    table.add_column("Status")

    for source in sources:
        table.add_row(
            str(source.get("id") or ""),
            str(source.get("company") or ""),
            str(source.get("ats_type") or "HTML"),
            _format_timestamp(source.get("last_checked_at")),
            str(source.get("last_new_jobs") or 0),
            "● Active" if source.get("active") else "○ Inactive",
        )
    console.print(table)


@companies.command("add")
def companies_add():
    """Guided company add flow."""
    company = _prompt_text("Company name:")
    career_url = _prompt_text("Career page URL:")
    country = _prompt_text("Country:", default="Italy")
    ats_type = _prompt_select("ATS type:", ["none", "greenhouse", "lever", "ashby"], default="none")
    ats_slug = ""
    if ats_type != "none":
        ats_slug = _prompt_text("ATS slug:", default="")

    params: dict[str, object] = {
        "company": company,
        "career_url": career_url,
        "country": country or "Italy",
    }
    if ats_type != "none":
        params["ats_type"] = ats_type
    if ats_slug:
        params["ats_slug"] = ats_slug

    payload = _api("POST", "/career-pages", params=params).json()
    console.print(f"[green]✓ Added {payload['company']} (ID: {payload['id']})[/green]")


@companies.command("toggle")
@click.argument("source_id", type=int)
def companies_toggle(source_id: int):
    """Toggle a watched company active/inactive."""
    sources = _api("GET", "/career-pages").json()
    current = next((item for item in sources if item.get("id") == source_id), None)
    _api("POST", f"/career-pages/{source_id}/toggle-active")
    if current is None:
        console.print(f"[green]✓ Company {source_id} toggled.[/green]")
        return
    new_state = "Active" if not current.get("active") else "Inactive"
    console.print(f"[green]✓ Company {source_id} is now {new_state}[/green]")


@companies.command("remove")
@click.argument("source_id", type=int)
def companies_remove(source_id: int):
    """Delete a watched company."""
    sources = _api("GET", "/career-pages").json()
    current = next((item for item in sources if item.get("id") == source_id), None)
    company_name = str(current.get("company")) if current else f"Company {source_id}"

    if not _prompt_confirm(
        f"Remove {company_name}? This will delete all scan history.",
        default=False,
    ):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    _api("DELETE", f"/career-pages/{source_id}")
    console.print(f"[green]✓ Removed {company_name}[/green]")


@cli.group("settings")
def settings_group():
    """Read and update user-editable settings."""


@settings_group.command("show")
def settings_show():
    """Show current settings."""
    _run_settings_show()


@settings_group.command("set")
@click.argument("key")
@click.argument("value")
def settings_set(key: str, value: str):
    """Set one user-editable setting."""
    coerced = _coerce_setting_value(value)
    _api("POST", "/settings/save", json={key: coerced})
    console.print(f"[green]✓ Updated {key} = {coerced}[/green]")

    if _prompt_confirm("Reload server to apply?", default=True):
        _api("POST", "/settings/reload")
        console.print("[green]✓ Settings reloaded[/green]")


@settings_group.command("reload")
def settings_reload():
    """Reload settings from the user settings file."""
    _api("POST", "/settings/reload")
    console.print(f"[green]✓ Settings reloaded from {USER_SETTINGS_PATH}[/green]")


@cli.command("health", hidden=True)
def health_alias():
    """Backward-compatible alias for status."""
    _run_status()


@cli.command("config", hidden=True)
def config_alias():
    """Backward-compatible alias for settings show."""
    _run_settings_show()


@cli.group("jobs", hidden=True)
def jobs_group():
    """Backward-compatible HTTP job commands."""


@jobs_group.command("list")
@click.option("--limit", default=20, type=int, help="Number of jobs to show")
@click.option("--all", "show_all", is_flag=True, help="Show all jobs ignoring min-score filter")
@click.option("--min-score", default=None, type=int, help="Override min score filter")
def jobs_list(limit: int, show_all: bool, min_score: int | None):
    """List jobs over HTTP."""
    params: dict[str, object] = {"show_all": show_all}
    if min_score is not None:
        params["min_score"] = min_score
    jobs = _api("GET", "/jobs", params=params).json()
    _render_jobs_table(jobs[:limit], title="Jobs")


if __name__ == "__main__":
    cli()
