import { computed, reactive, ref } from "vue";

import {
  connectGmailOAuth,
  disconnectGmailOAuth,
  fetchSearchRecommendations,
  reloadSettings,
  runWorkspaceAction,
  saveSettings,
} from "../../api/settingsApi";
import { useSettingsData } from "./useSettingsData";
import {
  buildCvPayload,
  buildGmailPayload,
  buildSearchPayload,
  normalizeLanguageRows,
  primaryCountry,
  roleLines,
  validateMaintenancePhrase,
} from "./workspaceHelpers";

export function useWorkspaceSettings() {
  const { settingsLoading, settingsError, loadSettings } = useSettingsData();
  const searchSaving = ref(false);
  const gmailSaving = ref(false);
  const cvSaving = ref(false);
  const maintenanceBusy = ref(false);
  const suggestionsLoading = ref(false);
  const languageOptions = ref([]);
  const languageLevelOptions = ref([]);
  const activeCandidateId = ref("");

  const searchStatus = reactive({ message: "", tone: "neutral" });
  const gmailStatus = reactive({ message: "", tone: "neutral" });
  const cvStatus = reactive({ message: "", tone: "neutral" });
  const maintenanceStatus = reactive({ message: "", tone: "neutral" });
  const resetStatus = reactive({ message: "", tone: "neutral" });
  const deleteStatus = reactive({ message: "", tone: "neutral" });

  const search = reactive({
    targetSeniority: "junior",
    useJobspy: false,
    jobspyDiscoverLocation: "Italy",
    countriesText: "Italy",
    rolesText: "",
    languages: [{ name: "English", level: "professional" }],
    matchMinScore: 0,
    discoveryMinFitScore: 0,
    discoveryMaxVisibleJobs: 0,
  });
  const gmail = reactive({
    labelFilter: "LinkedIn Jobs",
    autoSync: false,
    clientId: "",
    clientSecret: "",
    oauthConfigured: false,
    connected: false,
    legacyConfigured: false,
  });
  const cv = reactive({
    cvPassScore: 0,
    cvReviseScore: 0,
    bulletClarifyWordLimit: 0,
  });
  const maintenance = reactive({
    shareUrl: "",
    resetPhrase: "START OVER",
    deletePhrase: "DELETE MY DATA",
    resetInput: "",
    deleteInput: "",
    openBackups: false,
    backupCount: 0,
  });

  const roleCount = computed(() => roleLines(search.rolesText).length);
  const roleLimitExceeded = computed(() => roleCount.value > 4);

  function setStatus(target, message, tone = "neutral") {
    target.message = message;
    target.tone = tone;
  }

  function hydrateWorkspaceSettings(payload) {
    const data = payload?.data || {};
    const searchData = data.search || {};
    const gmailData = data.gmail || {};
    const cvData = data.cv || {};
    const discoveryData = data.discovery || {};
    const maintenanceData = data.maintenance || {};

    languageOptions.value = Array.isArray(data.language_options) ? data.language_options : [];
    languageLevelOptions.value = Array.isArray(data.language_level_options) ? data.language_level_options : [];
    activeCandidateId.value = data.active_candidate_id || "";

    search.targetSeniority = searchData.target_job_seniority || "junior";
    search.useJobspy = Boolean(searchData.use_jobspy);
    search.rolesText = Array.isArray(searchData.jobspy_discover_queries)
      ? searchData.jobspy_discover_queries.join("\n")
      : "";
    search.countriesText = Array.isArray(searchData.job_search_countries) && searchData.job_search_countries.length
      ? searchData.job_search_countries.join("\n")
      : "Italy";
    search.jobspyDiscoverLocation = searchData.jobspy_discover_location || primaryCountry(search.countriesText);
    search.languages = normalizeLanguageRows(searchData.job_search_languages);
    search.matchMinScore = discoveryData.match_min_score ?? 0;
    search.discoveryMinFitScore = discoveryData.discovery_min_fit_score ?? 0;
    search.discoveryMaxVisibleJobs = discoveryData.discovery_max_visible_jobs ?? 0;

    gmail.labelFilter = gmailData.gmail_label_filter || "LinkedIn Jobs";
    gmail.autoSync = Boolean(gmailData.gmail_auto_sync);
    gmail.oauthConfigured = Boolean(gmailData.gmail_oauth_configured);
    gmail.connected = Boolean(gmailData.gmail_connected);
    gmail.legacyConfigured = Boolean(gmailData.gmail_legacy_configured);

    cv.cvPassScore = cvData.cv_pass_score ?? 0;
    cv.cvReviseScore = cvData.cv_revise_score ?? 0;
    cv.bulletClarifyWordLimit = cvData.bullet_clarify_word_limit ?? 0;

    maintenance.shareUrl = data.share_url || "";
    maintenance.resetPhrase = maintenanceData.reset_phrase || maintenance.resetPhrase;
    maintenance.deletePhrase = maintenanceData.delete_phrase || maintenance.deletePhrase;
    maintenance.backupCount = maintenanceData.backup_count ?? 0;

    const query = new URLSearchParams(window.location.search);
    if (query.get("gmail_oauth") === "connected") {
      gmail.connected = true;
      setStatus(gmailStatus, "Gmail OAuth connected.", "success");
    }
  }

  async function loadWorkspaceSettings() {
    try {
      const payload = await loadSettings();
      hydrateWorkspaceSettings(payload);
    } catch (error) {
      setStatus(maintenanceStatus, error?.message || "Settings could not be loaded.", "error");
    }
  }

  async function refreshRoleSuggestions() {
    suggestionsLoading.value = true;
    setStatus(searchStatus, "Refreshing role suggestions...");
    try {
      const recommendations = await fetchSearchRecommendations({
        candidateId: activeCandidateId.value,
        countries: primaryCountry(search.countriesText),
      });
      const roles = Array.isArray(recommendations?.suggested_roles)
        ? recommendations.suggested_roles.map((item) => String(item || "").trim()).filter(Boolean).slice(0, 4)
        : [];
      if (!roles.length) {
        throw new Error("No profile-based role suggestions are available yet.");
      }
      search.rolesText = roles.join("\n");
      setStatus(searchStatus, "Profile-based role suggestions loaded.", "success");
    } catch (error) {
      setStatus(searchStatus, error?.message || "Could not refresh role suggestions.", "error");
    } finally {
      suggestionsLoading.value = false;
    }
  }

  async function saveSearchSettings() {
    searchSaving.value = true;
    setStatus(searchStatus, "Saving workspace search settings...");
    try {
      const payload = buildSearchPayload(search);
      await saveSettings(payload);
      search.countriesText = payload.job_search_countries[0] || "Italy";
      search.languages = normalizeLanguageRows(payload.job_search_languages);
      setStatus(searchStatus, "Workspace search settings saved.", "success");
    } catch (error) {
      setStatus(searchStatus, error?.message || "Could not save search settings.", "error");
    } finally {
      searchSaving.value = false;
    }
  }

  function updateSearchField(field, value) {
    if (Object.prototype.hasOwnProperty.call(search, field)) {
      search[field] = value;
    }
  }

  function addLanguageRow() {
    search.languages = [...search.languages, { name: "English", level: "professional" }];
  }

  function updateLanguageRow(index, field, value) {
    search.languages = search.languages.map((row, rowIndex) =>
      rowIndex === index ? { ...row, [field]: value } : row,
    );
  }

  function removeLanguageRow(index) {
    const next = search.languages.filter((_row, rowIndex) => rowIndex !== index);
    search.languages = normalizeLanguageRows(next);
  }

  async function saveGmailSettings() {
    gmailSaving.value = true;
    setStatus(gmailStatus, "Saving Gmail settings...");
    try {
      await saveSettings(buildGmailPayload(gmail));
      gmail.clientSecret = "";
      setStatus(gmailStatus, "Gmail settings saved.", "success");
    } catch (error) {
      setStatus(gmailStatus, error?.message || "Could not save Gmail settings.", "error");
    } finally {
      gmailSaving.value = false;
    }
  }

  async function connectGmail() {
    if (!String(gmail.clientId || "").trim() && !gmail.oauthConfigured) {
      setStatus(gmailStatus, "Paste OAuth Client ID first.", "error");
      return;
    }

    gmailSaving.value = true;
    setStatus(gmailStatus, "Saving OAuth settings...");
    try {
      await saveSettings(buildGmailPayload(gmail));
      const payload = await connectGmailOAuth();
      if (!payload?.auth_url) {
        throw new Error("Could not start OAuth flow.");
      }
      window.location.href = payload.auth_url;
    } catch (error) {
      setStatus(gmailStatus, error?.message || "Could not start OAuth flow.", "error");
      gmailSaving.value = false;
    }
  }

  async function disconnectGmail() {
    gmailSaving.value = true;
    setStatus(gmailStatus, "Disconnecting Gmail...");
    try {
      await disconnectGmailOAuth();
      gmail.connected = false;
      setStatus(gmailStatus, "Gmail disconnected.", "success");
    } catch (error) {
      setStatus(gmailStatus, error?.message || "Disconnect failed.", "error");
    } finally {
      gmailSaving.value = false;
    }
  }

  function updateGmailField(field, value) {
    if (Object.prototype.hasOwnProperty.call(gmail, field)) {
      gmail[field] = value;
    }
  }

  async function saveCvSettings() {
    cvSaving.value = true;
    setStatus(cvStatus, "Saving CV settings...");
    try {
      await saveSettings(buildCvPayload(cv));
      setStatus(cvStatus, "CV settings saved.", "success");
    } catch (error) {
      setStatus(cvStatus, error?.message || "Could not save CV settings.", "error");
    } finally {
      cvSaving.value = false;
    }
  }

  function updateCvField(field, value) {
    if (Object.prototype.hasOwnProperty.call(cv, field)) {
      cv[field] = value;
    }
  }

  async function reloadRuntimeSettings() {
    maintenanceBusy.value = true;
    setStatus(maintenanceStatus, "Reloading settings...");
    try {
      await reloadSettings();
      setStatus(maintenanceStatus, "Settings reloaded.", "success");
    } catch (error) {
      setStatus(maintenanceStatus, error?.message || "Reload failed.", "error");
    } finally {
      maintenanceBusy.value = false;
    }
  }

  async function copyShareLink() {
    try {
      await navigator.clipboard.writeText(maintenance.shareUrl);
      setStatus(maintenanceStatus, "Share link copied.", "success");
    } catch (_error) {
      setStatus(maintenanceStatus, "Could not access clipboard.", "error");
    }
  }

  async function runDangerAction(action) {
    const phrase = action === "reset" ? maintenance.resetInput : maintenance.deleteInput;
    const expectedPhrase = action === "reset" ? maintenance.resetPhrase : maintenance.deletePhrase;
    const targetStatus = action === "reset" ? resetStatus : deleteStatus;
    const validationMessage = validateMaintenancePhrase(phrase, expectedPhrase);
    if (validationMessage) {
      setStatus(targetStatus, validationMessage, "error");
      return;
    }

    maintenanceBusy.value = true;
    setStatus(targetStatus, "Working...");
    try {
      await runWorkspaceAction(action, phrase);
      window.location.href =
        action === "reset"
          ? `/ui/workspace-reset?mode=reset${maintenance.openBackups ? "&open=1" : ""}`
          : "/ui/workspace-reset?mode=delete";
    } catch (error) {
      setStatus(targetStatus, error?.message || "Action failed.", "error");
      maintenanceBusy.value = false;
    }
  }

  function updateMaintenanceField(field, value) {
    if (Object.prototype.hasOwnProperty.call(maintenance, field)) {
      maintenance[field] = value;
    }
  }

  return {
    settingsLoading,
    settingsError,
    search,
    gmail,
    cv,
    maintenance,
    languageOptions,
    languageLevelOptions,
    roleCount,
    roleLimitExceeded,
    searchStatus,
    gmailStatus,
    cvStatus,
    maintenanceStatus,
    resetStatus,
    deleteStatus,
    searchSaving,
    gmailSaving,
    cvSaving,
    maintenanceBusy,
    suggestionsLoading,
    loadWorkspaceSettings,
    refreshRoleSuggestions,
    saveSearchSettings,
    updateSearchField,
    addLanguageRow,
    updateLanguageRow,
    removeLanguageRow,
    saveGmailSettings,
    connectGmail,
    disconnectGmail,
    updateGmailField,
    saveCvSettings,
    updateCvField,
    reloadRuntimeSettings,
    copyShareLink,
    runDangerAction,
    updateMaintenanceField,
  };
}
