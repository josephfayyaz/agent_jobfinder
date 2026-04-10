"""Cover letter generation with company website context."""

from __future__ import annotations

import logging
from urllib.parse import urljoin, urlparse
from uuid import UUID

from bs4 import BeautifulSoup
import httpx
from sqlalchemy.orm import Session

from job_agent.llm import LLMRouter, ProviderUnavailableError
from job_agent.models import JobPost, MasterProfile, ResumeDraft, ResumeTrack
from job_agent.services.prompts import (
    build_cover_letter_system_prompt,
    build_cover_letter_user_prompt,
)

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Job-Agent/1.0)",
    "Accept": "text/html,application/xhtml+xml",
}
_CONTEXT_MAX_CHARS = 3000
_ABOUT_PATHS = ["/about", "/about-us", "/mission", "/chi-siamo", "/company"]


def fetch_company_context(company_url: str) -> str:
    """
    Fetch company About/Mission page and extract text for prompt context.
    Tries homepage + known About paths. Returns empty string on failure.
    """
    if not company_url:
        return ""

    parsed = urlparse(company_url)
    if not parsed.scheme or not parsed.netloc:
        return ""

    base = f"{parsed.scheme}://{parsed.netloc}"
    pages_to_try = [company_url, *[urljoin(base, path) for path in _ABOUT_PATHS]]
    collected: list[str] = []

    for url in pages_to_try[:3]:
        try:
            response = httpx.get(url, headers=_HEADERS, follow_redirects=True, timeout=10)
            if not response.is_success:
                continue
            soup = BeautifulSoup(response.text, "lxml")
            for tag in soup(["nav", "footer", "script", "style", "header"]):
                tag.decompose()
            for selector in ["[class*='about']", "[class*='mission']", "[class*='values']", "main", "article"]:
                element = soup.select_one(selector)
                if element is None:
                    continue
                text = element.get_text(separator=" ", strip=True)
                if len(text) > 100:
                    collected.append(text[:1000])
                    break
        except Exception as exc:
            logger.debug("Could not fetch company page %s: %s", url, exc)

    if not collected:
        return ""
    return " ".join(collected)[:_CONTEXT_MAX_CHARS]


class CoverLetterService:
    """Generates and manages cover letters for ResumeDraft records."""

    def __init__(self, session: Session, router: LLMRouter | None = None):
        self.session = session
        self.router = router or LLMRouter()

    def generate_cover_letter(
        self,
        draft_id: UUID,
        company_url: str | None = None,
    ) -> ResumeDraft:
        """
        Generate a cover letter for an existing ResumeDraft.
        Fetches company context from company_url if provided.
        Stores result in the draft and returns the updated ResumeDraft.
        """
        draft = self.session.get(ResumeDraft, draft_id)
        if draft is None:
            raise ValueError(f"ResumeDraft {draft_id} not found")

        job = self.session.get(JobPost, draft.job_post_id)
        profile = self.session.get(MasterProfile, 1)
        track = self.session.get(ResumeTrack, draft.resume_track_id)

        if job is None or profile is None or track is None:
            raise ValueError("Missing job, profile, or track — cannot generate cover letter")

        url_to_fetch = company_url or job.company_url or ""
        if url_to_fetch and not url_to_fetch.startswith("http"):
            url_to_fetch = f"https://{url_to_fetch}"

        logger.info("Fetching company context from: %s", url_to_fetch or "(none)")
        company_context = fetch_company_context(url_to_fetch) if url_to_fetch else ""
        if company_context:
            logger.info("Got %d chars of company context", len(company_context))
        else:
            logger.info("No company context available — generating without it")

        profile_dict = {
            "full_name": profile.full_name,
            "brand_summary": profile.public_brand_summary,
            "education": profile.education or [],
            "experiences": profile.experiences or [],
        }
        track_dict = {
            "title": track.title,
            "emphasis": track.emphasis,
        }
        job_dict = {
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "description": job.description,
            "company_url": url_to_fetch,
            "source_url": job.source_url,
        }

        try:
            result = self.router.generate(
                role="writer",
                system_prompt=build_cover_letter_system_prompt(),
                user_prompt=build_cover_letter_user_prompt(profile_dict, track_dict, job_dict, company_context),
                temperature=0.35,
            )
            subject = result.get("subject") or f"Application — {job.title} — {profile.full_name}"
            body = result.get("body") or self._heuristic_cover_letter(profile_dict, job_dict)
        except ProviderUnavailableError:
            subject = f"Application — {job.title} — {profile.full_name}"
            body = self._heuristic_cover_letter(profile_dict, job_dict)

        draft.cover_letter_text = body
        draft.cover_letter_subject = subject
        self.session.commit()
        self.session.refresh(draft)

        logger.info("Cover letter generated for draft %s (%d chars)", draft_id, len(body))
        return draft

    def _heuristic_cover_letter(self, profile: dict, job: dict) -> str:
        """Fallback plain-text cover letter when the LLM is unavailable."""
        name = profile.get("full_name", "Yousef Fayyaz")
        title = job.get("title", "this role")
        company = job.get("company", "your organization")
        return (
            f"Dear Hiring Team,\n\n"
            f"My name is {name}, a Master's student in Computer Engineering at Politecnico di Torino, "
            f"expected to graduate in June 2026. {company}'s work in data and technology caught my attention "
            f"and I am applying for the {title} position.\n\n"
            "Through academic projects and internships, I have developed strong skills in data engineering, "
            "Python, and cloud-based analytics pipelines. I would welcome the opportunity to contribute to "
            "your team and grow in a professional European environment.\n\n"
            "I would appreciate either a brief call at your convenience or a reply by email if that is easier.\n\n"
            f"Best regards,\n{name}"
        )
