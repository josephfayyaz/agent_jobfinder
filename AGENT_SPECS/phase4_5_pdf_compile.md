# Spec: Phase 4.5 — PDF Compilation from LaTeX
Status: pending

## Context
The CV workflow generates `.tex` files in `generated/` but never compiles them to PDF.
`pdflatex` is not currently on PATH — Texpad is installed but keeps TeX bundled internally.
This spec adds: one-time TeX installation, a `compile_pdf()` function, and a download endpoint.

## Step 0: Install BasicTeX (one-time, run manually — NOT in code)
```bash
brew install --cask basictex
# After install, add to PATH for this session:
eval "$(/usr/libexec/path_helper)"
# Verify:
pdflatex --version
```
BasicTeX installs to `/usr/local/texlive/*/bin/universal-darwin/pdflatex`.

## Changes

### File: `job_agent/services/documents.py`
Read the file first. Add the following at the end of the file (after the existing `render_resume_tex` function):

```python
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

_logger = logging.getLogger(__name__)

# Common locations where pdflatex may be installed on macOS.
_PDFLATEX_SEARCH_PATHS = [
    "/usr/local/texlive/2024/bin/universal-darwin/pdflatex",
    "/usr/local/texlive/2023/bin/universal-darwin/pdflatex",
    "/Library/TeX/texbin/pdflatex",
    "/opt/homebrew/bin/pdflatex",
    "pdflatex",  # rely on PATH as final fallback
]


def _find_pdflatex() -> str:
    """Return the first available pdflatex binary path, or raise if none found."""
    for candidate in _PDFLATEX_SEARCH_PATHS:
        if candidate == "pdflatex":
            if shutil.which("pdflatex"):
                return "pdflatex"
        elif Path(candidate).is_file():
            return candidate
    raise FileNotFoundError(
        "pdflatex not found. Install BasicTeX: brew install --cask basictex"
    )


def compile_pdf(tex_path: str) -> str:
    """Compile a .tex file to .pdf and return the PDF path.

    Runs pdflatex twice (needed for cross-references) in a temp directory,
    then copies the resulting PDF next to the .tex file.

    Args:
        tex_path: Absolute or relative path to the .tex source file.

    Returns:
        Absolute path of the generated .pdf file.

    Raises:
        FileNotFoundError: If pdflatex is not installed.
        RuntimeError: If pdflatex exits with a non-zero status.
    """
    tex_path = Path(tex_path).resolve()
    if not tex_path.exists():
        raise FileNotFoundError(f"TeX source not found: {tex_path}")

    pdflatex = _find_pdflatex()
    pdf_output = tex_path.with_suffix(".pdf")

    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = [
            pdflatex,
            "-interaction=nonstopmode",
            "-halt-on-error",
            f"-output-directory={tmpdir}",
            str(tex_path),
        ]
        for _pass in range(2):  # two passes for cross-references
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                _logger.error("pdflatex failed:\n%s", result.stdout[-2000:])
                raise RuntimeError(
                    f"pdflatex compilation failed (pass {_pass + 1}). "
                    f"Check the .tex file for syntax errors."
                )

        tmp_pdf = Path(tmpdir) / tex_path.with_suffix(".pdf").name
        shutil.copy(tmp_pdf, pdf_output)
        _logger.info("PDF compiled: %s", pdf_output)

    return str(pdf_output)
```

### File: `job_agent/main.py`
Read the file first. Add the following endpoint after the existing draft endpoints
(search for the `approve` endpoint and add after it):

```python
@app.get("/drafts/{draft_id}/pdf")
def download_draft_pdf(draft_id: UUID, db: Session = Depends(get_db)):
    """Compile the draft's .tex file to PDF and return it for download."""
    from fastapi.responses import FileResponse
    from job_agent.services.documents import compile_pdf

    draft = db.get(ResumeDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    if not draft.tex_path:
        raise HTTPException(status_code=400, detail="Draft has no .tex file")

    try:
        pdf_path = compile_pdf(draft.tex_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"resume_{draft_id}.pdf",
    )
```

Note: `UUID`, `HTTPException`, `Depends`, `Session`, `ResumeDraft`, `get_db` are
already imported in `main.py` — do not add duplicate imports.

## Verification
```bash
# After installing BasicTeX and restarting the API:
DRAFT_ID=$(curl -s localhost:8000/drafts | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")
curl -s "localhost:8000/drafts/$DRAFT_ID/pdf" -o /tmp/test_resume.pdf
file /tmp/test_resume.pdf
# Expected: /tmp/test_resume.pdf: PDF document, version ...

/Users/youseffayyaz/miniforge3/bin/conda run -n ML python -m ruff check job_agent/
# Expected: no errors
```

## Git
```bash
git add job_agent/services/documents.py job_agent/main.py
git commit -m "feat: add PDF compilation from LaTeX with download endpoint

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```
