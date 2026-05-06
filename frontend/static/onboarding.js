/*
 * Onboarding bootstrap.
 *
 * The detailed flow logic lives in `/static/onboarding/*.js`. This file only
 * binds shared controls and restores the correct step on page load.
 */

document.addEventListener("DOMContentLoaded", () => {
  const app = window.OnboardingApp;
  const setupConfigured = document.body?.dataset?.setupConfigured === "1";
  app.bindSharedControls();
  if (!setupConfigured) {
    window.localStorage.removeItem(app.introStorageKey);
    app.showIntroModal(0);
  } else {
    app.maybeShowIntroModal();
  }
  app.hydrateOnboardingState();
});
