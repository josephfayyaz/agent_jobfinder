# Phase 3.4 — Autonomous Company URL Discovery

## Goal
Automatically find a company's official website URL so cover letters can be personalized without any manual input. Stores the result in `JobPost.company_url` — resolved once, never again. Zero user intervention required.

**Priority chain:**
1. DuckDuckGo text search — free, no API key, no rate limit for personal use
2. Regex extraction from job description — fast, zero network calls
3. Clearbit Logo/Name API — optional, 50k calls/month free tier

## Dependencies
Add to `pyproject.toml` under `[project] dependencies`:
```
"duckduckgo-search>=8.0,<9",
```

Run: `/Users/youseffayyaz/miniforge3/bin/conda run -n ML pip install -e ".[dev]"`

## New Config Fields (`job_agent/config.py`)
```python
clearbit_api_key: str = Field(
    default="",
    description="Optional Clearbit API key for company URL fallback (50k calls/month free). Leave empty to use DuckDuckGo only."
)
```

Add to `.env`:
```
CLEARBIT_API_KEY=
```

## New File: `job_agent/services/company_resolver.py`

```python
"""Autonomous company website URL discovery."""

import logging
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Job board and aggregator domains to filter out — we want the company's own site
_BLOCKED_DOMAINS = {
    "linkedin.com", "indeed.com", "glassdoor.com", "monster.com",
    "ziprecruiter.com", "seek.com", "totaljobs.com", "reed.co.uk",
    "jobs.lever.co", "greenhouse.io", "workday.com", "icims.com",
    "taleo.net", "smartrecruiters.com", "jobs.ashbyhq.com",
    "boards.greenhouse.io", "apply.workable.com", "jobs.breezy.hr",
    "facebook.com", "twitter.com", "x.com", "youtube.com",
    "wikipedia.org", "wikidata.org", "bloomberg.com", "crunchbase.com",
    "pitchbook.com", "dnb.com",
}

# Regex: find "company.tld" patterns in plain text (job descriptions)
_URL_IN_TEXT_RE = re.compile(
    r"https?://(?:www\.)?([a-z0-9\-]+\.[a-z]{2,})",
    re.I,
)

# TLDs common in Italy + EU + global
_VALID_TLDS = {
    "com", "io", "ai", "co", "it", "eu", "de", "fr", "nl", "es",
    "se", "ch", "at", "be", "pl", "pt", "cz", "dk", "fi", "no",
    "tech", "dev", "app", "cloud", "net", "org",
}


def _is_allowed_domain(url: str) -> bool:
    """Return True if the URL is a company site (not a job board/aggregator)."""
    try:
        host = urlparse(url).netloc.lower().lstrip("www.")
        for blocked in _BLOCKED_DOMAINS:
            if host == blocked or host.endswith("." + blocked):
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

        for r in results:
            url = r.get("href") or r.get("url") or ""
            if url and _is_allowed_domain(url):
                # Normalize to origin only (strip paths like /careers)
                parsed = urlparse(url)
                return f"{parsed.scheme}://{parsed.netloc}"

    except Exception as exc:
        logger.debug("DuckDuckGo search failed for %r: %s", company_name, exc)

    return None


def _extract_from_description(description: str) -> str | None:
    """
    Fast regex pass over job description to find any company-domain URL.
    Useful when the JD directly mentions the company site.
    """
    if not description:
        return None

    for match in _URL_IN_TEXT_RE.finditer(description):
        url = match.group(0)
        domain = match.group(1)
        tld = domain.rsplit(".", 1)[-1].lower()
        if tld in _VALID_TLDS and _is_allowed_domain(url):
            parsed = urlparse(url)
            return f"{parsed.scheme}://{parsed.netloc}"

    return None


def _search_clearbit(company_name: str, api_key: str) -> str | None:
    """
    Use Clearbit's Name-to-Domain API (free tier: 50k/mo).
    Returns domain as https://company.com or None.
    """
    if not api_key:
        return None
    try:
        import httpx
        resp = httpx.get(
            "https://autocomplete.clearbit.com/v1/companies/suggest",
            params={"query": company_name},
            timeout=5,
        )
        if resp.is_success:
            data = resp.json()
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
    1. DuckDuckGo text search (free, no key, reliable)
    2. Regex extraction from job description text
    3. Clearbit Name-to-Domain API (if CLEARBIT_API_KEY set)

    Returns None if all methods fail. Never raises.
    Filters out job board URLs (LinkedIn, Indeed, Glassdoor, etc.).
    """
    if not company_name or company_name.lower() in ("unknown", "n/a", ""):
        return None

    from job_agent.config import get_settings
    settings = get_settings()

    # 1. DuckDuckGo
    url = _search_duckduckgo(company_name, location)
    if url:
        logger.info("Resolved %r via DuckDuckGo → %s", company_name, url)
        return url

    # 2. Description regex
    url = _extract_from_description(description)
    if url:
        logger.info("Resolved %r via description regex → %s", company_name, url)
        return url

    # 3. Clearbit
    url = _search_clearbit(company_name, settings.clearbit_api_key)
    if url:
        logger.info("Resolved %r via Clearbit → %s", company_name, url)
        return url

    logger.debug("Could not resolve company URL for %r", company_name)
    return None
```

## Integration: `job_agent/services/job_fetcher.py`

After enriching a job description, auto-resolve `company_url` if not already set:

```python
# In enrich_job() — after description is fetched and saved:
if not job.company_url and job.company and job.description:
    from job_agent.services.company_resolver import find_company_url
    resolved = find_company_url(
        company_name=job.company,
        location=job.location or "",
        description=job.description,
    )
    if resolved:
        job.company_url = resolved
        session.add(job)
        session.commit()
        logger.info("Auto-resolved company_url for job %d: %s", job.id, resolved)
```

## Integration: `job_agent/services/cover_letter.py`

In `generate_cover_letter()`, resolve if no URL provided and none stored:

```python
# In CoverLetterService.generate_cover_letter(), before fetch_company_context():
if not url_to_fetch and job.company:
    from job_agent.services.company_resolver import find_company_url
    resolved = find_company_url(
        company_name=job.company,
        location=job.location or "",
        description=job.description or "",
    )
    if resolved:
        url_to_fetch = resolved
        # Cache for future calls
        job.company_url = resolved
        self.session.add(job)
        self.session.flush()
        logger.info("Auto-resolved company URL for cover letter: %s", resolved)
```

## Tests
Add `tests/test_company_resolver.py`:

```python
def test_blocked_domains_filtered():
    from job_agent.services.company_resolver import _is_allowed_domain
    assert _is_allowed_domain("https://bendingspoons.com") is True
    assert _is_allowed_domain("https://www.linkedin.com/jobs/view/123") is False
    assert _is_allowed_domain("https://boards.greenhouse.io/company/job") is False
    assert _is_allowed_domain("https://company.workday.com") is False


def test_extract_from_description_finds_url():
    from job_agent.services.company_resolver import _extract_from_description
    desc = "Visit our website at https://www.bendingspoons.com/careers for more info."
    result = _extract_from_description(desc)
    assert result == "https://www.bendingspoons.com"


def test_extract_from_description_filters_job_boards():
    from job_agent.services.company_resolver import _extract_from_description
    desc = "Apply at https://boards.greenhouse.io/bendingspoons/jobs/123"
    result = _extract_from_description(desc)
    assert result is None


def test_find_company_url_returns_none_for_unknown():
    from job_agent.services.company_resolver import find_company_url
    # "Unknown" company name should return None immediately
    result = find_company_url("Unknown")
    assert result is None


def test_find_company_url_description_fallback(monkeypatch):
    """When DuckDuckGo fails, falls back to description regex."""
    from job_agent.services import company_resolver

    monkeypatch.setattr(company_resolver, "_search_duckduckgo", lambda *a, **kw: None)
    monkeypatch.setattr(company_resolver, "_search_clearbit", lambda *a, **kw: None)

    result = company_resolver.find_company_url(
        company_name="Satispay",
        description="Learn more at https://www.satispay.com about our mission.",
    )
    assert result == "https://www.satispay.com"
```

## Commit Message
```
feat: add autonomous company URL discovery via DuckDuckGo with description fallback (Phase 3.4)
```
