"""Build a reusable interview evidence bank from approved drafts and verified facts."""

from __future__ import annotations

from hashlib import sha1
import re

from sqlalchemy.orm import Session

from job_agent.models import BulletClarification, InterviewStory, ResumeDraft, VerifiedCandidateFact

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9+#.-]{1,}")


def _dedupe_key(*parts: str) -> str:
    joined = " | ".join(part.strip().lower() for part in parts if part.strip())
    return sha1(joined.encode("utf-8")).hexdigest()


def _extract_tools(text: str) -> list[str]:
    seen: list[str] = []
    for token in _TOKEN_RE.findall(text or ""):
        normalized = token.strip()
        if len(normalized) < 3:
            continue
        if normalized.lower() in {"with", "from", "that", "this", "have", "used", "built", "team"}:
            continue
        if normalized not in seen:
            seen.append(normalized)
        if len(seen) >= 6:
            break
    return seen


class InterviewBankService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def rebuild(self, candidate_id: str | None) -> int:
        candidate_scope = candidate_id or None
        existing = (
            self.session.query(InterviewStory)
            .filter(InterviewStory.candidate_id == candidate_scope)
            .all()
        )
        for row in existing:
            row.is_active = False

        created = 0
        seen: set[str] = set()

        facts = (
            self.session.query(VerifiedCandidateFact)
            .filter(
                VerifiedCandidateFact.is_active.is_(True),
                VerifiedCandidateFact.candidate_id == candidate_scope,
            )
            .all()
        )
        for fact in facts:
            fingerprint = _dedupe_key(fact.gap_label, fact.evidence)
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            self.session.add(
                InterviewStory(
                    candidate_id=candidate_scope,
                    title=fact.gap_label,
                    context=f"Verified profile memory for {fact.gap_label}.",
                    action=fact.evidence,
                    result=fact.evidence,
                    tools=_extract_tools(fact.evidence),
                    role_family_tags=[fact.fact_type] if fact.fact_type else [],
                    confidence_source="verified-memory",
                    fingerprint=fingerprint,
                    source_ref=str(fact.source_draft_id or ""),
                    is_active=True,
                )
            )
            created += 1

        approved_drafts = (
            self.session.query(ResumeDraft)
            .filter(ResumeDraft.approved.is_(True))
            .order_by(ResumeDraft.updated_at.desc())
            .all()
        )
        for draft in approved_drafts:
            role_family = ""
            if draft.resume_track is not None:
                role_family = str(draft.resume_track.role_family or "").strip()
            experiences = list((draft.content or {}).get("selected_experiences") or [])
            for index, experience in enumerate(experiences):
                bullets = list(experience.get("bullets") or [])
                if not bullets:
                    continue
                title = str(experience.get("title") or "Approved project evidence").strip()
                company = str(experience.get("company") or "").strip()
                action = bullets[0]
                result = bullets[1] if len(bullets) > 1 else bullets[0]
                fingerprint = _dedupe_key(title, company, action, result)
                if fingerprint in seen:
                    continue
                seen.add(fingerprint)
                context = f"{title} at {company}".strip().strip(" at")
                self.session.add(
                    InterviewStory(
                        candidate_id=candidate_scope,
                        title=context or title,
                        context=context or "Approved draft evidence",
                        action=action,
                        result=result,
                        tools=_extract_tools(" ".join(bullets)),
                        role_family_tags=[role_family] if role_family else [],
                        confidence_source="approved-draft",
                        fingerprint=fingerprint,
                        source_ref=str(draft.id),
                        is_active=True,
                    )
                )
                created += 1
                if index >= 3:
                    break

        accepted_clarifications = (
            self.session.query(BulletClarification)
            .filter(BulletClarification.user_accepted.is_(True))
            .order_by(BulletClarification.updated_at.desc())
            .all()
        )
        for clarification in accepted_clarifications:
            if clarification.draft is None or clarification.draft.resume_track is None:
                continue
            rewritten = clarification.rewritten_bullets or {}
            bullets: list[str] = []
            if isinstance(rewritten, dict):
                for value in rewritten.values():
                    if isinstance(value, list):
                        bullets.extend(str(item).strip() for item in value if str(item).strip())
                    elif isinstance(value, str) and value.strip():
                        bullets.append(value.strip())
            action = bullets[0] if bullets else str(clarification.suggested_rewrite or "").strip()
            if not action:
                continue
            result = bullets[1] if len(bullets) > 1 else action
            title = str(clarification.target_section or "Accepted clarification").replace("_", " ").title()
            fingerprint = _dedupe_key(title, action, result, str(clarification.draft_id))
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            role_family = str(clarification.draft.resume_track.role_family or "").strip()
            self.session.add(
                InterviewStory(
                    candidate_id=candidate_scope,
                    title=title,
                    context="Accepted clarification from a reviewed draft.",
                    action=action,
                    result=result,
                    tools=_extract_tools(" ".join(bullets) or action),
                    role_family_tags=[role_family] if role_family else [],
                    confidence_source="accepted-clarification",
                    fingerprint=fingerprint,
                    source_ref=str(clarification.id),
                    is_active=True,
                )
            )
            created += 1

        self.session.commit()
        return created

    def list_stories(
        self,
        candidate_id: str | None,
        *,
        role_family: str | None = None,
        confidence: str | None = None,
    ) -> list[InterviewStory]:
        query = self.session.query(InterviewStory).filter(
            InterviewStory.is_active.is_(True),
            InterviewStory.candidate_id == (candidate_id or None),
        )
        rows = query.order_by(InterviewStory.updated_at.desc(), InterviewStory.created_at.desc()).all()
        filtered: list[InterviewStory] = []
        for row in rows:
            if role_family and role_family not in (row.role_family_tags or []):
                continue
            if confidence and row.confidence_source != confidence:
                continue
            filtered.append(row)
        return filtered
