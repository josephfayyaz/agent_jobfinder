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

    // LLM-driven role suggestions (runs after rule-based suggestions are shown)
    if (!app.state.candidateId) {
      return;
    }
    const suggestSkeletons = document.getElementById("suggest-skeletons");
    const suggestStatus = document.getElementById("llm-suggest-status");
    const suggestedPanel = document.getElementById("suggested-roles");
    if (suggestSkeletons) {
      suggestSkeletons.classList.remove("hidden");
    }
    if (suggestedPanel) {
      suggestedPanel.classList.remove("hidden");
    }
    if (suggestStatus) {
      suggestStatus.textContent = "Refining with AI…";
    }
    try {
      const suggestResp = await fetch(`/candidates/${encodeURIComponent(app.state.candidateId)}/suggest-tracks`, {
        method: "POST",
      });
      if (suggestResp.ok) {
        const suggestData = await suggestResp.json();
        if (Array.isArray(suggestData.suggested_roles) && suggestData.suggested_roles.length) {
          app.renderSuggestedRoles(suggestData.suggested_roles);
          const rolesEl = document.getElementById("target-roles");
          if (rolesEl && !rolesEl.dataset.userEdited) {
            rolesEl.value = suggestData.suggested_roles.slice(0, 4).join("\n");
          }
        }
      }
    } catch (_error) {
      // Provider down — rule-based suggestions remain visible
    } finally {
      if (suggestSkeletons) {
        suggestSkeletons.classList.add("hidden");
      }
      if (suggestStatus) {
        suggestStatus.textContent = "";
      }
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

    // Show done panel first, then generate tracks
    document.querySelectorAll(".setup-step").forEach((section) => section.classList.add("hidden"));
    document.getElementById("done-panel").classList.remove("hidden");
    app.setStatus("");

    if (app.state.candidateId && roles.length) {
      const tracksStatus = document.getElementById("tracks-status");
      if (tracksStatus) {
        tracksStatus.classList.remove("hidden");
      }
      try {
        await fetch(`/candidates/${encodeURIComponent(app.state.candidateId)}/generate-tracks`, {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({roles}),
        });
      } catch (_error) {
        // Silent — tracks can be regenerated from settings
      } finally {
        if (tracksStatus) {
          tracksStatus.textContent = "Role tracks ready.";
          window.setTimeout(() => tracksStatus.classList.add("hidden"), 3000);
        }
      }
    }
  };

  window.saveSearchFocus = app.saveSearchFocus;
})();
