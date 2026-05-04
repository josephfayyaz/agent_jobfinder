/*
 * Settings bootstrap.
 *
 * Detailed per-section behavior lives in `/static/settings/*.js`. This file
 * only binds shared DOM listeners for the composed screen.
 */

document.addEventListener("DOMContentLoaded", () => {
  const app = window.SettingsApp;
  const queriesInput = document.querySelector('[name="jobspy_discover_queries"]');
  if (queriesInput) {
    queriesInput.addEventListener("input", app.syncRoleCount);
    app.syncRoleCount();
  }
  document.getElementById("suggest-discovery-roles")?.addEventListener("click", app.suggestDiscoveryRoles);

  app.ensureSettingsLanguageRows();
  app.syncRangeLabel("discovery_min_fit_score", "discovery-fit-value");
  app.syncRangeLabel("cv_pass_score", "cv-pass-value");
  app.syncRangeLabel("cv_revise_score", "cv-revise-value");
  [
    ["discovery_min_fit_score", "discovery-fit-value"],
    ["cv_pass_score", "cv-pass-value"],
    ["cv_revise_score", "cv-revise-value"],
  ].forEach(([inputId, labelId]) => {
    document.getElementById(inputId)?.addEventListener("input", () => app.syncRangeLabel(inputId, labelId));
    document.getElementById(inputId)?.addEventListener("change", () => app.syncRangeLabel(inputId, labelId));
  });

  const providerForm = document.getElementById("provider-form");
  providerForm?.querySelectorAll('input[name="provider_mode"]').forEach((input) => {
    input.addEventListener("change", () => app.syncProviderVisibility(providerForm));
  });
  providerForm?.elements.lm_studio_local_model?.addEventListener("change", () => app.syncSingleLocalModelFields(providerForm));
  providerForm?.elements.ollama_local_model?.addEventListener("change", () => app.syncSingleLocalModelFields(providerForm));
  app.syncProviderVisibility(providerForm);

  const params = new URLSearchParams(window.location.search);
  const gmailOauth = params.get("gmail_oauth");
  const gmailStatus = document.getElementById("gmail-status");
  if (gmailStatus && gmailOauth === "connected") {
    gmailStatus.textContent = "✓ Gmail OAuth connected";
  }
});
