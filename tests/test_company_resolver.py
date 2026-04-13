from __future__ import annotations


def test_blocked_domains_filtered():
    from job_agent.services.company_resolver import _is_allowed_domain

    assert _is_allowed_domain("https://bendingspoons.com") is True
    assert _is_allowed_domain("https://www.linkedin.com/jobs/view/123") is False
    assert _is_allowed_domain("https://boards.greenhouse.io/company/job") is False
    assert _is_allowed_domain("https://company.workday.com") is False
    assert _is_allowed_domain("https://www.stepstone.de/jobs/data-engineer") is False
    assert _is_allowed_domain("https://www.xing.com/jobs/search") is False
    assert _is_allowed_domain("https://jobs.google.com/about") is False
    assert _is_allowed_domain("https://lever.co/company/acme") is False


def test_extract_from_description_finds_url():
    from job_agent.services.company_resolver import _extract_from_description

    description = "Visit our website at https://www.bendingspoons.com/careers for more info."
    result = _extract_from_description(description)
    assert result == "https://www.bendingspoons.com"


def test_extract_from_description_filters_job_boards():
    from job_agent.services.company_resolver import _extract_from_description

    description = "Apply at https://boards.greenhouse.io/bendingspoons/jobs/123"
    result = _extract_from_description(description)
    assert result is None


def test_find_company_url_returns_none_for_unknown():
    from job_agent.services.company_resolver import find_company_url

    result = find_company_url("Unknown")
    assert result is None


def test_find_company_url_description_fallback(monkeypatch):
    """When DuckDuckGo fails, falls back to description regex."""
    from job_agent.services import company_resolver

    monkeypatch.setattr(company_resolver, "_search_duckduckgo", lambda *args, **kwargs: None)
    monkeypatch.setattr(company_resolver, "_search_clearbit", lambda *args, **kwargs: None)

    result = company_resolver.find_company_url(
        company_name="Satispay",
        description="Learn more at https://www.satispay.com about our mission.",
    )
    assert result == "https://www.satispay.com"


def test_find_company_url_never_raises_on_internal_error(monkeypatch):
    from job_agent.services import company_resolver

    monkeypatch.setattr(company_resolver, "_search_duckduckgo", lambda *args, **kwargs: None)
    monkeypatch.setattr(company_resolver, "_search_clearbit", lambda *args, **kwargs: None)

    def _raise_error(_description: str) -> str | None:
        raise RuntimeError("forced error")

    monkeypatch.setattr(company_resolver, "_extract_from_description", _raise_error)

    result = company_resolver.find_company_url(
        company_name="Acme",
        description="Company text",
    )
    assert result is None
