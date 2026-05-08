from __future__ import annotations

from job_agent.providers import normalize_provider_mode, provider_prompt_char_limit


def trim_text_head_tail(text: str, limit: int, marker: str) -> str:
    cleaned = str(text or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    if limit <= len(marker) + 32:
        return cleaned[:limit].strip()
    keep_head = min(max(80, limit // 2), max(80, limit - len(marker) - 16))
    keep_tail = max(40, limit - keep_head - len(marker) - 8)
    return f"{cleaned[:keep_head].rstrip()}\n\n{marker}\n\n{cleaned[-keep_tail:].lstrip()}".strip()


def shape_text_for_workflow(text: str, *, workflow: str, provider_mode: str | None = None) -> str:
    mode = normalize_provider_mode(provider_mode)
    limit = provider_prompt_char_limit(workflow, mode)
    return trim_text_head_tail(text, limit, "[... provider-safe truncation ...]")


def shape_text_blocks_for_workflow(
    blocks: list[str], *, workflow: str, provider_mode: str | None = None
) -> list[str]:
    mode = normalize_provider_mode(provider_mode)
    total_limit = provider_prompt_char_limit(workflow, mode)
    normalized_blocks = [str(block or "").strip() for block in blocks if str(block or "").strip()]
    if not normalized_blocks:
        return []
    shaped_blocks: list[str] = []
    remaining_total = max(total_limit, 0)
    remaining_count = len(normalized_blocks)
    for block in normalized_blocks:
        block_limit = max(200, remaining_total // max(1, remaining_count))
        shaped = trim_text_head_tail(block, block_limit, "[... block truncated ...]")
        shaped_blocks.append(shaped)
        remaining_total = max(0, remaining_total - len(shaped))
        remaining_count -= 1
    return shaped_blocks
