from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ONBOARDING_PAGE = ROOT / "frontend/vue/src/pages/OnboardingPage.vue"

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


def _source() -> str:
    return ONBOARDING_PAGE.read_text(encoding="utf-8")


def test_vue_onboarding_shell_has_five_setup_step_labels() -> None:
    source = _source()

    for label in ("AI", "Facts", "Questions", "Review", "Search"):
        assert f'label: "{label}"' in source


def test_vue_onboarding_shell_has_provider_options() -> None:
    source = _source()

    for label in ("Local Gateway", "Ollama", "OpenAI", "Claude", "Google Gemini"):
        assert f'label: "{label}"' in source


def test_vue_onboarding_facts_step_ui_exists() -> None:
    source = _source()

    assert "Build your fact sheet" in source
    assert 'type="file"' in source
    assert 'accept=".pdf,.txt,.md,.rst,application/pdf,text/plain,text/markdown"' in source
    assert "Optional manual notes" in source
    assert "Analyse my profile" in source


def test_vue_onboarding_facts_step_validates_supported_source_files() -> None:
    source = _source()

    assert "SUPPORTED_SOURCE_EXTENSIONS" in source
    assert "SUPPORTED_SOURCE_TYPES" in source
    for item in (".pdf", ".txt", ".md", ".rst", "application/pdf", "text/plain", "text/markdown"):
        assert item in source
    assert "function isSupportedSourceFile" in source


def test_vue_onboarding_facts_step_rejects_unsupported_files_before_upload() -> None:
    source = _source()

    assert "const invalidFiles = files.filter((file) => !isSupportedSourceFile(file));" in source
    assert "if (invalidFiles.length)" in source
    assert "Only PDF, TXT, MD, or RST files are accepted in onboarding intake." in source


def test_vue_onboarding_questions_step_renders_returned_question_state() -> None:
    source = _source()

    assert "Answer only what is missing" in source
    assert "normalizedQuestions" in source
    assert 'v-for="(question, questionIndex) in normalizedQuestions"' in source
    assert "questionAnswers[question.id]" in source
    assert "Save answers" in source


def test_vue_onboarding_questions_step_supports_legacy_question_types() -> None:
    source = _source()

    for question_type in ("single_select", "multi_select", "text"):
        assert question_type in source
    assert "allow_free_text" in source
    assert "selected" in source
    assert "choices" in source


def test_vue_onboarding_questions_step_validates_required_answers() -> None:
    source = _source()

    assert "function buildAnswersPayload" in source
    assert "const missingPrompts = [];" in source
    assert "question.required && !value" in source
    assert "Please answer the required questions first. Missing:" in source


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
    source = _source()

    for snippet in REVIEW_ENDPOINT_SNIPPETS:
        assert snippet in source


def test_vue_onboarding_review_step_has_readiness_banner_logic() -> None:
    source = _source()

    assert "const readinessBanner = computed" in source
    assert "Profile Readiness: Ready" in source
    assert "Profile Readiness: Needs more evidence" in source
    assert "Profile Readiness: Usable with warnings" in source


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
    source = _source()

    assert "function buildReviewedFactSheetPayload" in source
    assert "responsibilities: splitLines(row.responsibilities_text)" in source
    assert "skills: {business_tools: splitLines(form.skillsText)}" in source
    assert 'level: String(row.level || "").trim() || "professional"' in source


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
    source = _source()

    for snippet in SEARCH_ENDPOINT_SNIPPETS:
        assert snippet in source


def test_vue_onboarding_search_step_preserves_legacy_constraints() -> None:
    source = _source()

    assert "function searchRoleList" in source
    assert "splitLines(searchRolesText.value).slice(0, 4)" in source
    assert "roles.length >= 4" in source
    assert "function primarySearchCountry" in source
    assert 'splitLines(searchCountry.value)[0] || "Italy"' in source
    assert "job_search_countries: [country]" in source
    assert "jobspy_discover_location: country" in source


def test_vue_onboarding_search_language_defaults_and_dedup_exist() -> None:
    source = _source()

    assert "function normalizeSearchLanguages" in source
    assert 'level: "professional"' in source
    assert 'name: "English"' in source
    assert "item.name.toLowerCase() === name.toLowerCase()" in source
    assert "function addSearchLanguage" in source
    assert "function removeSearchLanguage" in source


def test_vue_onboarding_search_hydration_respects_user_edits() -> None:
    source = _source()

    assert "searchTouched" in source
    assert "!searchTouched.value.country" in source
    assert "!searchTouched.value.roles" in source
    assert "!searchTouched.value.languages" in source
    assert "markSearchRolesTouched" in source
    assert "markSearchCountryTouched" in source
    assert "markSearchLanguagesTouched" in source


def test_vue_onboarding_done_panel_and_track_generation_status_exist() -> None:
    source = _source()

    assert "Your workspace is ready" in source
    assert "Find jobs now" in source
    assert 'href="/ui/jobs"' in source
    assert "Continue to dashboard" in source
    assert 'href="/ui"' in source
    assert "Building role tracks..." in source
    assert "Role tracks ready." in source


def test_vue_onboarding_track_generation_failure_is_non_fatal() -> None:
    source = _source()

    assert "async function generateRoleTracks" in source
    assert "Role tracks can be generated later." in source
    assert "catch (_error)" in source


def test_vue_onboarding_shell_has_no_intro_modal_behavior_or_copy() -> None:
    source = _source()
    lowered = source.lower()

    assert "onboarding-intro-modal" not in source
    assert "Read welcome" not in source
    assert "intro" not in lowered


def test_vue_onboarding_shell_only_calls_read_only_setup_endpoints() -> None:
    source = _source()
    endpoints = set(re.findall(r'vueApiFetch\("([^"]+)"\)', source))

    assert endpoints == READ_ONLY_ENDPOINTS


def test_vue_onboarding_shell_references_provider_validation_and_save_endpoints() -> None:
    source = _source()
    endpoints = set(re.findall(r'\bapiFetch\("([^"]+)"', source))

    assert PROVIDER_ENDPOINTS <= endpoints


def test_vue_onboarding_facts_step_references_candidate_upload_and_intake_endpoints() -> None:
    source = _source()

    for snippet in FACTS_ENDPOINT_SNIPPETS:
        assert snippet in source


def test_vue_onboarding_questions_step_references_answer_endpoint() -> None:
    source = _source()

    for snippet in QUESTIONS_ENDPOINT_SNIPPETS:
        assert snippet in source


def test_vue_onboarding_shell_does_not_store_api_keys_or_use_inline_handlers() -> None:
    source = _source()
    lowered = source.lower()

    assert "localStorage" not in source
    assert "sessionStorage" not in source
    assert "onclick" not in lowered


def test_vue_onboarding_facts_upload_uses_formdata_without_json_content_type() -> None:
    source = _source()
    upload_index = source.index("/sources/upload")
    fetch_start = source.rfind("legacyFetchJson(", 0, upload_index)
    fetch_end = source.index(");", upload_index)
    upload_call = source[fetch_start:fetch_end]

    assert "new FormData()" in source
    assert 'uploadData.append("replace_existing", "1")' in source
    assert "body: uploadData" in upload_call
    assert '"Content-Type": "application/json"' not in upload_call


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
