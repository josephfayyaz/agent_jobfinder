# Decision Matrix — What to Adopt from Career-Ops

## Scoring

- `Adopt now` = high fit, high leverage, low product risk
- `Adopt later` = good idea, but not current priority
- `Reject` = strong in career-ops, wrong for Job Agent

| Capability | Career-Ops Strength | Fit for Job Agent | Decision | Job Agent Version |
|---|---|---:|---|---|
| Filter-first philosophy | Excellent | Very high | Adopt now | Push users toward high-fit roles instead of mass applying |
| ATS/API-first scanning | Excellent | Very high | Adopt now | Expand company/page scanning with low-token discovery methods |
| Job legitimacy / ghost-post signal | Strong | High | Adopt now | Show freshness + confidence badges on jobs |
| Pipeline inbox | Strong | High | Adopt now | Build a “new jobs to review” queue in web UI |
| Tracker integrity scripts | Strong | High | Adopt now | Add background consistency checks and repair endpoints |
| Structured profile / narrative layer | Strong | Very high | Adopt now | Continue expanding fact sheet + verified memory + role preferences |
| AI-generated tailored CV per job | Strong | Already aligned | Keep improving | Maintain your existing draft workflow, not theirs |
| Batch evaluation with many workers | Strong | Medium | Adopt later | Use your task queue, not `claude -p` workers |
| Terminal dashboard | Good | Low | Reject | Your primary surface is browser UI, not TUI |
| Repo-as-UI | Core to them | Very low | Reject | Keep onboarding/settings/dashboard in app |
| Claude Code as product shell | Core to them | Very low | Reject | Keep provider-agnostic routing in your app |
| Markdown/TSV as canonical DB | Works for them | Low | Reject | Keep SQLite as source of truth |
| Manual config-first setup | Works for them | Very low | Reject | Keep guided onboarding and setup gates |
| Archetype-based scoring | Good | Medium | Adopt later | Convert to role families / search focus cards, not hidden jargon |
| Interview story bank | Strong | High | Adopt later | Add structured STAR story memory from approved drafts and fact sheet |
| Offer evaluation / negotiation | Strong | Medium | Adopt later | Good expansion after search + CV loop is stable |
| Deep company research mode | Strong | Medium | Adopt later | Add premium “company brief” stage for shortlisted jobs |
| Language-aware modes | Good | High | Already aligned | Continue via UI language + job-language filtering |

## Product Interpretation

### What Career-Ops gets very right

1. It treats job search as a **pipeline**, not a list.
2. It assumes the user’s time is scarce.
3. It emphasizes **fit and selectivity**, not volume.
4. It separates discovery, evaluation, asset generation, and tracking.
5. It uses low-token acquisition paths where possible.

### What Job Agent should do differently

1. Explain every major step through the UI.
2. Keep the workflow accessible to nontechnical users.
3. Manage providers and costs inside the app.
4. Treat local LLM as optional advanced infrastructure.
5. Replace file choreography with explicit app states, queues, and screens.

## Direct Adoption Priorities

### Tier 1

- Opportunity filtering
- Discovery pipeline discipline
- Freshness / legitimacy signals
- Review queue
- tracker integrity

### Tier 2

- Deep personalization via role focus and evidence memory
- Shortlist-centric company research
- Interview story bank

### Tier 3

- Offer scoring
- Negotiation support
- advanced archetype tuning

## Main Recommendation

If you only import three ideas from career-ops, import these:

1. **Filter-first thinking**
2. **Low-token discovery architecture**
3. **Pipeline integrity and review discipline**

Those three will improve Job Agent the most without distorting your product.
