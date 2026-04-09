from __future__ import annotations

from datetime import datetime, timezone
import logging
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Response
from sqlalchemy.orm import Session

from job_agent.db import SessionLocal, get_db, prepare_database
from job_agent.llm import LLMRouter
from job_agent.models import (
    Application,
    CommunicationEvent,
    CsvExport,
    FactSource,
    JobPost,
    JobSource,
    JobTrackScore,
    MasterProfile,
    ContactEvent,
    OutreachDraft,
    ResumeDraft,
    ResumeTrack,
    ThesisTarget,
    WorkflowTask,
)
from job_agent.schemas import (
    ApplyEnhancementsRequest,
    ApplicationCreate,
    ApplicationOut,
    ApplicationUpdate,
    CommunicationEventCreate,
    CommunicationEventOut,
    ContactEventCreate,
    ContactEventOut,
    CsvExportOut,
    FactSheetIngestRequest,
    FactSheetIngestResponse,
    JobSourceOut,
    JobPostCreate,
    JobPostOut,
    MasterProfileIn,
    MasterProfileOut,
    OutreachDraftOut,
    OutreachDraftRevisionRequest,
    ResumeDraftOut,
    ResumeTrackOut,
    ThesisTargetCreate,
    ThesisTargetOut,
    ThesisTargetUpdate,
    WorkflowTaskCreate,
    WorkflowTaskOut,
)
from job_agent.seed import seed_reference_data
from job_agent.services.exporters import CsvExportService
from job_agent.services.fact_ingestion import FactSheetIngestionService
from job_agent.services.gmail import GmailService
from job_agent.services.job_fetcher import JobFetcher
from job_agent.services.matching import score_tracks_for_job
from job_agent.services.thesis_outreach import ThesisOutreachService
from job_agent.services.workflows import CVWorkflowService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

app = FastAPI(title="Local LLM Job Agent", version="0.1.0")


@app.on_event("startup")
def startup() -> None:
    prepare_database()
    with SessionLocal() as session:
        seed_reference_data(session)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/providers")
def providers() -> dict:
    return LLMRouter().provider_status()


@app.get("/tracks", response_model=list[ResumeTrackOut])
def list_tracks(db: Session = Depends(get_db)) -> list[ResumeTrack]:
    return db.query(ResumeTrack).filter(ResumeTrack.active.is_(True)).order_by(ResumeTrack.title.asc()).all()


@app.get("/job-sources", response_model=list[JobSourceOut])
def list_job_sources(db: Session = Depends(get_db)) -> list[JobSource]:
    return db.query(JobSource).filter(JobSource.active.is_(True)).order_by(JobSource.priority.asc()).all()


@app.get("/fact-sources/latest")
def latest_fact_source(db: Session = Depends(get_db)) -> dict:
    latest = db.query(FactSource).order_by(FactSource.imported_at.desc()).first()
    if latest is None:
        raise HTTPException(status_code=404, detail="No fact source has been ingested yet.")
    return {
        "id": str(latest.id),
        "source_path": latest.source_path,
        "source_hash": latest.source_hash,
        "imported_at": latest.imported_at.isoformat(),
        "parsed_metadata": latest.parsed_metadata,
    }


@app.post("/fact-sources/ingest", response_model=FactSheetIngestResponse)
def ingest_fact_source(payload: FactSheetIngestRequest, db: Session = Depends(get_db)) -> dict:
    service = FactSheetIngestionService(db)
    return service.ingest(path=payload.path, content=payload.content, source_path=payload.source_path)


@app.get("/profile", response_model=MasterProfileOut)
def get_profile(db: Session = Depends(get_db)) -> MasterProfile:
    profile = db.get(MasterProfile, 1)
    if profile is None:
        raise HTTPException(status_code=404, detail="Master profile not found.")
    return profile


@app.put("/profile", response_model=MasterProfileOut)
def put_profile(payload: MasterProfileIn, db: Session = Depends(get_db)) -> MasterProfile:
    profile = db.get(MasterProfile, 1)
    if profile is None:
        profile = MasterProfile(id=1)
        db.add(profile)

    for key, value in payload.model_dump().items():
        setattr(profile, key, value)

    db.commit()
    db.refresh(profile)
    return profile


@app.post("/jobs", response_model=JobPostOut)
def create_job(payload: JobPostCreate, db: Session = Depends(get_db)) -> JobPost:
    payload_data = payload.model_dump()
    tracks = db.query(ResumeTrack).filter(ResumeTrack.active.is_(True)).order_by(ResumeTrack.title.asc()).all()
    track_scores = score_tracks_for_job(payload_data, tracks)
    extracted_metadata = dict(payload_data.get("extracted_metadata", {}))
    extracted_metadata["track_scores"] = track_scores
    if payload_data["role_track_hint"] == "" and track_scores:
        payload_data["role_track_hint"] = track_scores[0]["slug"]
    if payload_data["role_family"] == "" and track_scores:
        payload_data["role_family"] = track_scores[0]["role_family"]
    if payload_data["match_notes"] == "" and track_scores:
        top = track_scores[0]
        payload_data["match_notes"] = (
            f"Top track {top['slug']} matched keywords: {', '.join(top['matched_keywords']) or 'none'}."
        )
    if payload_data["canonical_apply_url"] == "":
        payload_data["canonical_apply_url"] = payload_data["source_url"]
    payload_data["extracted_metadata"] = extracted_metadata

    job = JobPost(**payload_data)
    db.add(job)
    db.flush()
    for track_score in track_scores:
        track = next((item for item in tracks if item.slug == track_score["slug"]), None)
        if track is None:
            continue
        db.add(
            JobTrackScore(
                job_post_id=job.id,
                resume_track_id=track.id,
                score=float(track_score["score"]),
                matched_keywords=track_score["matched_keywords"],
            )
        )
    db.commit()
    db.refresh(job)
    return job


@app.get("/jobs", response_model=list[JobPostOut])
def list_jobs(db: Session = Depends(get_db)) -> list[JobPost]:
    return db.query(JobPost).order_by(JobPost.created_at.desc()).all()


@app.get("/jobs/{job_id}/track-fit")
def job_track_fit(job_id: str, db: Session = Depends(get_db)) -> dict:
    job = db.get(JobPost, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job post not found.")
    tracks = db.query(ResumeTrack).filter(ResumeTrack.active.is_(True)).order_by(ResumeTrack.title.asc()).all()
    return {
        "job_post_id": str(job.id),
        "recommended_tracks": score_tracks_for_job(
            {"title": job.title, "description": job.description},
            tracks,
        ),
    }


@app.post("/jobs/sync-gmail")
def sync_jobs_from_gmail(db: Session = Depends(get_db)) -> dict[str, object]:
    posts = GmailService().sync_jobs(db)
    return {
        "created": len(posts),
        "job_ids": [str(post.id) for post in posts],
    }


@app.post("/jobs/{job_id}/enrich")
def enrich_job(job_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    job = db.get(JobPost, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    success = JobFetcher().enrich_job(job, db)
    db.commit()
    return {"enriched": success, "description_length": len(job.description or "")}


@app.post("/jobs/enrich-pending")
def enrich_pending_jobs(limit: int = 20, db: Session = Depends(get_db)) -> dict[str, int]:
    count = JobFetcher().enrich_pending(db, limit=limit)
    return {"enriched": count}


@app.post("/tasks/cv-workflow", response_model=WorkflowTaskOut)
def queue_cv_workflow(payload: WorkflowTaskCreate, db: Session = Depends(get_db)) -> WorkflowTask:
    track = (
        db.query(ResumeTrack)
        .filter(ResumeTrack.slug == payload.resume_track_slug, ResumeTrack.active.is_(True))
        .first()
    )
    if track is None:
        raise HTTPException(status_code=404, detail="Resume track not found.")
    job = db.get(JobPost, payload.job_post_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job post not found.")
    service = CVWorkflowService(db)
    return service.queue_cv_workflow(
        job_post_id=payload.job_post_id,
        resume_track_slug=payload.resume_track_slug,
        force_cloud_review=payload.force_cloud_review,
    )


@app.get("/tasks", response_model=list[WorkflowTaskOut])
def list_tasks(db: Session = Depends(get_db)) -> list[WorkflowTask]:
    return db.query(WorkflowTask).order_by(WorkflowTask.created_at.desc()).all()


@app.get("/tasks/{task_id}", response_model=WorkflowTaskOut)
def get_task(task_id: str, db: Session = Depends(get_db)) -> WorkflowTask:
    task = db.get(WorkflowTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return task


@app.get("/drafts", response_model=list[ResumeDraftOut])
def list_drafts(db: Session = Depends(get_db)) -> list[ResumeDraft]:
    return db.query(ResumeDraft).order_by(ResumeDraft.created_at.desc()).all()


@app.get("/drafts/{draft_id}", response_model=ResumeDraftOut)
def get_draft(draft_id: str, db: Session = Depends(get_db)) -> ResumeDraft:
    draft = db.get(ResumeDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")
    return draft


@app.post("/drafts/{draft_id}/approve", response_model=ResumeDraftOut)
def approve_draft(draft_id: str, db: Session = Depends(get_db)) -> ResumeDraft:
    draft = db.get(ResumeDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")
    draft.approved = True
    draft.status = "approved"
    db.commit()
    db.refresh(draft)
    return draft


@app.post("/drafts/{draft_id}/propose-enhancements")
def propose_enhancements(draft_id: UUID, db: Session = Depends(get_db)):
    """Generate expert enhancement proposals for a draft (human approval required)."""
    from job_agent.schemas import EnhancementProposalOut

    service = CVWorkflowService(session=db)
    try:
        proposals = service.generate_enhancement_proposals(draft_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [EnhancementProposalOut.model_validate(proposal) for proposal in proposals]


@app.get("/drafts/{draft_id}/pending-approvals")
def get_pending_approvals(draft_id: UUID, db: Session = Depends(get_db)):
    """List enhancement proposals awaiting user approval for a draft."""
    from job_agent.models import EnhancementProposal
    from job_agent.schemas import EnhancementProposalOut

    proposals = (
        db.query(EnhancementProposal)
        .filter(
            EnhancementProposal.draft_id == draft_id,
            EnhancementProposal.approved.is_(None),
        )
        .all()
    )
    return [EnhancementProposalOut.model_validate(proposal) for proposal in proposals]


@app.post("/drafts/{draft_id}/apply-enhancements")
def apply_enhancements(
    draft_id: UUID,
    body: ApplyEnhancementsRequest,
    db: Session = Depends(get_db),
):
    """Apply user-approved enhancement proposals to the draft content."""
    service = CVWorkflowService(session=db)
    try:
        updated_draft = service.apply_approved_enhancements(
            draft_id, body.approved_proposal_ids
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"draft_id": str(updated_draft.id), "status": "enhancements_applied"}


@app.get("/drafts/{draft_id}/pdf")
def download_draft_pdf(draft_id: UUID, db: Session = Depends(get_db)):
    """Compile the draft's .tex file to PDF and return it for download."""
    from fastapi.responses import FileResponse

    from job_agent.services.documents import compile_pdf

    draft = db.get(ResumeDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    if not draft.tex_path:
        raise HTTPException(status_code=400, detail="Draft has no .tex file")

    try:
        pdf_path = compile_pdf(draft.tex_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"resume_{draft_id}.pdf",
    )


@app.post("/applications", response_model=ApplicationOut)
def create_application(payload: ApplicationCreate, db: Session = Depends(get_db)) -> Application:
    job = db.get(JobPost, payload.job_post_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job post not found.")

    resume_track_id = None
    if payload.resume_track_slug:
        track = (
            db.query(ResumeTrack)
            .filter(ResumeTrack.slug == payload.resume_track_slug, ResumeTrack.active.is_(True))
            .first()
        )
        if track is None:
            raise HTTPException(status_code=404, detail="Resume track not found.")
        resume_track_id = track.id

    application = Application(
        job_post_id=payload.job_post_id,
        resume_track_id=resume_track_id,
        resume_draft_id=payload.resume_draft_id,
        status=payload.status,
        next_action=payload.next_action,
        notes=payload.notes,
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@app.get("/applications", response_model=list[ApplicationOut])
def list_applications(db: Session = Depends(get_db)) -> list[Application]:
    return db.query(Application).order_by(Application.updated_at.desc()).all()


@app.patch("/applications/{application_id}", response_model=ApplicationOut)
def update_application(application_id: str, payload: ApplicationUpdate, db: Session = Depends(get_db)) -> Application:
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(application, key, value)
    db.commit()
    db.refresh(application)
    return application


@app.post("/applications/{application_id}/communications", response_model=CommunicationEventOut)
def add_communication_event(
    application_id: str,
    payload: CommunicationEventCreate,
    db: Session = Depends(get_db),
) -> CommunicationEvent:
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found.")
    event = CommunicationEvent(
        application_id=application.id,
        channel=payload.channel,
        direction=payload.direction,
        event_type=payload.event_type,
        sender_name=payload.sender_name,
        sender_email=payload.sender_email,
        subject=payload.subject,
        snippet=payload.snippet,
        event_at=payload.event_at or datetime.now(timezone.utc),
    )
    db.add(event)
    application.last_email_at = event.event_at
    db.commit()
    db.refresh(event)
    return event


@app.get("/applications/{application_id}/communications", response_model=list[CommunicationEventOut])
def list_communication_events(application_id: str, db: Session = Depends(get_db)) -> list[CommunicationEvent]:
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found.")
    return (
        db.query(CommunicationEvent)
        .filter(CommunicationEvent.application_id == application.id)
        .order_by(CommunicationEvent.event_at.desc())
        .all()
    )


@app.post("/exports/jobs-csv", response_model=CsvExportOut)
def export_jobs_csv(db: Session = Depends(get_db)) -> CsvExport:
    service = CsvExportService(db)
    return service.export_jobs_snapshot()


@app.get("/exports", response_model=list[CsvExportOut])
def list_exports(db: Session = Depends(get_db)) -> list[CsvExport]:
    return db.query(CsvExport).order_by(CsvExport.created_at.desc()).all()


@app.post("/thesis-targets", response_model=ThesisTargetOut, status_code=201)
def create_thesis_target(payload: ThesisTargetCreate, db: Session = Depends(get_db)) -> ThesisTarget:
    target = ThesisTarget(**payload.model_dump())
    db.add(target)
    db.commit()
    db.refresh(target)
    return target


@app.get("/thesis-targets", response_model=list[ThesisTargetOut])
def list_thesis_targets(
    status: str | None = None,
    country: str | None = None,
    type: str | None = None,
    db: Session = Depends(get_db),
) -> list[ThesisTarget]:
    query = db.query(ThesisTarget)
    if status:
        query = query.filter(ThesisTarget.status == status)
    if country:
        query = query.filter(ThesisTarget.country == country)
    if type:
        query = query.filter(ThesisTarget.type == type)
    return query.order_by(ThesisTarget.priority.asc(), ThesisTarget.created_at.desc()).all()


@app.get("/thesis-targets/{target_id}", response_model=ThesisTargetOut)
def get_thesis_target(target_id: int, db: Session = Depends(get_db)) -> ThesisTarget:
    target = db.query(ThesisTarget).filter_by(id=target_id).first()
    if target is None:
        raise HTTPException(status_code=404, detail="Thesis target not found.")
    return target


@app.patch("/thesis-targets/{target_id}", response_model=ThesisTargetOut)
def update_thesis_target(
    target_id: int,
    payload: ThesisTargetUpdate,
    db: Session = Depends(get_db),
) -> ThesisTarget:
    target = db.query(ThesisTarget).filter_by(id=target_id).first()
    if target is None:
        raise HTTPException(status_code=404, detail="Thesis target not found.")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(target, field, value)
    target.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(target)
    return target


@app.delete("/thesis-targets/{target_id}", status_code=204)
def archive_thesis_target(target_id: int, db: Session = Depends(get_db)) -> Response:
    target = db.query(ThesisTarget).filter_by(id=target_id).first()
    if target is None:
        raise HTTPException(status_code=404, detail="Thesis target not found.")
    target.status = "archived"
    target.updated_at = datetime.now(timezone.utc)
    db.commit()
    return Response(status_code=204)


@app.post("/thesis-targets/{target_id}/communications", response_model=ContactEventOut, status_code=201)
def log_contact_event(
    target_id: int,
    payload: ContactEventCreate,
    db: Session = Depends(get_db),
) -> ContactEvent:
    target = db.query(ThesisTarget).filter_by(id=target_id).first()
    if target is None:
        raise HTTPException(status_code=404, detail="Thesis target not found.")
    event = ContactEvent(
        target_id=target_id,
        **payload.model_dump(exclude_none=True, exclude={"event_at"}),
        event_at=payload.event_at or datetime.now(timezone.utc),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@app.get("/thesis-targets/{target_id}/communications", response_model=list[ContactEventOut])
def list_contact_events(target_id: int, db: Session = Depends(get_db)) -> list[ContactEvent]:
    return (
        db.query(ContactEvent)
        .filter_by(target_id=target_id)
        .order_by(ContactEvent.event_at.desc())
        .all()
    )


@app.get("/thesis-targets/{target_id}/outreach-drafts", response_model=list[OutreachDraftOut])
def list_outreach_drafts(target_id: int, db: Session = Depends(get_db)) -> list[OutreachDraft]:
    return (
        db.query(OutreachDraft)
        .filter_by(target_id=target_id)
        .order_by(OutreachDraft.created_at.desc())
        .all()
    )


@app.post("/outreach-drafts/{draft_id}/approve", response_model=OutreachDraftOut)
def approve_outreach_draft(draft_id: int, db: Session = Depends(get_db)) -> OutreachDraft:
    draft = db.query(OutreachDraft).filter_by(id=draft_id).first()
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")
    draft.approved = True
    draft.status = "approved"

    siblings = (
        db.query(OutreachDraft)
        .filter(OutreachDraft.target_id == draft.target_id, OutreachDraft.id != draft_id)
        .all()
    )
    for sibling in siblings:
        sibling.approved = False
        if sibling.status == "approved":
            sibling.status = "rejected"

    target = db.query(ThesisTarget).filter_by(id=draft.target_id).first()
    if target is not None and target.status == "email_drafted":
        target.status = "email_approved"
        target.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(draft)
    return draft


@app.post("/thesis-targets/{target_id}/generate-email", response_model=OutreachDraftOut, status_code=201)
def generate_outreach_email(target_id: int, db: Session = Depends(get_db)) -> OutreachDraft:
    try:
        return ThesisOutreachService().generate_email(target_id, db)
    except ValueError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@app.post("/outreach-drafts/{draft_id}/revise", response_model=OutreachDraftOut)
def revise_outreach_draft(
    draft_id: int,
    payload: OutreachDraftRevisionRequest,
    db: Session = Depends(get_db),
) -> OutreachDraft:
    try:
        return ThesisOutreachService().revise_email(draft_id, payload.feedback, db)
    except ValueError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@app.post("/outreach-drafts/{draft_id}/mark-sent", response_model=OutreachDraftOut)
def mark_outreach_draft_sent(draft_id: int, db: Session = Depends(get_db)) -> OutreachDraft:
    try:
        return ThesisOutreachService().mark_sent(draft_id, db)
    except ValueError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
