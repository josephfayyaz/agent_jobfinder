from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MasterProfileIn(APIModel):
    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin_url: str = ""
    github_url: str = ""
    public_brand_summary: str = ""
    experiences: list[dict[str, Any]] = Field(default_factory=list)
    projects: list[dict[str, Any]] = Field(default_factory=list)
    education: list[dict[str, Any]] = Field(default_factory=list)
    certifications: list[dict[str, Any]] = Field(default_factory=list)
    achievements: list[dict[str, Any]] = Field(default_factory=list)
    global_skills: list[str] = Field(default_factory=list)
    additional_notes: dict[str, Any] = Field(default_factory=dict)


class MasterProfileOut(MasterProfileIn):
    id: int
    updated_at: datetime


class ResumeTrackOut(APIModel):
    id: UUID
    slug: str
    title: str
    role_family: str
    baseline_summary: str
    target_keywords: list[str]
    emphasis: dict[str, Any]
    linkedin_strategy: str
    github_strategy: str
    active: bool


class JobPostCreate(APIModel):
    source_id: UUID | None = None
    source_name: str = "manual"
    source_url: str = ""
    canonical_apply_url: str = ""
    company: str
    company_domain: str = ""
    title: str
    city: str = ""
    country: str = ""
    remote_policy: str = ""
    salary_text: str = ""
    recruiter_name: str = ""
    recruiter_email: str = ""
    location: str = ""
    role_track_hint: str = ""
    role_family: str = ""
    description: str
    match_notes: str = ""
    extracted_metadata: dict[str, Any] = Field(default_factory=dict)
    posted_date: str = ""


class JobPostOut(JobPostCreate):
    id: UUID
    status: str
    created_at: datetime
    last_seen_at: datetime


class ResumeDraftOut(APIModel):
    id: UUID
    job_post_id: UUID
    resume_track_id: UUID
    provider: str
    status: str
    score: float | None
    content: dict[str, Any]
    review_feedback: dict[str, Any]
    tex_path: str
    approved: bool
    created_at: datetime
    updated_at: datetime


class EnhancementProposalOut(BaseModel):
    id: UUID
    draft_id: UUID
    section: str
    original_text: str
    proposed_text: str
    rationale: str
    question_for_user: str
    approved: bool | None

    model_config = ConfigDict(from_attributes=True)


class ApplyEnhancementsRequest(BaseModel):
    approved_proposal_ids: list[UUID]


class WorkflowTaskCreate(APIModel):
    job_post_id: UUID
    resume_track_slug: str
    force_cloud_review: bool = False


class WorkflowTaskOut(APIModel):
    id: UUID
    kind: str
    status: str
    payload: dict[str, Any]
    result: dict[str, Any]
    error_message: str
    created_at: datetime
    updated_at: datetime


class FactSheetIngestRequest(APIModel):
    path: str | None = None
    source_path: str | None = None
    content: str | None = None


class FactSheetIngestResponse(APIModel):
    source_path: str
    source_hash: str
    reused_existing_source: bool
    counts: dict[str, int]


class JobSourceOut(APIModel):
    id: UUID
    slug: str
    name: str
    source_type: str
    base_url: str
    target_regions: list[str]
    role_families: list[str]
    access_mode: str
    compliance_notes: str
    active: bool
    priority: int


class ApplicationCreate(APIModel):
    job_post_id: UUID
    resume_track_slug: str | None = None
    resume_draft_id: UUID | None = None
    status: str = "discovered"
    next_action: str = ""
    notes: str = ""


class ApplicationUpdate(APIModel):
    status: str | None = None
    next_action: str | None = None
    notes: str | None = None
    applied_at: datetime | None = None


class ApplicationOut(APIModel):
    id: UUID
    job_post_id: UUID
    resume_track_id: UUID | None
    resume_draft_id: UUID | None
    status: str
    applied_at: datetime | None
    last_email_at: datetime | None
    next_action: str
    notes: str
    created_at: datetime
    updated_at: datetime


class CommunicationEventCreate(APIModel):
    channel: str = "email"
    direction: str = "inbound"
    event_type: str = "message"
    sender_name: str = ""
    sender_email: str = ""
    subject: str = ""
    snippet: str = ""
    event_at: datetime | None = None


class CommunicationEventOut(APIModel):
    id: UUID
    application_id: UUID
    channel: str
    direction: str
    event_type: str
    sender_name: str
    sender_email: str
    subject: str
    snippet: str
    event_at: datetime
    created_at: datetime


class CsvExportOut(APIModel):
    id: UUID
    export_type: str
    file_path: str
    row_count: int
    filters: dict[str, Any]
    created_at: datetime
