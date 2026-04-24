# Manual Acceptance Test Checklist
**Date:** [fill in]  **Tester:** [fill in]

## Prerequisites

- [ ] `.env` is configured
- [ ] Run in terminal 1: `uvicorn job_agent.main:app --host 127.0.0.1 --port 8000 --reload`
- [ ] Run in terminal 2: `python -m job_agent.worker`
- [ ] Verify server: `curl -s 127.0.0.1:8000/health`

---

## Section 1: First-run setup

- [ ] Open `http://127.0.0.1:8000/ui`
- [ ] If setup is incomplete, app redirects to `/ui/setup-required`
- [ ] Continue to onboarding and finish:
  - [ ] profile
  - [ ] AI provider
  - [ ] fact intake
  - [ ] follow-up questions
  - [ ] search focus
- [ ] Dashboard unlocks after setup

## Section 2: Dashboard and navigation

- [ ] Dashboard loads with no 500 error
- [ ] Sidebar links all load correctly
- [ ] Settings and Help pages load
- [ ] Profile Memory badge appears if saved facts exist

## Section 3: Job discovery

- [ ] `/ui/companies` loads
- [ ] Add a company watch source
- [ ] Toggle active/inactive
- [ ] Run `Scan All Now`
- [ ] `/ui/jobs` loads and filtering works
- [ ] Empty-state actions are helpful when filters hide all jobs
- [ ] `posted_after` date filter works

## Section 4: Apply flow

- [ ] Open `/ui/apply`
- [ ] Paste a job description
- [ ] Match score appears
- [ ] Clarifying questions appear when gaps exist
- [ ] Generation step polls until draft is ready
- [ ] Draft opens at `/ui/drafts/{id}`

## Section 5: Draft review

- [ ] Draft detail renders summary, experience, skills
- [ ] Approve and Reject actions work with HTMX replacement
- [ ] Bullet rewrite flow works
- [ ] Profile-memory save works
- [ ] Role-readiness gap panel loads
- [ ] Cover letter generation works if configured

## Section 6: Analytics

- [ ] `/ui/analytics` loads with no errors
- [ ] Rejection analytics empty state is friendly when little data exists
- [ ] Skill gap card loads
- [ ] Posting velocity area loads

## Section 7: Privacy and workspace controls

- [ ] Settings -> Share card copies the repo/profile link
- [ ] Download My Data produces a backup zip
- [ ] Start Fresh requires typed confirmation
- [ ] Delete My Data requires typed confirmation
- [ ] Reset success page offers `Open Backup Folder`

## Section 8: Reliability

- [ ] Restart the worker and confirm pending tasks resume
- [ ] Restart the API and confirm existing data still loads
- [ ] No machine-specific filesystem paths appear in error messages or defaults

---

## Sign-off

**Status:** [ ] PASS  [ ] FAIL
**Notes:** ___
