"""Autonomous company website URL discovery."""

from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

_BLOCKED_DOMAINS = {
    "linkedin.com",
    "indeed.com",
    "glassdoor.com",
    "monster.com",
    "ziprecruiter.com",
    "seek.com",
    "totaljobs.com",
    "reed.co.uk",
    "stepstone.de",
    "xing.com",
    "jobs.google.com",
    "lever.co",
    "jobs.lever.co",
    "greenhouse.io",
    "workday.com",
    "icims.com",
    "taleo.net",
    "smartrecruiters.com",
    "jobs.ashbyhq.com",
    "boards.greenhouse.io",
    "apply.workable.com",
    "jobs.breezy.hr",
    "facebook.com",
    "twitter.com",
    "x.com",
    "youtube.com",
    "wikipedia.org",
    "wikidata.org",
    "bloomberg.com",
    "crunchbase.com",
    "pitchbook.com",
    "dnb.com",
}

_URL_IN_TEXT_RE = re.compile(
    r"https?://(?:www\.)?([a-z0-9\-]+\.[a-z]{2,})",
    re.I,
)

_VALID_TLDS = {
    "com",
    "io",
    "ai",
    "co",
    "it",
    "eu",
    "de",
    "fr",
    "nl",
    "es",
    "se",
    "ch",
    "at",
    "be",
    "pl",
    "pt",
    "cz",
    "dk",
    "fi",
    "no",
    "tech",
    "dev",
    "app",
    "cloud",
    "net",
    "org",
}


def _is_allowed_domain(url: str) -> bool:
    """Return True if the URL is a company site, not a job board or aggregator."""
    try:
        host = urlparse(url).netloc.lower().lstrip("www.")
        for blocked in _BLOCKED_DOMAINS:
            if host == blocked or host.endswith(f".{blocked}"):
                return False
        return True
    except Exception:
        return False


def _search_duckduckgo(company_name: str, location: str = "") -> str | None:
    """
    Search DuckDuckGo for the company's official website.
    Returns the first non-blocked URL, or None.
    """
    try:
        from duckduckgo_search import DDGS

        query = f"{company_name} official website"
        if location:
            query += f" {location}"

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))

        for result in results:
            url = result.get("href") or result.get("url") or ""
            if url and _is_allowed_domain(url):
                parsed = urlparse(url)
                return f"{parsed.scheme}://{parsed.netloc}"
    except Exception as exc:
        logger.debug("DuckDuckGo search failed for %r: %s", company_name, exc)

    return None


def _extract_from_description(description: str) -> str | None:
    """
    Fast regex pass over job description to find any company-domain URL.
    Useful when the description directly mentions the company site.
    """
    if not description:
        return None

    try:
        for match in _URL_IN_TEXT_RE.finditer(description):
            url = match.group(0)
            domain = match.group(1)
            tld = domain.rsplit(".", 1)[-1].lower()
            if tld in _VALID_TLDS and _is_allowed_domain(url):
                parsed = urlparse(url)
                return f"{parsed.scheme}://{parsed.netloc}"
    except Exception as exc:
        logger.debug("Description URL extraction failed: %s", exc)

    return None


def _search_clearbit(company_name: str, api_key: str) -> str | None:
    """
    Use Clearbit's Name-to-Domain API.
    Returns domain as https://company.com or None.
    """
    if not api_key:
        return None
    try:
        response = httpx.get(
            "https://autocomplete.clearbit.com/v1/companies/suggest",
            params={"query": company_name},
            timeout=5,
        )
        if response.is_success:
            data = response.json()
            if data:
                domain = data[0].get("domain", "")
                if domain:
                    return f"https://{domain}"
    except Exception as exc:
        logger.debug("Clearbit lookup failed for %r: %s", company_name, exc)
    return None


def find_company_url(
    company_name: str,
    location: str = "",
    description: str = "",
) -> str | None:
    """
    Auto-discover a company's official website URL.

    Priority:
    1. DuckDuckGo text search
    2. Regex extraction from job description text
    3. Clearbit Name-to-Domain API
    """
    try:
        company_name_text = str(company_name or "").strip()
        if not company_name_text or company_name_text.lower() in {"unknown", "n/a"}:
            return None

        from job_agent.config import get_settings

        settings = get_settings()

        url = _search_duckduckgo(company_name_text, str(location or ""))
        if url:
            logger.info("Resolved %r via DuckDuckGo -> %s", company_name_text, url)
            return url

        url = _extract_from_description(str(description or ""))
        if url:
            logger.info("Resolved %r via description regex -> %s", company_name_text, url)
            return url

        url = _search_clearbit(company_name_text, settings.clearbit_api_key)
        if url:
            logger.info("Resolved %r via Clearbit -> %s", company_name_text, url)
            return url

        logger.debug("Could not resolve company URL for %r", company_name_text)
        return None
    except Exception as exc:
        logger.debug("Company URL resolution failed for %r: %s", company_name, exc)
        return None
