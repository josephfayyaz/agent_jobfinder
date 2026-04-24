from __future__ import annotations

import csv
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from job_agent.config import settings
from job_agent.models import Application, CommunicationEvent, CsvExport, JobPost, ResumeTrack
from job_agent.runtime_paths import resolve_artifacts_dir


class CsvExportService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def export_jobs_snapshot(self) -> CsvExport:
        export_dir = resolve_artifacts_dir(settings.artifacts_dir) / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        file_path = export_dir / f"jobs_snapshot_{timestamp}.csv"

        jobs = self.session.query(JobPost).order_by(JobPost.created_at.desc()).all()
        rows: list[dict[str, str]] = []

        for job in jobs:
            application = (
                self.session.query(Application)
                .filter(Application.job_post_id == job.id)
                .order_by(Application.updated_at.desc())
                .first()
            )
            track = None
            if application and application.resume_track_id:
                track = self.session.get(ResumeTrack, application.resume_track_id)
            if track is None and job.role_track_hint:
                track = self.session.query(ResumeTrack).filter(ResumeTrack.slug == job.role_track_hint).first()

            last_email = None
            if application is not None:
                last_email = (
                    self.session.query(CommunicationEvent)
                    .filter(CommunicationEvent.application_id == application.id)
                    .order_by(CommunicationEvent.event_at.desc())
                    .first()
                )

            rows.append(
                {
                    "job_id": str(job.id),
                    "discovered_at": job.created_at.isoformat(),
                    "source_platform": job.source_name,
                    "source_url": job.source_url,
                    "canonical_apply_url": job.canonical_apply_url or job.source_url,
                    "company_name": job.company,
                    "company_domain": job.company_domain,
                    "city": job.city or job.location,
                    "country": job.country,
                    "job_title": job.title,
                    "role_family": job.role_family,
                    "recommended_resume_track": track.slug if track else job.role_track_hint,
                    "job_status": job.status,
                    "application_status": application.status if application else "not_applied",
                    "applied_at": application.applied_at.isoformat() if application and application.applied_at else "",
                    "last_email_at": last_email.event_at.isoformat() if last_email else "",
                    "recruiter_name": job.recruiter_name,
                    "recruiter_email": job.recruiter_email,
                    "next_action": application.next_action if application else "",
                    "notes": application.notes if application else job.match_notes,
                }
            )

        fieldnames = [
            "job_id",
            "discovered_at",
            "source_platform",
            "source_url",
            "canonical_apply_url",
            "company_name",
            "company_domain",
            "city",
            "country",
            "job_title",
            "role_family",
            "recommended_resume_track",
            "job_status",
            "application_status",
            "applied_at",
            "last_email_at",
            "recruiter_name",
            "recruiter_email",
            "next_action",
            "notes",
        ]

        with file_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        export = CsvExport(
            export_type="jobs_snapshot",
            file_path=str(file_path),
            row_count=len(rows),
            filters={"regions": ["Italy", "EU"], "language": "English"},
        )
        self.session.add(export)
        self.session.commit()
        self.session.refresh(export)
        return export
