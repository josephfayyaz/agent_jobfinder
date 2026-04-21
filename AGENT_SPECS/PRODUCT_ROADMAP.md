# Job Agent — Product Roadmap
**Last updated:** 2026-04-20  
**Status:** UX1–UX5 specs written, ready for Codex

---

## Where We Are

| Dimension | Current State |
|-----------|--------------|
| Tests | 292 passing |
| Endpoints | 88+ |
| Web UI | 11 templates, full pipeline UI |
| Entry point | Manual: 3 terminals + know conda/uvicorn/worker |
| Config | `.env` only, hand-edited |
| Onboarding | None — expert knowledge required |
| LLM switching | Edit `.env`, restart server |
| Public-ready | No — hardcoded defaults, no guided setup |

---

## Gaps vs Public-Ready System

### Gap 1: No Single Entry Point
User must open 3 terminals, know the exact conda/uvicorn/worker commands, and start them in the right order. A new user has no path to a working system.

**Fix:** UX3 — `python -m job_agent.cli start` boots everything.

### Gap 2: Config Requires `.env` Knowledge
Switching from LM Studio to Claude requires editing `.env` and knowing the right variable names. Not friendly for non-developers.

**Fix:** UX1 — YAML user config layer. UX5 — web settings editor. UX4 — `job-agent settings set`.

### Gap 3: No Onboarding
No first-run detection. No guided setup. New users are dropped into a blank system with no profile, no companies, and no idea what to do.

**Fix:** UX2 — 6-step onboarding wizard.

### Gap 4: CLI Gap for Company Management
Companies can only be added via the web UI or raw HTTP. No terminal workflow.

**Fix:** UX4 — `job-agent companies add/list/toggle`.

### Gap 5: No Public Distribution Path
No `setup.cfg`/`pyproject.toml` entry point. `job-agent` command doesn't exist. No `run.sh`. No public install instructions.

**Fix:** UX4 registers the `job-agent` entrypoint. UX3 creates `run.sh`.

---

## UX Phase Roadmap

Execute in dependency order:

| Phase | Spec | What | Prerequisite | Status |
|-------|------|------|-------------|--------|
| UX1 | `prompt_UX1_settings_persistence.txt` | YAML config layer, `/settings/save`, `/settings/reload` | — | Spec ready |
| UX2 | `prompt_UX2_onboarding_wizard.txt` | 6-step guided setup CLI, prerequisite checks, model detection | UX1 | Spec ready |
| UX3 | `prompt_UX3_unified_entry.txt` | `python -m job_agent.cli start`, `run.sh`, preflight + browser open | UX1 | Spec ready |
| UX4 | `prompt_UX4_cli_commands.txt` | `job-agent` CLI: apply, companies, settings commands | UX1, UX3 | Spec ready |
| UX5 | `prompt_UX5_settings_web_ui.txt` | Settings page: provider switcher, model dropdowns, thresholds | UX1 | Spec ready |

---

## Best Practices Adopted (from career-ops + industry)

### From career-ops
| Idea | How We Apply It |
|------|----------------|
| Data contract: user layer vs system layer | `config/user_settings.yml` = user layer (never auto-overwritten by updates). `.env` = infra layer. App code = system layer. |
| Guided onboarding before any operation | UX2: check prerequisites → select models → configure → ingest profile |
| Required-file checks before running | UX2 Step 1 verifies Docker, DB, LM Studio before proceeding |
| YAML for user-editable config | `config/user_settings.yml` (like career-ops `profile.yml`) |
| Example config committed to repo | `config/user_settings.example.yml` (like career-ops `config/profile.example.yml`) |

### From Python CLI best practices
| Practice | Implementation |
|----------|---------------|
| Single responsibility CLI | click groups with one-level subcommands |
| Rich for terminal output | No raw print() — all output goes through `rich.console.Console` |
| HTTP-only CLI layer | CLI calls API, does not import business logic — one source of truth |
| questionary for guided input | Validation loops built-in, masked password input, defaults |
| `python -m module` entry | `job_agent/__main__.py` for natural invocation |
| Package entry point | `job-agent` script via `setup.cfg` |

### From 12-factor app principles
| Principle | How Applied |
|-----------|------------|
| Config in environment | `.env` for infrastructure — not in code |
| User config separate from deploy config | `user_settings.yml` overlays `.env` |
| Explicit dependencies | `requirements.txt` or `pyproject.toml` with all deps |
| Dev/prod parity | `APP_ENV=development/production` flag |

---

## Modern UI/UX Vision (Future Phases)

Not immediate — after UX1-5 are stable. These are design targets for a future UI refresh.

### Design Principles
1. **Information density over empty space** — this is a power-user tool, not a marketing site
2. **Keyboard-first** — shortcuts for common actions (K/J navigation, Enter to approve draft)
3. **Progressive disclosure** — summary cards expand to details on click, not separate pages
4. **Real-time feedback** — HTMX polling for task progress (draft generating → score appeared)
5. **Dark mode** — developer-friendly; Tailwind already supports it

### Component Upgrades

| Current | Target |
|---------|--------|
| Plain table for job list | Kanban columns by status, drag to move |
| Static draft text view | Split-pane: original JD left, CV draft right, diff highlights |
| Analytics bar charts (CSS widths) | Chart.js or ECharts inline bar/line charts |
| Settings read-only dump | Tabbed form with live validation (UX5 is step 1) |
| Navigation: plain links | Active-state sidebar with badge counts (jobs waiting, drafts pending) |

### Technology Path
- Stay on Jinja2 + HTMX (no React) — fast to ship, no build step
- Add Chart.js via CDN for analytics charts (no npm needed)
- Add Alpine.js (already in base.html) for toggles, modals, accordions
- Tailwind dark mode: `class="dark:..."` with `<html class="dark">` toggled by localStorage
- HTMX SSE (`hx-ext="sse"`) for live task progress instead of polling

### Keyboard Shortcuts (future)
- `j/k` — navigate list items
- `g d` — go to drafts
- `g j` — go to jobs
- `space` — expand/collapse card
- `a` — approve draft
- `r` — reject draft

---

## Public Distribution Checklist

Before releasing to other users:

- [ ] `config/user_settings.example.yml` committed (no personal data)
- [ ] `.gitignore` has `config/user_settings.yml`, `.env`, `generated/`
- [ ] `setup.cfg` or `pyproject.toml` has `job-agent` entry point + all deps listed
- [ ] `README.md` has 5-minute quickstart (docker compose → onboard → start)
- [ ] No hardcoded paths (`/Users/youseffayyaz/`) anywhere in codebase
- [ ] `DEFAULT_CANDIDATE_ID` has no hardcoded value in code (set via onboarding)
- [ ] LM Studio model names in defaults are generic (not Yousef's specific models)
- [ ] `config/user_settings.example.yml` has blank model names with explanatory comments
- [ ] `run.sh` is executable and has correct shebang
- [ ] `python -m job_agent.onboard` works from a fresh clone with only Docker + conda

---

## What We Explicitly Did NOT Copy from career-ops

| career-ops Pattern | Why We Didn't Copy |
|-------------------|-------------------|
| Claude Code as the UI layer | We have a real web app; Claude Code as UI is clever but not appropriate for a standalone tool |
| Markdown-as-DB | We have PostgreSQL — relational data belongs in a real DB |
| Go bubbletea TUI | Wrong language; our codebase is Python; Rich is sufficient |
| portals.yml as sole company source | Our `CareerPageSource` model is richer — YAML export/import is fine but not the primary store |
| Single-user assumption baked into Claude Code | We're building a standalone tool, not a Claude Code plugin |

---

## Execution Order for Codex

Send specs in this order (each depends on the previous):

```
1. prompt_UX1_settings_persistence.txt   ← do first, everything depends on it
2. prompt_UX3_unified_entry.txt          ← parallel with UX2 (different files)
   prompt_UX2_onboarding_wizard.txt      ← parallel with UX3
3. prompt_UX4_cli_commands.txt           ← after UX1 + UX3
4. prompt_UX5_settings_web_ui.txt        ← after UX1
```

UX2 and UX3 can be sent to Codex simultaneously — they touch different files.
UX4 and UX5 can also be sent simultaneously after UX1 is done.

After all UX phases: run the E2E test plan (`prompt_E2E_system_test.txt`) to validate end-to-end.
