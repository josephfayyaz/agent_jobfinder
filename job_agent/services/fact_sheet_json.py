from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import uuid

import jsonschema
from sqlalchemy.orm import Session

from job_agent.models import (
    Candidate,
    EducationFact,
    EvidenceIndexItem,
    ExperienceFact,
    FactConflict,
    FactSheetChangeLog,
    FactSource,
    MatchProfile,
    ProjectFact,
)
from job_agent.services.resource_loader import load_fact_sheet_schema


@dataclass
class CandidateIngestResult:
    candidate_id: str
    counts: dict[str, int]
    conflicts: list[dict]
    missing: list[str]


class FactSheetJsonIngestionService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def ingest_json(
        self,
        candidate_id: str | None,
        fact_sheet: dict,
        source_name: str = "json_upload",
    ) -> CandidateIngestResult:
        jsonschema.validate(instance=fact_sheet, schema=load_fact_sheet_schema())

        person = fact_sheet.get("person", {})
        contact = person.get("contact", {})
        candidate = self._resolve_candidate(candidate_id, person, contact, fact_sheet)
        source = self._upsert_fact_source(candidate.id, fact_sheet, source_name)
        self._upsert_match_profile(candidate.id, fact_sheet.get("match_profile", {}))

        counts = {
            "experience": self._upsert_experiences(candidate.id, source, fact_sheet.get("experience", [])),
            "projects": self._upsert_projects(candidate.id, source, fact_sheet.get("projects", [])),
            "education": self._upsert_education(candidate.id, source, fact_sheet.get("education", [])),
            "conflicts": self._upsert_conflicts(candidate.id, fact_sheet.get("conflicts", [])),
            "evidence_index": self._upsert_evidence_index(candidate.id, fact_sheet.get("evidence_index", [])),
            "change_log": self._upsert_change_log(candidate.id, fact_sheet.get("change_log", [])),
        }

        self.session.commit()
        return CandidateIngestResult(
            candidate_id=candidate.id,
            counts=counts,
            conflicts=list(fact_sheet.get("conflicts", [])),
            missing=list(fact_sheet.get("missing_information", [])),
        )

    def export_json(self, candidate_id: str) -> dict:
        candidate = self.session.get(Candidate, candidate_id)
        if candidate is None:
            raise ValueError(f"Candidate {candidate_id} not found")

        match_profile = self.session.query(MatchProfile).filter_by(candidate_id=candidate_id).first()
        source = (
            self.session.query(FactSource)
            .filter(FactSource.candidate_id == candidate_id)
            .order_by(FactSource.imported_at.desc())
            .first()
        )
        experiences = (
            self.session.query(ExperienceFact)
            .filter(ExperienceFact.candidate_id == candidate_id)
            .order_by(ExperienceFact.start_date.desc(), ExperienceFact.organization.asc())
            .all()
        )
        projects = (
            self.session.query(ProjectFact)
            .filter(ProjectFact.candidate_id == candidate_id)
            .order_by(ProjectFact.project_name.asc())
            .all()
        )
        education_items = (
            self.session.query(EducationFact)
            .filter(EducationFact.candidate_id == candidate_id)
            .order_by(EducationFact.start_date.desc(), EducationFact.institution.asc())
            .all()
        )
        conflicts = (
            self.session.query(FactConflict)
            .filter(FactConflict.candidate_id == candidate_id)
            .order_by(FactConflict.created_at.asc())
            .all()
        )
        evidence_items = (
            self.session.query(EvidenceIndexItem)
            .filter(EvidenceIndexItem.candidate_id == candidate_id)
            .order_by(EvidenceIndexItem.created_at.asc())
            .all()
        )
        change_log = (
            self.session.query(FactSheetChangeLog)
            .filter(FactSheetChangeLog.candidate_id == candidate_id)
            .order_by(FactSheetChangeLog.created_at.asc())
            .all()
        )

        missing_information: list[str] = []
        if source and isinstance(source.parsed_metadata, dict):
            missing_information = list(source.parsed_metadata.get("missing_information", []))

        return {
            "person": {
                "full_name": candidate.full_name,
                "preferred_name": candidate.preferred_name,
                "contact": {
                    "email": candidate.email,
                },
            },
            "match_profile": {
                "target_roles": list(match_profile.target_roles or []) if match_profile else [],
                "excluded_roles": list(match_profile.excluded_roles or []) if match_profile else [],
                "preferred_industries": list(match_profile.preferred_industries or []) if match_profile else [],
                "location_preferences": dict(match_profile.location_preferences or {}) if match_profile else {},
                "work_authorization": match_profile.work_authorization if match_profile else None,
                "availability": {
                    "status": match_profile.availability_status if match_profile else None,
                    "earliest_start_date": match_profile.earliest_start_date if match_profile else None,
                },
                "employment_preferences": dict(match_profile.employment_preferences or {}) if match_profile else {},
                "seniority_estimate": dict(match_profile.seniority_estimate or {}) if match_profile else {},
            },
            "experience": [self._export_experience(item) for item in experiences],
            "projects": [self._export_project(item) for item in projects],
            "education": [self._export_education(item) for item in education_items],
            "skills": self._skills_payload(candidate.skills_json),
            "languages": list(candidate.spoken_languages or []),
            "completion_status": candidate.completion_status or "usable_with_gaps",
            "confidence_summary": dict(candidate.confidence_summary or {}),
            "missing_information": missing_information,
            "conflicts": [self._export_conflict(item) for item in conflicts],
            "evidence_index": [self._export_evidence(item) for item in evidence_items],
            "change_log": [item.message for item in change_log],
        }

    def export_text(self, candidate_id: str) -> str:
        from job_agent.services.fact_sheet_renderer import render_fact_sheet_text

        return render_fact_sheet_text(self.export_json(candidate_id))

    def _resolve_candidate(
        self,
        candidate_id: str | None,
        person: dict,
        contact: dict,
        fact_sheet: dict,
    ) -> Candidate:
        if candidate_id:
            candidate = self.session.get(Candidate, candidate_id)
            if candidate is None:
                raise ValueError(f"Candidate {candidate_id} not found")
        else:
            candidate = Candidate(id=str(uuid.uuid4()), full_name=person.get("full_name", "Unknown"))
            self.session.add(candidate)
            self.session.flush()

        candidate.full_name = person.get("full_name") or candidate.full_name
        candidate.preferred_name = person.get("preferred_name")
        candidate.email = contact.get("email")
        candidate.completion_status = fact_sheet.get("completion_status")
        candidate.confidence_summary = dict(fact_sheet.get("confidence_summary", {}))
        candidate.spoken_languages = list(fact_sheet.get("languages", []))
        candidate.skills_json = dict(fact_sheet.get("skills", {}))
        self.session.add(candidate)
        self.session.flush()
        return candidate

    def _upsert_fact_source(self, candidate_id: str, fact_sheet: dict, source_name: str) -> FactSource:
        source_path = f"candidate://{candidate_id}/{source_name}.json"
        raw_content = json.dumps(fact_sheet, sort_keys=True)
        source_hash = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()
        source = self.session.query(FactSource).filter_by(source_path=source_path).first()
        if source is None:
            source = FactSource(
                candidate_id=candidate_id,
                source_path=source_path,
                source_hash=source_hash,
                raw_content=raw_content,
                parsed_metadata={},
            )
            self.session.add(source)
            self.session.flush()

        source.candidate_id = candidate_id
        source.source_hash = source_hash
        source.raw_content = raw_content
        source.parsed_metadata = {
            "format": "fact_sheet_json",
            "missing_information": list(fact_sheet.get("missing_information", [])),
            "completion_status": fact_sheet.get("completion_status"),
        }
        self.session.add(source)
        self.session.flush()
        return source

    def _upsert_match_profile(self, candidate_id: str, match_profile: dict) -> None:
        availability = match_profile.get("availability", {})
        record = self.session.query(MatchProfile).filter_by(candidate_id=candidate_id).first()
        if record is None:
            record = MatchProfile(id=str(uuid.uuid4()), candidate_id=candidate_id)

        record.target_roles = list(match_profile.get("target_roles", []) or [])
        record.excluded_roles = list(match_profile.get("excluded_roles", []) or [])
        record.preferred_industries = list(match_profile.get("preferred_industries", []) or [])
        record.location_preferences = dict(match_profile.get("location_preferences", {}) or {})
        record.work_authorization = match_profile.get("work_authorization")
        record.availability_status = availability.get("status")
        record.earliest_start_date = availability.get("earliest_start_date")
        record.employment_preferences = dict(match_profile.get("employment_preferences", {}) or {})
        record.seniority_estimate = dict(match_profile.get("seniority_estimate", {}) or {})
        self.session.add(record)
        self.session.flush()

    def _upsert_experiences(self, candidate_id: str, source: FactSource, items: list[dict]) -> int:
        for item in items:
            record = (
                self.session.query(ExperienceFact)
                .filter_by(
                    candidate_id=candidate_id,
                    organization=item.get("organization", ""),
                    role_title=item.get("role_title", ""),
                )
                .first()
            )
            if record is None:
                record = ExperienceFact(
                    candidate_id=candidate_id,
                    fact_source_id=source.id,
                    item_id=self._stable_item_id(
                        "exp",
                        candidate_id,
                        item.get("organization", ""),
                        item.get("role_title", ""),
                    ),
                    section_name="experience",
                )
            record.candidate_id = candidate_id
            record.fact_source_id = source.id
            record.section_name = "experience"
            record.role_title = item.get("role_title", "")
            record.organization = item.get("organization", "")
            record.location = item.get("location") or ""
            record.start_date = item.get("start_date") or ""
            record.end_date = item.get("end_date") or ""
            record.verified_core_facts = list(item.get("responsibilities", []) or [])
            record.tools_and_tech = list(item.get("tools", []) or [])
            record.enriched_description_bank = list(item.get("achievements", []) or [])
            record.evidence_links = list(item.get("evidence_refs", []) or [])
            verification_status = item.get("verification_status")
            record.tags = [f"verification_status:{verification_status}"] if verification_status else []
            self.session.add(record)
        self.session.flush()
        return len(items)

    def _upsert_projects(self, candidate_id: str, source: FactSource, items: list[dict]) -> int:
        for item in items:
            record = (
                self.session.query(ProjectFact)
                .filter_by(candidate_id=candidate_id, project_name=item.get("name", ""))
                .first()
            )
            if record is None:
                record = ProjectFact(
                    candidate_id=candidate_id,
                    fact_source_id=source.id,
                    item_id=self._stable_item_id("proj", candidate_id, item.get("name", "")),
                    project_name=item.get("name") or "",
                )
            record.candidate_id = candidate_id
            record.fact_source_id = source.id
            record.project_name = item.get("name") or ""
            record.short_resume_line = item.get("summary") or ""
            record.tools_and_tech = list(item.get("tools", []) or [])
            record.repo_url = item.get("link") or ""
            self.session.add(record)
        self.session.flush()
        return len(items)

    def _upsert_education(self, candidate_id: str, source: FactSource, items: list[dict]) -> int:
        for item in items:
            record = (
                self.session.query(EducationFact)
                .filter_by(
                    candidate_id=candidate_id,
                    institution=item.get("institution", ""),
                    degree=item.get("degree", ""),
                )
                .first()
            )
            if record is None:
                record = EducationFact(
                    candidate_id=candidate_id,
                    fact_source_id=source.id,
                    item_id=self._stable_item_id(
                        "edu",
                        candidate_id,
                        item.get("institution", ""),
                        item.get("degree", ""),
                    ),
                )
            record.candidate_id = candidate_id
            record.fact_source_id = source.id
            record.degree = item.get("degree") or ""
            record.field = item.get("field") or ""
            record.institution = item.get("institution") or ""
            record.location = item.get("location") or ""
            record.start_date = item.get("start_date") or ""
            record.end_date = item.get("end_date") or ""
            record.status = item.get("status") or ""
            notes = item.get("notes")
            record.notes = [notes] if isinstance(notes, str) and notes else list(notes or [])
            self.session.add(record)
        self.session.flush()
        return len(items)

    def _upsert_conflicts(self, candidate_id: str, items: list[dict]) -> int:
        for item in items:
            record = (
                self.session.query(FactConflict)
                .filter_by(
                    candidate_id=candidate_id,
                    field=item.get("field"),
                    source_a=item.get("source_a"),
                    source_b=item.get("source_b"),
                )
                .first()
            )
            if record is None:
                record = FactConflict(id=str(uuid.uuid4()), candidate_id=candidate_id)
            record.field = item.get("field")
            record.source_a = item.get("source_a")
            record.source_b = item.get("source_b")
            record.note = item.get("note")
            record.resolved = bool(item.get("resolved", record.resolved))
            self.session.add(record)
        self.session.flush()
        return len(items)

    def _upsert_evidence_index(self, candidate_id: str, items: list[dict]) -> int:
        for item in items:
            record = (
                self.session.query(EvidenceIndexItem)
                .filter_by(
                    candidate_id=candidate_id,
                    source_type=item.get("source_type"),
                    source_name=item.get("source_name"),
                    quote_or_summary=item.get("quote_or_summary"),
                )
                .first()
            )
            if record is None:
                record = EvidenceIndexItem(id=str(uuid.uuid4()), candidate_id=candidate_id)
            record.source_type = item.get("source_type")
            record.source_name = item.get("source_name")
            record.quote_or_summary = item.get("quote_or_summary")
            self.session.add(record)
        self.session.flush()
        return len(items)

    def _upsert_change_log(self, candidate_id: str, items: list) -> int:
        for item in items:
            message = item if isinstance(item, str) else item.get("message", "")
            record = (
                self.session.query(FactSheetChangeLog)
                .filter_by(candidate_id=candidate_id, message=message)
                .first()
            )
            if record is None:
                record = FactSheetChangeLog(id=str(uuid.uuid4()), candidate_id=candidate_id, message=message)
            else:
                record.message = message
            self.session.add(record)
        self.session.flush()
        return len(items)

    def _export_experience(self, item: ExperienceFact) -> dict:
        payload = {
            "role_title": item.role_title,
            "organization": item.organization,
            "location": item.location or None,
            "start_date": item.start_date or None,
            "end_date": item.end_date or None,
            "responsibilities": list(item.verified_core_facts or []),
            "tools": list(item.tools_and_tech or []),
            "achievements": list(item.enriched_description_bank or []),
            "evidence_refs": list(item.evidence_links or []),
        }
        verification_status = next(
            (tag.split(":", 1)[1] for tag in item.tags or [] if tag.startswith("verification_status:")),
            None,
        )
        if verification_status:
            payload["verification_status"] = verification_status
        return payload

    def _export_project(self, item: ProjectFact) -> dict:
        return {
            "name": item.project_name,
            "summary": item.short_resume_line or None,
            "tools": list(item.tools_and_tech or []),
            "link": item.repo_url or None,
        }

    def _export_education(self, item: EducationFact) -> dict:
        notes = "; ".join(item.notes or []) if item.notes else None
        return {
            "degree": item.degree,
            "field": item.field or None,
            "institution": item.institution,
            "location": item.location or None,
            "start_date": item.start_date or None,
            "end_date": item.end_date or None,
            "status": item.status or None,
            "notes": notes,
        }

    def _export_conflict(self, item: FactConflict) -> dict:
        payload = {}
        if item.field is not None:
            payload["field"] = item.field
        if item.source_a is not None:
            payload["source_a"] = item.source_a
        if item.source_b is not None:
            payload["source_b"] = item.source_b
        if item.note is not None:
            payload["note"] = item.note
        return payload

    def _export_evidence(self, item: EvidenceIndexItem) -> dict:
        payload = {"id": item.id}
        if item.source_type is not None:
            payload["source_type"] = item.source_type
        if item.source_name is not None:
            payload["source_name"] = item.source_name
        if item.quote_or_summary is not None:
            payload["quote_or_summary"] = item.quote_or_summary
        return payload

    def _skills_payload(self, skills_json: dict | None) -> dict:
        payload = {
            "programming_languages": [],
            "frameworks_and_platforms": [],
            "cloud_and_infra": [],
            "data_and_analytics": [],
            "business_tools": [],
            "methods": [],
        }
        if isinstance(skills_json, dict):
            payload.update(skills_json)
        return payload

    def _stable_item_id(self, prefix: str, *parts: str) -> str:
        digest = hashlib.sha1("||".join(parts).encode("utf-8")).hexdigest()[:16]
        return f"{prefix}-{digest}"
