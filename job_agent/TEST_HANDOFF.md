# Test Handoff

Last updated: 2026-05-02

Current QA sandbox:
- The older `mac_full_test_data_temp/` sandbox has been deleted on purpose.
- The only approved repo-local QA sandbox is now:
  - `/Users/youseffayyaz/Local_LLM/temp_mac_test`
- Historical sections below still mention the older path because they record
  what was true when those runs were executed. Do not rebuild or reuse that
  deleted folder for new testing.

Latest HTMX follow-up fixes:
- Recommendation: keep the inline queue-state change in
  `job_agent/routers/jobs.py`.
  - `/ui/jobs/{job_id}/queue-state` returning `partials/job_row.html` is the
    correct direction for queue UX and should not be reverted to
    `204 + HX-Refresh`.
- Remaining destructive reload handlers were narrowed to success-only reloads:
  - `frontend/templates/jobs.html`
    - `Scan Career Pages` now reloads only on success
  - `frontend/templates/companies.html`
    - `Scan All Now` and `toggle-active` now reload only on success
  - `frontend/templates/applications.html`
    - application stage advance now reloads only on success
  - `frontend/templates/drafts.html`
    - draft approve/reject now reload only on success
  - `frontend/templates/partials/drafts/sidebar.html`
    - compliance-matrix generation now reloads only on success
- Queue-state behavior is now consistent inside the Application Snapshot:
  - `frontend/templates/partials/apply_package_check.html`
    - `Add to Shortlist First` now targets `#job-row-{id}` with
      `hx-swap="outerHTML"`
    - successful shortlist action hides the open snapshot row
- Future helper drift reduced:
  - `job_agent/routers/job_queue_actions.py`
    - `queue_state_response(...)` now matches the partial-row inline update
      semantics instead of stale `204 + HX-Refresh`
- Focused regression coverage updated:
  - `tests/test_ui.py`
  - `tests/test_career_ops_adaptation.py`
- Validation:
  - `/Users/youseffayyaz/miniforge3/envs/ML/bin/python -m pytest tests/test_ui.py tests/test_review_queue.py tests/test_career_ops_adaptation.py tests/test_ui_draft_detail.py -q`
    → `33 passed`
  - `/Users/youseffayyaz/miniforge3/envs/ML/bin/python -m ruff check job_agent/routers/job_queue_actions.py tests/test_ui.py tests/test_career_ops_adaptation.py`
    → passed
  - `node --check frontend/static/jobs.js frontend/static/app.js frontend/static/apply.js`
    → passed
- Live browser note:
  - the fresh `temp_mac_test` sandbox currently hits the setup-incomplete gate
    on several screens unless a configured runtime is seeded first
  - browser verification confirmed the local app server is healthy again on
    `127.0.0.1:8000`, but populated-runtime action checks should be rerun after
    onboarding/provider setup is seeded into the fresh sandbox

Latest live QA and runtime alignment fixes:
- The fresh sandbox is now being treated as the only valid runtime for browser,
  API, and worker QA:
  - `JOB_AGENT_HOME=/Users/youseffayyaz/Local_LLM/temp_mac_test/.runtime/current`
  - `DATABASE_URL=sqlite:////Users/youseffayyaz/Local_LLM/temp_mac_test/.runtime/current/job_agent.db`
- A real runtime mismatch was found during QA:
  - the app server and worker were initially preserving an older inherited
    `JOB_AGENT_HOME`, so browser traffic and background processing were not
    using the same database as the fresh sandbox
  - this is now corrected by launching both server and worker with explicit
    sandbox env overrides instead of relying on inherited shell state
- Fresh user-path fixes completed in this pass:
  - onboarding provider hydration now prefers a ready local provider instead of
    landing on the unconfigured OpenAI default when LM Studio is already ready
  - settings provider panels now hide non-selected provider fields and only
    expose the matching local-provider test button
  - help page now reflects the current product contract:
    - one active provider for the whole workflow
    - one country
    - up to four roles
    - manual target/JD path
  - candidate fact-sheet JSON validation now returns `422` instead of `500`
    when the payload fails schema validation
  - `/jobs/{id}/track-fit` and sibling string job-id routes now coerce UUID
    strings before ORM lookup
  - `frontend/templates/draft_detail.html` no longer crashes on populated
    project bullets; the project preview loop now uses an explicit outer index
    instead of `loop.parent`
- Fresh runtime QA seed currently in the sandbox:
  - candidate id: `ae887e4d-3ab4-4605-906d-e51dc11d3481`
  - manual job id: `50f7d1d7-6f8a-40d6-b522-f5d16672b2e8`
  - generated draft id: `1e47f56d-b301-4605-8717-cc41f8a49cd0`
  - completed draft task id: `fe2fc877-310b-45d8-88fb-d1b7a33b23aa`
  - provider: `lm_studio`
  - live model: `openai/gpt-oss-20b`
- Fresh sandbox QA artifacts:
  - `/Users/youseffayyaz/Local_LLM/temp_mac_test/results/ui_qa_runtime_seed.json`
  - `/Users/youseffayyaz/Local_LLM/temp_mac_test/results/ui_action_endpoint_audit.json`
  - `/Users/youseffayyaz/Local_LLM/temp_mac_test/results/ui_qa_summary_2026-05-02.json`
- Endpoint/button-handler audit status:
  - `POST /providers/validate` → `200`
  - `GET /lm-studio/models` → `200`
  - `GET /ui/jobs/{job_id}/package-check` → `200`
  - `GET /ui/jobs/{job_id}/snapshot` → `200`
  - `POST /ui/jobs/{job_id}/refresh-signals` → `200`
  - `POST /ui/jobs/{job_id}/enrich-row` → `200`
  - `GET /drafts/{draft_id}/preview-state` → `200`
  - `POST /ui/drafts/{draft_id}/approve` → `409`
    - this block is intentional when preview confirmations remain pending
- Live browser QA now confirmed these screens render correctly in the fresh
  sandbox:
  - `/ui/onboarding`
  - `/ui/settings`
  - `/ui/help`
  - `/ui/jobs`
  - `/ui/drafts`
  - `/ui/drafts/1e47f56d-b301-4605-8717-cc41f8a49cd0`
- Current remaining product-level gap after this QA pass:
  - resume tracks are still tech/data-only (`4` tracks total), so non-tech
    candidate routing remains structurally biased even though the app shell,
    settings, jobs actions, and draft-detail flow are now behaving correctly
    in the fresh sandbox

Latest refactor/redesign progress:
- The first structural UI refactor pass is now underway on `main`.
- Jobs and draft review templates were split into stable partials:
  - `frontend/templates/partials/jobs/*`
  - `frontend/templates/partials/drafts/*`
- Settings and onboarding templates are now split into section/step partials:
  - `frontend/templates/partials/settings/*`
  - `frontend/templates/partials/onboarding/*`
- The largest remaining draft route file has now been materially reduced:
  - `job_agent/routers/drafts.py` dropped from ~1047 lines to ~569 lines
  - draft state transitions now live in `job_agent/routers/draft_actions.py`
- Onboarding and settings controllers were split into staged frontend modules:
  - `frontend/static/onboarding/*`
  - `frontend/static/settings/*`
- Frontend controller ownership is now clearer in:
  - `frontend/static/jobs.js`
  - `frontend/static/draft_detail.js`
  - `frontend/static/onboarding.js`
  - `frontend/static/settings.js`
- The application shell/navigation has been simplified for end-user flow:
  - primary nav: Dashboard / Jobs / CVs / Applications / Settings
  - secondary tools moved behind the Utilities disclosure
- Jobs and draft review UI now use clearer operational zones:
  - jobs page adds a right-side search command deck
  - draft review exposes explicit preview / evidence / fit / final-action zones
- Backend cleanup is now in progress without changing public route paths:
  - `job_agent/services/job_discovery_workflow.py`
    - dedicated queued JobSpy + ATS discovery orchestration
  - `job_agent/routers/job_queue_actions.py`
    - focused job-queue and discovery mutations used by `jobs.py`
  - `job_agent/routers/draft_actions.py`
    - focused preview-edit, clarification, inferred-addition, PDF, and approval state transitions used by `drafts.py`
  - `job_agent/services/workflows.py`
    - still the public orchestration surface, but now delegates discovery to the dedicated workflow module while preserving monkeypatch compatibility for tests
- Draft preview refresh now degrades safely when a legacy test draft has no
  candidate/master-profile context instead of crashing the UI:
  - `job_agent/routers/drafts.py`
- Focused verification for this pass:
  - `python -m pytest tests/test_ui.py tests/test_ui_draft_detail.py tests/test_bullet_clarify_ui.py -q` → `15 passed`
  - `python -m pytest tests/test_onboarding.py tests/test_settings_ui.py tests/test_ui.py -q` → `20 passed`
  - `python -m pytest tests/test_settings_ui.py tests/test_ui.py tests/test_onboarding.py tests/test_review_queue.py tests/test_ui_draft_detail.py tests/test_jobspy_scheduler.py tests/test_jobspy_service.py tests/test_api.py tests/test_workflows.py tests/test_job_enrichment_lock.py -q` → `139 passed`
  - `python -m pytest tests/test_jobspy_scheduler.py tests/test_jobspy_service.py tests/test_api.py tests/test_review_queue.py tests/test_workflows.py tests/test_job_enrichment_lock.py -q` → `106 passed`
  - `python -m pytest tests/test_onboarding.py tests/test_settings_ui.py tests/test_ui.py tests/test_ui_draft_detail.py tests/test_review_queue.py tests/test_jobspy_scheduler.py tests/test_jobspy_service.py tests/test_api.py tests/test_workflows.py tests/test_job_enrichment_lock.py tests/test_bullet_clarify.py tests/test_bullet_clarify_ui.py tests/test_inferred_additions.py tests/test_e2e_full_journey.py -q` → `169 passed`
  - `python -m pytest tests/test_api.py tests/test_ui_draft_detail.py tests/test_bullet_clarify.py tests/test_bullet_clarify_ui.py tests/test_inferred_additions.py tests/test_e2e_full_journey.py -q` → `109 passed`
  - `python -m ruff check job_agent/routers/drafts.py` → `All checks passed.`
  - `python -m ruff check job_agent/services/job_discovery_workflow.py job_agent/routers/job_queue_actions.py job_agent/services/workflows.py job_agent/routers/jobs.py` → `All checks passed.`
  - `python -m ruff check job_agent/routers/draft_actions.py job_agent/routers/drafts.py job_agent/routers/job_queue_actions.py job_agent/routers/jobs.py job_agent/services/job_discovery_workflow.py job_agent/services/workflows.py` → `All checks passed.`
  - `node --check frontend/static/jobs.js`
  - `node --check frontend/static/draft_detail.js`
  - `node --check frontend/static/onboarding/*.js`
  - `node --check frontend/static/settings/*.js`
- Live browser QA:
  - verified `/ui/jobs`, `/ui/onboarding`, and `/ui/settings` in the fresh sandbox after the template/controller splits
  - the fresh sandbox still correctly opens in setup-required mode until a candidate + provider are configured
- Current structural line-count snapshot:
  - `job_agent/routers/jobs.py` → `1179`
  - `job_agent/routers/drafts.py` → `569`
  - `job_agent/services/workflows.py` → `1390`
  - `frontend/templates/settings.html` → `57`
  - `frontend/templates/onboarding.html` → `50`

Latest F6 completion:
- Phase `F6` is now complete.
- Real runtime CV validation was executed against the isolated F6 workspace:
  - `JOB_AGENT_HOME=/Users/youseffayyaz/Local_LLM/mac_full_test_data_temp/.browser_f6_runtime`
  - live app port: `8141`
  - explicit interpreter: `/Users/youseffayyaz/miniforge3/envs/ML/bin/python`
  - live LM Studio model: `openai/gpt-oss-20b`
- Three real runtime problems were identified and fixed during this phase:
  - `job_agent/config.py`
    - YAML reload now preserves `jobspy_detail_enrichment_enabled` and `jobspy_detail_enrichment_limit`
  - `job_agent/routers/drafts.py`
    - draft fetch/approve routes now coerce UUID string path params before ORM lookup
  - `job_agent/models.py`, `job_agent/db.py`, `job_agent/services/workflows.py`, `job_agent/routers/drafts.py`, `job_agent/services/bullet_clarify.py`
    - saved drafts now persist `candidate_id`
    - queued CV tasks snapshot `candidate_id` at queue time
    - draft preview/rerender/clarification paths now use the draft’s stored candidate instead of the current default candidate
- New regression coverage added:
  - `tests/test_user_settings.py::test_yaml_overlay_loads_jobspy_detail_enrichment_fields`
  - `tests/test_api.py::test_get_draft_accepts_uuid_string_path`
  - `tests/test_api.py::test_approve_draft_accepts_uuid_string_path`
  - `tests/test_api.py::test_preview_state_uses_draft_candidate_after_default_candidate_switch`
  - `tests/test_candidate_workflow.py::test_load_context_uses_explicit_candidate_id_over_changed_default`
  - `tests/test_candidate_workflow.py::test_queue_cv_workflow_persists_candidate_id_snapshot`
- Exact F6 suite passed in `ML`:
  - `python -m pytest tests/test_documents.py tests/test_workflows.py tests/test_candidate_workflow.py tests/test_api.py -q` → `91 passed`
  - `python -m pytest tests/test_candidate_workflow.py tests/test_api.py tests/test_ui_draft_detail.py tests/test_bullet_clarify.py -q` → `85 passed`
  - `python -m ruff check job_agent/models.py job_agent/db.py job_agent/schemas.py job_agent/services/workflows.py job_agent/routers/drafts.py job_agent/services/bullet_clarify.py job_agent/config.py tests/test_documents.py tests/test_workflows.py tests/test_candidate_workflow.py tests/test_api.py tests/test_user_settings.py` → `All checks passed.`
- F6 runtime artifacts now available:
  - primary audit:
    - `/Users/youseffayyaz/Local_LLM/mac_full_test_data_temp/results/f6_yousef_discovered_report.json`
    - `/Users/youseffayyaz/Local_LLM/mac_full_test_data_temp/results/f6_rina_manual_report.json`
    - `/Users/youseffayyaz/Local_LLM/mac_full_test_data_temp/results/f6_farah_sparse_control_report.json`
    - `/Users/youseffayyaz/Local_LLM/mac_full_test_data_temp/results/f6_cv_runtime_validation_summary.json`
  - post-fix candidate-binding proof:
    - `/Users/youseffayyaz/Local_LLM/mac_full_test_data_temp/results/f6_rina_manual_postfix_report.json`
    - `/Users/youseffayyaz/Local_LLM/mac_full_test_data_temp/results/f6_candidate_binding_before_restart.json`
    - `/Users/youseffayyaz/Local_LLM/mac_full_test_data_temp/results/f6_candidate_binding_after_restart.json`
- Important live conclusion:
  - persisted drafts now survive restart and remain semantically tied to the original candidate even after the default candidate is switched to a different person
  - proof artifact:
    - `draft_id=cd499866-9488-401e-83a9-5c5f06c721c1`
    - stored `draft_candidate_id=8896efd5-7d71-475c-9215-f8419f8e1b92`
    - restarted app default candidate: `e4b29493-0854-4dc2-8656-2f89d9ba9fa3`
    - post-restart preview readiness stayed `ready` for the original Rina profile
- Remaining F6 recommendations:
  - tighten preview gating for rich profiles because some high-scoring bullets still require confirmation
  - filter JD heading/company boilerplate more aggressively out of `recommended_improvements`
  - consider requiring explicit acknowledgment before final PDF export when pending preview confirmations remain

Latest F1-F5 CV phase implementation:
- Phases `F1` through `F5` are now implemented in the main app code path and verified under the explicit `ML` interpreter:
  - `/Users/youseffayyaz/miniforge3/envs/ML/bin/python`
- New CV-phase backend services:
  - `job_agent/services/profile_readiness.py`
    - deterministic readiness gate with `ready`, `usable_with_warnings`, and `insufficient_profile_data`
  - `job_agent/services/job_target_profile.py`
    - structured manual-JD target profile extraction
    - requirement tiering (`must_have`, `important`, `nice_to_have`, `contextual`)
    - evidence-to-requirement fit map
    - gap severity levels (`strong_match`, `partial_match`, `stretch_match`, `high_gap`)
  - `job_agent/services/draft_preview.py`
    - preview annotation tags (`direct_fact`, `safe_paraphrase`, `adjacent_inference`, `needs_user_confirmation`)
- F1 implementation status:
  - onboarding now includes a dedicated review step before search setup
  - candidate review/readiness endpoints now exist:
    - `GET /candidates/{id}/readiness`
    - `GET /candidates/{id}/onboarding-review`
  - CV queue/generate routes now block final drafting when the active profile is too thin
- F2 implementation status:
  - manual target intake now has an app UI panel on `/ui/jobs`
  - existing endpoints now return structured target-profile data:
    - `POST /jobs/from-text`
    - `POST /jobs/add`
- F3 implementation status:
  - CV workflow now writes a `target_fit_map` and `recommended_improvements` into draft review feedback
  - fit mapping is now evidence-first and domain-neutral instead of track-only
- F4 implementation status:
  - draft detail UI now exposes:
    - profile readiness
    - target fit map
    - recommended improvements
    - preview annotation badges
  - preview edit/update endpoints now exist:
    - `GET /drafts/{id}/preview-state`
    - `POST /drafts/{id}/preview/update`
  - final approval now blocks when preview items still need user confirmation
- F5 implementation status:
  - PDF/TeX artifact naming now includes date + company + candidate slug + short draft id
  - renderer now supports a `Languages` section when available
  - output contract is closer to a user-review-first CV workflow instead of direct blind PDF generation
- Main frontend files changed in this phase:
  - `frontend/templates/onboarding.html`
  - `frontend/static/onboarding.js`
  - `frontend/templates/jobs.html`
  - `frontend/static/jobs.js`
  - `frontend/templates/draft_detail.html`
  - `frontend/static/draft_detail.js`
- Main backend files changed in this phase:
  - `job_agent/routers/candidates.py`
  - `job_agent/routers/jobs.py`
  - `job_agent/routers/drafts.py`
  - `job_agent/services/workflows.py`
  - `job_agent/services/documents.py`
- Verification for this phase in `ML`:
  - `python -m pytest tests/test_cv_phase_f.py tests/test_candidate_workflow.py tests/test_documents.py tests/test_ui_draft_detail.py tests/test_api.py tests/test_workflows.py tests/test_onboarding.py tests/test_review_queue.py tests/test_api_profile.py tests/test_job_fit_scoring.py tests/test_e2e_full_journey.py -q` → `149 passed`
  - `python -m pytest tests/test_api.py::test_preview_state_returns_readiness_fit_map_and_annotations tests/test_ui_draft_detail.py::test_ui_draft_detail_returns_200 -q` → `2 passed`
  - `python -m ruff check job_agent/services/profile_readiness.py job_agent/services/job_target_profile.py job_agent/services/draft_preview.py job_agent/services/workflows.py job_agent/routers/candidates.py job_agent/routers/jobs.py job_agent/routers/drafts.py job_agent/services/documents.py tests/test_cv_phase_f.py tests/test_candidate_workflow.py tests/test_documents.py tests/test_ui_draft_detail.py tests/test_api.py tests/test_e2e_full_journey.py` → `All checks passed.`
  - `node --check frontend/static/onboarding.js frontend/static/jobs.js frontend/static/draft_detail.js` → passed
- Important limitation after F1-F5:
  - this phase adds the readiness, manual-target, fit-map, preview, and renderer contract
  - it does **not** yet include the real CV-quality runtime audit against rich user profiles and target jobs; that remains the purpose of `F6`

Latest CV runtime validation:
- Real LM Studio CV workflow was exercised directly against the two saved E4 non-tech runtimes:
  - Farah Lodi for `Trainee Accounts Receivable Specialist` at `Kuehne+Nagel`
  - Giorgio Palmieri for `FP&A Analyst` at `AB Parfums`
- CV workflow fixes in this pass:
  - sparse candidate profiles now trigger truthful draft constraints instead of inventing employers, years of experience, or quantified outcomes
  - prompt-track fallback now avoids feeding obviously weak tech-track framing into non-tech CV drafts when the stored track match is low-confidence
  - candidate project/profile-note evidence is preserved as `Relevant Evidence` instead of being rewritten as fake employment history
  - compliance requirement extraction now filters out much more company-branding copy before matrix generation
  - renderer now omits empty `Professional Experience` sections for sparse profiles and relabels profile-note project sections as `Relevant Evidence`
- Real artifacts written:
  - `/Users/youseffayyaz/Local_LLM/mac_full_test_data_temp/results/2026-05-01_KuehneNagel_Farah_Lodi_cv.pdf`
  - `/Users/youseffayyaz/Local_LLM/mac_full_test_data_temp/results/2026-05-01_AB_Parfums_Giorgio_Palmieri_cv.pdf`
  - matching `.json`, `.tex`, and first-page `.png` preview files alongside them
  - consolidated audit summary: `/Users/youseffayyaz/Local_LLM/mac_full_test_data_temp/results/cv_generation_validation_summary.json`
- Important interpretation:
  - the CVs are now truthful and visually cleaner, but they are still not application-ready at a high standard because the saved candidate data is too thin
  - both runtime candidates currently have education plus one profile-note evidence item and no structured `experience_facts`
  - this means the next product-level requirement is stronger candidate data capture and review before final CV generation
- Verification for this pass:
  - `pytest tests/test_candidate_workflow.py tests/test_compliance_matrix.py tests/test_prompts.py tests/test_workflows.py tests/test_documents.py -q` → `36 passed`
  - `ruff check job_agent/services/workflows.py job_agent/services/prompts.py job_agent/services/documents.py tests/test_candidate_workflow.py tests/test_compliance_matrix.py tests/test_prompts.py tests/test_documents.py` → `All checks passed.`

Latest E4 real-runtime validation:
- Fresh isolated runtimes were exercised under `mac_full_test_data_temp/.browser_nontech_cases_e4/`:
  - `06_accountant_junior` on `http://127.0.0.1:8137`
  - `07_financial_analyst_mid` on `http://127.0.0.1:8138`
- Runtime used:
  - explicit `ML` interpreter: `/Users/youseffayyaz/miniforge3/envs/ML/bin/python`
  - live LM Studio model: `openai/gpt-oss-20b`
  - real queued discovery with `use_jobspy=true`
  - detail enrichment enabled with limit `12`
- E4 code path is now complete:
  - jobs awaiting stronger JD enrichment have a dedicated truthful `awaiting` lane
  - thresholding only applies to `threshold_eligible=true` jobs
  - jobs UI/discovery summaries now expose:
    - `awaiting_enrichment_count`
    - `provider_scored_count`
    - `fallback_scored_count`
    - `ready_for_threshold_count`
- Live bug fixed during this phase:
  - `job_agent/user_config.py` now allows `jobspy_detail_enrichment_enabled` and `jobspy_detail_enrichment_limit` through `/settings/save`
  - regression added in `tests/test_user_settings.py`
- Real outcomes:
  - Farah Lodi (`Junior Accountant`, Italy): `18` saved jobs, `10` provider-scored, `8` awaiting enrichment, `9` jobs >= `70`, `9` jobs >= `80`
  - Giorgio Palmieri (`Financial Analyst`, Italy): `110` saved jobs, `63` provider-scored, `47` awaiting enrichment, `8` jobs >= `70`, `4` jobs >= `80`
  - in both cases the default jobs UI exposed the truthful awaiting-enrichment path without `show_all=true`
- Persistence proof:
  - restarting the app against the saved E4 runtimes preserved job rows and the awaiting-enrichment lane
  - Farah runtime reloaded with `18` jobs still available
  - Giorgio runtime reloaded with `110` jobs still available
  - artifact: `/Users/youseffayyaz/Local_LLM/mac_full_test_data_temp/results/e4_restart_persistence_check.json`
- Stale-job handling update:
  - `JobSignalService._freshness_signal()` now uses `posted_date` when available instead of relying only on `last_seen_at` / import recency
  - old-but-still-live postings now surface as `Older posting` / `Stale listing` based on actual publish age when the source provides it
  - regression added in `tests/test_review_queue.py`
- Important interpretation:
  - E4 acceptance is met: thin-JD jobs no longer masquerade as low-fit shortlist failures
  - these two live reruns proved meaningful local-provider scoring and truthful queue separation
  - they did **not** yet prove ATS/direct-source provider scoring; observed provider-scored rows were mainly `jobspy_linkedin` with `jd_extraction_method=readability` and `jd_source_kind=linkedin_enriched`
- Result artifacts written:
  - `/Users/youseffayyaz/Local_LLM/mac_full_test_data_temp/results/06_accountant_junior_e4_runtime_report.json`
  - `/Users/youseffayyaz/Local_LLM/mac_full_test_data_temp/results/07_financial_analyst_mid_e4_runtime_report.json`
  - `/Users/youseffayyaz/Local_LLM/mac_full_test_data_temp/results/e4_nontech_runtime_validation_summary.json`
- Verification after the live bugfix:
  - `pytest tests/test_api.py tests/test_review_queue.py tests/test_job_fit_scoring.py tests/test_job_fetcher.py tests/test_user_settings.py -q` → `88 passed`
  - `ruff check job_agent/routers/jobs.py job_agent/routers/job_views.py job_agent/services/workflows.py job_agent/user_config.py tests/test_api.py tests/test_review_queue.py tests/test_user_settings.py` → `All checks passed.`
  - `node --check frontend/static/jobs.js` → passed
- Note:
  - browser-use was not callable in this thread, so rendered jobs-page validation was done over live HTTP responses from the running app instead of plugin-driven browser automation

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

Latest planning update:
- A new post-R5 execution pack now exists for the real JD-enrichment bottleneck:
  - `/Users/youseffayyaz/Local_LLM/AGENT_SPECS/pending/codex/phase_E0_jd_enrichment_execution_order.md`
  - `/Users/youseffayyaz/Local_LLM/AGENT_SPECS/pending/codex/phase_E1_truthful_jd_readiness_and_quality_gate.md`
  - `/Users/youseffayyaz/Local_LLM/AGENT_SPECS/pending/codex/phase_E2_selective_jobspy_detail_enrichment.md`
  - `/Users/youseffayyaz/Local_LLM/AGENT_SPECS/pending/codex/phase_E3_structured_extraction_and_source_priority.md`
  - `/Users/youseffayyaz/Local_LLM/AGENT_SPECS/pending/codex/phase_E4_queue_ui_and_real_validation.md`
- This pack is based on the accepted live-runtime diagnosis:
  - real retrieval is already contextually meaningful
  - the critical bottleneck is weak JD completeness before provider scoring
  - the fix order is:
    1. truthful JD-readiness states
    2. selective JobSpy detail enrichment
    3. structured ATS/company extraction priority
    4. truthful queue UI plus real rerun validation
- Real-provider rule remains strict for this pack:
  - do not substitute a fake LM Studio provider unless the user explicitly approves that fallback

E1 completion status:
- Phase E1 is now complete and verified.
- New deterministic JD-quality evaluator:
  - `/Users/youseffayyaz/Local_LLM/job_agent/services/job_description_quality.py`
- Key E1 behavioral changes:
  - weak or missing job descriptions now persist as `score_source=awaiting_enrichment` instead of generic fallback
  - candidate-fit payloads now include `threshold_eligible` and `awaiting_enrichment`
  - discovery visible-after-threshold counts now exclude `threshold_eligible=false` jobs
  - job-row payloads now expose JD quality score/label/reason and stop labeling weak-JD rows as plain fallback
- E1 validation completed in `ML`:
  - `pytest tests/test_job_fetcher.py tests/test_job_fit_scoring.py tests/test_job_description_quality.py -q` → `16 passed`
  - `pytest tests/test_api.py tests/test_review_queue.py tests/test_job_enrichment_lock.py -q` → `66 passed`
  - `ruff check job_agent/services/job_description_quality.py job_agent/services/job_fetcher.py job_agent/services/job_fit_scoring.py job_agent/services/workflows.py job_agent/routers/job_views.py job_agent/routers/jobs.py tests/test_job_fetcher.py tests/test_job_fit_scoring.py tests/test_job_description_quality.py tests/test_review_queue.py` → `All checks passed.`

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

E2 completion status:
- Phase E2 is now complete and verified.
- New selective second-pass detail enrichment:
  - `job_agent/services/jobspy_service.py` → `JobSpyService.detail_enrich_survivors()`
- Key E2 behavioral changes:
  - discovery pipeline now includes a `detail_enrichment` stage after ATS discovery and before generic LinkedIn HTML fetching
  - JobSpy-origin jobs with weak JDs are selectively re-fetched with `linkedin_fetch_description=True`
  - enrichment cap is configurable via `JOBSPY_DETAIL_ENRICHMENT_LIMIT` (default: 10)
  - feature is opt-in via `JOBSPY_DETAIL_ENRICHMENT_ENABLED` (default: false)
  - survivors are selected deterministically: country → role match → seniority → weakest JD first
  - richer descriptions replace thin snippets; provenance is stamped (`jobspy_detail_enriched`, `direct_job_url`, etc.)
  - JD quality is re-evaluated after enrichment via the E1 quality evaluator
  - ATS-origin and manual jobs are excluded from the second pass
  - already-ready-for-scoring jobs are skipped
- E2 validation completed in `ML`:
  - `pytest tests/test_jobspy_scheduler.py tests/test_jobspy_service.py -q` → `22 passed`
  - `ruff check job_agent/services/jobspy_service.py job_agent/services/workflows.py job_agent/services/job_fetcher.py job_agent/config.py tests/test_jobspy_scheduler.py tests/test_jobspy_service.py` → `All checks passed.`
- Discovery pipeline order is now:
  1. JobSpy broad discovery
  2. ATS discovery
  3. Selective JobSpy detail enrichment (E2)
  4. Generic LinkedIn HTML fetch fallback
  5. Provider scoring

E3 completion status:
- Phase E3 is now complete and verified.
- New dedicated extraction service:
  - `job_agent/services/job_description_extractor.py` — full source-priority pipeline
- Dependencies added to `pyproject.toml`:
  - `extruct>=0.17,<1` — JSON-LD / Microdata / JobPosting extraction
  - `trafilatura>=2.0,<3` — main-content extraction from HTML
  - `readability-lxml>=0.8,<1` — last-resort HTML cleanup fallback
- Key E3 behavioral changes:
  - `enrich_job()` now runs the E3 extraction pipeline before LinkedIn fallback
  - extraction priority: ATS payload → direct company URL → JSON-LD → trafilatura → readability → LinkedIn HTML
  - ATS-origin jobs with strong existing descriptions are not re-fetched from weaker sources
  - provenance metadata persisted: `jd_extraction_method`, `jd_source_url`, `jd_source_kind`, `jd_last_enriched_at`
  - JD quality is always re-evaluated after extraction via E1's `evaluate_job_description()`
  - extraction failure leaves truthful unready state — no fake ready states
  - no LLM usage, no browser automation — all deterministic
- E3 validation completed in `ML`:
  - `pytest tests/test_job_description_extractor.py tests/test_job_fetcher.py tests/test_ats_scanner.py -q` → `32 passed`
  - `ruff check ... ` → `All checks passed.`
  - Broader regression: `116 passed` across E1/E2/E3 + API + quality + scheduler tests

UI stabilization follow-up:
- Manual JD intake is now queue-optional by design:
  - `frontend/templates/partials/jobs/manual_target.html`
  - `frontend/static/jobs.js`
  - `job_agent/routers/jobs.py`
- The direct analyze endpoint now returns score, matched evidence, gaps, summary, and raw text without creating a `JobPost`:
  - `POST /ui/jobs/manual-target/analyze`
- Draft preview and PDF export are now separated:
  - `/drafts/{id}/pdf-inline` for in-app / new-tab preview
  - `/drafts/{id}/pdf` for explicit download
- Queue state actions now refresh more than the row:
  - `job_group` responses include OOB updates for lane chips and the queue table shell
  - this keeps counts and empty-state copy aligned after shortlist/save/pass actions
- Jobs empty-state copy is clearer when review is empty but awaiting-enrichment has jobs.
- Draft detail no longer exposes temporary `Zone N` scaffolding in the UI.
- Focused validation completed in `ML`:
  - `pytest tests/test_review_queue.py tests/test_ui.py tests/test_ui_draft_detail.py tests/test_web_apply_flow.py tests/test_career_ops_adaptation.py -q` → `40 passed`
  - `ruff check job_agent/routers/jobs.py job_agent/routers/drafts.py job_agent/routers/draft_actions.py tests/test_review_queue.py tests/test_ui.py tests/test_ui_draft_detail.py tests/test_web_apply_flow.py tests/test_career_ops_adaptation.py` → `All checks passed.`
