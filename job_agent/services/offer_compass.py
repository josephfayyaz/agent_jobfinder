"""Simple offer comparison and negotiation guidance."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from job_agent.models import OfferDecision

_NUMBER_RE = re.compile(r"(\d[\d.,]*)")

DEFAULT_PRIORITIES = {
    "compensation": 5,
    "location": 4,
    "learning": 4,
    "visa": 3,
    "work_life": 4,
}


def _parse_salary(value: str) -> float:
    matches = _NUMBER_RE.findall(value or "")
    if not matches:
        return 0.0
    values: list[float] = []
    for match in matches[:2]:
        normalized = match.replace(",", "").strip()
        try:
            values.append(float(normalized))
        except ValueError:
            continue
    return max(values) if values else 0.0


class OfferCompassService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def priorities(self, raw: dict[str, object] | None = None) -> dict[str, int]:
        values = dict(DEFAULT_PRIORITIES)
        for key in values:
            try:
                parsed = int((raw or {}).get(key, values[key]))
            except (TypeError, ValueError):
                parsed = values[key]
            values[key] = min(5, max(1, parsed))
        return values

    def list_offers(self, candidate_id: str | None) -> list[OfferDecision]:
        return (
            self.session.query(OfferDecision)
            .filter(OfferDecision.candidate_id == (candidate_id or None))
            .order_by(OfferDecision.updated_at.desc(), OfferDecision.created_at.desc())
            .all()
        )

    def score_offer(self, offer: OfferDecision, priorities: dict[str, int]) -> dict[str, Any]:
        salary_value = _parse_salary(offer.salary_text)
        compensation = 5 if salary_value >= 90000 else 4 if salary_value >= 65000 else 3 if salary_value >= 40000 else 2 if salary_value else 1
        remote_policy = str(offer.remote_policy or "").lower()
        location_score = 5 if "remote" in remote_policy else 4 if "hybrid" in remote_policy else 3 if offer.location else 2
        learning_score = 4 if len(str(offer.learning_notes or "").strip()) > 25 else 3 if offer.learning_notes else 2
        visa_score = 4 if len(str(offer.visa_notes or "").strip()) > 10 else 2 if offer.visa_notes else 3
        work_life_score = 4 if "remote" in remote_policy or "flex" in str(offer.work_life_notes or "").lower() else 3 if offer.work_life_notes else 2
        growth_score = 4 if len(str(offer.growth_notes or "").strip()) > 25 else 3 if offer.growth_notes else 2
        weighted = (
            compensation * priorities["compensation"]
            + location_score * priorities["location"]
            + max(learning_score, growth_score) * priorities["learning"]
            + visa_score * priorities["visa"]
            + work_life_score * priorities["work_life"]
        )
        max_score = 5 * sum(priorities.values())
        overall = round((weighted / max_score) * 100.0, 1) if max_score else 0.0
        return {
            "overall": overall,
            "salary_value": salary_value,
            "compensation": compensation,
            "location": location_score,
            "learning": max(learning_score, growth_score),
            "visa": visa_score,
            "work_life": work_life_score,
            "negotiation_bullets": self.negotiation_bullets(offer),
        }

    def compare(self, candidate_id: str | None, priorities: dict[str, int]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for offer in self.list_offers(candidate_id):
            rows.append({"offer": offer, "score": self.score_offer(offer, priorities)})
        rows.sort(key=lambda item: item["score"]["overall"], reverse=True)
        return rows

    def negotiation_bullets(self, offer: OfferDecision) -> list[str]:
        notes: list[str] = []
        if offer.salary_text:
            notes.append(f"Ask how the team benchmarks {offer.salary_text} against the market and role scope.")
        else:
            notes.append("Clarify the full compensation package before making a final decision.")
        if offer.remote_policy:
            notes.append(f"Confirm how the stated {offer.remote_policy} policy works in practice.")
        if offer.visa_notes:
            notes.append("Verify visa and relocation support in writing before accepting.")
        if offer.growth_notes:
            notes.append("Use the growth path as leverage when discussing title progression or review cycles.")
        return notes[:4]
