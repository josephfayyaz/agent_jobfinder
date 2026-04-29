# Test Handoff

Last updated: 2026-04-29

Current phase:
- Search-role recommendation testing after onboarding

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
