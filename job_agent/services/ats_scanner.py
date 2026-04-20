"""Zero-token ATS API scanner for Greenhouse, Lever, and Ashby."""

from __future__ import annotations

import httpx

_TIMEOUT = 10.0
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


class AtsApiScanner:
    """Fetches job listings directly from ATS public JSON APIs."""

    def fetch_jobs(self, ats_type: str, ats_slug: str) -> list[dict]:
        """
        Returns list of dicts: [{title, url, location}]
        Raises httpx.HTTPError on failure (caller handles fallback).
        """
        ats_type_normalized = ats_type.strip().lower()
        if ats_type_normalized == "greenhouse":
            return self._fetch_greenhouse(ats_slug)
        if ats_type_normalized == "lever":
            return self._fetch_lever(ats_slug)
        if ats_type_normalized == "ashby":
            return self._fetch_ashby(ats_slug)
        raise ValueError(f"Unknown ats_type: {ats_type}")

    def _fetch_greenhouse(self, slug: str) -> list[dict]:
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
        response = httpx.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return [
            {
                "title": job.get("title", ""),
                "url": job.get("absolute_url", ""),
                "location": (job.get("location") or {}).get("name") or "",
            }
            for job in data.get("jobs", [])
        ]

    def _fetch_lever(self, slug: str) -> list[dict]:
        url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
        response = httpx.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return [
            {
                "title": job.get("text", ""),
                "url": job.get("hostedUrl", ""),
                "location": (job.get("categories") or {}).get("location") or "",
            }
            for job in (data if isinstance(data, list) else [])
        ]

    def _fetch_ashby(self, slug: str) -> list[dict]:
        url = f"https://jobs.ashbyhq.com/api/non-user-facing/job-board/details/{slug}"
        response = httpx.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return [
            {
                "title": job.get("title", ""),
                "url": job.get("jobPostingUrl", ""),
                "location": job.get("locationName") or "",
            }
            for job in data.get("jobPostings", [])
        ]
