/*
 * Onboarding bootstrap.
 *
 * The detailed flow logic lives in `/static/onboarding/*.js`. This file only
 * binds shared controls and restores the correct step on page load.
 */

document.addEventListener("DOMContentLoaded", () => {
  const app = window.OnboardingApp;
  app.bindSharedControls();
  app.hydrateOnboardingState();
  app.maybeShowIntroModal();
});
