from __future__ import annotations

import subprocess
from uuid import UUID

import click
import httpx
from rich.console import Console
from rich.table import Table
from sqlalchemy import func

from job_agent.config import get_settings
from job_agent.db import SessionLocal

console = Console()
settings = get_settings()


def _jobs_query(session, threshold: int):
    from job_agent.models import JobPost, JobTrackScore

    subq = (
        session.query(
            JobTrackScore.job_post_id,
            func.max(JobTrackScore.score).label("max_score"),
        )
        .group_by(JobTrackScore.job_post_id)
        .subquery()
    )
    if threshold > 0:
        return (
            session.query(JobPost, subq.c.max_score)
            .join(subq, JobPost.id == subq.c.job_post_id)
            .filter(subq.c.max_score >= threshold)
            .order_by(subq.c.max_score.desc())
        )
    return (
        session.query(JobPost, subq.c.max_score)
        .outerjoin(subq, JobPost.id == subq.c.job_post_id)
        .order_by(JobPost.created_at.desc())
    )


@click.group()
def cli():
    """Local LLM Job Agent — daily operations CLI."""


@cli.group()
def jobs():
    """Job discovery and management."""


@cli.group()
def cv():
    """CV generation and management."""


@cli.group()
def thesis():
    """Thesis/traineeship target management."""


@cli.group()
def worker():
    """Worker process operations."""


@jobs.command("sync")
def jobs_sync():
    """Pull unread LinkedIn alert emails from Gmail and ingest new jobs."""
    from job_agent.services.gmail import GmailService

    with SessionLocal() as session:
        new_posts = GmailService().sync_jobs(session)
    console.print(f"[green]Synced {len(new_posts)} new jobs from Gmail.[/green]")
    for post in new_posts:
        console.print(f"  • {post.title} @ {post.company} [{post.id}]")


@jobs.command("list")
@click.option("--limit", default=20, help="Number of jobs to show")
@click.option("--all", "show_all", is_flag=True, help="Show all jobs ignoring min_score filter")
@click.option("--min-score", default=None, type=int, help="Override min score filter")
def jobs_list(limit, show_all, min_score):
    """List job posts with their best track match score."""
    threshold = 0 if show_all else (min_score if min_score is not None else settings.match_min_score)

    with SessionLocal() as session:
        rows = _jobs_query(session, threshold).limit(limit).all()

    table = Table(title="Jobs")
    table.add_column("ID")
    table.add_column("Title")
    table.add_column("Company")
    table.add_column("Location")
    table.add_column("Score")
    table.add_column("Status")

    for job, score in rows:
        table.add_row(
            str(job.id),
            job.title,
            job.company,
            job.location or job.city or "",
            "-" if score is None else str(round(float(score), 1)),
            job.status,
        )
    console.print(table)


@jobs.command("enrich-pending")
@click.option("--limit", default=10)
def jobs_enrich(limit):
    """Fetch descriptions for jobs with empty description fields."""
    from job_agent.services.job_fetcher import JobFetcher

    with SessionLocal() as session:
        count = JobFetcher().enrich_pending(session, limit=limit)
    console.print(f"[green]Enriched {count} jobs.[/green]")


@jobs.command("discover")
@click.option("--query", required=True, help='Search query e.g. "Data Engineer"')
@click.option("--location", default="Italy", help="Location e.g. Italy, Germany, Netherlands")
@click.option("--limit", default=25)
def jobs_discover(query, location, limit):
    """Discover jobs via JobSpy (requires USE_JOBSPY=true in .env)."""
    if not getattr(settings, "use_jobspy", False):
        console.print("[yellow]JobSpy is disabled. Set USE_JOBSPY=true in .env to enable.[/yellow]")
        return
    from job_agent.services.jobspy_service import JobSpyService

    with SessionLocal() as session:
        count = JobSpyService().discover(query=query, location=location, limit=limit, session=session)
    console.print(f"[green]Discovered and ingested {count} new jobs.[/green]")


@cv.command("generate")
@click.argument("job_id")
@click.option("--track", "track_slug", default=None, help="Force a specific resume track slug")
def cv_generate(job_id, track_slug):
    """Queue a CV generation workflow for a job."""
    from job_agent.models import JobTrackScore
    from job_agent.services.workflows import CVWorkflowService

    job_uuid = UUID(job_id)
    with SessionLocal() as session:
        svc = CVWorkflowService(session)
        if track_slug is None:
            best = (
                session.query(JobTrackScore)
                .filter_by(job_post_id=job_uuid)
                .order_by(JobTrackScore.score.desc())
                .first()
            )
            track_slug = best.resume_track.slug if best and best.resume_track else "data-engineering-analytics"
        task = svc.queue_cv_workflow(job_uuid, track_slug)
    console.print(f"[green]Queued CV workflow task {task.id} for job {job_id} (track: {track_slug})[/green]")
    console.print("Run [bold]job-agent worker start[/bold] to process, or check status with [bold]job-agent cv list[/bold]")


@cv.command("list")
@click.option("--job-id", default=None, help="Filter by job UUID")
@click.option("--limit", default=10)
def cv_list(job_id, limit):
    """List resume drafts with score, status, and track."""
    from job_agent.models import JobPost, ResumeDraft, ResumeTrack

    with SessionLocal() as session:
        query = (
            session.query(ResumeDraft, JobPost, ResumeTrack)
            .join(JobPost, ResumeDraft.job_post_id == JobPost.id)
            .join(ResumeTrack, ResumeDraft.resume_track_id == ResumeTrack.id)
            .order_by(ResumeDraft.created_at.desc())
        )
        if job_id:
            query = query.filter(ResumeDraft.job_post_id == UUID(job_id))
        rows = query.limit(limit).all()

    table = Table(title="CV Drafts")
    table.add_column("ID")
    table.add_column("Job")
    table.add_column("Track")
    table.add_column("Score")
    table.add_column("Status")
    table.add_column("Approved")

    for draft, job, track in rows:
        table.add_row(
            str(draft.id),
            job.title,
            track.slug,
            "-" if draft.score is None else str(round(float(draft.score), 1)),
            draft.status,
            str(draft.approved),
        )
    console.print(table)


@cv.command("pdf")
@click.argument("draft_id")
@click.option("--open", "open_file", is_flag=True, default=True, help="Open PDF after compiling")
def cv_pdf(draft_id, open_file):
    """Compile a draft's LaTeX file to PDF and optionally open it."""
    from job_agent.models import ResumeDraft
    from job_agent.services.documents import compile_pdf

    with SessionLocal() as session:
        draft = session.query(ResumeDraft).filter_by(id=UUID(draft_id)).first()
        if not draft or not draft.tex_path:
            console.print(f"[red]Draft {draft_id} not found or has no .tex file.[/red]")
            return
        pdf_path = compile_pdf(draft.tex_path)
    console.print(f"[green]PDF compiled: {pdf_path}[/green]")
    if open_file:
        subprocess.run(["open", str(pdf_path)], check=False)


@cv.command("cover-letter")
@click.argument("draft_id")
@click.option("--company-url", default=None, help="Company website URL for culture alignment")
def cv_cover_letter(draft_id, company_url):
    """Generate a cover letter for an approved CV draft."""
    from job_agent.services.cover_letter import CoverLetterService

    with SessionLocal() as session:
        svc = CoverLetterService(session)
        draft = svc.generate_cover_letter(UUID(draft_id), company_url=company_url)
    console.print(f"[green]Cover letter generated for draft {draft_id}.[/green]")
    console.print("\n--- SUBJECT ---")
    console.print(draft.cover_letter_subject or "(no subject)")
    console.print("\n--- BODY ---")
    console.print(draft.cover_letter_text or "(empty)")


@thesis.command("add")
def thesis_add():
    """Interactively add a new thesis/traineeship target."""
    from job_agent.models import ThesisTarget

    name = click.prompt("Name (professor/company)")
    institution = click.prompt("Institution")
    type_ = click.prompt("Type", type=click.Choice(["professor", "company", "lab", "research_group"]))
    country = click.prompt("Country", default="Italy")
    research_area = click.prompt("Research area")
    email = click.prompt("Email (optional)", default="", show_default=False)
    notes = click.prompt("Notes (optional)", default="", show_default=False)
    priority = click.prompt("Priority 1-5 (1=highest)", default=3, type=int)
    with SessionLocal() as session:
        target = ThesisTarget(
            type=type_,
            name=name,
            institution=institution,
            country=country,
            research_area=research_area,
            email=email or None,
            notes=notes or None,
            priority=priority,
        )
        session.add(target)
        session.commit()
        session.refresh(target)
    console.print(f"[green]Created thesis target {target.id}: {target.name}[/green]")


@thesis.command("list")
@click.option("--status", default=None)
def thesis_list(status):
    """List thesis targets, optionally filtered by status."""
    from job_agent.models import ThesisTarget

    with SessionLocal() as session:
        query = session.query(ThesisTarget).order_by(ThesisTarget.priority.asc(), ThesisTarget.created_at.desc())
        if status:
            query = query.filter(ThesisTarget.status == status)
        rows = query.all()

    table = Table(title="Thesis Targets")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Institution")
    table.add_column("Country")
    table.add_column("Area")
    table.add_column("Status")
    table.add_column("Priority")

    for target in rows:
        table.add_row(
            str(target.id),
            target.name,
            target.institution,
            target.country,
            target.research_area,
            target.status,
            str(target.priority),
        )
    console.print(table)


@thesis.command("email")
@click.argument("target_id", type=int)
def thesis_email(target_id):
    """Generate an outreach email for a thesis target."""
    from job_agent.services.thesis_outreach import ThesisOutreachService

    with SessionLocal() as session:
        draft = ThesisOutreachService().generate_email(target_id, session)
    console.print(f"[green]Outreach email draft {draft.id} created.[/green]")
    console.print(f"\n[bold]Subject:[/bold] {draft.subject}")
    console.print(f"\n[bold]Body:[/bold]\n{draft.body_text}")
    console.print(f"\nApprove: POST /outreach-drafts/{draft.id}/approve")


@cli.command("config")
def config_show():
    """Show key configuration settings."""
    table = Table(title="Job Agent Config")
    table.add_column("Setting")
    table.add_column("Value")
    pairs = [
        ("Target seniority", settings.target_job_seniority),
        ("Match min score", str(settings.match_min_score)),
        ("CV pass score", str(settings.cv_pass_score)),
        ("CV revise score", str(settings.cv_revise_score)),
        ("LM Studio (small)", settings.lm_studio_small_model),
        ("LM Studio (writer)", settings.lm_studio_writer_model),
        ("Gmail auto sync", str(settings.gmail_auto_sync)),
        ("Semantic matching weight", str(settings.semantic_matching_weight)),
        ("Use Claude review", str(settings.use_claude_final_review)),
        ("Use JobSpy", str(getattr(settings, "use_jobspy", False))),
    ]
    for key, value in pairs:
        table.add_row(key, value)
    console.print(table)


@worker.command("start")
def worker_start():
    """Start the background worker (Gmail sync + CV workflow processor)."""
    console.print("[bold green]Starting background worker... (Ctrl+C to stop)[/bold green]")
    from job_agent.worker import main as worker_main

    worker_main()


@cli.command("health")
def health():
    """Show system status and dashboard summary."""
    from job_agent.llm import LLMRouter
    from job_agent.models import JobPost, JobTrackScore, ResumeDraft
    from job_agent.services.documents import check_pdflatex

    try:
        response = httpx.get("http://localhost:8000/dashboard", timeout=5)
        response.raise_for_status()
        data = response.json()
        console.print("[green]API is online[/green]")
        console.print(f"New jobs (24h): {data.get('new_jobs_24h', 0)}")
        console.print(f"High-match jobs: {data.get('high_match_jobs', 0)}")
        console.print(f"Pending approvals: {data.get('pending_cv_approvals', 0)}")
        return
    except Exception:
        console.print("[yellow]API offline — checking DB directly...[/yellow]")

    pdf_ok, pdf_path = check_pdflatex()
    console.print(f"pdflatex: {'available' if pdf_ok else 'missing'}")
    if pdf_path:
        console.print(f"pdflatex path: {pdf_path}")

    try:
        with SessionLocal() as session:
            total_jobs = session.query(JobPost).count()
            high_match_jobs = (
                session.query(JobTrackScore)
                .filter(JobTrackScore.score >= settings.match_min_score)
                .count()
            )
            total_drafts = session.query(ResumeDraft).count()
        console.print(f"Jobs in DB: {total_jobs}")
        console.print(f"High-match scores: {high_match_jobs}")
        console.print(f"Resume drafts: {total_drafts}")
    except Exception as exc:
        console.print(f"[yellow]DB unavailable: {exc}[/yellow]")

    provider_status = LLMRouter().provider_status()
    console.print(f"LM Studio reachable: {provider_status['lm_studio']['reachable']}")
