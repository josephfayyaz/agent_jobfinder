from __future__ import annotations

from pathlib import Path
import re


class UnsupportedFileType(ValueError):
    pass


_PDF_EMPTY_ERROR = "Could not extract readable text from PDF. Try a different PDF export or add plain-text notes."


def _normalize_extracted_text(text: str) -> str:
    cleaned = str(text or "").replace("\x00", "")
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r" ?• ?", "\n- ", cleaned)
    cleaned = re.sub(r" ?▪ ?", "\n- ", cleaned)
    cleaned = re.sub(r" ?◦ ?", "\n- ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    lines = [line.strip() for line in cleaned.split("\n")]
    cleaned_lines: list[str] = []
    for line in lines:
        if not line:
            if cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")
            continue
        if (
            line.startswith("- ")
            and cleaned_lines[-1:] == [""]
            and len(cleaned_lines) >= 2
            and cleaned_lines[-2].startswith("- ")
        ):
            cleaned_lines.pop()
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def _extract_pdf_text_with_pdfplumber(path: Path) -> str:
    import pdfplumber

    page_blocks: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text(layout=True, x_tolerance=2, y_tolerance=3) or ""
            text = _normalize_extracted_text(text)
            if text:
                page_blocks.append(text)
                continue

            words = page.extract_words(
                use_text_flow=True,
                keep_blank_chars=False,
                split_at_punctuation=False,
            )
            if not words:
                continue

            grouped: dict[tuple[str, int], list[tuple[float, str]]] = {}
            midpoint = page.width / 2 if page.width else 0
            for word in words:
                text_value = str(word.get("text") or "").strip()
                if not text_value:
                    continue
                x0 = float(word.get("x0") or 0.0)
                top = int(round(float(word.get("top") or 0.0) / 3.0))
                column = "left" if x0 <= midpoint else "right"
                grouped.setdefault((column, top), []).append((x0, text_value))

            rebuilt_lines: list[str] = []
            for column in ("left", "right"):
                for key in sorted(item for item in grouped if item[0] == column):
                    parts = [value for _, value in sorted(grouped[key], key=lambda pair: pair[0])]
                    line = _normalize_extracted_text(" ".join(parts))
                    if line:
                        rebuilt_lines.append(line)
                if rebuilt_lines and rebuilt_lines[-1] != "":
                    rebuilt_lines.append("")
            rebuilt = _normalize_extracted_text("\n".join(rebuilt_lines))
            if rebuilt:
                page_blocks.append(rebuilt)

    return _normalize_extracted_text("\n\n".join(page_blocks))


def _extract_pdf_text_with_pdfminer(path: Path) -> str:
    from pdfminer.high_level import extract_text

    return _normalize_extracted_text(extract_text(str(path)))


def extract_text_from_pdf(path: Path) -> str:
    extracted = ""
    errors: list[str] = []

    try:
        extracted = _normalize_extracted_text(_extract_pdf_text_with_pdfplumber(path))
    except Exception as exc:
        errors.append(f"pdfplumber: {exc}")

    if extracted:
        return extracted

    try:
        extracted = _normalize_extracted_text(_extract_pdf_text_with_pdfminer(path))
    except Exception as exc:
        errors.append(f"pdfminer: {exc}")

    if extracted:
        return extracted

    if errors:
        raise ValueError(f"{_PDF_EMPTY_ERROR} ({'; '.join(errors)})")
    raise ValueError(_PDF_EMPTY_ERROR)


def extract_text_from_docx(path: Path) -> str:
    from docx import Document

    document = Document(str(path))
    return _normalize_extracted_text(
        "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())
    )


def extract_text_from_html(path: Path) -> str:
    from bs4 import BeautifulSoup

    html = path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return _normalize_extracted_text(soup.get_text(separator="\n", strip=True))


def extract_text_from_txt(path: Path) -> str:
    return _normalize_extracted_text(path.read_text(encoding="utf-8", errors="replace"))


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
