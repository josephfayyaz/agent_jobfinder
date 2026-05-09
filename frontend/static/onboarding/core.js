/*
 * Onboarding core helpers and shared state.
 *
 * This namespace keeps the server-rendered onboarding flow readable without
 * introducing a bundler. Later UI work can replace this with modules or a
 * framework, but the current behavior should remain deterministic and easy to
 * trace.
 */

(() => {
  const app = window.OnboardingApp || {};
  const providerController = window.ProviderController || {};

  app.state = app.state || {
    provider: {
      mode: "",
      lastValidation: null,
    },
    intake: {
      candidateId: "",
      questions: [],
    },
    review: {
      factSheet: null,
    },
    search: {
      recommendationsLoaded: false,
      languageOptions: [{code: "en", name: "English"}],
      levelOptions: [
        {value: "basic", label: "Basic"},
        {value: "working", label: "Working"},
        {value: "professional", label: "Professional"},
        {value: "fluent", label: "Fluent"},
      ],
      languagesTouched: false,
    },
    ui: {
      introIndex: 0,
      currentStep: 1,
    },
  };

  app.introStorageKey = "job-agent:onboarding-intro-seen:v1";

  app.stepTabClass = function stepTabClass(active) {
    return active ? "setup-step-tab is-active" : "setup-step-tab";
  };

  app.normalizePersonName = function normalizePersonName(value) {
    return String(value || "")
      .trim()
      .replace(/\s+/g, " ")
      .split(" ")
      .filter(Boolean)
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
      .join(" ");
  };

  app.validPersonName = function validPersonName(value) {
    const trimmed = String(value || "").trim();
    if (!trimmed) {
      return false;
    }
    return /^[\p{L} ]+$/u.test(trimmed);
  };

  app.validEmail = function validEmail(value) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(value || "").trim());
  };

  app.splitFullName = function splitFullName(value) {
    const normalized = String(value || "").trim().replace(/\s+/g, " ");
    if (!normalized) {
      return {firstName: "", familyName: ""};
    }
    const parts = normalized.split(" ");
    if (parts.length === 1) {
      return {firstName: app.normalizePersonName(parts[0]), familyName: ""};
    }
    return {
      firstName: app.normalizePersonName(parts.slice(0, -1).join(" ")),
      familyName: app.normalizePersonName(parts.slice(-1).join(" ")),
    };
  };

  app.escapeHtml = function escapeHtml(value) {
    return String(value || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  };

  app.onboardingSelect = function onboardingSelect(options, selectedValue, className) {
    const select = document.createElement("select");
    select.className = className;
    options.forEach((option) => {
      const el = document.createElement("option");
      el.value = option.value || option.name;
      el.textContent = option.label || option.name;
      if (el.value === selectedValue) {
        el.selected = true;
      }
      select.appendChild(el);
    });
    return select;
  };

  app.addOnboardingLanguageRow = function addOnboardingLanguageRow(
    value = {name: "English", level: "professional"},
    {markTouched = true} = {},
  ) {
    const container = document.getElementById("onboarding-language-rows");
    if (!container) {
      return;
    }
    const row = document.createElement("div");
    row.className = "grid gap-3 rounded-xl border border-slate-300 bg-white px-3 py-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]";

    const nameSelect = app.onboardingSelect(
      app.state.search.languageOptions,
      value.name || "English",
      "onboarding-job-language-name w-full rounded-xl border border-slate-300 px-3 py-2 text-sm",
    );
    const levelSelect = app.onboardingSelect(
      app.state.search.levelOptions,
      value.level || "professional",
      "onboarding-job-language-level w-full rounded-xl border border-slate-300 px-3 py-2 text-sm",
    );
    nameSelect.addEventListener("change", () => {
      app.state.search.languagesTouched = true;
    });
    levelSelect.addEventListener("change", () => {
      app.state.search.languagesTouched = true;
    });

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.className = "app-button app-button--sm app-button--danger";
    removeButton.textContent = "Remove";
    removeButton.addEventListener("click", () => {
      row.remove();
      app.state.search.languagesTouched = true;
      if (!container.children.length) {
        app.addOnboardingLanguageRow({name: "English", level: "professional"}, {markTouched: false});
      }
    });

    row.appendChild(nameSelect);
    row.appendChild(levelSelect);
    row.appendChild(removeButton);
    container.appendChild(row);
    if (markTouched) {
      app.state.search.languagesTouched = true;
    }
  };

  app.readOnboardingLanguageRows = function readOnboardingLanguageRows() {
    const rows = [];
    document.querySelectorAll("#onboarding-language-rows > div").forEach((row) => {
      const name = row.querySelector(".onboarding-job-language-name")?.value?.trim();
      const level = row.querySelector(".onboarding-job-language-level")?.value?.trim() || "professional";
      if (!name || rows.some((item) => item.name.toLowerCase() === name.toLowerCase())) {
        return;
      }
      rows.push({name, level});
    });
    return rows;
  };

  app.renderOnboardingLanguageRows = function renderOnboardingLanguageRows(values = [], {markTouched = false} = {}) {
    const container = document.getElementById("onboarding-language-rows");
    if (!container) {
      return;
    }
    container.innerHTML = "";
    const rows = Array.isArray(values) && values.length ? values : [{name: "English", level: "professional"}];
    rows.forEach((item) => app.addOnboardingLanguageRow(item, {markTouched}));
  };

  app.isSupportedSourceFile = function isSupportedSourceFile(file) {
    const name = (file?.name || "").toLowerCase();
    const type = (file?.type || "").toLowerCase();
    if (name.endsWith(".pdf") || name.endsWith(".txt") || name.endsWith(".md") || name.endsWith(".rst")) {
      return true;
    }
    return type === "application/pdf" || type === "text/plain" || type === "text/markdown";
  };

  app.onboardingTimeoutSignal = function onboardingTimeoutSignal(timeoutMs = 15000) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    return {
      signal: controller.signal,
      cancel() {
        clearTimeout(timer);
      },
    };
  };

  app.onboardingFetchJson = async function onboardingFetchJson(url, options = {}, timeoutMs = 15000) {
    const timeout = app.onboardingTimeoutSignal(timeoutMs);
    try {
      const response = await fetch(url, {...options, signal: timeout.signal});
      const text = await response.text();
      let data = {};
      if (text) {
        try {
          data = JSON.parse(text);
        } catch (_error) {
          data = {detail: text};
        }
      }
      return {response, data};
    } finally {
      timeout.cancel();
    }
  };

  app.chooseLocalModelDefaults = function chooseLocalModelDefaults(models) {
    return providerController.chooseLocalModelDefaults(models);
  };

  app.refreshOnboardingLocalModelChoices = function refreshOnboardingLocalModelChoices(selectId, models, selectedValue = "") {
    const select = document.getElementById(selectId);
    if (!select) {
      return;
    }
    const names = Array.isArray(models) ? models.filter(Boolean) : [];
    const current = selectedValue || select.value || "";
    select.innerHTML = "";
    if (!names.length) {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = "Validate first to load available models automatically";
      option.selected = true;
      select.appendChild(option);
      return;
    }
    names.forEach((name) => {
      const option = document.createElement("option");
      option.value = name;
      option.textContent = name;
      if (name === current) {
        option.selected = true;
      }
      select.appendChild(option);
    });
    if (!select.value && names.length) {
      select.value = names[0];
    }
  };

  app.selectedProvider = function selectedProvider() {
    const selected = document.querySelector('input[name="provider"]:checked')?.value || "";
    app.state.provider.mode = selected;
    return selected;
  };

  app.ensureCandidateShell = async function ensureCandidateShell() {
    if (app.state.intake.candidateId) {
      return app.state.intake.candidateId;
    }
    const response = await fetch("/candidates/ensure-owner", {method: "POST"});
    if (!response.ok) {
      throw new Error("Could not create the onboarding profile shell.");
    }
    const data = await response.json();
    app.state.intake.candidateId = data.id || "";
    return app.state.intake.candidateId;
  };

  app.toggleProviderFields = function toggleProviderFields() {
    const provider = app.selectedProvider();
    const setPanelVisibility = (id, active) => {
      const panel = document.getElementById(id);
      if (!panel) {
        return;
      }
      panel.hidden = !active;
      panel.classList.toggle("hidden", !active);
      panel.classList.toggle("is-hidden", !active);
    };
    setPanelVisibility("onboard-openai-fields", provider === "openai");
    setPanelVisibility("onboard-gemini-fields", provider === "gemini");
    setPanelVisibility("onboard-anthropic-fields", provider === "anthropic");
    setPanelVisibility("onboard-lmstudio-fields", provider === "lm_studio");
    setPanelVisibility("onboard-ollama-fields", provider === "ollama");
    document.querySelectorAll("[data-provider-card]").forEach((card) => {
      card.classList.toggle("is-selected", card.dataset.providerCard === provider);
    });
  };

  app.setStatus = function setStatus(message, isError = false) {
    const el = document.getElementById("setup-status");
    if (!el) {
      return;
    }
    el.textContent = message || "";
    el.className = isError ? "text-sm text-red-600" : "text-sm text-slate-500";
  };

  app.setInlineStatus = function setInlineStatus(id, message, isError = false) {
    const el = document.getElementById(id);
    if (!el) {
      return;
    }
    el.textContent = message || "";
    el.className = isError ? "text-sm text-red-600" : "text-sm text-slate-500";
  };

  app.renderIntroState = function renderIntroState(index = 0) {
    app.state.ui.introIndex = Math.max(0, Math.min(2, Number(index) || 0));
    document.querySelectorAll("[data-intro-slide]").forEach((slide) => {
      slide.classList.toggle("hidden", Number(slide.dataset.introSlide || "-1") !== app.state.ui.introIndex);
    });
    document.querySelectorAll("[data-intro-dot]").forEach((dot) => {
      dot.classList.toggle("is-active", Number(dot.dataset.introDot || "-1") === app.state.ui.introIndex);
    });
    document.getElementById("intro-back-button")?.classList.toggle("hidden", app.state.ui.introIndex === 0);
    const nextButton = document.getElementById("intro-next-button");
    if (nextButton) {
      nextButton.textContent = "Next";
    }
  };

  app.showIntroModal = function showIntroModal(startIndex = 0) {
    const modal = document.getElementById("onboarding-intro-modal");
    if (!modal) {
      return;
    }
    modal.classList.remove("hidden");
    document.body.classList.add("has-modal-open");
    app.renderIntroState(startIndex);
  };

  app.hideIntroModal = function hideIntroModal({persist = false} = {}) {
    const modal = document.getElementById("onboarding-intro-modal");
    if (!modal) {
      return;
    }
    modal.classList.add("hidden");
    document.body.classList.remove("has-modal-open");
    if (persist) {
      window.localStorage.setItem(app.introStorageKey, "1");
    }
  };

  app.maybeShowIntroModal = function maybeShowIntroModal() {
    if (window.localStorage.getItem(app.introStorageKey) === "1") {
      return;
    }
    app.showIntroModal(0);
  };

  app.goToStep = function goToStep(step) {
    app.state.ui.currentStep = step;
    document.querySelectorAll(".setup-step").forEach((section) => {
      section.classList.toggle("hidden", section.dataset.step !== String(step));
    });
    document.querySelectorAll("[data-step-tab]").forEach((tab) => {
      const active = tab.dataset.stepTab === String(step);
      tab.className = app.stepTabClass(active);
    });
    if (step === 5) {
      app.hydrateSearchFocus?.();
    }
    app.setStatus("");
  };

  app.selectProviderRadio = function selectProviderRadio(provider) {
    const target = document.querySelector(`input[name="provider"][value="${provider}"]`);
    if (!target) {
      return;
    }
    target.checked = true;
    app.toggleProviderFields();
  };

  app.renderSuggestedRoles = function renderSuggestedRoles(roles) {
    const panel = document.getElementById("suggested-roles");
    const list = document.getElementById("suggested-roles-list");
    if (!panel || !list) {
      return;
    }
    list.innerHTML = "";
    if (!(roles || []).length) {
      panel.classList.add("hidden");
      return;
    }
    panel.classList.remove("hidden");
    roles.forEach((role) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "rounded-full border border-indigo-200 bg-white px-3 py-1 text-sm text-indigo-700 hover:bg-indigo-100";
      button.textContent = role;
      button.addEventListener("click", () => {
        const textarea = document.getElementById("target-roles");
        const current = textarea.value.split("\n").map((item) => item.trim()).filter(Boolean);
        if (!current.includes(role) && current.length < 4) {
          current.push(role);
          textarea.value = current.join("\n");
        }
      });
      list.appendChild(button);
    });
  };

  app.renderRecommendedSources = function renderRecommendedSources(sources) {
    const list = document.getElementById("recommended-sources-list");
    if (!list) {
      return;
    }
    list.innerHTML = "";
    if (!(sources || []).length) {
      const empty = document.createElement("p");
      empty.className = "text-slate-400";
      empty.textContent = "Suggestions will appear after your profile is analysed.";
      list.appendChild(empty);
      return;
    }
    sources.forEach((source) => {
      const pill = document.createElement("span");
      pill.className = "inline-flex rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-sm text-slate-700";
      pill.title = source.why || "";
      pill.textContent = source.name;
      list.appendChild(pill);
    });
  };

  app.bindSharedControls = function bindSharedControls() {
    document.querySelectorAll('input[name="provider"]').forEach((input) => {
      input.addEventListener("change", app.toggleProviderFields);
    });
    document.querySelectorAll("[data-step-tab]").forEach((tab) => {
      tab.addEventListener("click", () => {
        const step = Number(tab.dataset.stepTab || "1");
        if (!Number.isNaN(step) && step >= 1 && step <= 5) {
          app.goToStep(step);
        }
      });
    });
    document.getElementById("target-roles")?.addEventListener("input", (event) => {
      event.currentTarget.dataset.userEdited = "1";
    });
    document.getElementById("search-countries")?.addEventListener("input", (event) => {
      event.currentTarget.dataset.userEdited = "1";
    });
    document.getElementById("onboarding-add-language")?.addEventListener("click", () => {
      app.addOnboardingLanguageRow();
    });
    document.getElementById("reopen-onboarding-intro")?.addEventListener("click", () => {
      app.showIntroModal(app.state.ui.introIndex || 0);
    });
    document.getElementById("intro-next-button")?.addEventListener("click", () => {
      if (app.state.ui.introIndex >= 2) {
        app.hideIntroModal({persist: true});
        return;
      }
      app.renderIntroState(app.state.ui.introIndex + 1);
    });
    document.getElementById("intro-back-button")?.addEventListener("click", () => {
      app.renderIntroState(app.state.ui.introIndex - 1);
    });
    document.querySelectorAll("[data-intro-skip], [data-intro-close]").forEach((control) => {
      control.addEventListener("click", () => {
        app.hideIntroModal({persist: true});
      });
    });
    app.renderOnboardingLanguageRows([], {markTouched: false});
    app.toggleProviderFields();
    app.renderIntroState(0);
  };

  window.OnboardingApp = app;
  window.goToStep = app.goToStep;
})();
