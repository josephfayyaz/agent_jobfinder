from __future__ import annotations

import signal
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

import click
import httpx
from rich.console import Console

from job_agent.config import settings
from job_agent.user_config import USER_SETTINGS_PATH

console = Console()
PYTHON = str(Path(sys.executable))
API_BASE_URL = "http://localhost:8000"
UI_URL = f"{API_BASE_URL}/ui"


def _user_settings_file() -> Path:
    return USER_SETTINGS_PATH


def _port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1.0)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def _api_online() -> bool:
    try:
        response = httpx.get(f"{API_BASE_URL}/health", timeout=2)
    except httpx.RequestError:
        return False
    return response.status_code == 200


def _lm_studio_status() -> tuple[bool, int]:
    try:
        response = httpx.get(f"{settings.lm_studio_base_url.rstrip('/')}/models", timeout=3)
        if response.status_code != 200:
            return False, 0
        payload = response.json()
    except (httpx.RequestError, ValueError):
        return False, 0

    data = payload.get("data", []) if isinstance(payload, dict) else []
    return True, len(data)


def _wait_for_api(max_attempts: int = 20, delay_seconds: float = 1.0) -> None:
    with console.status("[bold blue]Waiting for API server...[/bold blue]"):
        for _ in range(max_attempts):
            try:
                response = httpx.get(f"{API_BASE_URL}/health", timeout=2)
            except httpx.RequestError:
                time.sleep(delay_seconds)
                continue
            if response.status_code == 200:
                return
            time.sleep(delay_seconds)
    raise click.ClickException("API server failed to become ready.")


def _open_browser() -> None:
    console.print(f"[cyan]  → Opening browser at {UI_URL}[/cyan]")
    webbrowser.open(UI_URL)


def _terminate_process(proc: subprocess.Popen[bytes] | subprocess.Popen[str], timeout: float = 5.0) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass


def _preflight() -> None:
    from job_agent.preflight import check_and_install_packages

    check_and_install_packages()
    console.print("[bold]Job Agent[/bold] Starting...\n")

    if not _user_settings_file().exists():
        console.print("\n[yellow][!] Not configured yet.[/yellow]\n")
        console.print(f"Missing settings file: [dim]{_user_settings_file()}[/dim]\n")
        console.print("Run the setup wizard first:")
        console.print("    [bold]python -m job_agent.onboard[/bold]\n")
        console.print("Then start:")
        console.print("    [bold]python -m job_agent.cli start[/bold]")
        raise SystemExit(1)

    if not _port_is_free(8000):
        if _api_online():
            open_browser = click.confirm("Server already running? Open browser?", default=True)
            if open_browser:
                _open_browser()
                raise SystemExit(0)
            raise SystemExit(1)
        console.print("[red]  ✗ Port 8000 is already in use by another process[/red]")
        raise SystemExit(1)

    console.print("[bold]Preflight checks[/bold]")
    console.print("  · SQLite — no Docker required")

    lm_online, model_count = _lm_studio_status()
    if lm_online:
        console.print(f"[green]  ✓ LM Studio detected ({model_count} models loaded)[/green]")
    else:
        console.print("[yellow]  ⚠ LM Studio not reachable — start it before running workflows[/yellow]")


def start() -> None:
    _preflight()

    procs: list[tuple[str, subprocess.Popen[str]]] = []
    shutting_down = False

    def _shutdown(exit_code: int, reason: str | None = None) -> None:
        nonlocal shutting_down
        if shutting_down:
            raise SystemExit(exit_code)
        shutting_down = True
        if reason:
            console.print(reason)
        console.print("[yellow][Job Agent] Shutting down...[/yellow]")
        for _, proc in procs:
            _terminate_process(proc)
        console.print("[green][Job Agent] All services stopped.[/green]")
        raise SystemExit(exit_code)

    def _signal_handler(_sig: int, _frame) -> None:
        _shutdown(0)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    api_proc = subprocess.Popen(
        [
            PYTHON,
            "-m",
            "uvicorn",
            "job_agent.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
            "--reload",
        ],
        text=True,
    )
    procs.append(("API server", api_proc))

    worker_proc = subprocess.Popen([PYTHON, "-m", "job_agent.worker"], text=True)
    procs.append(("Worker", worker_proc))
    console.print(f"[green]  ✓ Worker started (PID {worker_proc.pid})[/green]")

    try:
        _wait_for_api()
    except click.ClickException as exc:
        _shutdown(1, f"[red]  ✗ {exc.message}[/red]")

    console.print(f"[green]  ✓ API server up at {API_BASE_URL}[/green]")
    _open_browser()
    console.print("\n[bold][Job Agent] Running. Press Ctrl+C to stop all services.[/bold]")

    while True:
        for name, proc in procs:
            exit_code = proc.poll()
            if exit_code is not None:
                _shutdown(1, f"[red][Job Agent] {name} exited with code {exit_code}.[/red]")
        time.sleep(2)
