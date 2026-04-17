# Phase 3.5 — Parallel Job Ingestion

## Goal
Speed up the two slowest operations in the pipeline using `ThreadPoolExecutor`:
- **Career page scan:** 10 pages × ~2s each = ~20s sequential → ~4s with 5 workers
- **Job enrichment:** 20 jobs × ~2s each = ~40s sequential → ~8s with 5 workers

**Approach: ThreadPoolExecutor (NOT asyncio)**
All services use synchronous SQLAlchemy + synchronous httpx. A full asyncio refactor would be a large, risky change with no meaningful benefit for a local personal tool. ThreadPoolExecutor wraps sync HTTP calls with zero changes to the service layer.

**Thread-safety pattern:**
- Worker threads do HTTP fetching + HTML parsing only — no DB writes
- Worker threads return raw data (Python dicts/tuples)
- Main thread collects all results, then performs all DB writes in a single transaction
- This avoids SQLAlchemy session sharing across threads

## New Config Fields (`job_agent/config.py`)
```python
scan_max_workers: int = Field(
    default=5,
    description="Max concurrent threads for parallel career page scanning and job enrichment. Set to 1 to disable parallelism."
)
```

Add to `.env`:
```
SCAN_MAX_WORKERS=5
```

---

## Changes to `job_agent/services/career_scanner.py`

Add `scan_all_parallel()` alongside the existing `scan_all()`. The worker calls the parallel version; sequential remains available for testing.

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field


@dataclass
class _ScannedJob:
    """Raw job data extracted by a worker thread (no DB objects)."""
    company: str
    title: str
    source_url: str
    location: str
    description: str = ""


def _scan_one_thread(source_data: dict) -> list[_ScannedJob]:
    """
    Pure HTTP + HTML parsing — no DB access. Safe to run in a thread pool.
    Receives source as a plain dict (not ORM object, not thread-safe).
    Returns list of raw ScannedJob records.
    """
    company = source_data["company"]
    career_url = source_data["career_url"]
    css_selector = source_data.get("css_selector")
    country = source_data.get("country", "Italy")

    results = []

    try:
        resp = httpx.get(career_url, headers=_HEADERS, follow_redirects=True, timeout=15)
    except httpx.RequestError as exc:
        logger.warning("Network error fetching %s: %s", career_url, exc)
        return results

    if not resp.is_success:
        logger.warning("HTTP %d for %s", resp.status_code, career_url)
        return results

    soup = BeautifulSoup(resp.text, "lxml")

    if css_selector:
        links = soup.select(css_selector)
    else:
        links = soup.find_all("a", href=True)

    for link in links:
        href = link.get("href", "")
        if not href:
            continue

        if href.startswith("http"):
            url = href
        elif href.startswith("/"):
            from urllib.parse import urlparse
            parsed = urlparse(career_url)
            url = f"{parsed.scheme}://{parsed.netloc}{href}"
        else:
            continue

        if not _looks_like_job_url(url):
            continue

        title = _extract_title_from_link(link)
        if not title or len(title) < 3:
            continue

        results.append(_ScannedJob(
            company=company,
            title=title,
            source_url=url,
            location=country,
        ))

    return results


class CareerPageScanner:
    # ... existing scan_all() and _scan_one() methods unchanged ...

    def scan_all_parallel(self, session: Session, max_workers: int | None = None) -> int:
        """
        Parallel version of scan_all() — fetches all career pages concurrently.
        HTTP work happens in threads; all DB writes happen in the main thread.
        Returns total number of new JobPost records created.
        """
        from job_agent.config import get_settings
        settings = get_settings()
        workers = max_workers or settings.scan_max_workers

        sources = session.query(CareerPageSource).filter_by(active=True).all()
        if not sources:
            logger.info("No active career page sources to scan")
            return 0

        logger.info("Parallel scanning %d career pages with %d workers", len(sources), workers)

        # Serialize ORM objects to plain dicts before threading (thread-safe)
        source_dicts = [
            {
                "id": s.id,
                "company": s.company,
                "career_url": s.career_url,
                "css_selector": s.css_selector,
                "country": s.country,
            }
            for s in sources
        ]

        # Collect raw results from threads (no DB writes in threads)
        all_results: dict[int, list[_ScannedJob]] = {}  # source_id → jobs

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_source = {
                executor.submit(_scan_one_thread, sd): sd
                for sd in source_dicts
            }
            for future in as_completed(future_to_source):
                sd = future_to_source[future]
                try:
                    jobs = future.result()
                    all_results[sd["id"]] = jobs
                    logger.debug("Thread result for %s: %d jobs found", sd["company"], len(jobs))
                except Exception as exc:
                    logger.error("Thread failed for %s: %s", sd["company"], exc)
                    all_results[sd["id"]] = []

        # DB writes — single thread, main session
        tracks = session.query(ResumeTrack).filter_by(active=True).all()
        total_new = self._insert_posts(all_results, sources, session, tracks)
        session.commit()

        logger.info("Parallel career scan complete: %d new jobs total", total_new)
        return total_new

    def _insert_posts(
        self,
        results: dict,
        sources: list,
        session: Session,
        tracks: list,
    ) -> int:
        """Insert new JobPost records from parallel scan results. Main thread only."""
        source_map = {s.id: s for s in sources}
        new_count = 0

        for source_id, jobs in results.items():
            source = source_map.get(source_id)
            if not source:
                continue

            new_from_source = 0
            for job in jobs:
                # Deduplicate — check after all threads have returned
                if session.query(JobPost).filter_by(source_url=job.source_url).first():
                    continue

                post = JobPost(
                    title=job.title,
                    company=job.company,
                    location=job.location,
                    description=job.description,
                    source_url=job.source_url,
                    status="new",
                    created_at=datetime.now(timezone.utc),
                )
                session.add(post)
                session.flush()

                if tracks:
                    scored = score_tracks_for_job(post, tracks)
                    for result in scored:
                        session.add(JobTrackScore(
                            job_post_id=post.id,
                            resume_track_id=result["track_id"],
                            score=result["score"],
                            matched_keywords=result["matched_keywords"],
                        ))

                new_from_source += 1
                new_count += 1

            # Update source metadata
            source.last_checked_at = datetime.now(timezone.utc)
            source.last_new_jobs = new_from_source

        return new_count
```

## Changes to `job_agent/services/job_fetcher.py`

Add `enrich_pending_parallel()` alongside the existing `enrich_pending()`.

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass


@dataclass
class _FetchedDescription:
    """Result from a worker thread — plain data, no ORM."""
    job_id: int
    description: str
    company_url: str | None = None
    success: bool = True


def _fetch_one_thread(job_data: dict) -> _FetchedDescription:
    """
    Fetch job description for one job. Thread-safe (no DB access).
    job_data: plain dict with id, source_url, company, location.
    """
    job_id = job_data["id"]
    source_url = job_data["source_url"]

    if not source_url:
        return _FetchedDescription(job_id=job_id, description="", success=False)

    try:
        description = _fetch_description_from_url(source_url)  # existing logic
        return _FetchedDescription(job_id=job_id, description=description, success=True)
    except Exception as exc:
        logger.warning("Failed to fetch description for job %d: %s", job_id, exc)
        return _FetchedDescription(job_id=job_id, description="", success=False)


class JobFetcher:
    # ... existing enrich_pending() and enrich_job() methods unchanged ...

    def enrich_pending_parallel(
        self,
        session: Session,
        limit: int = 20,
        max_workers: int | None = None,
    ) -> int:
        """
        Parallel version of enrich_pending() — fetches job descriptions concurrently.
        Returns count of jobs successfully enriched.
        """
        from job_agent.config import get_settings
        settings = get_settings()
        workers = max_workers or settings.scan_max_workers

        pending = (
            session.query(JobPost)
            .filter(
                (JobPost.description == "") | (JobPost.description.is_(None)),
                JobPost.source_url.isnot(None),
            )
            .limit(limit)
            .all()
        )

        if not pending:
            logger.info("No pending jobs to enrich")
            return 0

        logger.info(
            "Parallel enriching %d jobs with %d workers", len(pending), workers
        )

        # Serialize to dicts before threading
        job_dicts = [
            {
                "id": j.id,
                "source_url": j.source_url,
                "company": j.company,
                "location": j.location,
            }
            for j in pending
        ]

        # Fetch concurrently
        fetch_results: list[_FetchedDescription] = []
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_fetch_one_thread, jd): jd for jd in job_dicts}
            for future in as_completed(futures):
                try:
                    fetch_results.append(future.result())
                except Exception as exc:
                    jd = futures[future]
                    logger.error("Thread failed for job %d: %s", jd["id"], exc)

        # DB writes — main thread only
        job_map = {j.id: j for j in pending}
        enriched = 0

        for result in fetch_results:
            if not result.success or not result.description:
                continue
            job = job_map.get(result.job_id)
            if not job:
                continue

            job.description = result.description
            if result.company_url and not job.company_url:
                job.company_url = result.company_url
            session.add(job)
            enriched += 1

        session.commit()
        logger.info("Parallel enrichment complete: %d/%d jobs enriched", enriched, len(pending))
        return enriched
```

## Worker Integration (`job_agent/worker.py`)

Replace sequential calls with parallel versions:

```python
# Replace:
CareerPageScanner().scan_all(session)
# With:
CareerPageScanner().scan_all_parallel(session)

# Replace:
JobFetcher().enrich_pending(session, limit=20)
# With:
JobFetcher().enrich_pending_parallel(session, limit=20)
```

## Tests
Add `tests/test_parallel_ingestion.py`:

```python
from unittest.mock import patch, MagicMock
import pandas as pd


def test_scan_all_parallel_returns_same_count_as_sequential(db_session, monkeypatch):
    """Parallel scan produces the same result as sequential scan."""
    from job_agent.models import CareerPageSource
    from job_agent.services.career_scanner import CareerPageScanner

    # Add a fake career page source
    db_session.add(CareerPageSource(
        company="TestCo",
        career_url="https://testco.example.com/jobs",
        active=True,
        country="Italy",
    ))
    db_session.commit()

    fake_html = """
    <html><body>
      <a href="/jobs/data-engineer">Data Engineer</a>
      <a href="/about">About Us</a>
    </body></html>
    """

    import httpx
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.is_success = True
    mock_response.text = fake_html
    mock_response.status_code = 200

    with patch("httpx.get", return_value=mock_response):
        count_parallel = CareerPageScanner().scan_all_parallel(db_session, max_workers=2)

    assert count_parallel == 1  # only the /jobs/ link qualifies


def test_scan_parallel_deduplicates(db_session, monkeypatch):
    """Parallel scan does not insert duplicate URLs."""
    from job_agent.models import CareerPageSource, JobPost
    from job_agent.services.career_scanner import CareerPageScanner

    existing_url = "https://testco.example.com/jobs/data-engineer"
    db_session.add(JobPost(
        title="Data Engineer", company="TestCo",
        source_url=existing_url, status="new", description=""
    ))
    db_session.add(CareerPageSource(
        company="TestCo",
        career_url="https://testco.example.com/jobs",
        active=True, country="Italy",
    ))
    db_session.commit()

    fake_html = f'<html><body><a href="{existing_url}">Data Engineer</a></body></html>'

    import httpx
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.is_success = True
    mock_response.text = fake_html
    mock_response.status_code = 200

    with patch("httpx.get", return_value=mock_response):
        count = CareerPageScanner().scan_all_parallel(db_session, max_workers=2)

    assert count == 0  # duplicate skipped


def test_enrich_parallel_writes_descriptions(db_session, monkeypatch):
    """Parallel enrichment writes descriptions to DB."""
    from job_agent.models import JobPost
    from job_agent.services.job_fetcher import JobFetcher

    job = JobPost(
        title="Data Engineer", company="TestCo",
        source_url="https://testco.example.com/jobs/de",
        status="new", description="",
    )
    db_session.add(job)
    db_session.commit()

    monkeypatch.setattr(
        "job_agent.services.job_fetcher._fetch_description_from_url",
        lambda url: "Exciting data engineering role at TestCo."
    )

    count = JobFetcher().enrich_pending_parallel(db_session, limit=5, max_workers=2)
    assert count == 1
    db_session.refresh(job)
    assert "TestCo" in job.description
```

## Commit Message
```
feat: add parallel career page scanning and job enrichment with ThreadPoolExecutor (Phase 3.5)
```
