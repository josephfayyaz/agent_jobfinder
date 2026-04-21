# Manual Acceptance Test Checklist
**Date:** [fill in]  **Tester:** [fill in]  **Version:** 292+ tests

## Prerequisites

- [ ] Docker running: `docker ps` shows containers
- [ ] Run: `docker compose up -d db` -> db container healthy
- [ ] Run in terminal 1: `conda activate ML && uvicorn job_agent.main:app --host 0.0.0.0 --port 8000 --reload`
- [ ] Wait for: `Application startup complete.`
- [ ] Run in terminal 2: `conda activate ML && python -m job_agent.worker`
- [ ] Verify server: `curl -s localhost:8000/health` -> `{"status":"ok"}`

---

## Section 1: API Health & Schema
- [ ] `curl -s localhost:8000/health` -> `{"status":"ok"}`
- [ ] `curl -s localhost:8000/providers` -> list of configured LLM providers
- [ ] `curl -s localhost:8000/openapi.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d['paths']), 'endpoints')"` -> 85+ endpoints

## Section 2: Dashboard & Navigation (Browser)
Open: http://localhost:8000/ui
- [ ] Dashboard loads — no 500 error
- [ ] Left sidebar visible with: Jobs, CVs, Thesis, Applications, Analytics, Companies, Settings
- [ ] Click each nav item -> page loads (no 500)
- [ ] Active nav item is highlighted in indigo

## Section 3: Job Discovery

### 3a. Career Page Scanner
- [ ] Go to http://localhost:8000/ui/companies
- [ ] Click "Add" with: Company=TestCo, URL=https://testco.example.com/careers, ATS Type=None
- [ ] New row appears in table
- [ ] Click "Scan All Now" -> page reloads, no error

### 3b. ATS Source (Greenhouse)
- [ ] Add company: Company=OpenAI, ATS Type=greenhouse, ATS Slug=openai
- [ ] Row shows "greenhouse / openai" badge
- [ ] Click "Scan All Now" -> if online, new jobs should appear in /ui/jobs

### 3c. Jobs Table
- [ ] Go to http://localhost:8000/ui/jobs
- [ ] Jobs table loads
- [ ] Filter by Status=new -> table updates (HTMX partial swap)
- [ ] Filter by min_score=50 -> table filters

## Section 4: CV Workflow

### 4a. Queue a CV
- [ ] Go to /ui/jobs
- [ ] Find any job with a score badge
- [ ] Click "Queue CV" button for that job -> button disappears or shows confirmation
- [ ] Go to terminal 2 (worker) -> see log line: `Picked up task ... (kind=cv_workflow)`
- [ ] See log line: `Task ... completed`

### 4b. Review Draft
- [ ] Go to http://localhost:8000/ui/drafts
- [ ] New draft row appears with job title and score
- [ ] Click the job title link -> navigates to /ui/drafts/{id}

### 4c. Draft Detail Page
- [ ] Professional Summary section shows text (or "No summary generated" if heuristic)
- [ ] Experience section shows role + bullets
- [ ] Skills section shows tag chips
- [ ] Right sidebar: "Compliance Matrix" — shows "Generate Compliance Matrix" button
- [ ] Click "Generate Compliance Matrix" -> loading, then matrix appears with coverage %
- [ ] Coverage bar renders (green/yellow/red based on %)
- [ ] Requirements table shows ✓ strong, ~ partial, ✗ missing rows
- [ ] "Approve" and "Reject" buttons visible (if not yet approved)
- [ ] Click "Approve" -> page reloads, status changes to "approved", buttons disappear

### 4e. PDF Download
- [ ] If draft has tex_path: "PDF" button appears -> click -> PDF opens in new tab

## Section 5: Rejection Prediction

- [ ] `curl -s -X POST localhost:8000/jobs/{JOB_ID}/rejection-risk` (replace {JOB_ID})
    -> Response has: `{"risks": [...], "overall_risk": "low|medium|high", "recommendation": "..."}`
- [ ] `curl -s localhost:8000/jobs/{JOB_ID}/rejection-risk`
    -> Same prediction returned (was stored in extracted_metadata)

## Section 6: Application Pipeline

- [ ] Go to http://localhost:8000/ui/applications
- [ ] Kanban board shows columns: Applied, Phone Screen, Interview, Offer, Rejected
- [ ] `curl -s -X POST localhost:8000/applications -H "Content-Type: application/json" -d '{"job_post_id": "{JOB_ID}", "status": "applied"}'`
- [ ] Reload /ui/applications -> new card appears in "Applied" column
- [ ] Click "Advance to Phone Screen" -> card moves to Phone Screen column

## Section 7: Analytics

- [ ] Go to http://localhost:8000/ui/analytics
- [ ] If < 5 applications: "Not enough data yet" message shown — no 500
- [ ] After creating 5+ applications (or via curl): page shows funnel, score bars, skill gaps
- [ ] "Posting Velocity" section always visible at bottom (even if empty)
- [ ] `curl -s localhost:8000/analytics/rejection-patterns` -> JSON with funnel, score_buckets, skill_gaps
- [ ] `curl -s localhost:8000/analytics/posting-velocity?days=7` -> JSON with days=7 and companies list

## Section 8: start_apply CLI

Open a NEW terminal (no server needed):
```bash
conda activate ML
cd /Users/youseffayyaz/Local_LLM
python -m start_apply.cli
```
- [ ] CLI prints a prompt asking for job info
- [ ] Paste a job description (any real job posting text)
- [ ] CLI asks clarifying questions (max 3)
- [ ] CLI writes a CV file to start_apply/output/cv_<timestamp>.txt
- [ ] Open the output file — contains formatted CV content

## Section 9: Edge Cases

- [ ] GET /ui/drafts/{random-uuid} -> 404 page (not 500)
- [ ] POST /career-pages with ats_type=invalid -> 400 with "Invalid ats_type" message
- [ ] GET /jobs/{random-uuid}/rejection-risk -> 404 "No prediction generated"
- [ ] GET /drafts/{random-uuid}/compliance-matrix -> 404 "not yet generated"
- [ ] Go to /ui/analytics with 0 applications -> friendly empty state, not crash
- [ ] Toggle inactive company -> row dims (opacity-50)
- [ ] Toggle back -> row returns to full opacity

## Section 10: Worker Reliability

- [ ] Restart the worker (Ctrl+C in terminal 2, restart command)
- [ ] Worker resumes picking up pending tasks without data loss
- [ ] `curl -s localhost:8000/tasks` -> pending tasks still visible

---

## Sign-off Criteria

All items above checked. No 500 errors encountered. Worker log shows no unhandled
exceptions. start_apply CLI produces a readable output file.

**Status:** [ ] PASS  [ ] FAIL
**Notes:** ___
