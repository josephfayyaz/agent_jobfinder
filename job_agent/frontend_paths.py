"""Frontend asset path helpers."""

from __future__ import annotations

from pathlib import Path


def frontend_root() -> Path:
    return Path(__file__).resolve().parent.parent / "frontend"


def frontend_templates_dir() -> Path:
    return frontend_root() / "templates"


def frontend_static_dir() -> Path:
    return frontend_root() / "static"
