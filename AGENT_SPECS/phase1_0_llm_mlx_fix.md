# Spec: Phase 1.0 — LLM Router MLX Compatibility Fix
Status: done
Implemented by: Claude Code on 2026-04-08

## Context

The project was built assuming the LM Studio models would be GGUF format, which
supports `response_format={"type":"json_object"}` natively. The models have been
replaced with MLX versions (Apple Silicon native). Testing revealed three issues:

1. MLX models reject `response_format={"type":"json_object"}` with an error.
2. Qwen3.5 and similar thinking/reasoning models use a multi-phase token budget:
   - Phase 1: Reasoning (stored in `reasoning_content`, not `content`)
   - Phase 2: Final output (stored in `content`)
   If `max_tokens` is too low, reasoning consumes the entire budget and `content`
   stays empty. Token budgets must be configured per model role.
3. The `openai/gpt-oss-20b` model emits a structured prefix before its JSON:
   `<|channel|>final <|constrain|>JSON<|message|>{actual json}`
   This must be stripped before JSON parsing.

Additionally, the router used hard-coded model name strings (`model=settings.lm_studio_writer_model`)
instead of role names, making it impossible to swap models without changing code.

## What Was Changed

### 1. `job_agent/config.py` — Full redesign for public use
- Added `lm_studio_mid_model` (for the 20B model)
- Added `lm_studio_embedding_model`
- Added `lm_studio_max_tokens_small` (default: 4000)
- Added `lm_studio_max_tokens_writer` (default: 6000)
- Added `lm_studio_max_tokens_mid` (default: 4000)
- Added `anthropic_api_key`, `anthropic_model`, `use_claude_final_review`
- Changed `use_openai_review` default: True → False
- Changed `cv_revise_score` default: 75 → 60
- Changed `worker_poll_seconds` default: 3 → 5
- All fields now have `description=` for inline documentation

### 2. `job_agent/llm.py` — Complete rewrite
Key changes:
- Removed `generate_with_lm_studio(model=..., ...)` — replaced with role-based API
- Added `generate(role="small"|"writer"|"mid", ...)` — single public method
- `_ROLE_MAP` dict maps role → (model_attr, tokens_attr) on Settings
- Added `max_tokens` to all LM Studio requests (per role budget from config)
- Removed `response_format` from LM Studio requests (MLX doesn't support it)
- Added `_extract_json()` with 4-step fallback:
  1. Strip `<|channel|>...<|message|>` prefix (gpt-oss-20b quirk)
  2. Strip markdown code fences
  3. Try direct `json.loads()`
  4. Regex extract outermost `{...}` from prose
- Added `generate_with_claude()` using Anthropic Messages API
- Added warning log when `finish_reason == "length"` (token budget too small)
- Raises `ProviderUnavailableError` with descriptive messages when content is empty

### 3. `job_agent/services/workflows.py` — Updated to use role-based API
- `_generate_draft`: changed `generate_with_lm_studio(model=writer_model, ...)` → `generate(role="writer", ...)`
- `_review_draft`: changed `generate_with_lm_studio(model=small_model, ...)` → `generate(role="small", ...)`
  - Added Claude review path before OpenAI path
- `_apply_review_decision`: changed small model call → `generate(role="small", ...)`
  - Added Claude rewrite path (for score < cv_revise_score)

### 4. `.env` and `.env.example`
- Added all new settings with comments

### 5. `AGENTS.md` — Created
Codex-compatible project guide (equivalent of CLAUDE.md for OpenAI agents).

## Verification

```bash
# 1. Confirm API starts with new config
curl localhost:8000/health
# Expected: {"status":"ok"}

# 2. Confirm all three models appear in provider status
curl localhost:8000/providers
# Expected: small_model_configured=true, writer_model_configured=true, mid_model_configured=true

# 3. Run a CV workflow — should use role-based routing
curl -sX POST localhost:8000/tasks/cv-workflow \
  -H 'Content-Type: application/json' \
  -d '{"job_post_id":"<any existing job id>","resume_track_slug":"data-engineering-analytics","force_cloud_review":false}'
# Expected: task completes with status="completed", provider="lm_studio_writer" or "review_pass"

# 4. Lint
ruff check job_agent/
# Expected: no errors
```

## For Future Codex Tasks

When implementing the next spec (`phase1_1_prompts_rewrite.md`), the pattern to follow:
- All LLM calls use `self.router.generate(role=..., system_prompt=..., user_prompt=...)`
- System prompts must end with: "Return valid JSON only. No markdown, no explanation."
- User prompts must format profile/job data as readable text, NOT raw Python dict repr
- Never call `self.router.generate_with_lm_studio(...)` directly — that method no longer exists
