/*
 * Onboarding hydration.
 *
 * This recovers the current setup state so users can resume where they left
 * off instead of restarting the entire setup sequence.
 */

(() => {
  const app = window.OnboardingApp;

  app.hydrateOnboardingState = async function hydrateOnboardingState() {
    try {
      const [setupResponse, settingsResponse, candidatesResponse] = await Promise.all([
        fetch("/setup/status"),
        fetch("/settings/current"),
        fetch("/candidates"),
      ]);
      if (!setupResponse.ok || !settingsResponse.ok || !candidatesResponse.ok) {
        app.goToStep(1);
        return;
      }

      const setup = await setupResponse.json();
      const currentSettings = await settingsResponse.json();
      const candidates = await candidatesResponse.json();
      const candidate = Array.isArray(candidates) && candidates.length ? candidates[0] : null;

      const providerReadiness = {
        openai: Boolean(currentSettings.openai_api_key && currentSettings.openai_api_key !== "***"),
        anthropic: Boolean(currentSettings.anthropic_api_key && currentSettings.anthropic_api_key !== "***"),
        lm_studio: Boolean(setup.provider?.lm_studio_ready || setup.provider?.local_ready),
        ollama: Boolean(setup.provider?.ollama_ready),
      };
      let providerMode = currentSettings.llm_provider_mode || "";
      if (!providerReadiness[providerMode]) {
        if (providerReadiness.lm_studio) {
          providerMode = "lm_studio";
        } else if (providerReadiness.ollama) {
          providerMode = "ollama";
        } else if (providerReadiness.openai) {
          providerMode = "openai";
        } else if (providerReadiness.anthropic) {
          providerMode = "anthropic";
        } else {
          providerMode = "lm_studio";
        }
      }
      app.selectProviderRadio(providerMode);
      if (providerMode === "lm_studio") {
        const lmUrl = document.getElementById("lmstudio-url");
        if (lmUrl) {
          lmUrl.value = currentSettings.lm_studio_base_url || lmUrl.value;
        }
      }
      if (providerMode === "ollama") {
        const ollamaUrl = document.getElementById("ollama-url");
        if (ollamaUrl) {
          ollamaUrl.value = currentSettings.ollama_base_url || ollamaUrl.value;
        }
      }

      if (candidate) {
        app.state.candidateId = candidate.id || "";
        const fullNameInput = document.getElementById("full-name");
        const emailInput = document.getElementById("email");
        if (fullNameInput && !fullNameInput.value) {
          fullNameInput.value = candidate.full_name || "";
        }
        if (emailInput && !emailInput.value) {
          emailInput.value = candidate.email || "";
        }
      }

      if (setup.complete) {
        const rolesEl = document.getElementById("target-roles");
        const countriesEl = document.getElementById("search-countries");
        if (rolesEl) {
          rolesEl.value = (currentSettings.jobspy_discover_queries || []).join("\n");
        }
        if (countriesEl) {
          countriesEl.value = (currentSettings.job_search_countries || ["Italy"])[0] || "Italy";
        }
        if (!app.state.languagesTouched) {
          app.renderOnboardingLanguageRows(currentSettings.job_search_languages || [], {markTouched: false});
        }
        const seniorityEl = document.getElementById("target-seniority");
        if (seniorityEl && currentSettings.target_job_seniority) {
          seniorityEl.value = currentSettings.target_job_seniority;
        }
        document.querySelectorAll(".setup-step").forEach((section) => section.classList.add("hidden"));
        document.getElementById("done-panel").classList.remove("hidden");
        return;
      }

      if (app.state.candidateId) {
        const intakeResponse = await fetch(`/candidates/${app.state.candidateId}/intake/status`);
        if (intakeResponse.ok) {
          const intake = await intakeResponse.json();
          if (intake.status === "questions_needed" && (intake.questions || []).length) {
            app.state.questions = intake.questions || [];
            app.renderQuestions();
            app.goToStep(4);
            return;
          }
        }
      }

      if (setup.fact_sheet_ready) {
        const rolesEl = document.getElementById("target-roles");
        const countriesEl = document.getElementById("search-countries");
        if (rolesEl) {
          rolesEl.value = (currentSettings.jobspy_discover_queries || []).join("\n");
        }
        if (countriesEl) {
          countriesEl.value = (currentSettings.job_search_countries || ["Italy"])[0] || "Italy";
        }
        if (!app.state.languagesTouched) {
          app.renderOnboardingLanguageRows(currentSettings.job_search_languages || [], {markTouched: false});
        }
        const seniorityEl = document.getElementById("target-seniority");
        if (seniorityEl && currentSettings.target_job_seniority) {
          seniorityEl.value = currentSettings.target_job_seniority;
        }
        await app.loadProfileReview();
        await app.hydrateSearchFocus(true);
        app.goToStep(6);
        return;
      }

      if (app.state.candidateId) {
        app.goToStep(3);
        return;
      }
      if (setup.provider?.ready) {
        app.goToStep(2);
        return;
      }
      app.goToStep(1);
    } catch (_error) {
      app.goToStep(1);
    }
  };
})();
