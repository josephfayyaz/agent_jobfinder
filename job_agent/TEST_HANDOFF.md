# Test Handoff

Last updated: 2026-04-30

Latest bounded real-runtime validation:
- Two non-tech isolated runtimes were exercised under `mac_full_test_data_temp/.browser_nontech_cases/`:
  - `farah_discovery_runtime` on `http://127.0.0.1:8133`
  - `giorgio_discovery_runtime` on `http://127.0.0.1:8134`
- Important environment finding:
  - shell-style `conda activate ML` was not reliable in this desktop thread for subprocess launches
  - explicit binaries from `/Users/youseffayyaz/miniforge3/envs/ML/bin/` were required for correct `python-jobspy` resolution
  - using the wrong interpreter surfaced the unrelated `jobspy` package from base Miniforge instead of `python-jobspy`
- Live LM Studio finding:
  - direct chat probe showed `qwen3.5-9b-mlx` timed out at 45s for a trivial JSON response
  - direct chat probe showed `openai/gpt-oss-20b` returned in about 2.4s for the same trivial JSON request
  - the isolated non-tech runtimes were therefore switched to `lm_studio_small_model=openai/gpt-oss-20b` and `lm_studio_mid_model=openai/gpt-oss-20b`
- New backend bug fixed during this phase:
  - `job_agent/services/ats_discovery.py` now skips broken ATS sources instead of aborting the whole discovery run on one upstream 404
  - regression test added in `tests/test_ats_scanner.py`
  - verification: `15 passed` in `tests/test_ats_scanner.py` and `ruff check` clean
- Real retrieval outcome for bounded non-tech validation:
  - Farah Lodi (`Junior Accountant`, Italy): `9` real LinkedIn/JobSpy jobs saved
  - Giorgio Palmieri (`Financial Analyst`, Italy): `23` real LinkedIn/JobSpy jobs saved
  - Browser UI verified on `/ui/jobs?show_all=true&lane=all` for both runtimes
- Real scoring outcome:
  - `0` jobs >= 70 for Farah
  - `0` jobs >= 70 for Giorgio
  - dominant reason was not role mismatch; it was weak upstream job description payloads from LinkedIn/JobSpy
  - UI showed repeated `Fallback score` / `Job description is too weak for provider scoring.` with `Enrichment: Pending enrichment` on the saved rows
- Interpretation:
  - retrieval quality is contextually meaningful for both non-tech users
  - the current weak point is downstream JD completeness from JobSpy/LinkedIn, not gross title mismatch
  - to get trustworthy 70+/80+ candidate-fit scoring, the app needs stronger enrichment or direct ATS/company descriptions before scoring
- Result artifacts written:
  - `/Users/youseffayyaz/Local_LLM/mac_full_test_data_temp/results/farah_bounded_runtime_report.json`
  - `/Users/youseffayyaz/Local_LLM/mac_full_test_data_temp/results/giorgio_bounded_runtime_report.json`
  - `/Users/youseffayyaz/Local_LLM/mac_full_test_data_temp/results/nontech_runtime_validation_summary.json`

Current phase:
- Hybrid discovery is now active in the main queued `/ui/jobs/discover` flow: JobSpy remains the board source and active ATS feeds are merged into the same run before scoring
- Discovery now hard-fails if the imported `jobspy` module is not backed by the expected `python-jobspy` distribution in the `ML` environment
- ATS payloads now carry description text when the upstream feed exposes it, which improves scoring quality before secondary enrichment
- The jobs UI copy and progress panel now reflect hybrid discovery rather than a JobSpy-only run
- Verification for this patch set completed in `ML`:
  - `pytest tests/test_ats_scanner.py tests/test_jobspy_scheduler.py tests/test_api.py --tb=short -q` → `89 passed`
  - `pytest tests/test_onboarding.py tests/test_search_profile_preferences.py tests/test_provider_resilience.py tests/test_e2e_full_journey.py tests/test_worker.py --tb=short -q` → `59 passed`
  - `ruff check job_agent/services/ats_discovery.py job_agent/services/ats_scanner.py job_agent/services/jobspy_service.py job_agent/services/workflows.py tests/test_ats_scanner.py tests/test_jobspy_scheduler.py tests/test_api.py` → `All checks passed.`
- R3/R4/R5 discovery implementation is complete and verified in the `ML` environment
- Candidate-fit scoring now runs after JobSpy retrieval using the single active provider and persists per-candidate fit metadata on jobs
- The jobs UI now runs discovery asynchronously, shows live progress, and renders fit/risk details in the queue
- The discovery smoke harness is now live under `/Users/youseffayyaz/Local_LLM/mac_full_test_data_temp` and passed both positive and negative-path audits
- Two live regressions were found and fixed during R5 validation:
  - `/tasks/{id}` now accepts UUID strings cleanly instead of 500ing in SQLAlchemy task lookups
  - candidate-fit scoring and discovery visibility counting now coerce saved JobPost UUID strings before ORM lookup

Completed previously:
- Onboarding flow debugged and stabilized
- Intake normalization fixed for multiple LM Studio output shapes
- Onboarding resume/reload behavior fixed
- Browser-based onboarding persistence verified
- Isolated onboarding audit passed for 20 synthetic users

Execution environment:
- Use conda environment `ML`
- Disposable test harness lives under `/Users/youseffayyaz/Local_LLM/mac_full_test_data_temp`
- Browser-based UI checks used the `browser-use` plugin

Role phase completed:
- Recommended search roles now come from contextual profile-based suggestions instead of shallow echoing
- Discovery-role limit is now enforced at 4 end-to-end
- Settings page now exposes a post-onboarding `Suggest from profile` refresh path
- Batch role-suggestion audit passed for 20 synthetic users

Current planning status:
- Release workflow direction is now fixed:
  - one active AI provider powers the whole workflow
  - one country only for discovery
  - up to 4 desired roles
  - language proficiency is persisted but treated as a soft scoring signal
  - JobSpy is the only active discovery source in the next implementation pack
- Ordered implementation specs were added under `/Users/youseffayyaz/Local_LLM/AGENT_SPECS/pending/codex/`
- The spec pack is split into:
  - provider/search contract
  - JobSpy discovery backend
  - candidate-fit scoring
  - jobs progress/results UI
  - smoke audit and reporting

Next expected implementation phase:
- Start the next post-discovery implementation batch after R3/R4/R5 acceptance
- Use conda environment `ML` for all commands, tests, browser checks, and audits

R1/R2 verification status:
- Copilot Codex implementation was close but not perfect on first pass
- After the regression fixes above, verification reruns should be treated as the accepted R1/R2 baseline

R3/R4/R5 verification status:
- Discovery scoring/UI/audit work is now the accepted baseline
- Validation runs completed in `ML`:
  - `pytest tests/test_job_fit_scoring.py tests/test_jobspy_scheduler.py tests/test_api.py --tb=short -q` → `73 passed in 4.75s`
  - `pytest tests/test_onboarding.py tests/test_search_profile_preferences.py tests/test_jobspy_scheduler.py tests/test_job_fit_scoring.py tests/test_api.py tests/test_e2e_full_journey.py --tb=short -q` → `109 passed in 15.23s`
  - `ruff check job_agent tests mac_full_test_data_temp/discovery_smoke_audit.py mac_full_test_data_temp/fake_lm_studio_server.py` → `All checks passed.`
  - `bash mac_full_test_data_temp/run_discovery_smoke_audit.sh` → passed 3 positive scenarios plus zero-result and disabled-JobSpy negative scenarios

Discovery phase delivered:
- `discovery_min_fit_score` and `discovery_max_visible_jobs` are now configurable and enforced in the default queue
- JobSpy discovery now records saved job ids, queues post-save scoring, and reports scoring visibility counts
- Candidate-fit metadata now stores fit score, score source, provider mode, language assessment, seniority assessment, and short reasoning per candidate
- `/ui/jobs/discover` now returns a task payload and the jobs page polls `/tasks/{id}` instead of blind reload
- The jobs UI now shows provider/fallback scoring badges, language risk, seniority risk, and queue-cap context
- The disposable smoke harness now exercises:
  - provider validation
  - search-settings persistence
  - fact-sheet ingestion
  - JobSpy discovery
  - async task polling
  - default-cap enforcement
  - zero-result handling
  - disabled-JobSpy handling

Role phase verification:
- `pytest tests/test_intake.py tests/test_search_profile_preferences.py tests/test_seed_companies.py -q` passed in `ML`
- `mac_full_test_data_temp/run_role_suggestion_audit.sh` passed `20/20`
- Role audit covered:
  - contextual suggestions after onboarding
  - save and persistence of selected roles
  - edit/update of selected roles
  - persistence after restart
  - re-suggestion after fact-sheet target-role updates
  - rejection of more than 4 discovery roles

Files changed in this phase:
- `/Users/youseffayyaz/Local_LLM/job_agent/search_preferences.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/routers/system.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/routers/ui_context.py`
- `/Users/youseffayyaz/Local_LLM/job_agent/routers/setup_state.py`
- `/Users/youseffayyaz/Local_LLM/frontend/static/onboarding.js`
- `/Users/youseffayyaz/Local_LLM/frontend/templates/onboarding.html`
- `/Users/youseffayyaz/Local_LLM/frontend/static/settings.js`
- `/Users/youseffayyaz/Local_LLM/frontend/templates/settings.html`
- `/Users/youseffayyaz/Local_LLM/tests/test_search_profile_preferences.py`
- `/Users/youseffayyaz/Local_LLM/tests/test_seed_companies.py`
- `/Users/youseffayyaz/Local_LLM/mac_full_test_data_temp/role_suggestion_audit.py`
- `/Users/youseffayyaz/Local_LLM/mac_full_test_data_temp/run_role_suggestion_audit.sh`

Environment note:
- The disposable harness continues to rely on the persisted `ML` python path via `/Users/youseffayyaz/Local_LLM/mac_full_test_data_temp/.python-bin`

Current real-browser validation note:
- Real-browser discovery validation now follows a strict rule: use the real configured LM Studio provider unless the user explicitly approves a fake/stub fallback.
- Removed the fake discovery smoke-audit harness files from `mac_full_test_data_temp` and updated that folder README to describe real-source, real-provider testing only.
- Active real-browser runs are on `http://127.0.0.1:8121` for `03_backend_engineer_mid` and `http://127.0.0.1:8122` for `04_qa_automation_junior`, each backed by isolated runtimes under `mac_full_test_data_temp/.browser_real_cases/`.
- Backend browser run has already verified the live jobs progress UI while discovery is running; current backend task `f4fa9e29-2c8f-4a14-b572-259e53dd1b20` saved `72` jobs after filtering and is still enriching/scoring against the real `openai/gpt-oss-20b` model.
