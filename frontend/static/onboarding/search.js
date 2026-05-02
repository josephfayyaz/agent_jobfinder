/*
 * Search focus stage.
 *
 * This stage translates the reviewed profile into search roles, one-country
 * targeting, and language preferences used by discovery.
 */

(() => {
  const app = window.OnboardingApp;

  app.hydrateSearchFocus = async function hydrateSearchFocus(force = false) {
    if (!app.state.candidateId || (app.state.searchRecommendationsLoaded && !force)) {
      return;
    }
    try {
      const response = await fetch(`/search/preferences/recommendations?candidate_id=${encodeURIComponent(app.state.candidateId)}`);
      if (!response.ok) {
        return;
      }
      const data = await response.json();
      app.state.languageOptions = Array.isArray(data.language_options) && data.language_options.length
        ? data.language_options
        : app.state.languageOptions;
      app.state.levelOptions = Array.isArray(data.level_options) && data.level_options.length
        ? data.level_options
        : app.state.levelOptions;

      const countriesEl = document.getElementById("search-countries");
      if (countriesEl && !countriesEl.dataset.userEdited) {
        const country = (data.countries || ["Italy"])[0] || "Italy";
        countriesEl.value = country;
      }

      const rolesEl = document.getElementById("target-roles");
      if (rolesEl && !rolesEl.dataset.userEdited && (data.suggested_roles || []).length) {
        rolesEl.value = data.suggested_roles.slice(0, 4).join("\n");
      }
      if (!app.state.languagesTouched) {
        app.renderOnboardingLanguageRows(data.selected_languages || [], {markTouched: false});
      }

      app.renderSuggestedRoles(data.suggested_roles || []);
      app.renderRecommendedSources(data.recommended_sources || []);
      app.state.searchRecommendationsLoaded = true;
    } catch (_error) {
      app.renderRecommendedSources([]);
    }
  };

  app.saveSearchFocus = async function saveSearchFocus() {
    const roles = document.getElementById("target-roles").value
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean)
      .slice(0, 4);
    const countries = document.getElementById("search-countries").value
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean)
      .slice(0, 1);
    const country = countries[0] || "Italy";
    const languages = app.readOnboardingLanguageRows();
    if (!roles.length) {
      app.setStatus("Add at least one target role.", true);
      return;
    }
    const payload = {
      jobspy_discover_queries: roles,
      job_search_countries: [country],
      jobspy_discover_location: country,
      target_job_seniority: document.getElementById("target-seniority").value,
      job_search_languages: languages,
    };
    const response = await fetch("/settings/save", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      app.setStatus(await response.text(), true);
      return;
    }
    document.querySelectorAll(".setup-step").forEach((section) => section.classList.add("hidden"));
    document.getElementById("done-panel").classList.remove("hidden");
    app.setStatus("");
  };

  window.saveSearchFocus = app.saveSearchFocus;
})();
