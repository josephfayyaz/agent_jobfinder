/*
 * Settings core helpers and shared state.
 *
 * The settings screen is still server-rendered, so we keep a small namespace
 * instead of introducing a bundler. Each concern area extends this shared
 * object.
 */

(() => {
  const app = window.SettingsApp || {};
  const providerController = window.ProviderController || {};

  app.parsePageData = function parsePageData() {
    const el = document.getElementById("settings-page-data");
    if (!el || !el.textContent) {
      return {
        languageOptions: [],
        languageLevelOptions: [],
        initialJobLanguages: [],
        shareUrl: "",
        activeCandidateId: "",
      };
    }
    try {
      return JSON.parse(el.textContent);
    } catch (_error) {
      return {
        languageOptions: [],
        languageLevelOptions: [],
        initialJobLanguages: [],
        shareUrl: "",
        activeCandidateId: "",
      };
    }
  };

  const pageData = app.parsePageData();
  app.state = {
    languageOptions: pageData.languageOptions || [],
    languageLevelOptions: pageData.languageLevelOptions || [],
    initialJobLanguages: pageData.initialJobLanguages || [],
    shareUrl: pageData.shareUrl || "",
    activeCandidateId: pageData.activeCandidateId || "",
  };

  app.settingsTimeoutSignal = function settingsTimeoutSignal(timeoutMs = 12000) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    return {
      signal: controller.signal,
      cancel() {
        clearTimeout(timer);
      },
    };
  };

  app.settingsFetchJson = async function settingsFetchJson(url, options = {}, timeoutMs = 12000) {
    const timeout = app.settingsTimeoutSignal(timeoutMs);
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
    return providerController.nonEmbeddingModels(models);
  };

  app.chooseLocalModelDefaults = function chooseLocalModelDefaults(models) {
    return providerController.chooseLocalModelDefaults(models);
  };

  app.syncRangeLabel = function syncRangeLabel(inputId, labelId) {
    const input = document.getElementById(inputId);
    const label = document.getElementById(labelId);
    if (input && label) {
      label.textContent = input.value;
    }
  };

  app.settingsSelect = function settingsSelect(options, selectedValue, className) {
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

  app.addSettingsLanguageRow = function addSettingsLanguageRow(value = {name: "English", level: "professional"}) {
    const container = document.getElementById("settings-language-rows");
    if (!container) {
      return;
    }

    const row = document.createElement("div");
    row.className = "grid gap-3 rounded-xl border border-[var(--border)] bg-[rgba(15,27,46,0.6)] px-3 py-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]";

    const nameSelect = app.settingsSelect(
      app.state.languageOptions,
      value.name || "English",
      "settings-job-language-name field-select"
    );
    const levelSelect = app.settingsSelect(
      app.state.languageLevelOptions,
      value.level || "professional",
      "settings-job-language-level field-select"
    );

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.className = "app-button app-button--sm app-button--danger";
    removeButton.textContent = "Remove";
    removeButton.addEventListener("click", () => row.remove());

    row.appendChild(nameSelect);
    row.appendChild(levelSelect);
    row.appendChild(removeButton);
    container.appendChild(row);
  };

  app.readSettingsLanguageRows = function readSettingsLanguageRows() {
    const rows = [];
    document.querySelectorAll("#settings-language-rows > div").forEach((row) => {
      const name = row.querySelector(".settings-job-language-name")?.value?.trim();
      const level = row.querySelector(".settings-job-language-level")?.value?.trim() || "professional";
      if (!name || rows.some((item) => item.name.toLowerCase() === name.toLowerCase())) {
        return;
      }
      rows.push({name, level});
    });
    return rows;
  };

  app.ensureSettingsLanguageRows = function ensureSettingsLanguageRows() {
    const container = document.getElementById("settings-language-rows");
    if (!container) {
      return;
    }
    container.innerHTML = "";
    app.state.initialJobLanguages.forEach((item) => app.addSettingsLanguageRow(item));
    if (!container.children.length) {
      app.addSettingsLanguageRow();
    }
  };

  app.copyShareLink = async function copyShareLink() {
    const status = document.getElementById("share-status");
    try {
      await navigator.clipboard.writeText(app.state.shareUrl);
      if (status) {
        status.textContent = "✓ Share link copied";
      }
    } catch (_error) {
      if (status) {
        status.textContent = "✗ Could not access clipboard";
      }
    }
  };

  app.toggleDangerBox = function toggleDangerBox(id) {
    const el = document.getElementById(id);
    if (el) {
      el.classList.toggle("hidden");
    }
  };

  app.readProviderEntries = function readProviderEntries(form) {
    if (!form) {
      return {openai: "", gemini: "", anthropic: ""};
    }
    return {
      openai: (form.elements.openai_entry?.value || "").trim(),
      gemini: (form.elements.gemini_entry?.value || "").trim(),
      anthropic: (form.elements.anthropic_entry?.value || "").trim(),
    };
  };

  app.readGmailEntries = function readGmailEntries(form) {
    if (!form) {
      return {clientId: "", clientEntry: ""};
    }
    return {
      clientId: (form.elements.gmail_connect_id?.value || "").trim(),
      clientEntry: (form.elements.gmail_connect_entry?.value || "").trim(),
    };
  };

  window.SettingsApp = app;
  window.copyShareLink = app.copyShareLink;
  window.toggleDangerBox = app.toggleDangerBox;
})();
