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

      const lmUrl = document.getElementById("lmstudio-url");
      if (lmUrl) {
        lmUrl.value = currentSettings.lm_studio_base_url || lmUrl.value;
      }
      const lmModel = document.getElementById("lmstudio-model");
      if (lmModel && (currentSettings.lm_studio_writer_model || currentSettings.lm_studio_small_model)) {
        app.refreshOnboardingLocalModelChoices(
          "lmstudio-model",
          [
            currentSettings.lm_studio_writer_model || "",
            currentSettings.lm_studio_small_model || "",
            currentSettings.lm_studio_mid_model || "",
          ].filter(Boolean),
          currentSettings.lm_studio_writer_model || currentSettings.lm_studio_small_model || "",
        );
      }
      const ollamaUrl = document.getElementById("ollama-url");
      if (ollamaUrl) {
        ollamaUrl.value = currentSettings.ollama_base_url || ollamaUrl.value;
      }
      const ollamaModel = document.getElementById("ollama-model");
      if (ollamaModel && (currentSettings.ollama_writer_model || currentSettings.ollama_fast_model)) {
        ollamaModel.value = currentSettings.ollama_writer_model || currentSettings.ollama_fast_model || "";
      }
      const geminiKey = document.getElementById("gemini-key");
      if (geminiKey && currentSettings.gemini_api_key === "***") {
        geminiKey.placeholder = "***";
      }
      const openaiKey = document.getElementById("openai-key");
      if (openaiKey && currentSettings.openai_api_key === "***") {
        openaiKey.placeholder = "***";
      }
      const anthropicKey = document.getElementById("anthropic-key");
      if (anthropicKey && currentSettings.anthropic_api_key === "***") {
        anthropicKey.placeholder = "***";
      }

      if (candidate) {
        app.state.intake.candidateId = candidate.id || "";
      }

      if (setup.complete) {
        const rolesEl = document.getElementById("target-roles");
        const countriesEl = document.getElementById("search-countries");
        const regionEl = document.getElementById("search-region");
        if (rolesEl) {
          rolesEl.value = (currentSettings.jobspy_discover_queries || []).join("\n");
        }
        if (countriesEl) {
          countriesEl.value = (currentSettings.job_search_countries || ["Italy"])[0] || "Italy";
        }
        if (regionEl) {
          regionEl.value = currentSettings.job_search_region || "";
        }
        if (!app.state.search.languagesTouched) {
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

      if (app.state.intake.candidateId) {
        const intakeResponse = await fetch(`/candidates/${app.state.intake.candidateId}/intake/status`);
        if (intakeResponse.ok) {
          const intake = await intakeResponse.json();
          if (intake.status === "questions_needed" && (intake.questions || []).length) {
            app.state.intake.questions = intake.questions || [];
            app.renderQuestions();
            app.goToStep(3);
            return;
          }
        }
      }

      if (setup.fact_sheet_ready) {
        const rolesEl = document.getElementById("target-roles");
        const countriesEl = document.getElementById("search-countries");
        const regionEl = document.getElementById("search-region");
        if (rolesEl) {
          rolesEl.value = (currentSettings.jobspy_discover_queries || []).join("\n");
        }
        if (countriesEl) {
          countriesEl.value = (currentSettings.job_search_countries || ["Italy"])[0] || "Italy";
        }
        if (regionEl) {
          regionEl.value = currentSettings.job_search_region || "";
        }
        if (!app.state.search.languagesTouched) {
          app.renderOnboardingLanguageRows(currentSettings.job_search_languages || [], {markTouched: false});
        }
        const seniorityEl = document.getElementById("target-seniority");
        if (seniorityEl && currentSettings.target_job_seniority) {
          seniorityEl.value = currentSettings.target_job_seniority;
        }
        await app.loadProfileReview();
        await app.hydrateSearchFocus(true);
        app.goToStep(5);
        return;
      }

      if (app.state.intake.candidateId) {
        app.goToStep(2);
        return;
      }
      if (setup.provider?.ready) {
        await app.ensureCandidateShell();
        app.goToStep(2);
        return;
      }
      app.goToStep(1);
    } catch (_error) {
      app.goToStep(1);
    }
  };
})();
