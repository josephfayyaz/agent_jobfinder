from __future__ import annotations

from pathlib import Path


class UnsupportedFileType(ValueError):
    pass


def extract_text_from_pdf(path: Path) -> str:
    from pdfminer.high_level import extract_text

    return extract_text(str(path))


def extract_text_from_docx(path: Path) -> str:
    from docx import Document

    document = Document(str(path))
    return "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())


def extract_text_from_html(path: Path) -> str:
    from bs4 import BeautifulSoup

    html = path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def extract_text_from_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def extract_text_auto(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(path)
    if suffix in {".docx", ".doc"}:
        return extract_text_from_docx(path)
    if suffix in {".html", ".htm"}:
        return extract_text_from_html(path)
    if suffix in {".txt", ".md", ".rst"}:
        return extract_text_from_txt(path)
    raise UnsupportedFileType(f"Unsupported file type: {suffix}")
