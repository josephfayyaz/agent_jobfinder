/*
 * Search preference settings controller.
 */

(() => {
  const app = window.SettingsApp;

  app.suggestDiscoveryRoles = async function suggestDiscoveryRoles() {
    const queriesInput = document.querySelector('[name="jobspy_discover_queries"]');
    const status = document.getElementById("system-status");
    if (!queriesInput) {
      return;
    }

    const params = new URLSearchParams();
    if (app.state.activeCandidateId) {
      params.set("candidate_id", app.state.activeCandidateId);
    }

    const countriesInput = document.querySelector('[name="job_search_countries"]');
    const countries = (countriesInput?.value || "")
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean);
    if (countries.length) {
      params.set("countries", countries.join("\n"));
    }

    try {
      if (status) {
        status.textContent = "Refreshing role suggestions...";
      }
      const suffix = params.toString();
      const {response, data} = await app.settingsFetchJson(`/search/preferences/recommendations${suffix ? `?${suffix}` : ""}`);
      if (!response.ok) {
        throw new Error(data?.detail || "Could not refresh role suggestions.");
      }
      const roles = Array.isArray(data?.suggested_roles)
        ? data.suggested_roles.map((item) => String(item || "").trim()).filter(Boolean).slice(0, 4)
        : [];
      if (!roles.length) {
        throw new Error("No profile-based role suggestions are available yet.");
      }
      queriesInput.value = roles.join("\n");
      app.syncRoleCount();
      if (status) {
        status.textContent = "Profile-based role suggestions loaded.";
      }
    } catch (error) {
      if (status) {
        status.textContent = error.message || "Could not refresh role suggestions.";
      }
    }
  };

  app.syncRoleCount = function syncRoleCount() {
    const queriesInput = document.querySelector('[name="jobspy_discover_queries"]');
    const roleCount = document.getElementById("role-count");
    if (!queriesInput || !roleCount) {
      return;
    }

    const count = queriesInput.value.split("\n").filter((line) => line.trim()).length;
    roleCount.textContent = String(count);
    queriesInput.style.borderColor = count > 4 ? "rgb(239,68,68)" : "";
  };

  window.suggestDiscoveryRoles = app.suggestDiscoveryRoles;
})();
