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

  app.state = app.state || {
    candidateId: "",
    questions: [],
    searchRecommendationsLoaded: false,
    languageOptions: [{code: "en", name: "English"}],
    levelOptions: [
      {value: "basic", label: "Basic"},
      {value: "working", label: "Working"},
      {value: "professional", label: "Professional"},
      {value: "fluent", label: "Fluent"},
    ],
    languagesTouched: false,
    reviewFactSheet: null,
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
      app.state.languageOptions,
      value.name || "English",
      "onboarding-job-language-name w-full rounded-xl border border-slate-300 px-3 py-2 text-sm",
    );
    const levelSelect = app.onboardingSelect(
      app.state.levelOptions,
      value.level || "professional",
      "onboarding-job-language-level w-full rounded-xl border border-slate-300 px-3 py-2 text-sm",
    );
    nameSelect.addEventListener("change", () => {
      app.state.languagesTouched = true;
    });
    levelSelect.addEventListener("change", () => {
      app.state.languagesTouched = true;
    });

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.className = "app-button app-button--sm app-button--danger";
    removeButton.textContent = "Remove";
    removeButton.addEventListener("click", () => {
      row.remove();
      app.state.languagesTouched = true;
      if (!container.children.length) {
        app.addOnboardingLanguageRow({name: "English", level: "professional"}, {markTouched: false});
      }
    });

    row.appendChild(nameSelect);
    row.appendChild(levelSelect);
    row.appendChild(removeButton);
    container.appendChild(row);
    if (markTouched) {
      app.state.languagesTouched = true;
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

  app.nonEmbeddingModels = function nonEmbeddingModels(models) {
    return (models || []).filter((name) => !/embed/i.test(name));
  };

  app.chooseLocalModelDefaults = function chooseLocalModelDefaults(models) {
    const chatModels = app.nonEmbeddingModels(models);
    if (!chatModels.length) {
      return {small: "", writer: "", mid: ""};
    }

    const safeChatModels = chatModels.filter(
      (name) => !/(27b|32b|70b|72b|405b|671b|claude-4\\.6-opus-distilled)/i.test(name),
    );
    const preferred = safeChatModels.length ? safeChatModels : chatModels;
    const gptOss = preferred.find((name) => /gpt-oss/i.test(name));
    const compact = preferred.find((name) => /(mini|small|7b|8b|9b|10b|11b|12b|14b)/i.test(name));

    const small = gptOss || compact || preferred[0];
    const writer =
      gptOss ||
      preferred.find((name) => /(writer|instruct|chat)/i.test(name)) ||
      compact ||
      preferred[0];
    const mid =
      preferred.find((name) => name !== small && name !== writer) ||
      writer ||
      small;

    return {small, writer, mid};
  };

  app.selectedProvider = function selectedProvider() {
    return document.querySelector('input[name="provider"]:checked')?.value || "openai";
  };

  app.toggleProviderFields = function toggleProviderFields() {
    const provider = app.selectedProvider();
    document.getElementById("onboard-openai-fields")?.classList.toggle("hidden", provider !== "openai");
    document.getElementById("onboard-anthropic-fields")?.classList.toggle("hidden", provider !== "anthropic");
    document.getElementById("onboard-lmstudio-fields")?.classList.toggle("hidden", provider !== "lm_studio");
    document.getElementById("onboard-ollama-fields")?.classList.toggle("hidden", provider !== "ollama");
  };

  app.setStatus = function setStatus(message, isError = false) {
    const el = document.getElementById("setup-status");
    if (!el) {
      return;
    }
    el.textContent = message || "";
    el.className = isError ? "text-sm text-red-600" : "text-sm text-slate-500";
  };

  app.goToStep = function goToStep(step) {
    document.querySelectorAll(".setup-step").forEach((section) => {
      section.classList.toggle("hidden", section.dataset.step !== String(step));
    });
    document.querySelectorAll("[data-step-tab]").forEach((tab) => {
      const active = tab.dataset.stepTab === String(step);
      tab.className = active
        ? "rounded-xl border border-indigo-600 bg-indigo-50 px-3 py-3 text-left text-sm font-semibold text-indigo-700"
        : "rounded-xl border border-slate-200 bg-white px-3 py-3 text-left text-sm text-slate-500";
    });
    if (step === 6) {
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
        if (!Number.isNaN(step) && step >= 1 && step <= 6) {
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
    app.renderOnboardingLanguageRows([], {markTouched: false});
    app.toggleProviderFields();
  };

  window.OnboardingApp = app;
  window.goToStep = app.goToStep;
})();
