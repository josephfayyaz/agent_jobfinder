/*
 * Provider validation, intake, and follow-up questions.
 *
 * These actions move the candidate from initial setup into a profile that can
 * be reviewed and later used for discovery and drafting.
 */

(() => {
  const app = window.OnboardingApp;

  app.createProfile = async function createProfile() {
    const firstName = app.normalizePersonName(document.getElementById("first-name")?.value || "");
    const familyName = app.normalizePersonName(document.getElementById("family-name")?.value || "");
    const email = (document.getElementById("email")?.value || "").trim();
    if (!firstName || !familyName || !email) {
      app.setStatus("Please enter first name, family name, and email.", true);
      return;
    }
    if (!app.validPersonName(firstName) || !app.validPersonName(familyName)) {
      app.setStatus("Names can contain letters and spaces only.", true);
      return;
    }
    if (!app.validEmail(email)) {
      app.setStatus("Please enter a valid email address.", true);
      return;
    }
    const firstNameInput = document.getElementById("first-name");
    const familyNameInput = document.getElementById("family-name");
    if (firstNameInput) {
      firstNameInput.value = firstName;
    }
    if (familyNameInput) {
      familyNameInput.value = familyName;
    }
    const fullName = `${firstName} ${familyName}`.trim();
    const response = await fetch("/candidates", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({full_name: fullName, email}),
    });
    if (!response.ok) {
      app.setStatus(await response.text(), true);
      return;
    }
    const data = await response.json();
    app.state.candidateId = data.id;
    app.goToStep(3);
  };

  app.validateAndSaveProvider = async function validateAndSaveProvider() {
    const provider = app.selectedProvider();
    if (!provider) {
      const status = document.getElementById("provider-validate-status");
      if (status) {
        status.textContent = "Select one provider before continuing.";
        status.className = "text-sm text-red-600";
      }
      return;
    }
    const openaiKey = document.getElementById("openai-key").value.trim();
    const geminiKey = document.getElementById("gemini-key")?.value.trim() || "";
    const anthropicKey = document.getElementById("anthropic-key").value.trim();
    const lmStudioUrl = document.getElementById("lmstudio-url")?.value.trim() || "";
    const ollamaUrl = document.getElementById("ollama-url")?.value.trim() || "";
    const status = document.getElementById("provider-validate-status");
    const button = Array.from(document.querySelectorAll("button")).find((el) => el.textContent.includes("Validate & Continue"));
    if (status) {
      status.textContent = "Validating...";
      status.className = "text-sm text-slate-500";
    }
    if (button) {
      button.disabled = true;
    }

    try {
      const {response: validationResponse, data: validation} = await app.onboardingFetchJson("/providers/validate", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          provider_mode: provider,
          openai_api_key: openaiKey,
          gemini_api_key: geminiKey,
          anthropic_api_key: anthropicKey,
          lm_studio_base_url: lmStudioUrl,
          ollama_base_url: ollamaUrl,
        }),
      }, 15000);
      if (!validationResponse.ok || !validation.ok) {
        const detail = validation?.detail || "Provider validation failed.";
        if (status) {
          status.textContent = detail;
          status.className = "text-sm text-red-600";
        }
        return;
      }

      const payload = {
        llm_provider_mode: provider,
        use_openai_review: provider === "openai",
        use_claude_final_review: provider === "anthropic",
        lm_studio_base_url: lmStudioUrl || "http://localhost:1234/v1",
        ollama_base_url: ollamaUrl || "http://localhost:11434",
      };
      const discoveredModels = Array.isArray(validation.models) ? validation.models.filter(Boolean) : [];
      const chosen = app.chooseLocalModelDefaults(discoveredModels);
      if (provider === "lm_studio" && !app.nonEmbeddingModels(discoveredModels).length) {
        if (status) {
          status.textContent = "LM Studio responded, but no usable chat models were found. Load a non-embedding model first.";
          status.className = "text-sm text-red-600";
        }
        return;
      }
      if (provider === "ollama") {
        const singleLocalModel = chosen.writer || chosen.small;
        payload.ollama_fast_model = singleLocalModel;
        payload.ollama_writer_model = singleLocalModel;
        if (!singleLocalModel) {
          if (status) {
            status.textContent = "Ollama responded, but no usable chat models were found. Pull a model first.";
            status.className = "text-sm text-red-600";
          }
          return;
        }
      }
      if (provider === "lm_studio") {
        const singleLocalModel = chosen.writer || chosen.small;
        payload.lm_studio_small_model = singleLocalModel;
        payload.lm_studio_writer_model = singleLocalModel;
        payload.lm_studio_mid_model = singleLocalModel;
      }
      if (openaiKey) {
        payload.openai_api_key = openaiKey;
      }
      if (geminiKey) {
        payload.gemini_api_key = geminiKey;
      }
      if (anthropicKey) {
        payload.anthropic_api_key = anthropicKey;
      }
      const {response, data} = await app.onboardingFetchJson("/settings/save", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload),
      }, 12000);
      if (!response.ok) {
        const detail = data?.detail || "Saving provider settings failed.";
        if (status) {
          status.textContent = detail;
          status.className = "text-sm text-red-600";
        }
        return;
      }
      if (status) {
        status.textContent = validation.detail || "Provider ready.";
        status.className = "text-sm text-emerald-700";
      }
      app.goToStep(2);
    } catch (error) {
      if (status) {
        status.textContent = error?.name === "AbortError"
          ? "Provider validation timed out. Check the provider and try again."
          : `Provider validation failed: ${error.message || error}`;
        status.className = "text-sm text-red-600";
      }
    } finally {
      if (button) {
        button.disabled = false;
      }
    }
  };

  app.renderQuestions = function renderQuestions() {
    const container = document.getElementById("questions-container");
    container.innerHTML = "";
    app.state.questions.forEach((question, index) => {
      const questionObj = typeof question === "string"
        ? {id: `q${index + 1}`, prompt: question, kind: "text", options: [], allow_free_text: true}
        : question;
      const questionId = questionObj.id || `q${index + 1}`;
      const label = document.createElement("label");
      label.className = "block text-sm";
      const span = document.createElement("span");
      span.className = "mb-1 block font-medium text-slate-700";
      span.textContent = questionObj.prompt || questionObj.question || questionId;
      label.appendChild(span);
      if (questionObj.required !== false) {
        const hint = document.createElement("p");
        hint.className = "mb-2 text-xs font-medium uppercase tracking-wide text-amber-700";
        hint.textContent = "Required to build a usable fact sheet";
        label.appendChild(hint);
      }

      const kind = questionObj.kind || "text";
      const options = Array.isArray(questionObj.options) ? questionObj.options : [];

      if (kind === "single_select" && options.length) {
        const list = document.createElement("div");
        list.className = "space-y-2";
        options.forEach((option, optionIndex) => {
          const optionLabel = document.createElement("label");
          optionLabel.className = "flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2";
          const input = document.createElement("input");
          input.type = "radio";
          input.name = `answer-${questionId}`;
          input.value = option;
          input.id = `answer-${questionId}-${optionIndex}`;
          optionLabel.appendChild(input);
          const text = document.createElement("span");
          text.textContent = option;
          optionLabel.appendChild(text);
          list.appendChild(optionLabel);
        });
        label.appendChild(list);
      } else if (kind === "multi_select" && options.length) {
        const list = document.createElement("div");
        list.className = "space-y-2";
        options.forEach((option, optionIndex) => {
          const optionLabel = document.createElement("label");
          optionLabel.className = "flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2";
          const input = document.createElement("input");
          input.type = "checkbox";
          input.value = option;
          input.id = `answer-${questionId}-${optionIndex}`;
          input.dataset.questionId = questionId;
          optionLabel.appendChild(input);
          const text = document.createElement("span");
          text.textContent = option;
          optionLabel.appendChild(text);
          list.appendChild(optionLabel);
        });
        label.appendChild(list);
      }

      if (kind === "text" || questionObj.allow_free_text) {
        const textarea = document.createElement("textarea");
        textarea.rows = kind === "text" ? 3 : 2;
        textarea.id = `answer-${questionId}`;
        textarea.className = "mt-2 w-full rounded-xl border border-slate-300 px-3 py-2";
        textarea.placeholder = kind === "text" ? "Type your answer" : "Optional note";
        label.appendChild(textarea);
      }

      container.appendChild(label);
    });
  };

  app.ensureFactSheetReady = async function ensureFactSheetReady() {
    try {
      const response = await fetch("/setup/status");
      if (!response.ok) {
        return true;
      }
      const data = await response.json();
      if (data?.fact_sheet_ready) {
        return true;
      }
      const missing = Array.isArray(data?.missing_steps) ? data.missing_steps : [];
      const hint = missing.length ? ` Missing: ${missing.join(", ")}.` : "";
      app.setStatus(`Intake finished but your fact sheet is still incomplete.${hint} Upload a richer CV or add more details.`, true);
      return false;
    } catch (_error) {
      return true;
    }
  };

  app.runIntake = async function runIntake() {
    const files = document.getElementById("source-files").files;
    const notes = document.getElementById("profile-notes").value.trim();
    const factsButton = document.getElementById("run-intake-button");
    if (!app.state.candidateId) {
      app.setStatus("Create your profile first.", true);
      app.setInlineStatus("facts-status", "Create your profile first.", true);
      app.goToStep(2);
      return;
    }
    if (!files.length && !notes) {
      app.setStatus("Upload at least one CV file (PDF/TXT) or add manual notes.", true);
      app.setInlineStatus("facts-status", "Upload at least one CV file (PDF/TXT) or add manual notes.", true);
      return;
    }
    if (files.length) {
      const invalid = Array.from(files).filter((file) => !app.isSupportedSourceFile(file));
      if (invalid.length) {
        app.setStatus("Only PDF or plain-text files are accepted in onboarding intake.", true);
        app.setInlineStatus("facts-status", "Only PDF or plain-text files are accepted in onboarding intake.", true);
        return;
      }
    }
    app.setStatus("Analysing your profile...");
    app.setInlineStatus("facts-status", "Analysing your profile...");
    const intakeSkeleton = document.getElementById("intake-skeleton");
    let intakeData = null;
    try {
      if (factsButton) {
        factsButton.disabled = true;
      }
      if (intakeSkeleton) {
        intakeSkeleton.classList.remove("hidden");
      }
      if (files.length) {
        const uploadData = new FormData();
        uploadData.append("replace_existing", "1");
        for (const file of files) {
          uploadData.append("files", file);
        }
        const uploadResponse = await fetch(`/candidates/${app.state.candidateId}/sources/upload`, {
          method: "POST",
          body: uploadData,
        });
        if (!uploadResponse.ok) {
          const detail = await uploadResponse.text();
          app.setStatus(detail, true);
          app.setInlineStatus("facts-status", detail, true);
          return;
        }
      }
      const intakeResponse = await fetch(`/candidates/${app.state.candidateId}/intake/start`, {
        method: "POST",
        headers: {"Content-Type": "application/x-www-form-urlencoded"},
        body: new URLSearchParams({profile_notes: notes}),
      });
      if (!intakeResponse.ok) {
        let errMsg = "The AI provider could not complete intake. Check your provider key in Settings.";
        try {
          const errData = await intakeResponse.json();
          if (errData.detail) {
            errMsg = errData.detail;
          }
        } catch (_error) {
          // Keep the generic status message when the response body is not JSON.
        }
        app.setStatus(errMsg, true);
        app.setInlineStatus("facts-status", errMsg, true);
        return;
      }
      intakeData = await intakeResponse.json();
    } finally {
      if (factsButton) {
        factsButton.disabled = false;
      }
      if (intakeSkeleton) {
        intakeSkeleton.classList.add("hidden");
      }
    }
    if (intakeData.status === "questions_needed" && (intakeData.questions || []).length) {
      app.setInlineStatus("facts-status", "Profile intake saved. Answer the remaining questions.");
      app.state.questions = intakeData.questions || [];
      app.renderQuestions();
      app.goToStep(4);
    } else {
      const setupReady = await app.ensureFactSheetReady();
      if (!setupReady) {
        app.goToStep(3);
        return;
      }
      app.setInlineStatus("facts-status", "Profile intake saved.");
      await app.loadProfileReview();
      app.goToStep(5);
    }
  };

  app.submitAnswers = async function submitAnswers() {
    const questionsButton = document.getElementById("submit-answers-button");
    const answers = {};
    const missingPrompts = [];
    app.state.questions.forEach((question, index) => {
      const questionObj = typeof question === "string"
        ? {id: `q${index + 1}`, prompt: question, kind: "text", options: [], allow_free_text: true, required: true}
        : question;
      const questionId = questionObj.id || `q${index + 1}`;
      const kind = questionObj.kind || "text";
      const required = questionObj.required !== false;

      if (kind === "single_select") {
        const selected = document.querySelector(`input[name="answer-${questionId}"]:checked`);
        const note = document.getElementById(`answer-${questionId}`)?.value?.trim();
        const value = note || selected?.value || "";
        answers[questionId] = value;
        if (required && !value) {
          missingPrompts.push(questionObj.prompt || questionId);
        }
        return;
      }

      if (kind === "multi_select") {
        const values = Array.from(document.querySelectorAll(`input[data-question-id="${questionId}"]:checked`))
          .map((input) => input.value)
          .filter(Boolean);
        const note = document.getElementById(`answer-${questionId}`)?.value?.trim();
        const value = note ? [...values, note] : values;
        answers[questionId] = value;
        if (required && !value.length) {
          missingPrompts.push(questionObj.prompt || questionId);
        }
        return;
      }

      const value = document.getElementById(`answer-${questionId}`)?.value?.trim() || "";
      answers[questionId] = value;
      if (required && !value) {
        missingPrompts.push(questionObj.prompt || questionId);
      }
    });

    if (missingPrompts.length) {
      app.setStatus(`Please answer the required questions first. Missing: ${missingPrompts[0]}`, true);
      app.setInlineStatus("questions-status", `Please answer the required questions first. Missing: ${missingPrompts[0]}`, true);
      return;
    }

    try {
      if (questionsButton) {
        questionsButton.disabled = true;
      }
      app.setInlineStatus("questions-status", "Saving your answers...");
      const response = await fetch(`/candidates/${app.state.candidateId}/intake/answer`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({answers}),
      });
      if (!response.ok) {
        const detail = await response.text();
        app.setStatus(detail, true);
        app.setInlineStatus("questions-status", detail, true);
        return;
      }
      const data = await response.json();
      if (data.status === "questions_needed" && (data.questions || []).length) {
        app.setInlineStatus("questions-status", "More detail is still needed. Answer the updated questions below.");
        app.state.questions = data.questions || [];
        app.renderQuestions();
      } else {
        const setupReady = await app.ensureFactSheetReady();
        if (!setupReady) {
          app.goToStep(3);
          return;
        }
        app.setInlineStatus("questions-status", "Answers saved.");
        await app.loadProfileReview();
        app.goToStep(5);
      }
    } finally {
      if (questionsButton) {
        questionsButton.disabled = false;
      }
    }
  };

  window.createProfile = app.createProfile;
  window.validateAndSaveProvider = app.validateAndSaveProvider;
  window.runIntake = app.runIntake;
  window.submitAnswers = app.submitAnswers;
})();
