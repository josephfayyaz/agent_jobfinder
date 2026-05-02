from __future__ import annotations

import re
from typing import Any


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").casefold()).strip()


def _evidence_bank(profile_data: dict[str, Any]) -> list[str]:
    bank: list[str] = []
    for section_key in ("experiences", "projects"):
        for item in profile_data.get(section_key) or []:
            if not isinstance(item, dict):
                continue
            for bullet in item.get("bullets") or []:
                text = str(bullet).strip()
                if text:
                    bank.append(text)
            for key in ("summary", "description", "short_resume_line"):
                text = str(item.get(key) or "").strip()
                if text:
                    bank.append(text)
    for skill in profile_data.get("global_skills") or []:
        text = str(skill).strip()
        if text:
            bank.append(text)
    return bank


def _token_overlap(text: str, evidence: str) -> float:
    left = {token for token in re.findall(r"[a-z0-9][a-z0-9+/.-]{2,}", _normalize(text))}
    right = {token for token in re.findall(r"[a-z0-9][a-z0-9+/.-]{2,}", _normalize(evidence))}
    if not left or not right:
        return 0.0
    return len(left & right) / max(len(left), 1)


def classify_preview_text(text: str, evidence_bank: list[str]) -> str:
    normalized = _normalize(text)
    if not normalized:
        return "direct_fact"
    for evidence in evidence_bank:
        if normalized == _normalize(evidence):
            return "direct_fact"
    best_overlap = 0.0
    for evidence in evidence_bank:
        best_overlap = max(best_overlap, _token_overlap(text, evidence))
    if best_overlap >= 0.48:
        return "safe_paraphrase"
    if best_overlap >= 0.22:
        return "adjacent_inference"
    return "needs_user_confirmation"


def build_preview_annotations(
    *,
    draft_content: dict[str, Any],
    profile_data: dict[str, Any],
    accepted_item_ids: list[str] | None = None,
) -> dict[str, Any]:
    accepted = set(accepted_item_ids or [])
    evidence_bank = _evidence_bank(profile_data)
    items: list[dict[str, Any]] = []

    summary = str(draft_content.get("professional_summary") or "").strip()
    if summary:
        tag = classify_preview_text(summary, evidence_bank)
        items.append(
            {
                "item_id": "summary",
                "section": "summary",
                "text": summary,
                "tag": tag,
                "confirmed": tag in {"direct_fact", "safe_paraphrase"} or "summary" in accepted,
            }
        )

    for section_name in ("selected_experiences", "selected_projects"):
        for item_index, item in enumerate(draft_content.get(section_name) or []):
            if not isinstance(item, dict):
                continue
            for bullet_index, bullet in enumerate(item.get("bullets") or []):
                text = str(bullet).strip()
                if not text:
                    continue
                item_id = f"{section_name}:{item_index}:{bullet_index}"
                tag = classify_preview_text(text, evidence_bank)
                items.append(
                    {
                        "item_id": item_id,
                        "section": section_name,
                        "text": text,
                        "tag": tag,
                        "confirmed": tag in {"direct_fact", "safe_paraphrase"} or item_id in accepted,
                    }
                )

    pending = [
        item
        for item in items
        if item["tag"] in {"adjacent_inference", "needs_user_confirmation"} and not item["confirmed"]
    ]
    return {
        "items": items,
        "pending_confirmation_count": len(pending),
        "pending_item_ids": [item["item_id"] for item in pending],
    }
