# Graph Report - .  (2026-04-16)

## Corpus Check
- 69 files · ~88,360 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1005 nodes · 4152 edges · 61 communities detected
- Extraction: 32% EXTRACTED · 68% INFERRED · 0% AMBIGUOUS · INFERRED: 2810 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]

## God Nodes (most connected - your core abstractions)
1. `JobPost` - 140 edges
2. `ResumeTrack` - 123 edges
3. `JobTrackScore` - 100 edges
4. `CVWorkflowService` - 99 edges
5. `JobFetcher` - 80 edges
6. `ResumeDraft` - 77 edges
7. `ThesisTarget` - 72 edges
8. `ThesisOutreachService` - 70 edges
9. `GmailService` - 68 edges
10. `FactSheetJsonIngestionService` - 68 edges

## Surprising Connections (you probably didn't know these)
- `Tests for the CV workflow service.` --uses--> `CVWorkflowService`  [INFERRED]
  /Users/youseffayyaz/Local_LLM/tests/test_workflows.py → job_agent/services/workflows.py
- `queue_cv_workflow creates a WorkflowTask with status=pending.` --uses--> `CVWorkflowService`  [INFERRED]
  /Users/youseffayyaz/Local_LLM/tests/test_workflows.py → job_agent/services/workflows.py
- `process_next_task picks up the pending task and runs it.` --uses--> `CVWorkflowService`  [INFERRED]
  /Users/youseffayyaz/Local_LLM/tests/test_workflows.py → job_agent/services/workflows.py
- `process_next_task sets status=failed if run_cv_workflow raises.` --uses--> `CVWorkflowService`  [INFERRED]
  /Users/youseffayyaz/Local_LLM/tests/test_workflows.py → job_agent/services/workflows.py
- `Full pipeline: mocked writer/reviewer responses still create a ResumeDraft.` --uses--> `CVWorkflowService`  [INFERRED]
  /Users/youseffayyaz/Local_LLM/tests/test_workflows.py → job_agent/services/workflows.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.04
Nodes (128): BaseSettings, CareerPageScanner, _extract_title_from_link(), _looks_like_job_url(), Scanner for Italian company career pages — discovers new job postings., Scans active career page sources and creates JobPost records for new listings., Scan all active CareerPageSource records.         Returns total number of new Jo, Fetch one career page and extract job links.         Returns count of new JobPos (+120 more)

### Community 1 - "Community 1"
Cohesion: 0.04
Nodes (73): Base, AttrDict, Shared pytest fixtures., A minimal resume track object (plain dict, not ORM)., Dict with attribute access for tests that use dot notation., A pending WorkflowTask linked to a job and a track slug., sample_job(), sample_track() (+65 more)

### Community 2 - "Community 2"
Cohesion: 0.03
Nodes (36): accept_inferred_additions(), answer_candidate_intake(), _append_unique(), apply_enhancements(), _blank_to_none(), _build_job_ui_payload(), create_career_page(), _default_jobspy_query() (+28 more)

### Community 3 - "Community 3"
Cohesion: 0.36
Nodes (83): BaseModel, CsvExportService, FactSheetIntakeService, UploadedFile, LLMRouter, Routes generation requests to the appropriate backend.      Usage:         route, JobDiscoverRequest, List job posts.     By default, only shows jobs with max track score >= MATCH_MI (+75 more)

### Community 4 - "Community 4"
Cohesion: 0.08
Nodes (57): _create_application(), _create_draft(), _create_outreach_draft(), _create_target(), jresp(), _patch_uuid_session_get(), Pretty-print response JSON on assertion failure., test_add_and_list_application_communications() (+49 more)

### Community 5 - "Community 5"
Cohesion: 0.08
Nodes (26): build_cover_letter_user_prompt(), build_enhancement_prompt(), build_reviewer_user_prompt(), build_revision_prompt(), build_thesis_outreach_user_prompt(), build_thesis_revision_prompt(), build_writer_user_prompt(), _format_draft_experiences() (+18 more)

### Community 6 - "Community 6"
Cohesion: 0.19
Nodes (25): _as_string_list(), _best_bullets_for_track(), _bullet_count_for_mode(), _experience_bullets(), _experience_keywords(), _experience_org(), _experience_start_date(), _experience_title() (+17 more)

### Community 7 - "Community 7"
Cohesion: 0.17
Nodes (1): CVWorkflowService

### Community 8 - "Community 8"
Cohesion: 0.08
Nodes (19): Tests for job-to-track matching algorithm., Senior in job title reduces score when target_seniority=junior., A job with zero keyword matches should score below 30., Job requiring 5+ years penalized when target_seniority=junior., Intern/junior in title boosts score when target_seniority=junior., target_seniority=any disables all seniority adjustments., A clearly relevant job should score above the 60 revise threshold., matched_keywords should list which track keywords appeared in the job. (+11 more)

### Community 9 - "Community 9"
Cohesion: 0.21
Nodes (23): _bullets(), _confidence_lines(), _field(), _join_location(), _list_block(), _location_preferences_lines(), _minor_join(), _render_change_log() (+15 more)

### Community 10 - "Community 10"
Cohesion: 0.17
Nodes (1): FactSheetJsonIngestionService

### Community 11 - "Community 11"
Cohesion: 0.16
Nodes (7): _FakeQuery, _FakeSession, _matches_condition(), Tests for thesis target CRUD helpers and outreach approval flow., test_approve_outreach_draft_updates_parent_target(), test_archive_thesis_target_sets_archived_status(), test_create_and_update_thesis_target()

### Community 12 - "Community 12"
Cohesion: 0.15
Nodes (6): _FakeQuery, _FakeRouter, _FakeSession, Tests for thesis outreach prompt building and draft lifecycle., test_generate_email_creates_outreach_draft(), test_revise_and_mark_sent_updates_history()

### Community 13 - "Community 13"
Cohesion: 0.15
Nodes (17): extract_prompt_section(), load_fact_sheet_resource(), load_fact_sheet_schema(), load_prompt_pack(), load_render_template(), load_renderer_prompt(), load_renderer_spec(), load_tool_definitions() (+9 more)

### Community 14 - "Community 14"
Cohesion: 0.14
Nodes (0): 

### Community 15 - "Community 15"
Cohesion: 0.3
Nodes (9): _build_answer_prompt(), _build_intake_system_prompt(), _build_intake_user_prompt(), _canonical_minimal_fact_sheet(), _ensure_candidate(), IntakeResult, _parse_llm_response(), _safe_extract_text() (+1 more)

### Community 16 - "Community 16"
Cohesion: 0.24
Nodes (11): _extract_from_description(), find_company_url(), _is_allowed_domain(), Autonomous company website URL discovery., Fast regex pass over job description to find any company-domain URL.     Useful, Use Clearbit's Name-to-Domain API.     Returns domain as https://company.com or, Auto-discover a company's official website URL.      Priority:     1. DuckDuckGo, Return True if the URL is a company site, not a job board or aggregator. (+3 more)

### Community 17 - "Community 17"
Cohesion: 0.18
Nodes (0): 

### Community 18 - "Community 18"
Cohesion: 0.25
Nodes (10): _mock_session(), Tests for one-iteration worker behavior., Worker triggers GmailService.sync_jobs when interval has elapsed., Worker does NOT call GmailService when gmail_auto_sync=false., Worker calls JobFetcher.enrich_pending_parallel after enrichment interval elapse, Worker uses scan_all_parallel() and not scan_all() for career scans., test_worker_calls_enrich_after_interval(), test_worker_calls_gmail_sync_after_interval() (+2 more)

### Community 19 - "Community 19"
Cohesion: 0.51
Nodes (9): _make_exp(), _make_job(), test_bullet_selection_scores_against_job_keywords(), test_roles_returned_in_chronological_order_for_display(), test_select_bullets_keeps_2_to_3_for_junior_mode(), test_select_bullets_keeps_3_to_4_for_senior_mode(), test_select_experiences_drops_at_most_one_role_per_job(), test_select_experiences_for_job_preserves_minimum_three_roles() (+1 more)

### Community 20 - "Community 20"
Cohesion: 0.4
Nodes (9): jresp(), _load_real_fact_sheet_or_skip(), _profile_payload(), Pretty-print response JSON on assertion failure., test_fact_sources_latest_returns_404_initially(), test_ingest_fact_source_creates_profile(), test_ingest_fact_source_idempotent(), test_put_profile_creates_profile() (+1 more)

### Community 21 - "Community 21"
Cohesion: 0.29
Nodes (9): check_pdflatex(), compile_pdf(), ensure_artifacts_dir(), _find_pdflatex(), latex_escape(), Return the first available pdflatex binary path, or raise if none found., Check if pdflatex is available on the system.     Returns (available: bool, path, Compile a .tex file to .pdf and return the PDF path. (+1 more)

### Community 22 - "Community 22"
Cohesion: 0.22
Nodes (3): Tests for prompt builders — check structure and key content., Profile data must be formatted as readable text, not Python dict repr., test_writer_user_prompt_no_raw_dict_repr()

### Community 23 - "Community 23"
Cohesion: 0.25
Nodes (3): _FakeDataFrame, test_discover_deduplicates_existing_url(), test_discover_skips_when_disabled()

### Community 24 - "Community 24"
Cohesion: 0.22
Nodes (1): Tests for job_agent/seed.py — resume-track and job-source seeding.

### Community 25 - "Community 25"
Cohesion: 0.44
Nodes (7): as_list(), collapse_value(), parse_fact_sheet(), parse_key_value_block(), sanitize_list(), sanitize_text(), split_item_blocks()

### Community 26 - "Community 26"
Cohesion: 0.25
Nodes (2): When DuckDuckGo fails, falls back to description regex., test_find_company_url_description_fallback()

### Community 27 - "Community 27"
Cohesion: 0.29
Nodes (2): _SessionContext, test_jobs_list_runs()

### Community 28 - "Community 28"
Cohesion: 0.54
Nodes (7): _apply_seniority_adjustment(), _compute_keyword_score(), _cosine_similarity(), _get_embedding(), _job_value(), score_semantic(), score_tracks_for_job()

### Community 29 - "Community 29"
Cohesion: 0.43
Nodes (7): extract_text_auto(), extract_text_from_docx(), extract_text_from_html(), extract_text_from_pdf(), extract_text_from_txt(), UnsupportedFileType, ValueError

### Community 30 - "Community 30"
Cohesion: 0.29
Nodes (0): 

### Community 31 - "Community 31"
Cohesion: 0.29
Nodes (0): 

### Community 32 - "Community 32"
Cohesion: 0.29
Nodes (6): Dashboard config section includes target_seniority., new_24h count increments when a new job is added., GET /dashboard returns all expected top-level keys., test_dashboard_config_has_seniority(), test_dashboard_jobs_new_24h_counts_correctly(), test_dashboard_returns_expected_keys()

### Community 33 - "Community 33"
Cohesion: 0.29
Nodes (0): 

### Community 34 - "Community 34"
Cohesion: 0.29
Nodes (0): 

### Community 35 - "Community 35"
Cohesion: 0.29
Nodes (0): 

### Community 36 - "Community 36"
Cohesion: 0.71
Nodes (6): _create_job(), _fake_render_resume(), _ingest_profile(), test_full_pipeline_job_to_approved_cv(), test_pipeline_low_score_uses_heuristic_rewrite(), test_pipeline_revises_on_low_score()

### Community 37 - "Community 37"
Cohesion: 0.33
Nodes (0): 

### Community 38 - "Community 38"
Cohesion: 0.33
Nodes (0): 

### Community 39 - "Community 39"
Cohesion: 0.53
Nodes (5): _patch_uuid_session_get(), test_create_job_auto_resolves_company_url_when_missing(), test_resolve_company_url_endpoint_sets_company_url(), test_resolve_company_url_endpoint_skips_when_already_set(), _track_score_payload()

### Community 40 - "Community 40"
Cohesion: 0.33
Nodes (5): Tests for LaTeX rendering., render_resume_tex should create a .tex file with content., Special LaTeX characters in content should be escaped., test_render_creates_tex_file(), test_render_escapes_special_chars()

### Community 41 - "Community 41"
Cohesion: 0.4
Nodes (0): 

### Community 42 - "Community 42"
Cohesion: 0.4
Nodes (1): Tests for Gmail LinkedIn alert ingestion helpers.

### Community 43 - "Community 43"
Cohesion: 0.4
Nodes (0): 

### Community 44 - "Community 44"
Cohesion: 0.4
Nodes (0): 

### Community 45 - "Community 45"
Cohesion: 0.4
Nodes (2): Fallback outreach email when the LLM returns an empty body., Generate and store a new outreach draft for a thesis target.

### Community 46 - "Community 46"
Cohesion: 0.5
Nodes (3): get_settings(), Application settings — loaded from .env (or environment variables).  All behavio, Compatibility helper for services and tests that need the singleton settings.

### Community 47 - "Community 47"
Cohesion: 0.5
Nodes (1): Service layer for workflows and document rendering.

### Community 48 - "Community 48"
Cohesion: 1.0
Nodes (2): main(), _run_one_iteration()

### Community 49 - "Community 49"
Cohesion: 0.67
Nodes (1): Return current provider configuration and reachability.

### Community 50 - "Community 50"
Cohesion: 1.0
Nodes (2): seed_career_pages(), seed_reference_data()

### Community 51 - "Community 51"
Cohesion: 1.0
Nodes (0): 

### Community 52 - "Community 52"
Cohesion: 1.0
Nodes (0): 

### Community 53 - "Community 53"
Cohesion: 1.0
Nodes (0): 

### Community 54 - "Community 54"
Cohesion: 1.0
Nodes (1): Compatibility helper for services and tests that need the singleton settings.

### Community 55 - "Community 55"
Cohesion: 1.0
Nodes (1): When DuckDuckGo fails, falls back to description regex.

### Community 56 - "Community 56"
Cohesion: 1.0
Nodes (1): Return True if the URL is a company site, not a job board or aggregator.

### Community 57 - "Community 57"
Cohesion: 1.0
Nodes (1): Search DuckDuckGo for the company's official website.     Returns the first non-

### Community 58 - "Community 58"
Cohesion: 1.0
Nodes (1): Fast regex pass over job description to find any company-domain URL.     Useful

### Community 59 - "Community 59"
Cohesion: 1.0
Nodes (1): Use Clearbit's Name-to-Domain API.     Returns domain as https://company.com or

### Community 60 - "Community 60"
Cohesion: 1.0
Nodes (1): Auto-discover a company's official website URL.      Priority:     1. DuckDuckGo

## Knowledge Gaps
- **74 isolated node(s):** `Tests for prompt builders — check structure and key content.`, `Profile data must be formatted as readable text, not Python dict repr.`, `Tests for one-iteration worker behavior.`, `Worker triggers GmailService.sync_jobs when interval has elapsed.`, `Worker does NOT call GmailService when gmail_auto_sync=false.` (+69 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 51`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 52`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 53`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 54`** (1 nodes): `Compatibility helper for services and tests that need the singleton settings.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 55`** (1 nodes): `When DuckDuckGo fails, falls back to description regex.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 56`** (1 nodes): `Return True if the URL is a company site, not a job board or aggregator.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 57`** (1 nodes): `Search DuckDuckGo for the company's official website.     Returns the first non-`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 58`** (1 nodes): `Fast regex pass over job description to find any company-domain URL.     Useful`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 59`** (1 nodes): `Use Clearbit's Name-to-Domain API.     Returns domain as https://company.com or`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 60`** (1 nodes): `Auto-discover a company's official website URL.      Priority:     1. DuckDuckGo`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `JobDiscoverRequest` connect `Community 3` to `Community 0`, `Community 1`, `Community 2`, `Community 7`, `Community 10`?**
  _High betweenness centrality (0.099) - this node is a cross-community bridge._
- **Why does `Pretty-print response JSON on assertion failure.` connect `Community 4` to `Community 0`, `Community 1`, `Community 3`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Are the 138 inferred relationships involving `JobPost` (e.g. with `Parallel scan produces the same result as sequential scan.` and `Parallel scan does not insert duplicate URLs.`) actually correct?**
  _`JobPost` has 138 INFERRED edges - model-reasoned connections that need verification._
- **Are the 121 inferred relationships involving `ResumeTrack` (e.g. with `Tests for job_agent/seed.py — resume-track and job-source seeding.` and `JobDiscoverRequest`) actually correct?**
  _`ResumeTrack` has 121 INFERRED edges - model-reasoned connections that need verification._
- **Are the 98 inferred relationships involving `JobTrackScore` (e.g. with `Pretty-print response JSON on assertion failure.` and `JobDiscoverRequest`) actually correct?**
  _`JobTrackScore` has 98 INFERRED edges - model-reasoned connections that need verification._
- **Are the 74 inferred relationships involving `CVWorkflowService` (e.g. with `JobDiscoverRequest` and `Daily status summary for the current state of the job search.     Shared by the`) actually correct?**
  _`CVWorkflowService` has 74 INFERRED edges - model-reasoned connections that need verification._
- **Are the 73 inferred relationships involving `JobFetcher` (e.g. with `Parallel scan produces the same result as sequential scan.` and `Parallel scan does not insert duplicate URLs.`) actually correct?**
  _`JobFetcher` has 73 INFERRED edges - model-reasoned connections that need verification._