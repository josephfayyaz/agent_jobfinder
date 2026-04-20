# Job Agent — Complete User Manual

> **Who this is for:** Anyone who wants to use this system to find jobs, generate tailored CVs, and manage applications — no prior technical knowledge required.
> 
> **What this system does:** It finds job listings, reads your background, and automatically writes a custom CV for each job using local AI models on your Mac. Nothing is sent to the cloud unless you explicitly turn that on.

---

## Table of Contents

1. [What You Need Before Starting](#1-what-you-need-before-starting)
2. [First-Time Setup (Do This Once)](#2-first-time-setup-do-this-once)
3. [Starting the System Every Day](#3-starting-the-system-every-day)
4. [The Dashboard — Your Main Screen](#4-the-dashboard--your-main-screen)
5. [Adding Jobs Manually](#5-adding-jobs-manually)
6. [Automatic Job Discovery (LinkedIn Scraper)](#6-automatic-job-discovery-linkedin-scraper)
7. [Gmail Auto-Import (LinkedIn Email Alerts)](#7-gmail-auto-import-linkedin-email-alerts)
8. [Generating a CV for a Job](#8-generating-a-cv-for-a-job)
9. [Reviewing and Downloading Your CV](#9-reviewing-and-downloading-your-cv)
10. [Keeping Your Profile Up to Date](#10-keeping-your-profile-up-to-date)
11. [Thesis / Traineeship Outreach](#11-thesis--traineeship-outreach)
12. [Connecting Claude AI for Final CV Polish](#12-connecting-claude-ai-for-final-cv-polish)
13. [Connecting Codex for Code Tasks](#13-connecting-codex-for-code-tasks)
14. [Troubleshooting Common Problems](#14-troubleshooting-common-problems)
15. [Quick Reference: All Web Pages](#15-quick-reference-all-web-pages)
16. [Quick Reference: The .env Settings File](#16-quick-reference-the-env-settings-file)

---

## 1. What You Need Before Starting

You need these four programs installed on your Mac. Check the list — most are already on your machine.

| Program | What It Does | Already Installed? |
|---------|-------------|-------------------|
| **Docker Desktop** | Runs the database that stores all your jobs and CVs | Check: open Docker Desktop app — if it opens, yes |
| **LM Studio** | Runs the AI models locally on your Mac | Check: open LM Studio app — if it opens, yes |
| **Miniforge (conda)** | Runs the Python code | Yes — at `/Users/youseffayyaz/miniforge3` |
| **LaTeX (pdflatex)** | Converts your CV into a PDF file | Yes — confirmed working |

If Docker Desktop or LM Studio is missing, download them:
- Docker Desktop: https://www.docker.com/products/docker-desktop/
- LM Studio: https://lmstudio.ai

---

## 2. First-Time Setup (Do This Once)

> **Skip this section if you have already run the system before.** Go straight to section 3.

### Step 2.1 — Check your .env file

The `.env` file tells the system your settings (passwords, model names, etc.). It lives at:

```
/Users/youseffayyaz/Local_LLM/.env
```

Open it in any text editor (TextEdit, VS Code, etc.). The file should already exist from when the system was built. You do not need to change anything to get started — defaults are fine.

### Step 2.2 — Load models in LM Studio

1. Open **LM Studio** on your Mac
2. Click the **Models** tab on the left sidebar
3. Make sure these four models are downloaded and loaded:
   - `qwen3.5-9b-mlx` — the fast model (reviewer, router)
   - `qwen3.5-27b-claude-4.6-opus-distilled-mlx` — the writer model (generates CVs)
   - `openai/gpt-oss-20b` — the mid model
   - `text-embedding-nomic-embed-text-v1.5` — the embedding model
4. For each model: click on it → click **Load Model**
5. In LM Studio's **Local Server** tab: make sure the server is **Running** on port **1234**

> **Tip:** LM Studio must always be open and running when you use the job agent. Think of it as the "brain" of the system.

### Step 2.3 — Create the database for the first time

Open your Terminal app and run these commands one at a time:

```bash
# Navigate to the project folder
cd /Users/youseffayyaz/Local_LLM

# Start the database
docker compose up -d db
```

You should see: `Container local-llm-db Started`

The database is now running. It will remember all your jobs and CVs even after you restart your Mac (as long as Docker Desktop is running).

---

## 3. Starting the System Every Day

Every time you want to use the system, follow these steps **in order**. Think of it like turning on a car — you need to start the engine before driving.

### Step 1 — Open Docker Desktop
- Find Docker Desktop in your Applications folder and open it
- Wait until the whale icon in your menu bar is steady (not animated)
- This takes about 30 seconds

### Step 2 — Start the database

Open Terminal and run:

```bash
cd /Users/youseffayyaz/Local_LLM
docker compose up -d db
```

You only need to do this once per Mac restart. If Docker Desktop was already running and you didn't restart your Mac, the database is already up.

### Step 3 — Open LM Studio and confirm models are loaded
- Open **LM Studio**
- Go to the **Local Server** tab
- Confirm the server shows **Running** on port 1234
- If models are not loaded: go to the Models tab and load them (see Section 2.2)

### Step 4 — Open two Terminal windows

**Terminal window 1 — The API (the main brain):**

```bash
cd /Users/youseffayyaz/Local_LLM
conda activate ML
uvicorn job_agent.main:app --host 0.0.0.0 --port 8000 --reload
```

Wait until you see: `Application startup complete.`

**Terminal window 2 — The Worker (the background helper):**

```bash
cd /Users/youseffayyaz/Local_LLM
conda activate ML
python -m job_agent.worker
```

Wait until you see: `Worker started.` or a similar startup message.

### Step 5 — Open the dashboard in your browser

Open your web browser (Safari, Chrome, etc.) and go to:

```
http://localhost:8000/dashboard
```

If you see the Job Agent dashboard, everything is working!

> **Quick health check:** Go to `http://localhost:8000/health` — you should see `{"status":"ok"}`. If you do, the system is running perfectly.

---

## 4. The Dashboard — Your Main Screen

Once the system is running, open your browser and go to:

```
http://localhost:8000/dashboard
```

Here you can see:
- How many jobs are saved
- How many CVs have been generated
- Recent activity
- Quick links to all other pages

**Other pages you can visit:**

| Page | Address | What It Does |
|------|---------|-------------|
| Dashboard | `http://localhost:8000/dashboard` | Overview of everything |
| Jobs list | See section below | All jobs you've collected |
| Drafts | `http://localhost:8000/drafts` | All generated CVs |
| Applications | `http://localhost:8000/applications` | Jobs you've applied to |
| Thesis targets | See section 11 | Professor/company outreach |
| Onboarding | `http://localhost:8000/ui/onboarding` | Set up a new candidate profile |

---

## 5. Adding Jobs Manually

The easiest way to add a job is to paste it directly into the system.

### From LinkedIn

1. Open LinkedIn and find a job you like
2. Copy the full job description text
3. Open Terminal and run this command, replacing the values with the real job details:

```bash
curl -sX POST http://localhost:8000/jobs \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Data Engineer",
    "company": "Company Name",
    "source_url": "https://www.linkedin.com/jobs/view/XXXXXXXXX",
    "canonical_apply_url": "https://www.linkedin.com/jobs/view/XXXXXXXXX",
    "description": "Paste the full job description here",
    "city": "Milan",
    "country": "Italy",
    "remote_policy": "hybrid",
    "source_name": "linkedin"
  }'
```

The system will automatically:
- Score the job against your 4 resume tracks
- Find the best matching CV template for you
- Store it for CV generation

> **Tip:** You can also use the ready-made example file. Run:
> ```bash
> curl -sX POST http://localhost:8000/jobs -H 'Content-Type: application/json' -d @examples/job.example.json
> ```

---

## 6. Automatic Job Discovery (LinkedIn Scraper)

The system can automatically search LinkedIn for jobs without you having to copy-paste anything. This uses a tool called **JobSpy**.

### How to turn it on

1. Open the file `/Users/youseffayyaz/Local_LLM/.env` in any text editor
2. Find this line:
   ```
   # USE_JOBSPY=false
   ```
3. Change it to (remove the `#` and change to `true`):
   ```
   USE_JOBSPY=true
   ```
4. Save the file
5. Restart the API (close Terminal window 1 and run the start command again)

### How to run a job search

In Terminal, run:

```bash
curl -sX POST 'http://localhost:8000/jobs/discover' \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "Data Engineer",
    "location": "Italy",
    "limit": 20
  }'
```

Change `"Data Engineer"` to whatever job title you want to search for.
Change `"Italy"` to any country or city.
Change `20` to how many results you want (maximum 50 recommended).

The system will automatically find jobs, score them, and save them for you.

**Other useful searches:**

```bash
# Search for AI/ML Engineer jobs in Europe
curl -sX POST 'http://localhost:8000/jobs/discover' \
  -H 'Content-Type: application/json' \
  -d '{"query": "Machine Learning Engineer", "location": "Europe", "limit": 30}'

# Search for Data Analyst internships in Italy
curl -sX POST 'http://localhost:8000/jobs/discover' \
  -H 'Content-Type: application/json' \
  -d '{"query": "Data Analyst internship", "location": "Italy", "limit": 25}'
```

> **Note:** JobSpy scrapes LinkedIn's public search results — no LinkedIn login is required. However, searching too fast may get temporarily blocked. The system automatically adds a delay between requests.

---

## 7. Gmail Auto-Import (LinkedIn Email Alerts)

If you have LinkedIn job alerts set up, they come to your Gmail as emails. This system can automatically read those emails and add the jobs to your database.

### Step 7.1 — Set up LinkedIn Job Alerts (on LinkedIn)

1. Go to LinkedIn → Jobs → Job Alerts
2. Create alerts for your desired job titles and locations
3. Set delivery to **Immediately** or **Daily Digest**
4. LinkedIn will start emailing you matching jobs at `jobs-noreply@linkedin.com`

### Step 7.2 — Create a Gmail App Password

Gmail requires a special password for apps (not your regular Gmail password). This is a security feature.

1. Go to your Google Account: https://myaccount.google.com
2. Click **Security** in the left menu
3. Under "How you sign in to Google", find **2-Step Verification** — it must be **ON**
   - If it's off, turn it on first (follow Google's steps)
4. After turning on 2-Step Verification, go back to Security
5. Scroll down and click **App passwords** (it appears after 2-Step is enabled)
6. Click **Select app** → choose **Mail**
7. Click **Select device** → choose **Other (Custom name)** → type `Job Agent`
8. Click **Generate**
9. Google shows you a 16-character password like: `abcd efgh ijkl mnop`
10. **Copy this password** — you will only see it once

### Step 7.3 — Add credentials to .env

Open `/Users/youseffayyaz/Local_LLM/.env` and add these lines:

```
GMAIL_EMAIL=your.email@gmail.com
GMAIL_APP_PASSWORD=abcdefghijklmnop
GMAIL_AUTO_SYNC=true
GMAIL_SYNC_INTERVAL_MINUTES=30
GMAIL_MAX_EMAILS_PER_SYNC=20
```

Replace `your.email@gmail.com` with your actual Gmail address.
Replace `abcdefghijklmnop` with the 16-character App Password you generated (no spaces).

### Step 7.4 — Restart the system

Close Terminal windows 1 and 2 (the API and Worker), then start them again using the commands in Section 3.

The worker will now automatically check your Gmail every 30 minutes and add any new LinkedIn job alert emails to your database.

> **How it works:** The system reads emails from `jobs-noreply@linkedin.com`, extracts job title, company, location, and LinkedIn URL, then fetches the full job description and stores it. Emails are marked as read after processing.

---

## 8. Generating a CV for a Job

Once you have jobs in your database, you can generate a tailored CV for any of them.

### Step 8.1 — Find the job's ID

```bash
# List your jobs (shows the most recent 10)
curl -s 'http://localhost:8000/jobs?limit=10' | python3 -c "
import sys, json
jobs = json.load(sys.stdin)
for j in jobs:
    print(j['id'], '|', j['title'], '@', j['company'])
"
```

Copy the long ID (looks like: `b71a0788-d6bd-432c-a94d-75de9b0f8fd9`) of the job you want.

### Step 8.2 — Choose a CV track

Pick the track that best matches the job:

| Track Slug | Best For |
|------------|---------|
| `data-engineering-analytics` | Data Engineer, Analytics Engineer, ETL/ELT roles |
| `data-analyst-bi-product` | Data Analyst, BI Analyst, Product Analytics |
| `ai-ml-engineering` | AI Engineer, ML Engineer, Data Scientist |
| `cloud-mlops-ai-platform` | Cloud Engineer, MLOps, Platform Engineering |

### Step 8.3 — Start the CV workflow

```bash
curl -sX POST http://localhost:8000/tasks/cv-workflow \
  -H 'Content-Type: application/json' \
  -d '{
    "job_post_id": "PASTE-JOB-ID-HERE",
    "resume_track_slug": "data-engineering-analytics",
    "force_cloud_review": false
  }'
```

Replace `PASTE-JOB-ID-HERE` with the job ID from Step 8.1.
Replace `data-engineering-analytics` with whichever track fits best.

The command will return a **task ID** (another long ID). Copy it.

### Step 8.4 — Wait for the CV to be generated

CV generation takes 2–5 minutes (the AI is writing your CV). Check the status:

```bash
curl -s http://localhost:8000/tasks/PASTE-TASK-ID-HERE
```

When `"status"` changes from `"pending"` or `"running"` to `"done"`, your CV is ready.

### Step 8.5 — Download the PDF

Go to:

```
http://localhost:8000/drafts
```

Find your draft and click the **PDF** button to download it.

Or from Terminal:

```bash
# List drafts (shows the most recent)
curl -s 'http://localhost:8000/drafts?limit=5' | python3 -c "
import sys, json
drafts = json.load(sys.stdin)
for d in drafts:
    print(d['id'], '|', d.get('status'), '|', d.get('score'))
"

# Download the PDF (replace DRAFT-ID with the actual ID)
curl -s http://localhost:8000/drafts/DRAFT-ID/pdf --output my_cv.pdf
open my_cv.pdf
```

---

## 9. Reviewing and Downloading Your CV

After the CV is generated, the system gives it a **score from 0 to 100**:

| Score | Meaning | What Happens |
|-------|---------|-------------|
| 85–100 | Excellent match | CV is accepted as-is |
| 60–84 | Good but needs tweaks | System automatically revises it |
| Below 60 | Weak match | System escalates (uses a better model or Claude if enabled) |

### Seeing what the AI reviewer said

```bash
curl -s http://localhost:8000/drafts/DRAFT-ID | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('Score:', d.get('reviewer_score'))
print('Feedback:', json.dumps(d.get('review_feedback'), indent=2))
"
```

### Approving a draft

When you are happy with a CV draft:

```bash
curl -sX POST http://localhost:8000/drafts/DRAFT-ID/approve
```

This marks the CV as approved and ready to send.

---

## 10. Keeping Your Profile Up to Date

Your background facts are stored in a plain text file called the **master fact sheet**:

```
/Users/youseffayyaz/Polito/Resume-CV/fact_sheet/master_fact_sheet.txt
```

Whenever you update this file (new job, new project, new skill), you need to re-import it:

```bash
FACT_PATH="/Users/youseffayyaz/Polito/Resume-CV/fact_sheet/master_fact_sheet.txt"
jq -Rs --arg p "$FACT_PATH" '{source_path:$p,content:.}' "$FACT_PATH" \
  | curl -sX POST http://localhost:8000/fact-sources/ingest \
    -H 'Content-Type: application/json' -d @-
```

> **Rule of thumb:**
> - If you added/changed bullets, dates, or numbers → just re-run the command above
> - If you added a completely new type of section (e.g., "Publications") → ask Claude Code first, the parser may need an update

---

## 11. Thesis / Traineeship Outreach

This part of the system helps you reach out to professors and companies for thesis/traineeship positions in Europe.

### Adding a thesis target

```bash
curl -sX POST http://localhost:8000/thesis-targets \
  -H 'Content-Type: application/json' \
  -d '{
    "institution": "Politecnico di Milano",
    "contact_name": "Prof. Mario Rossi",
    "contact_email": "mario.rossi@polimi.it",
    "research_area": "Machine Learning for NLP",
    "country": "Italy",
    "notes": "Works on transformer models, published in ACL 2024"
  }'
```

### Generating an outreach email

```bash
curl -sX POST http://localhost:8000/thesis-targets/TARGET-ID/generate-email
```

This uses the local AI to write a personalised outreach email for that professor or company contact.

### Approving and marking as sent

```bash
# Approve the draft email
curl -sX POST http://localhost:8000/outreach-drafts/DRAFT-ID/approve

# Mark as sent (after you have actually sent it)
curl -sX POST http://localhost:8000/outreach-drafts/DRAFT-ID/mark-sent
```

---

## 12. Connecting Claude AI for Final CV Polish

By default, all CV generation happens locally using LM Studio models. You can optionally add **Claude** (Anthropic's AI) as a final polishing step for the highest-quality output.

This costs a small amount of money per CV (typically less than $0.05) but produces noticeably better results.

### Step 12.1 — Get an Anthropic API key

1. Go to: https://console.anthropic.com
2. Sign up or log in
3. Click **API Keys** in the left menu
4. Click **Create Key**
5. Give it a name (e.g., `Job Agent`)
6. Copy the key — it starts with `sk-ant-...`

### Step 12.2 — Add the key to your .env file

Open `/Users/youseffayyaz/Local_LLM/.env` and update these lines:

```
ANTHROPIC_API_KEY=sk-ant-YOUR-KEY-HERE
USE_CLAUDE_FINAL_REVIEW=true
```

### Step 12.3 — Restart the API

Close Terminal window 1 and run the start command again (Section 3, Step 4).

### Step 12.4 — Use Claude for a specific CV

When you start the CV workflow, set `force_cloud_review` to `true`:

```bash
curl -sX POST http://localhost:8000/tasks/cv-workflow \
  -H 'Content-Type: application/json' \
  -d '{
    "job_post_id": "PASTE-JOB-ID-HERE",
    "resume_track_slug": "data-engineering-analytics",
    "force_cloud_review": true
  }'
```

> **How it works:** The local model (qwen3.5-27b) writes the first draft. Claude then reviews it, catches errors, improves phrasing, and ensures it reads naturally to a human recruiter. The final PDF is the Claude-polished version.

---

## 13. Connecting Codex for Code Tasks

Codex (GitHub Copilot agent / OpenAI Codex) is used to implement new features and fix bugs in this codebase. You do not need Codex to use the job agent — it is only for developers who want to extend the system.

### How the relay workflow works

1. **Claude Code** (this assistant) reads the codebase, writes a specification file (`.md`), and prepares a ready-to-paste prompt
2. **You** copy the prompt from `AGENT_SPECS/codex_prompts/` and paste it into Codex
3. **Codex** implements the feature and writes a completion report to `AGENT_SPECS/completed/`
4. **You** paste the report back to Claude Code, which reviews it and approves or flags issues

### Prompt files are in:

```
/Users/youseffayyaz/Local_LLM/AGENT_SPECS/codex_prompts/
```

Each file is a self-contained prompt you can copy and paste directly into Codex.

### Completion reports land in:

```
/Users/youseffayyaz/Local_LLM/AGENT_SPECS/completed/
```

### Connecting OpenAI API (for Codex cloud features)

If you want to use OpenAI's models for CV review (not needed for basic use):

1. Get an OpenAI API key: https://platform.openai.com/api-keys
2. Add to `.env`:
   ```
   OPENAI_API_KEY=sk-YOUR-OPENAI-KEY-HERE
   USE_OPENAI_REVIEW=true
   ```
3. Restart the API

---

## 14. Troubleshooting Common Problems

### "Connection refused" when opening the dashboard

**Cause:** The API is not running.
**Fix:** Open Terminal and run the API start command from Section 3, Step 4.

### "Cannot connect to the Docker daemon"

**Cause:** Docker Desktop is not open.
**Fix:** Open Docker Desktop from your Applications folder and wait for it to fully start (the whale icon stops animating).

### CV generation is stuck at "pending" for more than 10 minutes

**Cause:** LM Studio model is not loaded or not responding.
**Fix:**
1. Open LM Studio
2. Go to the **Local Server** tab — confirm it says **Running** on port 1234
3. Go to the **Models** tab — confirm `qwen3.5-27b-claude-4.6-opus-distilled-mlx` is loaded
4. Try a test call: `curl -s http://localhost:8000/providers` — check `"reachable": true`

### "LM Studio request failed: timed out"

**Cause:** The model is loaded but not responding quickly enough (cold start).
**Fix:** Wait 2–3 minutes and try again. The first request after loading a model is always slower.

### Gmail sync is not finding emails

**Fix checklist:**
1. Confirm `GMAIL_EMAIL` and `GMAIL_APP_PASSWORD` are set in `.env`
2. Confirm the App Password is the 16-character code (no spaces)
3. Confirm you have LinkedIn job alerts set up and LinkedIn is sending emails to that Gmail address
4. Confirm 2-Step Verification is enabled on your Google account
5. Run manually: `curl -sX POST http://localhost:8000/jobs/sync-gmail`

### JobSpy / LinkedIn search returns 0 results

**Fix checklist:**
1. Confirm `USE_JOBSPY=true` in `.env` and you restarted the API
2. Try a broader search: shorter query, "Europe" instead of a specific city
3. Wait 10 minutes and try again — LinkedIn may have temporarily rate-limited the scraper

### The database is empty after restarting

**Cause:** Docker container was removed (not just stopped).
**Note:** As long as you used `docker compose up -d db` (not `docker compose down -v`), your data is safe in a named volume. The data persists across restarts.

### Something else is wrong

Check the live logs in your Terminal windows:
- **API window** (Terminal 1): shows all requests and errors in real time
- **Worker window** (Terminal 2): shows background job processing

---

## 15. Quick Reference: All Web Pages

Open these in your browser while the system is running:

| Page | URL | What It Shows |
|------|-----|--------------|
| Dashboard | `http://localhost:8000/dashboard` | Overview, stats, recent jobs |
| Drafts | `http://localhost:8000/drafts` | All generated CVs, download PDFs |
| Applications | `http://localhost:8000/applications` | Jobs you've applied to |
| Thesis targets | (API only — see Section 11) | Professor/company outreach |
| Onboarding | `http://localhost:8000/ui/onboarding` | Set up a new candidate profile |
| Health check | `http://localhost:8000/health` | Is the system running? |
| Providers | `http://localhost:8000/providers` | Are LM Studio and Claude connected? |

---

## 16. Quick Reference: The .env Settings File

Location: `/Users/youseffayyaz/Local_LLM/.env`

| Setting | Default | What It Controls |
|---------|---------|-----------------|
| `LM_STUDIO_SMALL_MODEL` | `qwen3.5-9b-mlx` | Fast model — must match name in LM Studio |
| `LM_STUDIO_WRITER_MODEL` | `qwen3.5-27b-claude-4.6-opus-distilled-mlx` | CV writing model — must match name in LM Studio |
| `CV_PASS_SCORE` | `85` | Score above this → CV accepted automatically |
| `CV_REVISE_SCORE` | `60` | Score below this → model tries harder / escalates |
| `TARGET_JOB_SENIORITY` | `junior` | Changes how CVs are framed (`intern`, `junior`, `mid`, `senior`) |
| `GMAIL_EMAIL` | _(empty)_ | Your Gmail address for job alert import |
| `GMAIL_APP_PASSWORD` | _(empty)_ | 16-char Google App Password |
| `GMAIL_AUTO_SYNC` | `false` | Set to `true` to sync automatically every 30 min |
| `USE_JOBSPY` | `false` | Set to `true` to enable LinkedIn auto-search |
| `ANTHROPIC_API_KEY` | _(empty)_ | Your Claude API key (starts with `sk-ant-`) |
| `USE_CLAUDE_FINAL_REVIEW` | `false` | Set to `true` to use Claude for final CV polish |
| `MATCH_MIN_SCORE` | `75` | Jobs below this track score are filtered out |
| `WORKER_POLL_SECONDS` | `5` | How often the worker checks for new tasks |

> **After changing any .env setting:** Close Terminal window 1 (the API) and start it again. The worker (Terminal window 2) also needs restarting.

---

## Summary: The 5-Minute Daily Routine

1. **Open Docker Desktop** — wait for the whale icon to stop moving
2. **Open LM Studio** — confirm server is running on port 1234
3. **Run in Terminal 1:**
   ```bash
   cd /Users/youseffayyaz/Local_LLM && conda activate ML && uvicorn job_agent.main:app --host 0.0.0.0 --port 8000 --reload
   ```
4. **Run in Terminal 2:**
   ```bash
   cd /Users/youseffayyaz/Local_LLM && conda activate ML && python -m job_agent.worker
   ```
5. **Open browser:** `http://localhost:8000/dashboard`
6. Find a job → add it → generate CV → download PDF

That's it.
