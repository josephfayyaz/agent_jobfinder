"""JobSpy integration for active LinkedIn job discovery."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import time

from sqlalchemy.orm import Session

from job_agent.config import get_settings
from job_agent.models import JobPost, JobTrackScore, ResumeTrack
from job_agent.services.matching import score_tracks_for_job

logger = logging.getLogger(__name__)
settings = get_settings()


def _build_seniority_query_suffix(target_seniority: str) -> str:
    """
    Append seniority-related terms to job queries to bias results toward
    the configured level. Returns empty string for 'mid', 'senior', 'any'.
    """
    if target_seniority == "intern":
        return " internship OR stage OR tirocinio"
    if target_seniority == "junior":
        return ' junior OR "entry level" OR graduate OR "new grad"'
    return ""


class JobSpyService:
    """Wraps jobspy library for LinkedIn public job board discovery."""

    def discover(
        self,
        query: str,
        location: str = "Italy",
        session: Session | None = None,
        limit: int | None = None,
        sources: list[str] | None = None,
    ) -> int:
        """
        Search for jobs using JobSpy, deduplicate against DB, create JobPost records.
        Returns count of new jobs ingested.
        """
        if not settings.use_jobspy:
            logger.info("JobSpy is disabled (USE_JOBSPY=false). Skipping discovery.")
            return 0
        if session is None:
            raise ValueError("A database session is required for JobSpy discovery.")

        try:
            from jobspy import scrape_jobs
        except ImportError:
            logger.error("jobspy package not installed. Run the project install command again.")
            return 0

        limit = limit or settings.jobspy_default_limit
        sources = sources or ["linkedin"]
        suffix = _build_seniority_query_suffix(settings.target_job_seniority)
        full_query = f"{query}{suffix}"

        logger.info(
            "JobSpy search: query=%r location=%r sources=%s limit=%d",
            full_query,
            location,
            sources,
            limit,
        )

        try:
            dataframe = scrape_jobs(
                site_name=sources,
                search_term=full_query,
                location=location,
                results_wanted=limit,
                country_indeed="Italy" if "italy" in location.lower() else None,
            )
        except Exception as exc:
            logger.error("JobSpy scrape failed: %s", exc)
            return 0

        if dataframe is None or dataframe.empty:
            logger.info("JobSpy returned no results for query=%r", full_query)
            return 0

        logger.info("JobSpy returned %d results", len(dataframe))

        tracks = session.query(ResumeTrack).filter_by(active=True).all()
        new_count = 0

        for _, row in dataframe.iterrows():
            row_data = row if isinstance(row, dict) else dict(row)
            url = str(row_data.get("job_url") or row_data.get("url") or "")
            if not url:
                continue

            if session.query(JobPost).filter_by(source_url=url).first():
                continue

            title = str(row_data.get("title") or "Unknown")
            company = str(row_data.get("company") or "Unknown")
            location_str = str(row_data.get("location") or location)
            description = str(row_data.get("description") or "")

            post = JobPost(
                source_name="jobspy_linkedin",
                source_url=url,
                canonical_apply_url=url,
                title=title,
                company=company,
                location=location_str,
                description=description,
                status="new",
                created_at=datetime.now(timezone.utc),
                last_seen_at=datetime.now(timezone.utc),
            )
            session.add(post)
            session.flush()

            if tracks:
                scored = score_tracks_for_job(post, tracks)
                for result in scored:
                    session.add(
                        JobTrackScore(
                            job_post_id=post.id,
                            resume_track_id=result["track_id"],
                            score=result["score"],
                            matched_keywords=result["matched_keywords"],
                        )
                    )

            new_count += 1
            time.sleep(0.1)

        session.commit()
        logger.info("JobSpy: ingested %d new jobs", new_count)
        time.sleep(settings.jobspy_request_delay)
        return new_count
