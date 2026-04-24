"""Shared frontend template loader."""

from __future__ import annotations

from fastapi.templating import Jinja2Templates

from job_agent.frontend_paths import frontend_templates_dir

templates = Jinja2Templates(directory=str(frontend_templates_dir()))
