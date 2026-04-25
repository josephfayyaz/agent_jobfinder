# Design: Multi-Provider AI, Gmail OAuth, Ollama, and Resilience
**Date:** 2026-04-24
**Status:** Approved — ready for Codex implementation
**Sub-projects:** P2 · P3 · P4 · P5

---

## Context

The app is feature-complete through I11 + P1. This design adds four independent
improvements that make the app production-quality for a wider audience:

- **P4** — OpenAI as the default AI provider with a guided first-run wizard
- **P2** — Gmail OAuth2 (replace App Password) + enhanced job scraping pipeline
- **P3** — Ollama as a third local LLM backend alongside LM Studio
- **P5** — Structured error handling for network drops and model failures

Build order: P4 → P2 → P3 → P5

---

## P4 — OpenAI Default + Guided Setup Wizard

### Decision
`llm_provider_mode` default changes from `"local"` to `"openai"`.
The existing OpenAI routing in `LLMRouter` is unchanged.

### Model roles (user-editable, all providers)
| Role | Purpose | OpenAI default | LM Studio default | Ollama default |
|------|---------|---------------|-------------------|----------------|
| fast | Scoring, ATS matching, analysis | `gpt-4o-mini` | existing `small` model | `llama3:8b` |
| writer | CV drafts, cover letters, outreach | `gpt-4o` | existing `writer` model | `mistral:7b` |

New config fields: `openai_fast_model`, `openai_writer_model`
(existing `openai_review_model` and `openai_escalation_model` kept for backward compat,
mapped to fast/writer respectively)

### Onboarding wizard — AI as mandatory Step 1
The existing 6-step onboarding gains a new first step: AI provider configuration.
The step validates the key/URL before allowing "Next". The user cannot proceed
without a working AI connection.

```
Step 1  Configure AI provider (required — validated before Next)
        ├─ OpenAI → API key field + "How to get your key" guide
        │   Guide: platform.openai.com → API keys → Create new → copy → paste → Validate
        ├─ LM Studio → base URL field → ping test
        └─ Ollama → base URL field → ping test
Step 2  Name + contact info
Step 3  Upload CV / paste experience
Step 4  Generate fact sheet  (uses Step 1 AI)
Step 5  Review job roles
Step 6  Done
```

### Non-dismissable banner for missing AI config
If a returning user has no configured AI provider, every page shows:
```
⚠ No AI provider configured — CV generation and job scoring are disabled.  [Configure →]
```
Rendered in `base.html`, driven by `GET /health/ai-status` returning
`{"configured": bool}`. Jobs in this state show locked action buttons.

---

## P2 — Gmail OAuth2 + Enhanced Scraping Pipeline

### Auth — OAuth2 Desktop flow (replacing IMAP App Password)
Library: `google-auth-oauthlib` + `google-api-python-client`

Flow:
1. User enters `client_id` + `client_secret` from their Google Cloud Console project
   (in-app wizard guides through the 5-step Google Cloud setup)
2. User clicks "Connect Gmail" → app spins up `localhost:8080` callback server
3. Browser opens Google OAuth consent screen
4. User clicks Allow → Google redirects to `localhost:8080`
5. App exchanges code for access + refresh tokens
6. Tokens saved to `{app_data_home}/gmail_token.json`
7. Callback server shuts down
8. Settings shows `● Connected: user@gmail.com`
9. Token refreshes automatically — user never prompted again
10. "Disconnect" button revokes via Google's revocation endpoint + deletes token file

### Sender filter — domain-pattern matching (not hardcoded address)
```python
# Current (wrong):  _LINKEDIN_SENDER = "jobs-noreply@linkedin.com"
# New:
_LINKEDIN_SENDER_RE = re.compile(
    r'^[\w\-]*(alert|job|notify)[\w\-]*@linkedin\.com$', re.IGNORECASE
)
```
IMAP search: `FROM "@linkedin.com" UNSEEN`
Python post-filter: apply `_LINKEDIN_SENDER_RE` to the `From` header.
Configurable override field in `user_settings.yml`: `gmail_sender_pattern`.

### Job posting date/time — from LinkedIn JSON-LD (not email Date header)
`_extract_from_json_ld()` in `job_fetcher.py` is extended to also extract:
- `datePosted` → stored as ISO 8601 datetime string in `JobPost.posted_date`
- `employmentType` → stored in `JobPost.employment_type` (new nullable column)
- `baseSalary` → stored in `JobPost.salary_range` (new nullable column)

Date-only values (`2024-01-15`) are normalised to `2024-01-15T00:00:00Z`.
The UI displays: `"15 Jan 2024 · 09:30 UTC"`.

### Three-tier enrichment fallback (no blind guessing)
```
Tier 1  LinkedIn HTTP scrape
        ✓ description + datePosted extracted → proceed to scoring
        ✗ 403 / 429 / empty →

Tier 2  AI-powered company career page search
        • company_resolver.py finds company careers URL
        • career_scanner.py scans for matching job listing
        ✓ found → extract description → proceed to scoring
        ✗ not found →

Tier 3  User manual input
        • JobPost.enrichment_status = "needs_input"
        • Job card shows ⚠ "Description needed" badge
        • All scoring/drafting action buttons locked
        • One-click link: /ui/apply?title=X&company=Y  (pre-filled)
        • User pastes full job text → saves → scoring runs
```

**Hard rule:** No scoring, matching, or CV drafting runs against a job with an
empty description. This is enforced at the service level, not just the UI.

### Privacy guarantee
Only emails matching `_LINKEDIN_SENDER_RE` are read. The IMAP search query is
narrowed by LinkedIn domain. No other email in the inbox is touched.

---

## P3 — Ollama Backend

### Architecture
Ollama exposes an OpenAI-compatible API at `http://localhost:11434/v1/`.
`LLMRouter._call_lm_studio()` is reused with a different base URL.
No new HTTP client code needed.

### New `llm_provider_mode` values
```
"openai"    → OpenAI API (default)
"lm_studio" → LM Studio local server (renamed from "local" — shim handles old value)
"ollama"    → Ollama local server
"anthropic" → Anthropic API
"mixed"     → LM Studio/Ollama first, falls back to OpenAI
```

Migration shim: if stored `llm_provider_mode == "local"`, treat as `"lm_studio"`.

### New config fields
```
ollama_base_url:     http://localhost:11434   (default)
ollama_fast_model:   llama3:8b               (default)
ollama_writer_model: mistral:7b              (default)
```

### Model discovery endpoint
`GET /ollama/models` → pings `{ollama_base_url}/api/tags` → returns list of
installed model names. Shown as dropdown in settings UI with "Refresh" button.
Same pattern as existing `/lm-studio/models`.

### Settings UI
Ollama gets a collapsible section alongside LM Studio:
- Base URL field + connection status badge
- Fast model dropdown (populated from /ollama/models) + free-text fallback
- Writer model dropdown + free-text fallback

---

## P5 — Resilience and Error UX

### Network detection
Background ping runs every 30s (worker tick or HTMX poll on `GET /health/connectivity`).
State stored in module-level bool. UI reacts via HTMX swap on `#network-banner`.

### Per-scenario behaviour
| Scenario | Behaviour |
|----------|-----------|
| Gmail sync fails (offline) | Queued; auto-retried next worker tick |
| Job scoring fails | Silent retry ×2 with 2s backoff → toast on final failure |
| CV draft generation fails | Immediate error banner on draft page + Retry button |
| Model not responding / timeout (60s) | Non-blocking banner: "AI model not responding" + Settings link |
| OpenAI 429 (quota exhausted) | Toast: "OpenAI quota reached — check billing at platform.openai.com" |
| Internet disconnected | Top-of-page banner: "No internet — cloud features paused", auto-dismisses on reconnect |

### UI components (all in base.html)
- `#network-banner` — top sticky bar, hidden by default
- `#ai-status-banner` — shown when no AI provider configured (non-dismissable)
- `#toast-container` — bottom-right stack, toasts auto-dismiss after 6s
- Inline locked state on job cards when `enrichment_status == "needs_input"`
- Inline error + Retry button on draft detail page

### Timeout config
New settings fields:
```
llm_request_timeout_seconds:   60    (model response timeout)
network_check_interval_seconds: 30   (connectivity poll interval)
```

---

## What is NOT in scope
- Multi-user support
- Outlook / other email providers (separate future discussion)
- Anthropic API key guided setup (low priority — OpenAI is the default path)
- Mobile UI

---

## Files touched per sub-project

**P4:**
`job_agent/config.py` · `job_agent/llm.py` · `job_agent/onboard.py` ·
`frontend/templates/onboarding.html` · `frontend/templates/settings.html` ·
`frontend/templates/base.html` · `job_agent/routers/system.py`

**P2:**
`job_agent/services/gmail.py` · `job_agent/services/job_fetcher.py` ·
`job_agent/models.py` · `job_agent/db.py` · `job_agent/config.py` ·
`frontend/templates/settings.html` · `job_agent/routers/system.py`

**P3:**
`job_agent/llm.py` · `job_agent/config.py` · `job_agent/routers/system.py` ·
`frontend/templates/settings.html`

**P5:**
`frontend/templates/base.html` · `job_agent/routers/system.py` ·
`job_agent/worker.py` · `frontend/static/app.js`
