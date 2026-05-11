from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

ONBOARDING_FILES = (
    "frontend/vue/src/pages/OnboardingPage.vue",
    "frontend/vue/src/components/onboarding/OnboardingStepCards.vue",
    "frontend/vue/src/components/onboarding/OnboardingStatusCard.vue",
    "frontend/vue/src/components/onboarding/OnboardingDonePanel.vue",
    "frontend/vue/src/components/onboarding/ProviderStep.vue",
    "frontend/vue/src/components/onboarding/FactsStep.vue",
    "frontend/vue/src/components/onboarding/QuestionsStep.vue",
    "frontend/vue/src/components/onboarding/ReviewStep.vue",
    "frontend/vue/src/components/onboarding/SearchStep.vue",
    "frontend/vue/src/components/onboarding/StatusMessage.vue",
    "frontend/vue/src/composables/onboarding/useOnboardingState.js",
    "frontend/vue/src/composables/onboarding/useProviderSetup.js",
    "frontend/vue/src/composables/onboarding/useFactsIntake.js",
    "frontend/vue/src/composables/onboarding/useQuestionIntake.js",
    "frontend/vue/src/composables/onboarding/useProfileReview.js",
    "frontend/vue/src/composables/onboarding/useSearchFocus.js",
    "frontend/vue/src/services/onboardingApi.js",
    "frontend/vue/src/utils/onboardingFormatters.js",
    "frontend/vue/src/utils/onboardingNormalizers.js",
)

READ_ONLY_ENDPOINTS = {
    "/onboarding/state",
    "/onboarding/steps",
    "/setup/state",
}

PROVIDER_ENDPOINTS = {
    "/providers/validate",
    "/settings/save",
}

FACTS_ENDPOINT_SNIPPETS = (
    "/candidates/ensure-owner",
    "/sources/upload",
    "/intake/start",
)

QUESTIONS_ENDPOINT_SNIPPETS = (
    "/intake/answer",
)

REVIEW_ENDPOINT_SNIPPETS = (
    "/onboarding-review",
    "/fact-sheet-json",
)

SEARCH_ENDPOINT_SNIPPETS = (
    "/search/preferences/recommendations",
    "suggest-tracks",
    "generate-tracks",
)


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _source() -> str:
    return "\n".join(_read(path) for path in ONBOARDING_FILES)


def _service_source() -> str:
    return _read("frontend/vue/src/services/onboardingApi.js")


def _component(name: str) -> str:
    return _read(f"frontend/vue/src/components/onboarding/{name}")


def _composable(name: str) -> str:
    return _read(f"frontend/vue/src/composables/onboarding/{name}")


def test_vue_onboarding_shell_has_five_setup_step_labels() -> None:
    source = _source()

    for label in ("AI", "Facts", "Questions", "Review", "Search"):
        assert f'label: "{label}"' in source


def test_vue_onboarding_primary_action_labels_match_migrated_flow() -> None:
    assert "Validate & Continue" in _component("ProviderStep.vue")
    assert "Analyse my profile" in _component("FactsStep.vue")
    assert "Save answers" in _component("QuestionsStep.vue")
    assert "Save profile review" in _component("ReviewStep.vue")
    assert "Finish setup" in _component("SearchStep.vue")


def test_vue_onboarding_shell_has_provider_options() -> None:
    source = _source()

    for label in ("Local Gateway", "Ollama", "OpenAI", "Claude", "Google Gemini"):
        assert f'label: "{label}"' in source


def test_vue_provider_step_validates_and_saves_like_legacy_controller() -> None:
    provider = _composable("useProviderSetup.js")
    component = _component("ProviderStep.vue")
    legacy = _read("frontend/static/provider_controller.js")

    assert '@click="provider.validateAndSaveProvider"' in component
    assert 'validateProvider(buildValidationPayload())' in provider
    assert 'apiFetch("/providers/validate"' in _service_source()
    assert "provider_mode" in provider
    assert "provider_mode" in legacy
    assert "provider: selectedProvider.value" not in provider
    assert "llm_provider_mode" in provider
    assert "use_openai_review" in provider
    assert "use_claude_final_review" in provider
    assert 'apiFetch("/settings/save"' in _service_source()
    assert 'currentStep.value = "facts"' in provider


def test_vue_provider_step_preserves_local_model_save_shape() -> None:
    provider = _composable("useProviderSetup.js")

    for field in (
        "lm_studio_small_model",
        "lm_studio_writer_model",
        "lm_studio_mid_model",
        "ollama_fast_model",
        "ollama_writer_model",
    ):
        assert field in provider
    assert "nonEmbeddingModels" in provider
    assert "No usable LM Studio chat model was found." in provider
    assert "No usable Ollama chat model was found." in provider


def test_vue_onboarding_facts_step_ui_exists() -> None:
    source = _source()

    assert "Build your fact sheet" in source
    assert 'type="file"' in source
    assert 'accept=".pdf,.txt,.md,.rst,application/pdf,text/plain,text/markdown"' in source
    assert "Optional manual notes" in source
    assert "Analyse my profile" in source


def test_vue_onboarding_facts_step_validates_supported_source_files() -> None:
    facts = _composable("useFactsIntake.js")

    assert "SUPPORTED_SOURCE_EXTENSIONS" in facts
    assert "SUPPORTED_SOURCE_TYPES" in facts
    for item in (".pdf", ".txt", ".md", ".rst", "application/pdf", "text/plain", "text/markdown"):
        assert item in facts
    assert "function isSupportedSourceFile" in facts


def test_vue_onboarding_facts_step_rejects_unsupported_files_before_upload() -> None:
    facts = _composable("useFactsIntake.js")

    assert "const invalidFiles = files.filter((file) => !isSupportedSourceFile(file));" in facts
    assert "if (invalidFiles.length)" in facts
    assert "Only PDF, TXT, MD, or RST files are accepted in onboarding intake." in facts


def test_vue_onboarding_facts_step_uses_legacy_candidate_upload_and_intake_contracts() -> None:
    facts = _composable("useFactsIntake.js")
    service = _service_source()

    for snippet in FACTS_ENDPOINT_SNIPPETS:
        assert snippet in service

    assert '@click="facts.runFactsIntake"' in _component("FactsStep.vue")
    assert "ensureCandidateShellApi()" in facts
    assert "new FormData()" in facts
    assert 'uploadData.append("replace_existing", "1")' in facts
    assert 'uploadData.append("files", file)' in facts
    assert 'credentials: "same-origin"' in service
    assert 'headers: { "Content-Type": "application/x-www-form-urlencoded" }' in service
    assert "new URLSearchParams({ profile_notes: notes })" in service
    assert 'currentStep.value = "questions"' in facts
    assert "await openReviewStep()" in facts


def test_vue_onboarding_facts_upload_uses_formdata_without_json_content_type() -> None:
    service = _service_source()
    upload_start = service.index("export function uploadCandidateSources")
    upload_end = service.index("export function startCandidateIntake")
    upload_function = service[upload_start:upload_end]

    assert "legacyFetchJson(" in upload_function
    assert "body: formData" in upload_function
    assert "Content-Type" not in upload_function


def test_vue_onboarding_questions_step_renders_returned_question_state() -> None:
    source = _source()

    assert "Answer only what is missing" in source
    assert "normalizedQuestions" in source
    assert 'v-for="(question, questionIndex) in questions.normalizedQuestions.value"' in source
    assert "questions.questionAnswers.value[question.id]" in source
    assert "Save answers" in source


def test_vue_onboarding_questions_step_supports_legacy_question_types() -> None:
    source = _source()

    for question_type in ("single_select", "multi_select", "text"):
        assert question_type in source
    assert "allow_free_text" in source
    assert "selected" in source
    assert "choices" in source


def test_vue_onboarding_questions_step_validates_required_answers() -> None:
    questions = _composable("useQuestionIntake.js")

    assert "function buildAnswersPayload" in questions
    assert "const missingPrompts = [];" in questions
    assert "question.required && !value" in questions
    assert "Please answer the required questions first. Missing:" in questions


def test_vue_onboarding_questions_step_submits_answers_and_opens_review_like_legacy() -> None:
    questions = _composable("useQuestionIntake.js")
    service = _service_source()

    for snippet in QUESTIONS_ENDPOINT_SNIPPETS:
        assert snippet in service

    assert '@click="questions.submitQuestionAnswers"' in _component("QuestionsStep.vue")
    assert "answerCandidateIntake(candidateId.value, answers)" in questions
    assert "body: JSON.stringify({ answers })" in service
    assert 'currentStep.value = "questions"' in questions
    assert "More detail is still needed. Answer the updated questions below." in questions
    assert "await openReviewStep()" in questions
    assert "questionsAnswered.value = true;" not in questions


def test_vue_onboarding_review_step_ui_exists() -> None:
    source = _source()

    assert "Review your extracted profile" in source
    assert "Save profile review" in source
    assert "Identity" in source
    assert "Education" in source
    assert "Experience" in source
    assert "Projects and evidence" in source
    assert "Skills and languages" in source


def test_vue_onboarding_review_step_references_review_endpoints() -> None:
    service = _service_source()

    for snippet in REVIEW_ENDPOINT_SNIPPETS:
        assert snippet in service


def test_vue_onboarding_review_step_has_readiness_banner_logic() -> None:
    review = _composable("useProfileReview.js")

    assert "const readinessBanner = computed" in review
    assert "Profile Readiness: Ready" in review
    assert "Profile Readiness: Needs more evidence" in review
    assert "Profile Readiness: Usable with warnings" in review


def test_vue_onboarding_review_step_has_add_remove_row_behavior() -> None:
    source = _source()

    assert "function addReviewRow" in source
    assert "function removeReviewRow" in source
    assert "function addReviewLanguage" in source
    assert "function removeReviewLanguage" in source
    for section in ("education", "experience", "projects"):
        assert f"addReviewRow('{section}')" in source
        assert f"removeReviewRow('{section}', index)" in source


def test_vue_onboarding_review_step_preserves_legacy_save_shape() -> None:
    review = _composable("useProfileReview.js")
    service = _service_source()

    assert "function buildReviewedFactSheetPayload" in review
    assert "responsibilities: splitLines(row.responsibilities_text)" in review
    assert "skills: { business_tools: splitLines(form.skillsText) }" in review
    assert 'level: String(row.level || "").trim() || "professional"' in review
    assert "body: JSON.stringify(payload)" in service
    assert "await openSearchStep()" in review


def test_vue_onboarding_search_step_ui_exists() -> None:
    source = _source()

    assert "Choose your search focus" in source
    assert "Target roles, one per line" in source
    assert "Detected role suggestions" in source
    assert "Target country" in source
    assert "Seniority" in source
    assert "Job description languages" in source
    assert "Discovery hints" in source
    assert "Finish setup" in source


def test_vue_onboarding_search_step_references_search_and_track_endpoints() -> None:
    service = _service_source()

    for snippet in SEARCH_ENDPOINT_SNIPPETS:
        assert snippet in service


def test_vue_onboarding_search_step_preserves_legacy_constraints() -> None:
    search = _composable("useSearchFocus.js")

    assert "function searchRoleList" in search
    assert "splitLines(searchRolesText.value).slice(0, 4)" in search
    assert "roles.length >= 4" in search
    assert "function primarySearchCountry" in search
    assert 'splitLines(searchCountry.value)[0] || "Italy"' in search
    assert "job_search_countries: [country]" in search
    assert "jobspy_discover_location: country" in search


def test_vue_onboarding_search_language_defaults_and_dedup_exist() -> None:
    source = _source()

    assert "function normalizeSearchLanguages" in source
    assert 'level: "professional"' in source
    assert 'name: "English"' in source
    assert "item.name.toLowerCase() === name.toLowerCase()" in source
    assert "function addSearchLanguage" in source
    assert "function removeSearchLanguage" in source


def test_vue_onboarding_search_hydration_respects_user_edits() -> None:
    search = _composable("useSearchFocus.js")

    assert "searchTouched" in search
    assert "!searchTouched.value.country" in search
    assert "!searchTouched.value.roles" in search
    assert "!searchTouched.value.languages" in search
    assert "markSearchRolesTouched" in search
    assert "markSearchCountryTouched" in search
    assert "markSearchLanguagesTouched" in search


def test_vue_onboarding_search_save_finishes_and_track_generation_is_non_fatal() -> None:
    search = _composable("useSearchFocus.js")
    service = _service_source()

    assert '@click="search.saveSearchFocus"' in _component("SearchStep.vue")
    assert 'apiFetch("/settings/save"' in service
    assert "jobspy_discover_queries: roles" in search
    assert "job_search_countries: [country]" in search
    assert "target_job_seniority: searchSeniority.value" in search
    assert "job_search_languages: languages" in search
    assert 'currentStep.value = "done"' in search
    assert "donePanelVisible.value = true" in search
    assert "async function generateRoleTracks" in search
    assert "Role tracks can be generated later." in search


def test_vue_onboarding_done_panel_and_track_generation_status_exist() -> None:
    source = _source()

    assert "Your workspace is ready" in source
    assert "Find jobs now" in source
    assert 'href="/ui/jobs"' in source
    assert "Continue to dashboard" in source
    assert 'href="/ui"' in source
    assert "Building role tracks..." in source
    assert "Role tracks ready." in source


def test_vue_onboarding_shell_has_no_intro_modal_behavior_or_copy() -> None:
    source = _source()
    lowered = source.lower()

    assert "onboarding-intro-modal" not in source
    assert "Read welcome" not in source
    assert "intro" not in lowered


def test_vue_onboarding_shell_only_calls_read_only_setup_endpoints() -> None:
    endpoints = set(re.findall(r'vueApiFetch\("([^"]+)"\)', _service_source()))

    assert endpoints == READ_ONLY_ENDPOINTS


def test_vue_onboarding_shell_references_provider_validation_and_save_endpoints() -> None:
    endpoints = set(re.findall(r'\bapiFetch\("([^"]+)"', _service_source()))

    assert PROVIDER_ENDPOINTS <= endpoints


def test_vue_onboarding_shell_does_not_store_sensitive_flow_data_or_use_inline_handlers() -> None:
    source = _source()
    lowered = source.lower()

    assert "localStorage" not in source
    assert "sessionStorage" not in source
    assert "onclick" not in lowered


def test_vue_onboarding_unknown_step_placeholder_remains_for_safety() -> None:
    source = _source()

    assert "This Vue step is still read-only during the migration." in source


def test_vue_onboarding_shell_links_to_legacy_onboarding_fallback() -> None:
    source = _source()

    assert 'href="/ui/onboarding"' in source


def test_legacy_onboarding_page_still_serves_html(client) -> None:
    response = client.get("/ui/onboarding")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
