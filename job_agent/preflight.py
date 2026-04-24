"""Package availability check and auto-install on first run."""
from __future__ import annotations

import importlib
from pathlib import Path
import subprocess
import sys

from rich.console import Console

console = Console()

REQUIRED_PACKAGES = [
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn"),
    ("sqlalchemy", "sqlalchemy"),
    ("httpx", "httpx"),
    ("click", "click"),
    ("rich", "rich"),
    ("pydantic", "pydantic"),
    ("pydantic_settings", "pydantic-settings"),
    ("yaml", "pyyaml"),
    ("questionary", "questionary"),
    ("bs4", "beautifulsoup4"),
    ("jinja2", "jinja2"),
]


def _is_importable(module_name: str) -> bool:
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False


def _check_network() -> bool:
    """Return True if PyPI is reachable."""
    try:
        import httpx

        response = httpx.get("https://pypi.org", timeout=5)
        return response.is_success
    except Exception:
        return False


def check_and_install_packages(project_root: Path | None = None) -> None:
    """
    Check required packages. If any are missing:
    - Try to install with pip install -e .
    - If offline or install fails, print a clear error and raise SystemExit.
    - If all packages are present, return silently.
    """
    missing = [
        pip_name
        for module_name, pip_name in REQUIRED_PACKAGES
        if not _is_importable(module_name)
    ]

    if not missing:
        return

    console.print(f"\n[yellow]⚠ Missing packages detected:[/yellow] {', '.join(missing)}")
    console.print("[dim]Attempting automatic installation…[/dim]\n")

    if not _check_network():
        console.print(
            "[red]✗ Cannot reach PyPI (network offline or blocked).[/red]\n"
            "Please connect to the internet and run:\n"
            "    [bold]pip install -e .[/bold]\n"
            "Then restart the app."
        )
        raise SystemExit(1)

    install_root = project_root or Path(".")
    pyproject = install_root / "pyproject.toml"
    if not pyproject.exists():
        console.print(
            "[red]✗ pyproject.toml not found.[/red] Cannot auto-install.\n"
            f"Expected at: {pyproject}\n"
            "Run [bold]pip install -e .[/bold] manually from the project root."
        )
        raise SystemExit(1)

    console.print(f"[dim]Running: pip install -e {install_root}[/dim]")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", str(install_root)],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        console.print(
            f"[red]✗ Installation failed:[/red]\n{result.stderr[-800:] or result.stdout[-800:]}\n"
            "Fix the error above, then run [bold]pip install -e .[/bold] manually."
        )
        raise SystemExit(1)

    console.print("[green]✓ Packages installed successfully.[/green]")
    console.print("[dim]Continuing startup…[/dim]\n")
