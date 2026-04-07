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


class JobPost(Base):
    __tablename__ = "job_posts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("job_sources.id"), nullable=True, index=True)
    source_name: Mapped[str] = mapped_column(String(120), default="manual")
    source_url: Mapped[str] = mapped_column(String(500), default="")
    canonical_apply_url: Mapped[str] = mapped_column(String(500), default="")
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
    description: Mapped[str] = mapped_column(Text)
    match_notes: Mapped[str] = mapped_column(Text, default="")
    extracted_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(50), default="new")
    posted_date: Mapped[str] = mapped_column(String(80), default="")
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
    review_feedback: Mapped[dict] = mapped_column(JSONB, default=dict)
    tex_path: Mapped[str] = mapped_column(String(500), default="")
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    job_post: Mapped[JobPost] = relationship(back_populates="drafts")
    resume_track: Mapped[ResumeTrack] = relationship(back_populates="drafts")
    applications: Mapped[list["Application"]] = relationship(back_populates="resume_draft")


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


class FactSource(Base):
    __tablename__ = "fact_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
    fact_source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fact_sources.id"), index=True)
    key: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    value: Mapped[str] = mapped_column(Text)

    fact_source: Mapped[FactSource] = relationship(back_populates="summary_variants")


class KeywordSet(Base):
    __tablename__ = "keyword_sets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
