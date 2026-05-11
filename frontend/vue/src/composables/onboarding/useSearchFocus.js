import { computed, ref } from "vue";

import {
  generateCandidateTracks,
  loadSearchRecommendations,
  saveSettings,
  suggestCandidateTracks,
} from "../../services/onboardingApi";
import { splitLines } from "../../utils/onboardingFormatters";
import { normalizeSearchLanguages as normalizeSearchLanguagesUtil } from "../../utils/onboardingNormalizers";

export function useSearchFocus({
  candidateId,
  currentStep,
  donePanelVisible,
  setupData,
  onboardingData,
  onComplete,
}) {
  const searchRolesText = ref("");
  const searchCountry = ref("Italy");
  const searchSeniority = ref("junior");
  const searchLanguages = ref([{ name: "English", level: "professional" }]);
  const searchLanguageOptions = ref([{ code: "en", name: "English" }]);
  const searchLevelOptions = ref([
    { value: "basic", label: "Basic" },
    { value: "working", label: "Working" },
    { value: "professional", label: "Professional" },
    { value: "fluent", label: "Fluent" },
  ]);
  const suggestedRoles = ref([]);
  const recommendedSources = ref([]);
  const recommendationsLoaded = ref(false);
  const suggestionsBusy = ref(false);
  const searchBusy = ref(false);
  const searchSaving = ref(false);
  const searchStatus = ref("");
  const searchStatusError = ref(false);
  const trackStatus = ref("");
  const searchTouched = ref({ roles: false, country: false, languages: false });

  const searchReady = computed(() =>
    Boolean(
      setupData.value?.search_ready ||
        setupData.value?.search_focus_ready ||
        onboardingData.value?.search_ready ||
        onboardingData.value?.search_focus_ready,
    ),
  );

  function setSearchStatus(message, isError = false) {
    searchStatus.value = message;
    searchStatusError.value = isError;
  }

  function markSearchRolesTouched() {
    searchTouched.value.roles = true;
  }

  function markSearchCountryTouched() {
    searchTouched.value.country = true;
  }

  function markSearchLanguagesTouched() {
    searchTouched.value.languages = true;
  }

  function searchRoleList() {
    return splitLines(searchRolesText.value).slice(0, 4);
  }

  function primarySearchCountry() {
    return splitLines(searchCountry.value)[0] || "Italy";
  }

  function normalizeSearchLanguages(rows = searchLanguages.value) {
    return normalizeSearchLanguagesUtil(rows);
  }

  function languageOptionValue(option) {
    return option?.name || option?.value || "";
  }

  function languageOptionLabel(option) {
    return option?.label || option?.name || option?.value || "";
  }

  function levelOptionValue(option) {
    return option?.value || option?.name || "";
  }

  function levelOptionLabel(option) {
    return option?.label || option?.name || option?.value || "";
  }

  function addSearchLanguage() {
    searchLanguages.value.push({ name: "English", level: "professional" });
    markSearchLanguagesTouched();
  }

  function removeSearchLanguage(index) {
    searchLanguages.value.splice(index, 1);
    if (!searchLanguages.value.length) {
      searchLanguages.value.push({ name: "English", level: "professional" });
    }
    markSearchLanguagesTouched();
  }

  function addSuggestedRole(role) {
    const cleanRole = String(role || "").trim();
    if (!cleanRole) return;

    const roles = searchRoleList();
    const duplicate = roles.some((item) => item.toLowerCase() === cleanRole.toLowerCase());
    if (duplicate || roles.length >= 4) return;

    roles.push(cleanRole);
    searchRolesText.value = roles.join("\n");
    markSearchRolesTouched();
  }

  function applySearchRecommendations(data) {
    if (Array.isArray(data?.language_options) && data.language_options.length) {
      searchLanguageOptions.value = data.language_options;
    }

    if (Array.isArray(data?.level_options) && data.level_options.length) {
      searchLevelOptions.value = data.level_options;
    }

    if (!searchTouched.value.country) {
      searchCountry.value = (Array.isArray(data?.countries) && data.countries[0]) || "Italy";
    }

    if (!searchTouched.value.roles && Array.isArray(data?.suggested_roles) && data.suggested_roles.length) {
      searchRolesText.value = data.suggested_roles.slice(0, 4).join("\n");
    }

    if (!searchTouched.value.languages) {
      searchLanguages.value = normalizeSearchLanguages(data?.selected_languages || []);
    }

    suggestedRoles.value = Array.isArray(data?.suggested_roles) ? data.suggested_roles : [];
    recommendedSources.value = Array.isArray(data?.recommended_sources) ? data.recommended_sources : [];
  }

  async function suggestRoleTracks() {
    if (!candidateId.value) return;

    suggestionsBusy.value = true;

    try {
      const data = await suggestCandidateTracks(candidateId.value);
      if (Array.isArray(data?.suggested_roles) && data.suggested_roles.length) {
        suggestedRoles.value = data.suggested_roles;
        if (!searchTouched.value.roles) {
          searchRolesText.value = data.suggested_roles.slice(0, 4).join("\n");
        }
      }
    } catch {
      // Provider failure should not block the rule-based recommendations.
    } finally {
      suggestionsBusy.value = false;
    }
  }

  async function hydrateSearchFocus(force = false) {
    if (!candidateId.value || (recommendationsLoaded.value && !force)) return;

    searchBusy.value = true;
    setSearchStatus("Loading search recommendations...");

    try {
      const data = await loadSearchRecommendations(candidateId.value);
      applySearchRecommendations(data || {});
      recommendationsLoaded.value = true;
      setSearchStatus("");
    } catch {
      recommendedSources.value = [];
      setSearchStatus("");
    } finally {
      searchBusy.value = false;
    }

    await suggestRoleTracks();
  }

  async function openSearchStep() {
    currentStep.value = "search";
    await hydrateSearchFocus();
  }

  async function generateRoleTracks(roles) {
    if (!candidateId.value || !roles.length) return;

    trackStatus.value = "Building role tracks...";

    try {
      await generateCandidateTracks(candidateId.value, roles);
      trackStatus.value = "Role tracks ready.";
    } catch {
      trackStatus.value = "Role tracks can be generated later.";
    }
  }

  async function saveSearchFocus() {
    const roles = searchRoleList();
    const country = primarySearchCountry();
    const languages = normalizeSearchLanguages();

    if (!roles.length) {
      setSearchStatus("Add at least one target role.", true);
      return;
    }

    searchSaving.value = true;
    setSearchStatus("Saving search focus...");

    try {
      await saveSettings({
        jobspy_discover_queries: roles,
        job_search_countries: [country],
        jobspy_discover_location: country,
        target_job_seniority: searchSeniority.value,
        job_search_languages: languages,
      });

      setSearchStatus("");
      donePanelVisible.value = true;
      currentStep.value = "done";
      await generateRoleTracks(roles);
      await onComplete?.();
    } catch (error) {
      setSearchStatus(error?.message || "Saving search focus failed.", true);
      currentStep.value = "search";
    } finally {
      searchSaving.value = false;
    }
  }

  return {
    searchRolesText,
    searchCountry,
    searchSeniority,
    searchLanguages,
    searchLanguageOptions,
    searchLevelOptions,
    suggestedRoles,
    recommendedSources,
    recommendationsLoaded,
    suggestionsBusy,
    searchBusy,
    searchSaving,
    searchStatus,
    searchStatusError,
    searchReady,
    trackStatus,
    markSearchRolesTouched,
    markSearchCountryTouched,
    markSearchLanguagesTouched,
    languageOptionValue,
    languageOptionLabel,
    levelOptionValue,
    levelOptionLabel,
    addSearchLanguage,
    removeSearchLanguage,
    addSuggestedRole,
    hydrateSearchFocus,
    openSearchStep,
    saveSearchFocus,
  };
}
