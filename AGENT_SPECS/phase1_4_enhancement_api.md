# Spec: Phase 1.4 — Expert Enhancement API (Human Approval Gate)
Status: pending

## Context
After the CV workflow produces a draft that scores below 85, the user should be
able to request "expert enhancement proposals" — the LLM imagines itself as a
senior practitioner in the target role and suggests specific improvements to
bullet points or skills emphasis. The user approves or rejects each suggestion
individually before it is applied. This prevents the system from adding skills
the user doesn't actually have.

## Database Changes

### File: `job_agent/models.py`
Read the file first. Add a new model after the `ResumeDraft` model:

```python
class EnhancementProposal(Base):
    """A proposed improvement to a resume draft, awaiting user approval."""

    __tablename__ = "enhancement_proposals"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    draft_id: Mapped[UUID] = mapped_column(ForeignKey("resume_drafts.id"), nullable=False)
    section: Mapped[str] = mapped_column(String, nullable=False)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_text: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    question_for_user: Mapped[str] = mapped_column(Text, nullable=False)
    approved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # None = pending
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
```

Verify the existing imports at the top of `models.py` already include:
`UUID, uuid4, Base, Mapped, mapped_column, ForeignKey, String, Text, Boolean, DateTime, datetime, timezone`
If any are missing, add them.

### File: `job_agent/db.py`
The `EnhancementProposal` table will be created automatically by `Base.metadata.create_all()`
since the model is registered. No migration needed for development.

## Schema Changes

### File: `job_agent/schemas.py`
Read the file first. Add after the existing draft schemas:

```python
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
```

## Prompt Changes

### File: `job_agent/services/prompts.py`
Read the file first. Add this new function at the end of the file:

```python
def build_enhancement_prompt(profile: dict, job: dict, draft: dict, reviewer_gaps: list[str]) -> str:
    """Prompt for the mid model to propose expert enhancements.

    The model imagines itself as a senior practitioner and suggests specific,
    targeted improvements. It must only propose changes plausible given the
    candidate's existing experience — not fabrications.
    """
    gaps_text = "\n".join(f"  - {g}" for g in reviewer_gaps) or "  (none specified)"
    return f"""\
You are a senior {job.get("title", "technology")} professional at {job.get("company", "a top company")} \
reviewing a junior candidate's resume.

Your task: propose 3–5 specific, targeted improvements to this resume that would make it \
more compelling for this exact role. You may ONLY suggest changes that are plausible given \
the candidate's existing experience — do not invent skills or experiences.

For each proposal, ask the candidate a yes/no question to confirm they have the relevant \
experience before the change is applied.

══ TARGET JOB ═════════════════════════════════════════════════════════════
{job.get("title", "N/A")} at {job.get("company", "N/A")}
{str(job.get("description", ""))[:600]}

══ KNOWN GAPS (from reviewer) ═════════════════════════════════════════════
{gaps_text}

══ CURRENT DRAFT ═══════════════════════════════════════════════════════════
Headline: {draft.get("headline", "")}
Summary: {draft.get("professional_summary", "")}
Skills: {", ".join(draft.get("selected_skills") or [])}

══ CANDIDATE BACKGROUND ════════════════════════════════════════════════════
{profile.get("public_brand_summary", "")}

══ OUTPUT FORMAT ═══════════════════════════════════════════════════════════
Return valid JSON only. No markdown, no code fences, no extra text.
{{
  "proposals": [
    {{
      "section": "<headline|summary|skills|experience_bullet>",
      "original_text": "<the exact current text>",
      "proposed_text": "<the improved version>",
      "rationale": "<why this change improves the recruiter/ATS reception>",
      "question_for_user": "<yes/no question: e.g., 'Have you used dbt for pipeline transformation?'>"
    }}
  ]
}}""".strip()
```

## Workflow Changes

### File: `job_agent/services/workflows.py`
Read the file first. Add this new method to `CVWorkflowService` class,
after the `_heuristic_revision` method:

```python
def generate_enhancement_proposals(self, draft_id: UUID) -> list:
    """Generate expert enhancement proposals for a draft and store them in DB."""
    from job_agent.models import EnhancementProposal
    from job_agent.services.prompts import build_enhancement_prompt

    draft = self.session.get(ResumeDraft, draft_id)
    if draft is None:
        raise ValueError(f"Draft {draft_id} not found")

    context = self._load_context(
        str(draft.job_post_id), draft.resume_track.slug
    )

    # Use the reviewer's gaps if available, otherwise empty list
    reviewer_gaps = []
    if draft.review_feedback:
        reviewer_gaps = draft.review_feedback.get("gaps", [])

    try:
        result = self.router.generate(
            role="mid",
            system_prompt=(
                "You are an expert resume enhancement advisor. "
                "Return valid JSON only. No markdown, no extra text."
            ),
            user_prompt=build_enhancement_prompt(
                self._profile_dict(context.profile),
                self._job_dict(context.job),
                draft.content or {},
                reviewer_gaps,
            ),
        )
    except ProviderUnavailableError:
        # Fall back to small model if mid is unavailable
        result = self.router.generate(
            role="small",
            system_prompt=(
                "You are an expert resume enhancement advisor. "
                "Return valid JSON only. No markdown, no extra text."
            ),
            user_prompt=build_enhancement_prompt(
                self._profile_dict(context.profile),
                self._job_dict(context.job),
                draft.content or {},
                reviewer_gaps,
            ),
        )

    proposals = []
    for p in result.get("proposals", []):
        proposal = EnhancementProposal(
            draft_id=draft_id,
            section=p.get("section", ""),
            original_text=p.get("original_text", ""),
            proposed_text=p.get("proposed_text", ""),
            rationale=p.get("rationale", ""),
            question_for_user=p.get("question_for_user", ""),
        )
        self.session.add(proposal)
        proposals.append(proposal)

    self.session.commit()
    return proposals


def apply_approved_enhancements(self, draft_id: UUID, approved_ids: list[UUID]) -> ResumeDraft:
    """Apply user-approved enhancement proposals to the draft content."""
    from job_agent.models import EnhancementProposal
    import json

    draft = self.session.get(ResumeDraft, draft_id)
    if draft is None:
        raise ValueError(f"Draft {draft_id} not found")

    proposals = (
        self.session.query(EnhancementProposal)
        .filter(EnhancementProposal.draft_id == draft_id)
        .all()
    )

    content = dict(draft.content or {})

    for proposal in proposals:
        if proposal.id in approved_ids:
            proposal.approved = True
            # Apply the change: replace original_text with proposed_text
            # in whichever section it appears
            content_str = json.dumps(content)
            content_str = content_str.replace(
                json.dumps(proposal.original_text)[1:-1],
                json.dumps(proposal.proposed_text)[1:-1],
            )
            try:
                content = json.loads(content_str)
            except json.JSONDecodeError:
                pass  # If replacement fails, skip this proposal
        else:
            proposal.approved = False

    draft.content = content
    self.session.commit()
    self.session.refresh(draft)
    return draft
```

Note: You also need to add `resume_track` relationship loading. In `_load_context`,
the `track` is already returned as `context.track`. The `draft.resume_track` needs
to be eager-loaded. Add `lazy="select"` or use `session.get` with the track id.
Alternatively, load the track separately:
```python
track_slug = self.session.get(ResumeTrack, draft.resume_track_id).slug
context = self._load_context(str(draft.job_post_id), track_slug)
```

## API Endpoint Changes

### File: `job_agent/main.py`
Read the file first. Add these endpoints after the existing `/drafts/{draft_id}/approve` endpoint:

```python
@app.post("/drafts/{draft_id}/propose-enhancements")
def propose_enhancements(draft_id: UUID, db: Session = Depends(get_db)):
    """Generate expert enhancement proposals for a draft (human approval required)."""
    from job_agent.schemas import EnhancementProposalOut
    service = CVWorkflowService(session=db)
    try:
        proposals = service.generate_enhancement_proposals(draft_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [EnhancementProposalOut.model_validate(p) for p in proposals]


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
    return [EnhancementProposalOut.model_validate(p) for p in proposals]


@app.post("/drafts/{draft_id}/apply-enhancements")
def apply_enhancements(
    draft_id: UUID,
    body: "ApplyEnhancementsRequest",
    db: Session = Depends(get_db),
):
    """Apply user-approved enhancement proposals to the draft content."""
    from job_agent.schemas import ApplyEnhancementsRequest
    service = CVWorkflowService(session=db)
    try:
        updated_draft = service.apply_approved_enhancements(
            draft_id, body.approved_proposal_ids
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"draft_id": str(updated_draft.id), "status": "enhancements_applied"}
```

Add `ApplyEnhancementsRequest` to the imports from `job_agent.schemas` at the top of `main.py`.

## Verification
```bash
# Restart API then test:
curl -s localhost:8000/health
# Get a draft ID from existing drafts:
DRAFT_ID=$(curl -s localhost:8000/drafts | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")

# Generate proposals:
curl -s -X POST "localhost:8000/drafts/$DRAFT_ID/propose-enhancements" | python3 -m json.tool
# Expected: list of proposal objects with section, original_text, proposed_text, question_for_user

# Check pending:
curl -s "localhost:8000/drafts/$DRAFT_ID/pending-approvals" | python3 -m json.tool

/Users/youseffayyaz/miniforge3/bin/conda run -n ML python -m ruff check job_agent/
```

## Git
```bash
git add job_agent/models.py job_agent/schemas.py job_agent/services/prompts.py \
        job_agent/services/workflows.py job_agent/main.py
git commit -m "feat: add expert enhancement proposals with human approval gate

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```
