# Career-Ops Integration Opportunities

**Source repo:** `/Users/youseffayyaz/Downloads/career-ops-main`  
**Analysed:** 2026-04-16  
**Purpose:** Identify features from career-ops worth integrating into the Local LLM job agent.

---

## What career-ops is

A multi-agent Claude Code-based job search system with:
- 14 operational skill modes (evaluate, apply, interview prep, outreach, etc.)
- Zero-token portal scanner (Node.js hitting ATS APIs directly)
- ATS-optimised PDF generation (Playwright + HTML templates)
- Rejection pattern analytics
- Follow-up cadence automation
- Dashboard TUI (Go + Bubble Tea)
- Multi-language support (EN / DE / FR / JA) with region-specific legal/comp rules

---

## What our system already covers

| Feature | Our system | Career-ops equivalent |
|---|---|---|
| CV writer | Role-adaptive (junior/mid/senior) | PDF mode with keyword injection |
| Job reviewer | Score + gaps + comp check + legitimacy | Block A-G evaluation |
| Job discovery | JobSpy scheduled + manual | scan.mjs (45 curated companies) |
| Company URL resolver | find_company_url() | portals.yml |
| Career page scanner | scan_all_parallel() | Level 1 Playwright scan |
| Application tracker | applications.html | applications.md + merge-tracker.mjs |
| Fact sheet ingestion | JSON schema + FactSheetIntakeService | cv.md + profile.yml |
| Gmail sync | GmailService | — (career-ops has no email) |

---

## High-Priority Gaps to Fill

### 1. Human-in-the-loop bullet rewriter
**What career-ops does:** The PDF mode has explicit rules — extract company language from JD, map to user's existing bullets, NEVER invent skills, reformulate only what the user can prove.  
**What we're missing:** Our `_apply_review_decision()` rewrites bullets automatically without asking the user to confirm they actually have the skill.  
**Recommendation:** Add a two-prompt clarify → rewrite flow (see `AGENT_SPECS/phase_F1_bullet_clarify_rewrite.md` when written). High priority — directly improves honesty and quality.

### 2. ATS keyword extraction from JD
**What career-ops does:** Before writing the PDF, it extracts 15-20 keywords ranked by frequency and importance from the JD, then maps them to existing bullets.  
**What we're missing:** Our writer gets the full JD but has no explicit keyword-extraction step. Ranking is implicit.  
**Recommendation:** Add a preprocessing step in `_generate_draft()` that extracts ranked keywords first, then feeds them to the writer prompt. ~30 lines.

### 3. Rejection pattern analytics
**File:** `analyze-patterns.mjs` (~600 lines, standalone Node.js)  
**What it does:** After ≥5 applications, analyses outcomes by archetype, score band, tech stack gaps, remote policy, company size. Outputs data-driven score threshold and archetype recommendations.  
**What we're missing:** We have tracker data but no analytics layer.  
**Recommendation:** Port as a FastAPI analytics endpoint. Call the Node.js script as a subprocess or port the logic to Python. Expose at `GET /analytics/rejection-patterns`.

### 4. Follow-up cadence automation
**File:** `followup-cadence.mjs` (~350 lines, standalone Node.js)  
**What it does:** Reads applications, calculates aging per application, flags which need follow-up, drafts context-aware follow-up emails with value-first framing (NEVER "just checking in").  
**Cadence rules:** Applied (7d) → first follow-up; Replied (3d) → next follow-up; Interview (1d before) → prep reminder.  
**What we're missing:** Tracker exists but no follow-up engine.  
**Recommendation:** Add as a worker task. Port cadence logic to Python (~80 lines), draft generation to an LLM call. Expose at `GET /applications/followups-due`.

### 5. Zero-token ATS portal scanning
**File:** `scan.mjs` (~400 lines, standalone Node.js)  
**What it does:** Hits Greenhouse, Ashby, Lever, BambooHR, Workday, Teamtailor APIs directly (no LLM tokens spent). 45 pre-configured company career pages. Deduplicates against scan history. Verifies liveness of postings.  
**What we're missing:** Our scanner uses Playwright + LLM parsing (token cost). Career-ops zero-token scan is cheaper and more targeted for known companies.  
**Recommendation:** Run scan.mjs as a subprocess alongside JobSpy. Use it for the 45 curated companies, keep JobSpy for broad discovery.

### 6. Interview preparation
**What it does:** Structured Glassdoor/Blind/engineering blog research. Produces: process overview, round breakdown, likely questions, story bank mapping. Story bank accumulates across interviews (5-10 reusable STAR+R stories).  
**What we're missing:** We evaluate roles but don't prepare for interviews.  
**Recommendation:** Add as optional `POST /jobs/{id}/interview-prep` endpoint. Use public sources (engineering blogs, company pages) first. Mark Glassdoor-derived questions as `[inferred]`.

### 7. Application form assistant
**What it does:** Given an active application form, generates answers to "why this role / why this company / relevant experience" questions using the prior evaluation report. Tone framework: "I'm choosing you" (confident, proof-driven, specific, no clichés).  
**What we're missing:** We track applications but don't assist with form filling.  
**Recommendation:** Add as `POST /applications/{id}/form-answers`. Low implementation cost (~200 lines + prompt).

### 8. LinkedIn outreach drafts
**What it does:** Identifies recruiter / hiring manager / peer / interviewer via WebSearch. Generates 3-sentence 300-char LinkedIn connection messages adapted per contact type.  
**What we're missing:** No outreach automation.  
**Recommendation:** Add as `POST /applications/{id}/outreach` with contact type parameter. Pure prompt engineering, no infrastructure.

---

## Lower-Priority / Nice-to-Have

| Feature | Notes |
|---|---|
| Deep company research (6-axis) | Pure prompt template. Add as optional report endpoint. |
| Training/cert evaluator | Scores courses against career goals. Easy to add. |
| Project evaluator | Scores side projects for interview signal. Easy to add. |
| Dashboard TUI (Go) | Self-contained, hard to integrate into FastAPI. Skip unless you want a terminal UI. |
| Multi-language modes (DE/FR/JA) | Useful if you apply to DACH or French companies. Medium effort. |
| Batch parallel processing | Celery/worker adaptation. Worth adding after other items are stable. |

---

## Design Patterns Worth Adopting

### Zero-token separation
Career-ops deliberately avoids LLM calls for anything a script can do (scan, parse, dedup, cadence maths). Do not use the LLM where a deterministic function is sufficient.

### Ethical bullet rewriting
From the PDF mode: extract existing facts → map to JD language → NEVER invent skills → reformulate only what the user can prove. This maps directly to our planned human-in-the-loop rewriter.

### Legitimacy weighting
Block G weights signals by reliability (posting age = high, role-company fit = low). Thresholds adjust for context (government jobs, niche roles, pre-revenue startups). Our B4 reviewer has a simpler version — this is the upgrade path.

### Tracker integrity pattern
TSV staging files → merge script → dedup → canonical status enforcement. Prevents silent corruption in long-running tracker data. Worth adopting for our applications table.

### Data contract separation
User-owned layer (cv.md, profile.yml) is never auto-updated. System layer (modes, scripts) is safe to modify. This separation makes AI-driven self-modification safe. Our equivalent: `master_fact_sheet.txt` should be treated as user-owned, never overwritten by an agent.

---

---

## New Features — 2025 Best Practices Research

Features NOT in career-ops or our system, identified from market research:

### G1. Semantic ATS Compliance Matrix
Beyond keyword density: for each JD requirement, generate a structured table showing which bullet proves it and how strongly. Shows the reviewer (and the user) exactly where the coverage is thin — not just a score but a requirement-by-requirement map. Feeds into F1.

### G2. Pre-Application Salary Intelligence
Before applying, query aggregated comp data for the role + location (Glassdoor API, Levels.fyi, job posting scrape). Flag roles that are >20% below market for the user's target band. Avoids wasted applications and informs negotiation framing when the user does apply.

### G3. Dynamic Skill Gap → Learning Path
When rejection pattern analytics (F3) identifies a recurring gap (e.g. "missing Kubernetes"), generate a micro-path: 1-2 courses/projects to close it in 30 days, then auto-suggest re-applying to the same company. Closes the feedback loop between analytics and action.

### G4. Unified Outreach Persona Sync
If the user customises their CV for a role, auto-sync the same narrative to: cover letter, recruiter LinkedIn message, application email subject line. All four use the same value proposition, vocabulary, and proof points. Prevents incoherence between channels.

### G5. Posting Velocity Alerting
Track how many new roles appear per week at target companies (not just one-time scans). Sudden hiring spree = urgency (apply within 48h, competition not yet saturated). Auto-alert when a target company spikes. Helps prioritise the queue by timing, not just score.

### G6. Pre-Application Rejection Prediction
Before submitting, run a quick check: given the JD + profile, predict the most likely rejection reasons (visa, over/underqualified, missing cert, geo-restricted). Surfaces blockers early so the user can decide to customise harder, address the gap, or skip.

### G7. Multi-Persona Resume Strategy
Maintain 2-3 strategic persona variants (e.g. "platform engineer" vs "ML engineer") that are both truthful but emphasise different projects. System recommends which persona to activate per role based on JD analysis. Reduces per-application tailoring time while keeping everything authentic.

---

## Suggested Integration Roadmap

| Phase | What | Effort | Value |
|---|---|---|---|
| F1 | Human-in-the-loop bullet clarify + rewrite | Medium | Very high — SPEC WRITTEN |
| F2 | ATS keyword extraction preprocessing | Low (~30 lines in workflows.py) | High |
| F3 | Rejection pattern analytics endpoint | Medium | High |
| F4 | Follow-up cadence automation | Medium | High |
| F5 | Zero-token ATS scanner (scan.mjs subprocess) | Low | Medium |
| F7 | Form assistant + outreach drafts | Low | Medium |
| G1 | Semantic ATS compliance matrix | Medium | High |
| G2 | Pre-application salary intelligence | Medium | High |
| G5 | Posting velocity alerting | Low | Medium |
| G6 | Pre-application rejection prediction | Low | Medium |
| G3 | Dynamic skill gap → learning path | High | Medium |
| G4 | Unified outreach persona sync | Medium | Medium |
| G7 | Multi-persona resume strategy | High | Medium |
