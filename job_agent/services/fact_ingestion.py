from __future__ import annotations

from typing import Any
import hashlib

from sqlalchemy.orm import Session

from job_agent.models import (
    EducationFact,
    ExperienceFact,
    FactSource,
    KeywordSet,
    MasterProfile,
    ProjectFact,
    SummaryVariant,
)
from job_agent.parsers.fact_sheet import as_list, load_fact_sheet, parse_fact_sheet


class FactSheetIngestionService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def ingest(self, path: str | None = None, content: str | None = None, source_path: str | None = None) -> dict[str, Any]:
        if content is not None:
            if not source_path:
                source_path = path or "inline_fact_sheet.txt"
            source_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        elif path:
            source_path, source_hash, content = load_fact_sheet(path)
        else:
            raise ValueError("Either path or content must be provided for fact sheet ingestion.")
        parsed = parse_fact_sheet(content)

        latest = (
            self.session.query(FactSource)
            .filter(FactSource.source_path == source_path)
            .order_by(FactSource.imported_at.desc())
            .first()
        )
        reused_existing_source = bool(latest and latest.source_hash == source_hash)

        self.session.query(EducationFact).delete()
        self.session.query(ExperienceFact).delete()
        self.session.query(ProjectFact).delete()
        self.session.query(SummaryVariant).delete()
        self.session.query(KeywordSet).delete()

        if latest is None:
            source = FactSource(
                source_path=source_path,
                source_hash=source_hash,
                raw_content=content,
                parsed_metadata={},
            )
            self.session.add(source)
            self.session.flush()
        else:
            source = latest
            source.source_hash = source_hash
            source.raw_content = content

        source.parsed_metadata = {
            "core_profile": parsed.get("core_profile", {}),
            "skills_inventory": parsed.get("skills_inventory", {}),
            "custom_rules": parsed.get("custom_rules", {}),
            "open_items": parsed.get("open_items", []),
        }

        for key, value in parsed.get("summary_bank", {}).items():
            self.session.add(SummaryVariant(fact_source_id=source.id, key=key, value=str(value)))

        for key, value in parsed.get("keyword_sets", {}).items():
            self.session.add(KeywordSet(fact_source_id=source.id, key=key, values=as_list(value)))

        for item in parsed.get("education_items", []):
            self.session.add(
                EducationFact(
                    fact_source_id=source.id,
                    item_id=item.get("ITEM_ID", ""),
                    degree=item.get("DEGREE", ""),
                    field=item.get("FIELD", ""),
                    institution=item.get("INSTITUTION", ""),
                    location=item.get("LOCATION", ""),
                    start_date=item.get("START_DATE", ""),
                    end_date=item.get("END_DATE", ""),
                    status=item.get("STATUS", ""),
                    preferred_presentation=item.get("PREFERRED_PRESENTATION_IN_INDUSTRY_CVS", ""),
                    notes=as_list(item.get("NOTES", [])),
                )
            )

        for item in parsed.get("experience_items", []):
            self.session.add(
                ExperienceFact(
                    fact_source_id=source.id,
                    item_id=item.get("ITEM_ID", ""),
                    section_name=item.get("SECTION_NAME", ""),
                    role_title=item.get("ROLE_TITLE", ""),
                    organization=item.get("ORGANIZATION", ""),
                    location=item.get("LOCATION", ""),
                    start_date=item.get("START_DATE", item.get("INTERNAL_START_DATE", "")),
                    end_date=item.get("END_DATE", item.get("INTERNAL_END_DATE", "")),
                    employment_type=item.get("EMPLOYMENT_TYPE", ""),
                    role_match_priority=self._priority_dict(item.get("ROLE_MATCH_PRIORITY", [])),
                    business_context=item.get("BUSINESS_CONTEXT", ""),
                    project_context=item.get("PROJECT_CONTEXT", ""),
                    verified_core_facts=as_list(item.get("VERIFIED_CORE_FACTS", [])),
                    enriched_description_bank=as_list(item.get("ENRICHED_DESCRIPTION_BANK", [])),
                    tools_and_tech=as_list(item.get("TOOLS_AND_TECH", [])),
                    best_bullets_by_track=self._best_bullets(item),
                    metrics_to_capture=as_list(item.get("METRICS_TO_CAPTURE", [])),
                    evidence_links=as_list(item.get("EVIDENCE_LINKS", [])),
                    tags=as_list(item.get("TAGS", [])),
                )
            )

        for item in parsed.get("project_items", []):
            self.session.add(
                ProjectFact(
                    fact_source_id=source.id,
                    item_id=item.get("ITEM_ID", ""),
                    project_name=item.get("PROJECT_NAME", ""),
                    status=item.get("STATUS", ""),
                    dates=item.get("DATES", ""),
                    role=item.get("ROLE", ""),
                    repo_url=item.get("REPO_URL", ""),
                    short_resume_line=item.get("SHORT_RESUME_LINE", ""),
                    role_match_priority=self._priority_dict(item.get("ROLE_MATCH_PRIORITY", [])),
                    verified_core_facts=as_list(item.get("VERIFIED_CORE_FACTS", [])),
                    key_results=as_list(item.get("KEY_RESULTS", [])),
                    enriched_description_bank=as_list(item.get("ENRICHED_DESCRIPTION_BANK", [])),
                    tools_and_tech=as_list(item.get("TOOLS_AND_TECH", [])),
                    best_bullets_by_track=self._best_bullets(item),
                    tags=as_list(item.get("TAGS", [])),
                )
            )

        self._sync_master_profile(parsed, source)
        self.session.commit()

        return {
            "source_path": source_path,
            "source_hash": source_hash,
            "reused_existing_source": reused_existing_source,
            "counts": self._count_payload(parsed),
        }

    def _sync_master_profile(self, parsed: dict[str, Any], source: FactSource) -> None:
        core = parsed.get("core_profile", {})
        summary_bank = parsed.get("summary_bank", {})
        skills_inventory = parsed.get("skills_inventory", {})

        profile = self.session.get(MasterProfile, 1)
        if profile is None:
            profile = MasterProfile(id=1)
            self.session.add(profile)

        profile.full_name = core.get("FULL_NAME", profile.full_name)
        profile.email = core.get("PRIMARY_EMAIL", profile.email)
        profile.phone = core.get("PHONE", profile.phone)
        profile.location = core.get("CURRENT_LOCATION", profile.location)
        profile.linkedin_url = core.get("LINKEDIN", profile.linkedin_url)
        profile.github_url = core.get("GITHUB", profile.github_url)
        profile.public_brand_summary = (
            core.get("CURRENT_POSITIONING")
            or summary_bank.get("SHORT_PROFILE_LINE_FOR_LINKEDIN_OR_TOP_OF_CV", "")
            or profile.public_brand_summary
        )
        profile.experiences = [self._profile_experience(item) for item in parsed.get("experience_items", [])]
        profile.projects = [self._profile_project(item) for item in parsed.get("project_items", [])]
        profile.education = [self._profile_education(item) for item in parsed.get("education_items", [])]
        profile.certifications = []
        profile.achievements = []
        profile.global_skills = self._flatten_skills(skills_inventory)
        profile.additional_notes = {
            "source_path": source.source_path,
            "source_hash": source.source_hash,
            "target_regions": as_list(core.get("TARGET_REGIONS", [])),
            "current_positioning": core.get("CURRENT_POSITIONING", ""),
            "full_time_availability_note": core.get("FULL_TIME_AVAILABILITY_NOTE", ""),
            "recruiter_presentation_rule": core.get("RECRUITER_PRESENTATION_RULE", ""),
            "good_lead_options": as_list(core.get("GOOD_LEAD_OPTIONS", [])),
            "custom_rules": parsed.get("custom_rules", {}),
            "open_items": parsed.get("open_items", []),
        }

    def _flatten_skills(self, skills_inventory: dict[str, Any]) -> list[str]:
        seen: set[str] = set()
        flattened: list[str] = []
        excluded_keys = {"SKILL_SCOPE_NOTE", "CLOUD_DATA_STACK_PRESENTATION_RULE"}
        for key, value in skills_inventory.items():
            if key in excluded_keys:
                continue
            for item in as_list(value):
                normalized = item.strip()
                if not normalized or normalized.lower() in seen:
                    continue
                seen.add(normalized.lower())
                flattened.append(normalized)
        return flattened

    def _profile_experience(self, item: dict[str, Any]) -> dict[str, Any]:
        bullets = as_list(item.get("VERIFIED_CORE_FACTS", []))[:4]
        if not bullets:
            bullets = as_list(item.get("ENRICHED_DESCRIPTION_BANK", []))[:3]
        return {
            "item_id": item.get("ITEM_ID", ""),
            "title": item.get("ROLE_TITLE", ""),
            "company": item.get("ORGANIZATION", ""),
            "location": item.get("LOCATION", ""),
            "summary": item.get("BUSINESS_CONTEXT", "") or item.get("PROJECT_CONTEXT", ""),
            "bullets": bullets,
            "skills": as_list(item.get("TOOLS_AND_TECH", []))[:10],
            "tags": as_list(item.get("TAGS", [])),
        }

    def _profile_project(self, item: dict[str, Any]) -> dict[str, Any]:
        bullets = as_list(item.get("KEY_RESULTS", []))[:2] + as_list(item.get("VERIFIED_CORE_FACTS", []))[:2]
        return {
            "item_id": item.get("ITEM_ID", ""),
            "name": item.get("PROJECT_NAME", ""),
            "summary": item.get("SHORT_RESUME_LINE", ""),
            "bullets": bullets[:4],
            "skills": as_list(item.get("TOOLS_AND_TECH", []))[:10],
            "repo_url": item.get("REPO_URL", ""),
            "tags": as_list(item.get("TAGS", [])),
        }

    def _profile_education(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "item_id": item.get("ITEM_ID", ""),
            "institution": item.get("INSTITUTION", ""),
            "degree": item.get("DEGREE", ""),
            "field": item.get("FIELD", ""),
            "status": item.get("STATUS", ""),
            "presentation": item.get("PREFERRED_PRESENTATION_IN_INDUSTRY_CVS", ""),
        }

    def _priority_dict(self, values: Any) -> dict[str, str]:
        priorities: dict[str, str] = {}
        for item in as_list(values):
            if ":" not in item:
                continue
            key, value = item.split(":", 1)
            priorities[key.strip()] = value.strip()
        return priorities

    def _best_bullets(self, item: dict[str, Any]) -> dict[str, list[str]]:
        output: dict[str, list[str]] = {}
        for key, value in item.items():
            if key.startswith("BEST_BULLETS_FOR_"):
                output[key] = as_list(value)
        return output

    def _count_payload(self, parsed: dict[str, Any]) -> dict[str, int]:
        return {
            "education_items": len(parsed.get("education_items", [])),
            "experience_items": len(parsed.get("experience_items", [])),
            "project_items": len(parsed.get("project_items", [])),
            "summary_variants": len(parsed.get("summary_bank", {})),
            "keyword_sets": len(parsed.get("keyword_sets", {})),
        }
