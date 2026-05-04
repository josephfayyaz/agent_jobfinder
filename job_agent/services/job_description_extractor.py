"""Deterministic job description extraction with source priority.

Phase E3 — Structured Extraction And Source Priority.

This service extracts the best available job description text using
deterministic tools (no LLM):

1. ATS-provided plaintext or HTML (Greenhouse / Lever / Ashby)
2. Direct company or hosted apply URL
3. Structured metadata extraction from page HTML (JSON-LD / Microdata via extruct)
4. Main-content extraction from page HTML (trafilatura)
5. LinkedIn guest-page HTML fallback (readability-lxml)

Every extraction result includes provenance metadata so downstream scoring
can trust-weight the description.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import logging
from typing import Any

from bs4 import BeautifulSoup
import httpx

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
_FETCH_TIMEOUT = 15


@dataclass
class ExtractionResult:
    """Normalized result from the extraction pipeline."""

    description: str
    extraction_method: str
    source_url: str = ""
    source_kind: str = "unknown"
    success: bool = True
    quality_improved: bool = False
    provenance: dict[str, Any] = field(default_factory=dict)


# ── ATS plaintext normalization ──────────────────────────────────────────

def _strip_html(html_text: str) -> str:
    """Convert HTML to readable plaintext."""
    if not html_text or not html_text.strip():
        return ""
    soup = BeautifulSoup(html_text, "lxml")
    return soup.get_text(separator="\n", strip=True)


def extract_from_ats_payload(
    *,
    description_text: str,
    ats_type: str = "",
    source_url: str = "",
) -> ExtractionResult:
    """Normalize ATS-provided description (Greenhouse HTML, Lever plaintext, Ashby HTML)."""
    text = str(description_text or "").strip()
    if not text:
        return ExtractionResult(
            description="",
            extraction_method="ats_payload_empty",
            source_url=source_url,
            source_kind="ats_structured",
            success=False,
        )

    # Greenhouse returns HTML in `content`, Ashby in `descriptionHtml`
    if "<" in text and ">" in text:
        plaintext = _strip_html(text)
    else:
        plaintext = text

    if not plaintext or len(plaintext.strip()) < 20:
        return ExtractionResult(
            description=text,
            extraction_method="ats_payload_thin",
            source_url=source_url,
            source_kind="ats_structured",
            success=False,
        )

    return ExtractionResult(
        description=plaintext,
        extraction_method="ats_payload",
        source_url=source_url,
        source_kind="ats_structured",
        success=True,
        provenance={
            "ats_type": ats_type,
            "jd_extraction_method": "ats_payload",
            "jd_source_kind": "ats_structured",
            "jd_source_url": source_url,
            "jd_last_enriched_at": datetime.now(timezone.utc).isoformat(),
        },
    )


# ── Structured metadata extraction (JSON-LD / Microdata) ────────────────

def _extract_jsonld_job_posting(html: str) -> str | None:
    """Extract description from JSON-LD JobPosting schema using extruct."""
    data: dict[str, Any] = {}
    try:
        import extruct
    except ImportError:
        extruct = None
        logger.debug("extruct not installed; falling back to manual JSON-LD parsing.")

    if extruct is not None:
        try:
            data = extruct.extract(html, syntaxes=["json-ld", "microdata"], uniform=True)
        except Exception as exc:
            logger.debug("extruct extraction failed: %s", exc)
            data = {}

        # JSON-LD
        for item in data.get("json-ld", []):
            if not isinstance(item, dict):
                continue
            item_type = str(item.get("@type") or "")
            if item_type.casefold() == "jobposting" or "jobposting" in item_type.casefold():
                desc = item.get("description") or ""
                if isinstance(desc, str) and desc.strip():
                    return _strip_html(desc) if ("<" in desc and ">" in desc) else desc.strip()

        # Microdata
        for item in data.get("microdata", []):
            if not isinstance(item, dict):
                continue
            item_type = str(item.get("@type") or item.get("type") or "")
            if "jobposting" in item_type.casefold():
                props = item.get("properties") or item
                desc = props.get("description") or ""
                if isinstance(desc, str) and desc.strip():
                    return _strip_html(desc) if ("<" in desc and ">" in desc) else desc.strip()

    # Fallback parser for environments where extruct misses valid JSON-LD blocks.
    def _extract_from_jsonld_node(node: Any) -> str | None:
        if isinstance(node, list):
            for child in node:
                found = _extract_from_jsonld_node(child)
                if found:
                    return found
            return None
        if not isinstance(node, dict):
            return None

        item_type = node.get("@type")
        if isinstance(item_type, list):
            item_type_match = any("jobposting" in str(value).casefold() for value in item_type)
        else:
            item_type_match = "jobposting" in str(item_type or "").casefold()
        if item_type_match:
            desc = node.get("description") or ""
            if isinstance(desc, str) and desc.strip():
                return _strip_html(desc) if ("<" in desc and ">" in desc) else desc.strip()

        for key in ("@graph", "graph", "itemListElement"):
            nested = node.get(key)
            found = _extract_from_jsonld_node(nested)
            if found:
                return found
        return None

    soup = BeautifulSoup(html or "", "lxml")
    for script in soup.find_all("script"):
        script_type = str(script.get("type") or "").casefold()
        if "ld+json" not in script_type:
            continue
        raw = script.string or script.get_text()
        if not raw or not raw.strip():
            continue
        try:
            parsed = json.loads(raw)
        except Exception:
            continue
        found = _extract_from_jsonld_node(parsed)
        if found:
            return found

    return None


def extract_from_structured_metadata(html: str, *, source_url: str = "") -> ExtractionResult:
    """Try JSON-LD / Microdata extraction from raw page HTML."""
    description = _extract_jsonld_job_posting(html)
    if description and len(description) >= 50:
        return ExtractionResult(
            description=description,
            extraction_method="json_ld_job_posting",
            source_url=source_url,
            source_kind="company_page",
            success=True,
            provenance={
                "jd_extraction_method": "json_ld_job_posting",
                "jd_source_kind": "company_page",
                "jd_source_url": source_url,
                "jd_last_enriched_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    return ExtractionResult(
        description=description or "",
        extraction_method="json_ld_not_found",
        source_url=source_url,
        source_kind="unknown",
        success=False,
    )


# ── Main-content extraction (trafilatura) ────────────────────────────────

def extract_main_content(html: str, *, source_url: str = "") -> ExtractionResult:
    """Extract main content from HTML using trafilatura."""
    try:
        import trafilatura
    except ImportError:
        logger.debug("trafilatura not installed; skipping main-content extraction.")
        return ExtractionResult(
            description="",
            extraction_method="trafilatura_unavailable",
            source_url=source_url,
            success=False,
        )

    try:
        text = trafilatura.extract(html, include_comments=False, include_tables=True) or ""
    except Exception as exc:
        logger.debug("trafilatura extraction failed: %s", exc)
        return ExtractionResult(
            description="",
            extraction_method="trafilatura_error",
            source_url=source_url,
            success=False,
        )

    text = text.strip()
    if len(text) >= 80:
        return ExtractionResult(
            description=text,
            extraction_method="trafilatura",
            source_url=source_url,
            source_kind="company_page",
            success=True,
            provenance={
                "jd_extraction_method": "trafilatura",
                "jd_source_kind": "company_page",
                "jd_source_url": source_url,
                "jd_last_enriched_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    return ExtractionResult(
        description=text,
        extraction_method="trafilatura_thin",
        source_url=source_url,
        success=False,
    )


# ── Readability fallback ────────────────────────────────────────────────

def extract_with_readability(html: str, *, source_url: str = "") -> ExtractionResult:
    """Last-resort cleanup using readability-lxml."""
    try:
        from readability import Document
    except ImportError:
        logger.debug("readability-lxml not installed; skipping.")
        return ExtractionResult(
            description="",
            extraction_method="readability_unavailable",
            source_url=source_url,
            success=False,
        )

    try:
        doc = Document(html)
        summary_html = doc.summary()
        text = _strip_html(summary_html)
    except Exception as exc:
        logger.debug("readability extraction failed: %s", exc)
        return ExtractionResult(
            description="",
            extraction_method="readability_error",
            source_url=source_url,
            success=False,
        )

    text = text.strip()
    if len(text) >= 80:
        return ExtractionResult(
            description=text,
            extraction_method="readability",
            source_url=source_url,
            source_kind="company_page",
            success=True,
            provenance={
                "jd_extraction_method": "readability",
                "jd_source_kind": "company_page",
                "jd_source_url": source_url,
                "jd_last_enriched_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    return ExtractionResult(
        description=text,
        extraction_method="readability_thin",
        source_url=source_url,
        success=False,
    )


# ── URL fetch helper ────────────────────────────────────────────────────

def _fetch_html(url: str) -> str | None:
    """Fetch raw HTML from a URL. Returns None on error."""
    try:
        with httpx.Client(headers=_HEADERS, follow_redirects=True, timeout=_FETCH_TIMEOUT) as client:
            response = client.get(url)
        if not response.is_success:
            logger.debug("Non-success %d for %s", response.status_code, url)
            return None
        return response.text
    except httpx.RequestError as exc:
        logger.debug("Request error fetching %s: %s", url, exc)
        return None


# ── Multi-source extraction pipeline ────────────────────────────────────

def extract_best_description(
    *,
    existing_description: str = "",
    source_name: str = "",
    source_url: str = "",
    company_url: str = "",
    canonical_apply_url: str = "",
    ats_description: str = "",
    ats_type: str = "",
) -> ExtractionResult:
    """Run the full extraction pipeline in source-priority order.

    Priority:
    1. ATS-provided plaintext/HTML if available
    2. Direct company or hosted apply URL
    3. JSON-LD / Microdata from page HTML
    4. Main-content extraction (trafilatura)
    5. LinkedIn guest-page HTML fallback (readability-lxml)
    """

    # ── 1. ATS-provided description ──────────────────────────────────────
    if ats_description and ats_description.strip():
        result = extract_from_ats_payload(
            description_text=ats_description,
            ats_type=ats_type,
            source_url=source_url,
        )
        if result.success and len(result.description) > len(existing_description):
            result.quality_improved = True
            return result

    # Already-strong ATS source? Don't re-fetch from weaker sources.
    source_lower = str(source_name or "").casefold()
    is_ats_origin = any(hint in source_lower for hint in ("greenhouse", "lever", "ashby", "ats_"))
    if is_ats_origin and existing_description and len(existing_description) >= 200:
        return ExtractionResult(
            description=existing_description,
            extraction_method="ats_existing_strong",
            source_url=source_url,
            source_kind="ats_structured",
            success=True,
        )

    # ── 2. Direct company/apply URL ──────────────────────────────────────
    direct_url = ""
    if canonical_apply_url and "linkedin" not in canonical_apply_url.casefold():
        direct_url = canonical_apply_url
    elif company_url:
        direct_url = company_url

    if direct_url:
        html = _fetch_html(direct_url)
        if html:
            # 3. Try JSON-LD / Microdata first
            structured = extract_from_structured_metadata(html, source_url=direct_url)
            if structured.success and len(structured.description) > len(existing_description):
                structured.quality_improved = True
                return structured

            # 4. Main-content extraction
            main = extract_main_content(html, source_url=direct_url)
            if main.success and len(main.description) > len(existing_description):
                main.quality_improved = True
                return main

            # Readability fallback on company page
            readable = extract_with_readability(html, source_url=direct_url)
            if readable.success and len(readable.description) > len(existing_description):
                readable.quality_improved = True
                return readable

    # ── 5. LinkedIn guest-page HTML fallback ─────────────────────────────
    linkedin_url = ""
    if source_url and "linkedin" in source_url.casefold():
        linkedin_url = source_url

    if linkedin_url:
        html = _fetch_html(linkedin_url)
        if html:
            # Try structured first even on LinkedIn
            structured = extract_from_structured_metadata(html, source_url=linkedin_url)
            if structured.success and len(structured.description) > len(existing_description):
                structured.source_kind = "linkedin_enriched"
                structured.provenance["jd_source_kind"] = "linkedin_enriched"
                structured.quality_improved = True
                return structured

            readable = extract_with_readability(html, source_url=linkedin_url)
            if readable.success and len(readable.description) > len(existing_description):
                readable.source_kind = "linkedin_enriched"
                readable.provenance["jd_source_kind"] = "linkedin_enriched"
                readable.quality_improved = True
                return readable

    # ── No improvement found ─────────────────────────────────────────────
    return ExtractionResult(
        description=existing_description,
        extraction_method="no_improvement",
        source_url=source_url,
        source_kind="unknown",
        success=False,
        quality_improved=False,
    )
