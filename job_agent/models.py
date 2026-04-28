from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from job_agent.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MasterProfile(Base):
    __tablename__ = "master_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    full_name: Mapped[str] = mapped_column(String(200), default="")
    email: Mapped[str] = mapped_column(String(200), default="")
    phone: Mapped[str] = mapped_column(String(100), default="")
    location: Mapped[str] = mapped_column(String(200), default="")
    linkedin_url: Mapped[str] = mapped_column(String(300), default="")
    github_url: Mapped[str] = mapped_column(String(300), default="")
    public_brand_summary: Mapped[str] = mapped_column(Text, default="")
    experiences: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    projects: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    education: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    certifications: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    achievements: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    global_skills: Mapped[list[str]] = mapped_column(JSONB, default=list)
    additional_notes: Mapped[dict] = mapped_column(JSONB, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name: Mapped[str] = mapped_column(String(200))
    preferred_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    completion_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    confidence_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    spoken_languages: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    skills_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MatchProfile(Base):
    __tablename__ = "match_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidates.id"), index=True)
    target_roles: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    excluded_roles: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    preferred_industries: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    location_preferences: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    work_authorization: Mapped[str | None] = mapped_column(String(100), nullable=True)
    availability_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    earliest_start_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    employment_preferences: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    seniority_estimate: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class FactConflict(Base):
    __tablename__ = "fact_conflicts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidates.id"), index=True)
    field: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_a: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_b: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EvidenceIndexItem(Base):
    __tablename__ = "evidence_index_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidates.id"), index=True)
    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    quote_or_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FactSheetChangeLog(Base):
    __tablename__ = "fact_sheet_change_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidates.id"), index=True)
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CandidateSourceFile(Base):
    __tablename__ = "candidate_source_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidates.id"), index=True)
    original_name: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    stored_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CandidateIntakeDraft(Base):
    __tablename__ = "candidate_intake_drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidates.id"), index=True, unique=True)
    partial_fact_sheet: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    pending_questions: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    last_answers: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    iteration: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ResumeTrack(Base):
    __tablename__ = "resume_tracks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    role_family: Mapped[str] = mapped_column(String(120))
    baseline_summary: Mapped[str] = mapped_column(Text)
    target_keywords: Mapped[list[str]] = mapped_column(JSONB, default=list)
    emphasis: Mapped[dict] = mapped_column(JSONB, default=dict)
    linkedin_strategy: Mapped[str] = mapped_column(Text, default="")
    github_strategy: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    drafts: Mapped[list["ResumeDraft"]] = relationship(back_populates="resume_track")
    applications: Mapped[list["Application"]] = relationship(back_populates="resume_track")
    job_track_scores: Mapped[list["JobTrackScore"]] = relationship(back_populates="resume_track")


class JobSource(Base):
    __tablename__ = "job_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    source_type: Mapped[str] = mapped_column(String(80), default="public_board")
    base_url: Mapped[str] = mapped_column(String(500), default="")
    target_regions: Mapped[list[str]] = mapped_column(JSONB, default=list)
    role_families: Mapped[list[str]] = mapped_column(JSONB, default=list)
    access_mode: Mapped[str] = mapped_column(String(80), default="manual_review")
    compliance_notes: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    job_posts: Mapped[list["JobPost"]] = relationship(back_populates="job_source")


class CareerPageSource(Base):
    """
    A company career page to scan for new job postings.
    Each record represents one company + URL to poll.
    """

    __tablename__ = "career_page_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    company: Mapped[str] = mapped_column(String(200))
    career_url: Mapped[str] = mapped_column(String(500))
    css_selector: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ats_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ats_slug: Mapped[str | None] = mapped_column(String(200), nullable=True)
    country: Mapped[str] = mapped_column(String(100), default="Italy")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_new_jobs: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CareerPageScanLog(Base):
    __tablename__ = "career_page_scan_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("career_page_sources.id"), index=True)
    scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    jobs_found: Mapped[int] = mapped_column(Integer, default=0)
    new_jobs: Mapped[int] = mapped_column(Integer, default=0)


class JobPost(Base):
    __tablename__ = "job_posts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("job_sources.id"), nullable=True, index=True)
    source_name: Mapped[str] = mapped_column(String(120), default="manual")
    source_url: Mapped[str] = mapped_column(String(500), default="")
    canonical_apply_url: Mapped[str] = mapped_column(String(500), default="")
    company_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    company: Mapped[str] = mapped_column(String(200))
    company_domain: Mapped[str] = mapped_column(String(200), default="")
    title: Mapped[str] = mapped_column(String(200))
    city: Mapped[str] = mapped_column(String(120), default="")
    country: Mapped[str] = mapped_column(String(120), default="")
    remote_policy: Mapped[str] = mapped_column(String(80), default="")
    salary_text: Mapped[str] = mapped_column(String(200), default="")
    recruiter_name: Mapped[str] = mapped_column(String(200), default="")
    recruiter_email: Mapped[str] = mapped_column(String(200), default="")
    location: Mapped[str] = mapped_column(String(200), default="")
    role_track_hint: Mapped[str] = mapped_column(String(80), default="")
    role_family: Mapped[str] = mapped_column(String(120), default="")
    seniority: Mapped[str | None] = mapped_column(String(20), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    match_notes: Mapped[str] = mapped_column(Text, default="")
    extracted_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    queue_state: Mapped[str] = mapped_column(String(40), default="new")
    status: Mapped[str] = mapped_column(String(50), default="new")
    posted_date: Mapped[str] = mapped_column(String(80), default="")
    enrichment_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    job_source: Mapped[JobSource | None] = relationship(back_populates="job_posts")
    drafts: Mapped[list["ResumeDraft"]] = relationship(back_populates="job_post")
    applications: Mapped[list["Application"]] = relationship(back_populates="job_post")
    track_scores: Mapped[list["JobTrackScore"]] = relationship(back_populates="job_post")


class ResumeDraft(Base):
    __tablename__ = "resume_drafts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("job_posts.id"), index=True)
    resume_track_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resume_tracks.id"), index=True)
    provider: Mapped[str] = mapped_column(String(120), default="heuristic")
    status: Mapped[str] = mapped_column(String(50), default="drafted")
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    content: Mapped[dict] = mapped_column(JSONB, default=dict)
    inferred_additions: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True, default=None)
    accepted_inferred_additions: Mapped[list[dict] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
    )
    review_feedback: Mapped[dict] = mapped_column(JSONB, default=dict)
    tex_path: Mapped[str] = mapped_column(String(500), default="")
    cover_letter_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_letter_subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    job_post: Mapped[JobPost] = relationship(back_populates="drafts")
    resume_track: Mapped[ResumeTrack] = relationship(back_populates="drafts")
    applications: Mapped[list["Application"]] = relationship(back_populates="resume_draft")
    clarifications: Mapped[list["BulletClarification"]] = relationship(back_populates="draft")


class BulletClarification(Base):
    """
    Tracks a human-in-the-loop bullet refinement session for a ResumeDraft.
    Stage 1: language_map extracted from JD.
    Stage 2: clarifying questions generated (if gaps found).
    Stage 3: bullets rewritten using confirmed user answers.
    """

    __tablename__ = "bullet_clarifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    draft_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resume_drafts.id"), nullable=False, index=True)
    original_bullet: Mapped[str] = mapped_column(Text, default="")
    suggested_rewrite: Mapped[str] = mapped_column(Text, default="")
    user_accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    promoted_to_fact_sheet: Mapped[bool] = mapped_column(Boolean, default=False)
    target_section: Mapped[str] = mapped_column(String(32), default="")
    target_item_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_bullet_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language_map: Mapped[dict] = mapped_column(JSONB, default=dict)
    questions: Mapped[list] = mapped_column(JSONB, default=list)
    answers: Mapped[list] = mapped_column(JSONB, default=list)
    rewritten_bullets: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String, default="pending_questions")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    draft: Mapped["ResumeDraft"] = relationship(back_populates="clarifications")


class VerifiedCandidateFact(Base):
    """Persistent profile memory: user-confirmed facts from the apply flow."""

    __tablename__ = "verified_candidate_facts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("candidates.id"),
        nullable=True,
        index=True,
    )
    gap_label: Mapped[str] = mapped_column(String(200), nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    fact_type: Mapped[str] = mapped_column(String(50), default="general", nullable=False)
    source_draft_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resume_drafts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_posts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class EnhancementProposal(Base):
    """A proposed improvement to a resume draft, awaiting user approval."""

    __tablename__ = "enhancement_proposals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    draft_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resume_drafts.id"), nullable=False)
    section: Mapped[str] = mapped_column(String, nullable=False)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_text: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    question_for_user: Mapped[str] = mapped_column(Text, nullable=False)
    approved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class WorkflowTask(Base):
    __tablename__ = "workflow_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    result: Mapped[dict] = mapped_column(JSONB, default=dict)
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class DiscoveryEvent(Base):
    __tablename__ = "discovery_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_name: Mapped[str] = mapped_column(String(120), default="")
    acquisition_path: Mapped[str] = mapped_column(String(80), default="")
    outcome: Mapped[str] = mapped_column(String(40), default="ingested")
    reason: Mapped[str] = mapped_column(Text, default="")
    source_url: Mapped[str] = mapped_column(String(500), default="")
    canonical_key: Mapped[str] = mapped_column(String(500), default="")
    job_post_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_posts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class InterviewStory(Base):
    __tablename__ = "interview_stories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("candidates.id"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(240), default="")
    context: Mapped[str] = mapped_column(Text, default="")
    action: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[str] = mapped_column(Text, default="")
    tools: Mapped[list[str]] = mapped_column(JSONB, default=list)
    role_family_tags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    confidence_source: Mapped[str] = mapped_column(String(60), default="draft-derived")
    fingerprint: Mapped[str] = mapped_column(String(300), unique=True, index=True)
    source_ref: Mapped[str] = mapped_column(String(120), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class CompanySnapshot(Base):
    __tablename__ = "company_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_post_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("job_posts.id"), index=True)
    company_name: Mapped[str] = mapped_column(String(200), default="")
    provider: Mapped[str] = mapped_column(String(120), default="heuristic")
    status: Mapped[str] = mapped_column(String(40), default="ready")
    content: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class OfferDecision(Base):
    __tablename__ = "offer_decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("candidates.id"),
        nullable=True,
        index=True,
    )
    company: Mapped[str] = mapped_column(String(200), default="")
    title: Mapped[str] = mapped_column(String(200), default="")
    salary_text: Mapped[str] = mapped_column(String(200), default="")
    location: Mapped[str] = mapped_column(String(200), default="")
    remote_policy: Mapped[str] = mapped_column(String(80), default="")
    visa_notes: Mapped[str] = mapped_column(Text, default="")
    growth_notes: Mapped[str] = mapped_column(Text, default="")
    learning_notes: Mapped[str] = mapped_column(Text, default="")
    work_life_notes: Mapped[str] = mapped_column(Text, default="")
    negotiation_notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="active")
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class FactSource(Base):
    __tablename__ = "fact_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("candidates.id"),
        nullable=True,
        index=True,
    )
    source_path: Mapped[str] = mapped_column(String(500), unique=True)
    source_hash: Mapped[str] = mapped_column(String(128), index=True)
    parser_version: Mapped[str] = mapped_column(String(40), default="1")
    raw_content: Mapped[str] = mapped_column(Text)
    parsed_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    education_items: Mapped[list["EducationFact"]] = relationship(back_populates="fact_source")
    experience_items: Mapped[list["ExperienceFact"]] = relationship(back_populates="fact_source")
    project_items: Mapped[list["ProjectFact"]] = relationship(back_populates="fact_source")
    summary_variants: Mapped[list["SummaryVariant"]] = relationship(back_populates="fact_source")
    keyword_sets: Mapped[list["KeywordSet"]] = relationship(back_populates="fact_source")


class EducationFact(Base):
    __tablename__ = "education_facts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("candidates.id"),
        nullable=True,
        index=True,
    )
    fact_source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fact_sources.id"), index=True)
    item_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    degree: Mapped[str] = mapped_column(String(200), default="")
    field: Mapped[str] = mapped_column(String(200), default="")
    institution: Mapped[str] = mapped_column(String(200), default="")
    location: Mapped[str] = mapped_column(String(200), default="")
    start_date: Mapped[str] = mapped_column(String(80), default="")
    end_date: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(120), default="")
    preferred_presentation: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[list[str]] = mapped_column(JSONB, default=list)
    needs_confirmation: Mapped[bool] = mapped_column(Boolean, default=False)

    fact_source: Mapped[FactSource] = relationship(back_populates="education_items")


class ExperienceFact(Base):
    __tablename__ = "experience_facts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("candidates.id"),
        nullable=True,
        index=True,
    )
    fact_source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fact_sources.id"), index=True)
    item_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    section_name: Mapped[str] = mapped_column(String(120))
    role_title: Mapped[str] = mapped_column(String(200), default="")
    organization: Mapped[str] = mapped_column(String(200), default="")
    location: Mapped[str] = mapped_column(String(200), default="")
    start_date: Mapped[str] = mapped_column(String(80), default="")
    end_date: Mapped[str] = mapped_column(String(80), default="")
    employment_type: Mapped[str] = mapped_column(String(120), default="")
    role_match_priority: Mapped[dict] = mapped_column(JSONB, default=dict)
    business_context: Mapped[str] = mapped_column(Text, default="")
    project_context: Mapped[str] = mapped_column(Text, default="")
    verified_core_facts: Mapped[list[str]] = mapped_column(JSONB, default=list)
    enriched_description_bank: Mapped[list[str]] = mapped_column(JSONB, default=list)
    tools_and_tech: Mapped[list[str]] = mapped_column(JSONB, default=list)
    best_bullets_by_track: Mapped[dict] = mapped_column(JSONB, default=dict)
    metrics_to_capture: Mapped[list[str]] = mapped_column(JSONB, default=list)
    evidence_links: Mapped[list[str]] = mapped_column(JSONB, default=list)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    needs_confirmation: Mapped[bool] = mapped_column(Boolean, default=False)

    fact_source: Mapped[FactSource] = relationship(back_populates="experience_items")


class ProjectFact(Base):
    __tablename__ = "project_facts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("candidates.id"),
        nullable=True,
        index=True,
    )
    fact_source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fact_sources.id"), index=True)
    item_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    project_name: Mapped[str] = mapped_column(String(250))
    status: Mapped[str] = mapped_column(String(120), default="")
    dates: Mapped[str] = mapped_column(String(120), default="")
    role: Mapped[str] = mapped_column(String(200), default="")
    repo_url: Mapped[str] = mapped_column(String(500), default="")
    short_resume_line: Mapped[str] = mapped_column(String(300), default="")
    role_match_priority: Mapped[dict] = mapped_column(JSONB, default=dict)
    verified_core_facts: Mapped[list[str]] = mapped_column(JSONB, default=list)
    key_results: Mapped[list[str]] = mapped_column(JSONB, default=list)
    enriched_description_bank: Mapped[list[str]] = mapped_column(JSONB, default=list)
    tools_and_tech: Mapped[list[str]] = mapped_column(JSONB, default=list)
    best_bullets_by_track: Mapped[dict] = mapped_column(JSONB, default=dict)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    needs_confirmation: Mapped[bool] = mapped_column(Boolean, default=False)

    fact_source: Mapped[FactSource] = relationship(back_populates="project_items")


class SummaryVariant(Base):
    __tablename__ = "summary_variants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("candidates.id"),
        nullable=True,
        index=True,
    )
    fact_source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fact_sources.id"), index=True)
    key: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    value: Mapped[str] = mapped_column(Text)

    fact_source: Mapped[FactSource] = relationship(back_populates="summary_variants")


class KeywordSet(Base):
    __tablename__ = "keyword_sets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("candidates.id"),
        nullable=True,
        index=True,
    )
    fact_source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fact_sources.id"), index=True)
    key: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    values: Mapped[list[str]] = mapped_column(JSONB, default=list)

    fact_source: Mapped[FactSource] = relationship(back_populates="keyword_sets")


class JobTrackScore(Base):
    __tablename__ = "job_track_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("job_posts.id"), index=True)
    resume_track_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resume_tracks.id"), index=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    matched_keywords: Mapped[list[str]] = mapped_column(JSONB, default=list)
    embedding_cache: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    job_post: Mapped[JobPost] = relationship(back_populates="track_scores")
    resume_track: Mapped[ResumeTrack] = relationship(back_populates="job_track_scores")


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("job_posts.id"), index=True)
    resume_track_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("resume_tracks.id"), nullable=True)
    resume_draft_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("resume_drafts.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(80), default="discovered", index=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_email_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_action: Mapped[str] = mapped_column(String(200), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    job_post: Mapped[JobPost] = relationship(back_populates="applications")
    resume_track: Mapped[ResumeTrack | None] = relationship(back_populates="applications")
    resume_draft: Mapped[ResumeDraft | None] = relationship(back_populates="applications")
    communications: Mapped[list["CommunicationEvent"]] = relationship(back_populates="application")


class CommunicationEvent(Base):
    __tablename__ = "communication_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id"), index=True)
    channel: Mapped[str] = mapped_column(String(80), default="email")
    direction: Mapped[str] = mapped_column(String(40), default="inbound")
    event_type: Mapped[str] = mapped_column(String(80), default="message")
    sender_name: Mapped[str] = mapped_column(String(200), default="")
    sender_email: Mapped[str] = mapped_column(String(200), default="")
    subject: Mapped[str] = mapped_column(String(300), default="")
    snippet: Mapped[str] = mapped_column(Text, default="")
    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    application: Mapped[Application] = relationship(back_populates="communications")


class CsvExport(Base):
    __tablename__ = "csv_exports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    export_type: Mapped[str] = mapped_column(String(80), default="jobs")
    file_path: Mapped[str] = mapped_column(String(500))
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    filters: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ThesisTarget(Base):
    """A professor, lab, or company target for thesis or traineeship outreach."""

    __tablename__ = "thesis_targets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(200))
    institution: Mapped[str] = mapped_column(String(300))
    department: Mapped[str | None] = mapped_column(String(200), nullable=True)
    country: Mapped[str] = mapped_column(String(100))
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    research_area: Mapped[str] = mapped_column(String(300))
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    profile_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="identified")
    priority: Mapped[int] = mapped_column(Integer, default=3)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    outreach_drafts: Mapped[list["OutreachDraft"]] = relationship(
        back_populates="target",
        cascade="all, delete-orphan",
    )
    contact_events: Mapped[list["ContactEvent"]] = relationship(
        back_populates="target",
        cascade="all, delete-orphan",
    )


class OutreachDraft(Base):
    """An LLM-generated outreach email draft tied to a thesis target."""

    __tablename__ = "outreach_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("thesis_targets.id"), index=True)
    subject: Mapped[str] = mapped_column(String(500))
    body_text: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    approved: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=None)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    target: Mapped[ThesisTarget] = relationship(back_populates="outreach_drafts")


class ContactEvent(Base):
    """Communication log for thesis/traineeship outreach."""

    __tablename__ = "contact_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("thesis_targets.id"), index=True)
    direction: Mapped[str] = mapped_column(String(10))
    channel: Mapped[str] = mapped_column(String(20))
    event_type: Mapped[str] = mapped_column(String(30))
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    snippet: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    target: Mapped[ThesisTarget] = relationship(back_populates="contact_events")
