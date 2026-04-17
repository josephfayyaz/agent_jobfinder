# Phase 1.4 — Multi-Candidate Support + Fact Sheet JSON Schema Ingestion

## Goal

The current app has a single hardcoded `MasterProfile(id=1)`. Any second user who wants to
use the system must overwrite Yousef's data. Fix: introduce a `Candidate` model as the
first-class user/owner concept, a `MatchProfile` for structured job-matching inputs (replacing
the `additional_notes` dumping ground), and a JSON ingestion path that validates against the
canonical schema vendored in Phase 1.4.0.

Legacy endpoints (`GET /profile`, `POST /fact-sources/ingest`, etc.) continue to work
unchanged via a `DEFAULT_CANDIDATE_ID` config value that points to the migrated record.

## Dependencies

Add to `pyproject.toml` under `[project] dependencies`:
```
"jsonschema>=4.20,<5",
```

Run: `/Users/youseffayyaz/miniforge3/bin/conda run -n ML pip install -e ".[dev]"`

## New Models: `job_agent/models.py`

Add the following classes after the existing model definitions:

```python
import uuid as _uuid


class Candidate(Base):
    """Top-level user / candidate record. Owns all downstream facts."""
    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(_uuid.uuid4())
    )
    full_name: Mapped[str] = mapped_column(String(200))
    preferred_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MatchProfile(Base):
    """Structured matching inputs for a Candidate."""
    __tablename__ = "match_profiles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(_uuid.uuid4())
    )
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidates.id"), index=True)
    target_roles: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    excluded_roles: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    preferred_industries: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    location_preferences: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    work_authorization: Mapped[str | None] = mapped_column(String(100), nullable=True)
    availability_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    earliest_start_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    employment_preferences: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    seniority_estimate: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class FactConflict(Base):
    """First-class conflict tracking (schema: conflicts[])."""
    __tablename__ = "fact_conflicts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(_uuid.uuid4())
    )
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidates.id"), index=True)
    field: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_a: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_b: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EvidenceIndexItem(Base):
    """First-class evidence references (schema: evidence_index[])."""
    __tablename__ = "evidence_index_items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(_uuid.uuid4())
    )
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidates.id"), index=True)
    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    quote_or_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FactSheetChangeLog(Base):
    """Audit trail (schema: change_log[])."""
    __tablename__ = "fact_sheet_change_log"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(_uuid.uuid4())
    )
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidates.id"), index=True)
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

### Add nullable `candidate_id` FKs to existing fact tables

In each of these existing model classes, add ONE new column:

```python
# ExperienceFact, ProjectFact, EducationFact, SummaryVariant, KeywordSet, FactSource:
candidate_id: Mapped[str | None] = mapped_column(
    String(36), ForeignKey("candidates.id"), nullable=True, index=True
)
```

Leave nullable for now — the old single-user pathway still writes `None` here.
A future migration (Phase B1.1) will backfill and make them NOT NULL.

## Alembic Migration

Create `alembic/versions/xxxx_add_candidate_and_match_profile.py`:

```python
"""Add Candidate, MatchProfile, FactConflict, EvidenceIndexItem, FactSheetChangeLog tables;
add nullable candidate_id FK to existing fact tables.

Revision ID: b1c2d3e4f5a6
Revises: <previous_revision>
Create Date: 2026-04-11
"""
from alembic import op
import sqlalchemy as sa

def upgrade() -> None:
    # New tables
    op.create_table(
        "candidates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("preferred_name", sa.String(100), nullable=True),
        sa.Column("email", sa.String(200), nullable=True),
        sa.Column("active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_table(
        "match_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("candidate_id", sa.String(36), sa.ForeignKey("candidates.id"), nullable=False),
        sa.Column("target_roles", sa.JSON, nullable=True),
        sa.Column("excluded_roles", sa.JSON, nullable=True),
        sa.Column("preferred_industries", sa.JSON, nullable=True),
        sa.Column("location_preferences", sa.JSON, nullable=True),
        sa.Column("work_authorization", sa.String(100), nullable=True),
        sa.Column("availability_status", sa.String(50), nullable=True),
        sa.Column("earliest_start_date", sa.String(20), nullable=True),
        sa.Column("employment_preferences", sa.JSON, nullable=True),
        sa.Column("seniority_estimate", sa.JSON, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )
    op.create_table(
        "fact_conflicts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("candidate_id", sa.String(36), sa.ForeignKey("candidates.id"), nullable=False),
        sa.Column("field", sa.String(200), nullable=True),
        sa.Column("source_a", sa.Text, nullable=True),
        sa.Column("source_b", sa.Text, nullable=True),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("resolved", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_table(
        "evidence_index_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("candidate_id", sa.String(36), sa.ForeignKey("candidates.id"), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=True),
        sa.Column("source_name", sa.String(200), nullable=True),
        sa.Column("quote_or_summary", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_table(
        "fact_sheet_change_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("candidate_id", sa.String(36), sa.ForeignKey("candidates.id"), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    # Nullable candidate_id FK on existing fact tables
    for table in (
        "experience_facts", "project_facts", "education_facts",
        "summary_variants", "keyword_sets", "fact_sources",
    ):
        op.add_column(table, sa.Column(
            "candidate_id", sa.String(36),
            sa.ForeignKey("candidates.id"), nullable=True
        ))

    # Backfill: if MasterProfile(id=1) exists, create a Candidate and link existing rows.
    # Codex should implement this in the upgrade() body using op.execute() + a generated UUID.


def downgrade() -> None:
    for table in (
        "experience_facts", "project_facts", "education_facts",
        "summary_variants", "keyword_sets", "fact_sources",
    ):
        op.drop_column(table, "candidate_id")
    for table in (
        "fact_sheet_change_log", "evidence_index_items",
        "fact_conflicts", "match_profiles", "candidates",
    ):
        op.drop_table(table)
```

## New Config Field: `job_agent/config.py`

```python
default_candidate_id: str = Field(
    default="",
    description="UUID of the default candidate used by legacy single-user endpoints "
                "(GET /profile, POST /fact-sources/ingest). Set automatically on first "
                "candidate creation if not configured explicitly."
)
```

Add to `.env`:
```
DEFAULT_CANDIDATE_ID=
```

## New Service: `job_agent/services/fact_sheet_json.py`

```python
"""JSON fact sheet ingestion and export service."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

if TYPE_CHECKING:
    pass


@dataclass
class CandidateIngestResult:
    candidate_id: str
    counts: dict[str, int]   # {"experience": 3, "projects": 2, ...}
    conflicts: list[dict]    # raw conflict objects that were persisted
    missing: list[str]       # field paths flagged in fact_sheet["missing_information"]


class FactSheetJsonIngestionService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def ingest_json(
        self,
        candidate_id: str | None,
        fact_sheet: dict,
        source_name: str = "json_upload",
    ) -> CandidateIngestResult:
        """
        1. Validate fact_sheet against the canonical JSON Schema.
        2. If candidate_id is None, create a new Candidate from person.full_name.
        3. Upsert Candidate, MatchProfile, FactConflict, EvidenceIndexItem,
           FactSheetChangeLog, ExperienceFact, ProjectFact, EducationFact.
        4. NEVER cascade-delete; update-in-place keyed by (candidate_id, natural key).
        5. Return CandidateIngestResult.
        """
        from job_agent.services.resource_loader import load_fact_sheet_schema
        from job_agent.models import (
            Candidate, MatchProfile, FactConflict, EvidenceIndexItem,
            FactSheetChangeLog, ExperienceFact, ProjectFact, EducationFact,
        )
        import jsonschema

        schema = load_fact_sheet_schema()
        jsonschema.validate(instance=fact_sheet, schema=schema)

        # 1. Resolve / create Candidate
        person = fact_sheet.get("person", {})
        if not candidate_id:
            cand = Candidate(
                id=str(uuid.uuid4()),
                full_name=person.get("full_name", "Unknown"),
                preferred_name=person.get("preferred_name"),
                email=person.get("email"),
            )
            self.session.add(cand)
            self.session.flush()
            candidate_id = cand.id
        else:
            cand = self.session.get(Candidate, candidate_id)
            if not cand:
                raise ValueError(f"Candidate {candidate_id} not found")
            cand.full_name = person.get("full_name", cand.full_name)
            cand.preferred_name = person.get("preferred_name", cand.preferred_name)
            cand.email = person.get("email", cand.email)
            self.session.add(cand)

        # 2. Upsert MatchProfile
        mp_data = fact_sheet.get("match_profile", {})
        mp = self.session.query(MatchProfile).filter_by(candidate_id=candidate_id).first()
        if not mp:
            mp = MatchProfile(id=str(uuid.uuid4()), candidate_id=candidate_id)
        mp.target_roles = mp_data.get("target_roles", mp.target_roles)
        mp.excluded_roles = mp_data.get("excluded_roles", mp.excluded_roles)
        mp.preferred_industries = mp_data.get("preferred_industries", mp.preferred_industries)
        mp.location_preferences = mp_data.get("location_preferences", mp.location_preferences)
        mp.work_authorization = mp_data.get("work_authorization", mp.work_authorization)
        mp.availability_status = mp_data.get("availability_status", mp.availability_status)
        mp.earliest_start_date = mp_data.get("earliest_start_date", mp.earliest_start_date)
        mp.employment_preferences = mp_data.get("employment_preferences", mp.employment_preferences)
        mp.seniority_estimate = mp_data.get("seniority_estimate", mp.seniority_estimate)
        mp.updated_at = datetime.utcnow()
        self.session.add(mp)

        # 3. Persist conflicts, evidence, change log
        for conflict_data in fact_sheet.get("conflicts", []):
            fc = FactConflict(
                id=str(uuid.uuid4()),
                candidate_id=candidate_id,
                field=conflict_data.get("field"),
                source_a=conflict_data.get("source_a"),
                source_b=conflict_data.get("source_b"),
                note=conflict_data.get("note"),
                resolved=conflict_data.get("resolved", False),
                created_at=datetime.utcnow(),
            )
            self.session.add(fc)

        for item in fact_sheet.get("evidence_index", []):
            ei = EvidenceIndexItem(
                id=str(uuid.uuid4()),
                candidate_id=candidate_id,
                source_type=item.get("source_type"),
                source_name=item.get("source_name"),
                quote_or_summary=item.get("quote_or_summary"),
                created_at=datetime.utcnow(),
            )
            self.session.add(ei)

        for log_entry in fact_sheet.get("change_log", []):
            cl = FactSheetChangeLog(
                id=str(uuid.uuid4()),
                candidate_id=candidate_id,
                message=log_entry if isinstance(log_entry, str) else log_entry.get("message", ""),
                created_at=datetime.utcnow(),
            )
            self.session.add(cl)

        # 4. Upsert ExperienceFact rows (keyed by candidate_id + organization + title)
        counts: dict[str, int] = {}
        for exp in fact_sheet.get("experience", []):
            existing = self.session.query(ExperienceFact).filter_by(
                candidate_id=candidate_id,
                organization=exp.get("organization"),
                title=exp.get("title"),
            ).first()
            if not existing:
                existing = ExperienceFact(candidate_id=candidate_id)
            existing.organization = exp.get("organization")
            existing.title = exp.get("title")
            existing.start_date = exp.get("start_date")
            existing.end_date = exp.get("end_date")
            existing.bullets = exp.get("bullets", [])
            existing.keywords = exp.get("keywords", [])
            self.session.add(existing)
        counts["experience"] = len(fact_sheet.get("experience", []))

        for proj in fact_sheet.get("projects", []):
            existing = self.session.query(ProjectFact).filter_by(
                candidate_id=candidate_id,
                name=proj.get("name"),
            ).first()
            if not existing:
                existing = ProjectFact(candidate_id=candidate_id)
            existing.name = proj.get("name")
            existing.description = proj.get("description")
            existing.bullets = proj.get("bullets", [])
            existing.keywords = proj.get("keywords", [])
            self.session.add(existing)
        counts["projects"] = len(fact_sheet.get("projects", []))

        for edu in fact_sheet.get("education", []):
            existing = self.session.query(EducationFact).filter_by(
                candidate_id=candidate_id,
                institution=edu.get("institution"),
                degree=edu.get("degree"),
            ).first()
            if not existing:
                existing = EducationFact(candidate_id=candidate_id)
            existing.institution = edu.get("institution")
            existing.degree = edu.get("degree")
            existing.start_date = edu.get("start_date")
            existing.end_date = edu.get("end_date")
            self.session.add(existing)
        counts["education"] = len(fact_sheet.get("education", []))

        self.session.commit()

        return CandidateIngestResult(
            candidate_id=candidate_id,
            counts=counts,
            conflicts=fact_sheet.get("conflicts", []),
            missing=fact_sheet.get("missing_information", []),
        )

    def export_json(self, candidate_id: str) -> dict:
        """
        Dump the current candidate state as a canonical JSON schema-compliant dict.
        Inverse of ingest_json — used by GET /candidates/{id}/fact-sheet-json.
        """
        from job_agent.models import (
            Candidate, MatchProfile, FactConflict, EvidenceIndexItem,
            FactSheetChangeLog, ExperienceFact, ProjectFact, EducationFact,
        )
        cand = self.session.get(Candidate, candidate_id)
        if not cand:
            raise ValueError(f"Candidate {candidate_id} not found")

        mp = self.session.query(MatchProfile).filter_by(candidate_id=candidate_id).first()
        experiences = self.session.query(ExperienceFact).filter_by(
            candidate_id=candidate_id
        ).all()
        projects = self.session.query(ProjectFact).filter_by(
            candidate_id=candidate_id
        ).all()
        education = self.session.query(EducationFact).filter_by(
            candidate_id=candidate_id
        ).all()
        conflicts = self.session.query(FactConflict).filter_by(
            candidate_id=candidate_id
        ).all()
        evidence = self.session.query(EvidenceIndexItem).filter_by(
            candidate_id=candidate_id
        ).all()
        change_log = self.session.query(FactSheetChangeLog).filter_by(
            candidate_id=candidate_id
        ).order_by(FactSheetChangeLog.created_at).all()

        return {
            "person": {
                "full_name": cand.full_name,
                "preferred_name": cand.preferred_name,
                "email": cand.email,
            },
            "match_profile": {
                "target_roles": mp.target_roles if mp else None,
                "excluded_roles": mp.excluded_roles if mp else None,
                "preferred_industries": mp.preferred_industries if mp else None,
                "location_preferences": mp.location_preferences if mp else None,
                "work_authorization": mp.work_authorization if mp else None,
                "availability_status": mp.availability_status if mp else None,
                "earliest_start_date": mp.earliest_start_date if mp else None,
                "employment_preferences": mp.employment_preferences if mp else None,
                "seniority_estimate": mp.seniority_estimate if mp else None,
            } if mp else {},
            "experience": [
                {
                    "title": e.title,
                    "organization": e.organization,
                    "start_date": e.start_date,
                    "end_date": e.end_date,
                    "bullets": e.bullets or [],
                    "keywords": e.keywords or [],
                }
                for e in sorted(experiences, key=lambda x: x.start_date or "", reverse=True)
            ],
            "projects": [
                {
                    "name": p.name,
                    "description": p.description,
                    "bullets": p.bullets or [],
                    "keywords": p.keywords or [],
                }
                for p in projects
            ],
            "education": [
                {
                    "degree": e.degree,
                    "institution": e.institution,
                    "start_date": e.start_date,
                    "end_date": e.end_date,
                }
                for e in education
            ],
            "conflicts": [
                {
                    "field": c.field,
                    "source_a": c.source_a,
                    "source_b": c.source_b,
                    "note": c.note,
                    "resolved": c.resolved,
                }
                for c in conflicts
            ],
            "evidence_index": [
                {
                    "source_type": e.source_type,
                    "source_name": e.source_name,
                    "quote_or_summary": e.quote_or_summary,
                }
                for e in evidence
            ],
            "change_log": [cl.message for cl in change_log],
            "missing_information": [],  # populated by intake flow (Phase B3)
        }
```

## New Endpoints: `job_agent/main.py`

```python
from job_agent.services.fact_sheet_json import FactSheetJsonIngestionService

@app.post("/candidates")
def create_candidate(body: dict, db: Session = Depends(get_db)):
    """Create a new candidate shell."""
    from job_agent.models import Candidate
    import uuid as _uuid
    cand = Candidate(
        id=str(_uuid.uuid4()),
        full_name=body["full_name"],
        email=body.get("email"),
    )
    db.add(cand)
    db.commit()
    return {"id": cand.id, "full_name": cand.full_name}


@app.get("/candidates")
def list_candidates(db: Session = Depends(get_db)):
    from job_agent.models import Candidate
    return [{"id": c.id, "full_name": c.full_name, "email": c.email} for c in db.query(Candidate).all()]


@app.get("/candidates/{candidate_id}")
def get_candidate(candidate_id: str, db: Session = Depends(get_db)):
    from job_agent.models import Candidate
    cand = db.get(Candidate, candidate_id)
    if not cand:
        raise HTTPException(404, "Candidate not found")
    svc = FactSheetJsonIngestionService(db)
    return svc.export_json(candidate_id)


@app.post("/candidates/{candidate_id}/fact-sheet-json")
def ingest_fact_sheet_json(candidate_id: str, body: dict, db: Session = Depends(get_db)):
    """Ingest or update a JSON fact sheet for one candidate."""
    svc = FactSheetJsonIngestionService(db)
    result = svc.ingest_json(candidate_id=candidate_id, fact_sheet=body)
    return {
        "candidate_id": result.candidate_id,
        "counts": result.counts,
        "conflicts": len(result.conflicts),
        "missing": result.missing,
    }


@app.get("/candidates/{candidate_id}/fact-sheet-json")
def export_fact_sheet_json(candidate_id: str, db: Session = Depends(get_db)):
    svc = FactSheetJsonIngestionService(db)
    return svc.export_json(candidate_id)


@app.get("/candidates/{candidate_id}/fact-sheet-text")
def export_fact_sheet_text(candidate_id: str, db: Session = Depends(get_db)):
    from job_agent.services.fact_sheet_renderer import render_fact_sheet_text
    svc = FactSheetJsonIngestionService(db)
    fact_sheet = svc.export_json(candidate_id)
    text = render_fact_sheet_text(fact_sheet)
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(text)
```

## Tests

### `tests/test_fact_sheet_json.py`

```python
import pytest
import uuid


_MINIMAL_FACT_SHEET = {
    "person": {"full_name": "Test User", "email": "test@example.com"},
    "match_profile": {"target_roles": ["Data Engineer"]},
    "experience": [
        {
            "title": "Data Engineer",
            "organization": "ACME Corp",
            "start_date": "2022-01",
            "end_date": None,
            "bullets": ["built ETL pipelines", "wrote Python scripts"],
            "keywords": ["python", "etl"],
        }
    ],
    "projects": [],
    "education": [],
    "conflicts": [],
    "evidence_index": [],
    "change_log": [],
    "missing_information": [],
}


def test_ingest_json_creates_candidate_and_match_profile(db_session):
    from job_agent.services.fact_sheet_json import FactSheetJsonIngestionService
    svc = FactSheetJsonIngestionService(db_session)
    result = svc.ingest_json(candidate_id=None, fact_sheet=_MINIMAL_FACT_SHEET)
    assert result.candidate_id
    from job_agent.models import Candidate, MatchProfile
    cand = db_session.get(Candidate, result.candidate_id)
    assert cand.full_name == "Test User"
    mp = db_session.query(MatchProfile).filter_by(candidate_id=result.candidate_id).first()
    assert mp is not None
    assert mp.target_roles == ["Data Engineer"]


def test_ingest_json_preserves_conflicts_and_evidence(db_session):
    from job_agent.services.fact_sheet_json import FactSheetJsonIngestionService
    fs = dict(_MINIMAL_FACT_SHEET)
    fs["conflicts"] = [{"field": "title", "source_a": "CV", "source_b": "LinkedIn", "note": ""}]
    fs["evidence_index"] = [{"source_type": "CV", "source_name": "cv.pdf", "quote_or_summary": "..."}]
    svc = FactSheetJsonIngestionService(db_session)
    result = svc.ingest_json(None, fs)
    from job_agent.models import FactConflict, EvidenceIndexItem
    assert db_session.query(FactConflict).filter_by(candidate_id=result.candidate_id).count() == 1
    assert db_session.query(EvidenceIndexItem).filter_by(candidate_id=result.candidate_id).count() == 1


def test_ingest_json_is_idempotent(db_session):
    """Re-ingesting the same JSON twice must not duplicate experience rows."""
    from job_agent.services.fact_sheet_json import FactSheetJsonIngestionService
    from job_agent.models import ExperienceFact
    svc = FactSheetJsonIngestionService(db_session)
    result = svc.ingest_json(None, _MINIMAL_FACT_SHEET)
    svc.ingest_json(result.candidate_id, _MINIMAL_FACT_SHEET)
    count = db_session.query(ExperienceFact).filter_by(candidate_id=result.candidate_id).count()
    assert count == 1


def test_export_json_roundtrip(db_session):
    """ingest → export must produce the same person, match_profile, and experience."""
    from job_agent.services.fact_sheet_json import FactSheetJsonIngestionService
    svc = FactSheetJsonIngestionService(db_session)
    result = svc.ingest_json(None, _MINIMAL_FACT_SHEET)
    exported = svc.export_json(result.candidate_id)
    assert exported["person"]["full_name"] == "Test User"
    assert exported["experience"][0]["title"] == "Data Engineer"
    assert exported["match_profile"]["target_roles"] == ["Data Engineer"]


def test_legacy_profile_endpoint_still_works_after_migration(client):
    """GET /profile must return 200 even after the new Candidate tables exist."""
    resp = client.get("/profile")
    assert resp.status_code in (200, 404)  # 404 if no profile seeded, but not 500


def test_invalid_json_rejected_with_jsonschema_error(db_session):
    from job_agent.services.fact_sheet_json import FactSheetJsonIngestionService
    import jsonschema
    svc = FactSheetJsonIngestionService(db_session)
    with pytest.raises(jsonschema.ValidationError):
        svc.ingest_json(None, {"totally": "wrong"})
```

## Commit Message
```
feat(fact_sheet): add multi-candidate support, JSON schema ingestion, and match_profile table (Phase 1.4)
```
