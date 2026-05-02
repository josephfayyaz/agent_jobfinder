/*
 * Settings screen controller.
 *
 * The page still combines provider setup, search preferences, integrations,
 * and advanced maintenance actions. The next cleanup should split those
 * sections into focused modules without changing the persisted settings shape.
 */

const _settingsPageData = (() => {
  const el = document.getElementById("settings-page-data");
  if (!el || !el.textContent) {
    return {
      languageOptions: [],
      languageLevelOptions: [],
      initialJobLanguages: [],
      shareUrl: "",
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
    };
  }
})();

const settingsLanguageOptions = _settingsPageData.languageOptions || [];
const settingsLanguageLevelOptions = _settingsPageData.languageLevelOptions || [];
const settingsInitialJobLanguages = _settingsPageData.initialJobLanguages || [];
const settingsShareUrl = _settingsPageData.shareUrl || "";
const settingsActiveCandidateId = _settingsPageData.activeCandidateId || "";

// Provider checks need explicit timeouts so the settings page stays responsive.
function settingsTimeoutSignal(timeoutMs = 12000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  return {
    signal: controller.signal,
    cancel() {
      clearTimeout(timer);
    },
  };
}

async function settingsFetchJson(url, options = {}, timeoutMs = 12000) {
  const timeout = settingsTimeoutSignal(timeoutMs);
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
}

function setProviderStatus(message, tone = "neutral") {
  const status = document.getElementById("provider-status");
  if (!status) {
    return;
  }
  status.textContent = message || "";
  status.className =
    tone === "error"
      ? "text-sm text-danger"
      : tone === "success"
        ? "text-sm text-success"
        : "text-sm text-muted";
}

function nonEmbeddingModels(models) {
  return (models || []).filter((name) => !/embed/i.test(name));
}

function chooseLocalModelDefaults(models) {
  const chatModels = nonEmbeddingModels(models);
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
}

function refreshLocalModelChoices(models) {
  const names = Array.isArray(models) ? models.filter(Boolean) : [];
  ["lm_studio_local_model"].forEach((fieldName) => {
    const el = document.querySelector(`#provider-form [name="${fieldName}"]`);
    if (!el || el.tagName !== "SELECT") {
      return;
    }
    const current = el.value;
    el.innerHTML = "";
    names.forEach((name) => {
      const option = document.createElement("option");
      option.value = name;
      option.textContent = name;
      if (name === current) {
        option.selected = true;
      }
      el.appendChild(option);
    });
  });
}

function syncSingleLocalModelFields(form) {
  if (!form) {
    return;
  }
  const lmStudioLocal = (form.elements.lm_studio_local_model?.value || "").trim();
  if (lmStudioLocal) {
    if (form.elements.lm_studio_small_model) form.elements.lm_studio_small_model.value = lmStudioLocal;
    if (form.elements.lm_studio_writer_model) form.elements.lm_studio_writer_model.value = lmStudioLocal;
    if (form.elements.lm_studio_mid_model) form.elements.lm_studio_mid_model.value = lmStudioLocal;
  }

  const ollamaLocal = (form.elements.ollama_local_model?.value || "").trim();
  if (ollamaLocal) {
    if (form.elements.ollama_fast_model) form.elements.ollama_fast_model.value = ollamaLocal;
    if (form.elements.ollama_writer_model) form.elements.ollama_writer_model.value = ollamaLocal;
  }
}

function syncRangeLabel(inputId, labelId) {
  const input = document.getElementById(inputId);
  const label = document.getElementById(labelId);
  if (input && label) {
    label.textContent = input.value;
  }
}

function providerFlags(form) {
  const selected = form.querySelector('input[name="provider_mode"]:checked');
  const mode = selected ? selected.value : "openai";
  return {
    llm_provider_mode: mode,
    use_openai_review: mode === "openai",
    use_claude_final_review: mode === "anthropic",
  };
}

function settingsSelect(options, selectedValue, className) {
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
}

function addSettingsLanguageRow(value = {name: "English", level: "professional"}) {
  const container = document.getElementById("settings-language-rows");
  if (!container) {
    return;
  }

  const row = document.createElement("div");
  row.className = "grid gap-3 rounded-xl border border-[var(--border)] bg-[rgba(15,27,46,0.6)] px-3 py-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]";

  const nameSelect = settingsSelect(
    settingsLanguageOptions,
    value.name || "English",
    "settings-job-language-name field-select"
  );
  const levelSelect = settingsSelect(
    settingsLanguageLevelOptions,
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
}

function readSettingsLanguageRows() {
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
}

function ensureSettingsLanguageRows() {
  const container = document.getElementById("settings-language-rows");
  if (!container) {
    return;
  }
  container.innerHTML = "";
  settingsInitialJobLanguages.forEach((item) => addSettingsLanguageRow(item));
  if (!container.children.length) {
    addSettingsLanguageRow();
  }
}

async function saveSection(formId, fields) {
  const form = document.getElementById(formId);
  if (!form) {
    return;
  }
  const data = {};

  for (const field of fields) {
    if (field === "job_search_languages") {
      data[field] = readSettingsLanguageRows();
      continue;
    }

    const el = form.elements[field];
    if (!el) {
      continue;
    }

    if (el.type === "checkbox") {
      data[field] = el.checked;
      continue;
    }

    const value = typeof el.value === "string" ? el.value.trim() : el.value;
    if (value === "") {
      continue;
    }

    if (field === "jobspy_discover_queries") {
      data[field] = value.split("\n").map((item) => item.trim()).filter(Boolean);
    } else if (field === "job_search_countries") {
      const countries = value.split("\n").map((item) => item.trim()).filter(Boolean);
      data[field] = countries.length ? [countries[0]] : ["Italy"];
    } else if (["match_min_score", "discovery_min_fit_score", "discovery_max_visible_jobs", "cv_pass_score", "cv_revise_score", "bullet_clarify_word_limit"].includes(field)) {
      const parsed = parseInt(value, 10);
      if (!Number.isNaN(parsed)) {
        data[field] = parsed;
      }
    } else {
      data[field] = value;
    }
  }

  if (formId === "provider-form") {
    Object.assign(data, providerFlags(form));
    syncSingleLocalModelFields(form);
    const lmStudioLocal = (form.elements.lm_studio_local_model?.value || "").trim();
    const ollamaLocal = (form.elements.ollama_local_model?.value || "").trim();
    if (lmStudioLocal) {
      data.lm_studio_small_model = lmStudioLocal;
      data.lm_studio_writer_model = lmStudioLocal;
      data.lm_studio_mid_model = lmStudioLocal;
    }
    if (ollamaLocal) {
      data.ollama_fast_model = ollamaLocal;
      data.ollama_writer_model = ollamaLocal;
    }
  }

  const status = document.getElementById(formId.replace("-form", "-status")) || document.getElementById("system-status");
  try {
    const {response, data: payload} = await settingsFetchJson("/settings/save", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(data),
    }, 12000);

    if (response.ok) {
      if (status) {
        status.textContent = "✓ Saved";
      }
      setTimeout(() => {
        if (status) {
          status.textContent = "";
        }
      }, 3000);
    } else if (status) {
      status.textContent = payload.detail || "✗ Save failed";
    }
  } catch (error) {
    if (status) {
      status.textContent = error?.name === "AbortError" ? "✗ Save timed out" : "✗ Save failed";
    }
  }
}

async function suggestDiscoveryRoles() {
  const queriesInput = document.querySelector('[name="jobspy_discover_queries"]');
  const status = document.getElementById("system-status");
  if (!queriesInput) {
    return;
  }

  const params = new URLSearchParams();
  if (settingsActiveCandidateId) {
    params.set("candidate_id", settingsActiveCandidateId);
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
    const {response, data} = await settingsFetchJson(`/search/preferences/recommendations${suffix ? `?${suffix}` : ""}`);
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
    syncRoleCount();
    if (status) {
      status.textContent = "Profile-based role suggestions loaded.";
    }
  } catch (error) {
    if (status) {
      status.textContent = error.message || "Could not refresh role suggestions.";
    }
  }
}

async function testLmStudio() {
  const input = document.querySelector('#provider-form [name="lm_studio_base_url"]');
  const url = input ? input.value.trim() : "";
  setProviderStatus("Checking LM Studio...");
  try {
    const {response, data} = await settingsFetchJson(`/lm-studio/models?base_url=${encodeURIComponent(url)}`, {}, 8000);
    if (!response.ok) {
      setProviderStatus(data.detail || "LM Studio check failed.", "error");
      return;
    }
    refreshLocalModelChoices(data.models || []);
    if (data.online && (data.models || []).length) {
      setProviderStatus(`LM Studio online — ${(data.models || []).length} models found.`, "success");
      return;
    }
    setProviderStatus("LM Studio reachable, but no models were found. Load at least one chat model in LM Studio.", "error");
  } catch (error) {
    const message = error?.name === "AbortError" ? "LM Studio check timed out." : `LM Studio check failed: ${error.message || error}`;
    setProviderStatus(message, "error");
  }
}

async function testOllama() {
  const input = document.querySelector('#provider-form [name="ollama_base_url"]');
  const url = input ? input.value.trim() : "";
  setProviderStatus("Checking Ollama...");
  try {
    const {response, data} = await settingsFetchJson(`/ollama/models?base_url=${encodeURIComponent(url)}`, {}, 8000);
    if (!response.ok) {
      setProviderStatus(data.detail || "Ollama check failed.", "error");
      return;
    }
    if (data.online && (data.models || []).length) {
      setProviderStatus(`Ollama online — ${(data.models || []).length} models found.`, "success");
      return;
    }
    setProviderStatus("Ollama reachable, but no models were found. Pull a model first.", "error");
  } catch (error) {
    const message = error?.name === "AbortError" ? "Ollama check timed out." : `Ollama check failed: ${error.message || error}`;
    setProviderStatus(message, "error");
  }
}

async function validateProviderForm() {
  const form = document.getElementById("provider-form");
  if (!form) {
    return;
  }
  const validateButton = Array.from(form.querySelectorAll("button")).find((button) => button.textContent.includes("Validate Selected Provider"));
  const mode = form.querySelector('input[name="provider_mode"]:checked')?.value || "openai";
  const openaiKey = (form.elements.openai_api_key?.value || "").trim();
  const anthropicKey = (form.elements.anthropic_api_key?.value || "").trim();
  const lmStudioUrl = (form.elements.lm_studio_base_url?.value || "").trim();
  const ollamaUrl = (form.elements.ollama_base_url?.value || "").trim();
  const lmStudioLocal = (form.elements.lm_studio_local_model?.value || "").trim();
  const ollamaLocal = (form.elements.ollama_local_model?.value || "").trim();
  const openaiReviewModel = (form.elements.openai_review_model?.value || "").trim();

  setProviderStatus("Validating…");
  if (validateButton) {
    validateButton.disabled = true;
    validateButton.innerHTML = '<span class="spin"></span> Validating…';
  }

  try {
    const {response, data} = await settingsFetchJson("/providers/validate", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        provider_mode: mode,
        openai_api_key: openaiKey,
        anthropic_api_key: anthropicKey,
        openai_review_model: openaiReviewModel,
        lm_studio_base_url: lmStudioUrl,
        ollama_base_url: ollamaUrl,
      }),
    }, 15000);
    if (!response.ok || !data.ok) {
      setProviderStatus(data.detail || "Provider not ready.", "error");
      return;
    }

    const savePayload = {
      ...providerFlags(form),
      lm_studio_base_url: lmStudioUrl || "http://localhost:1234/v1",
      ollama_base_url: ollamaUrl || "http://localhost:11434",
      openai_review_model: openaiReviewModel,
      openai_escalation_model: (form.elements.openai_escalation_model?.value || "").trim(),
      anthropic_model: (form.elements.anthropic_model?.value || "").trim(),
    };
    const discoveredModels = Array.isArray(data.models) ? data.models.filter(Boolean) : [];
    const chosen = chooseLocalModelDefaults(discoveredModels);
    if (mode === "lm_studio") {
      refreshLocalModelChoices(discoveredModels);
      const selectedLocal = lmStudioLocal || chosen.writer || chosen.small;
      savePayload.lm_studio_small_model = selectedLocal;
      savePayload.lm_studio_writer_model = selectedLocal;
      savePayload.lm_studio_mid_model = selectedLocal;
      if (!selectedLocal) {
        setProviderStatus("LM Studio responded, but no usable chat models were found.", "error");
        return;
      }
      if (form.elements.lm_studio_local_model) {
        form.elements.lm_studio_local_model.value = selectedLocal;
      }
    }
    if (mode === "ollama") {
      const selectedLocal = ollamaLocal || chosen.writer || chosen.small;
      savePayload.ollama_fast_model = selectedLocal;
      savePayload.ollama_writer_model = selectedLocal;
      if (!selectedLocal) {
        setProviderStatus("Ollama responded, but no usable chat models were found.", "error");
        return;
      }
      if (form.elements.ollama_local_model) {
        form.elements.ollama_local_model.value = selectedLocal;
      }
    }
    if (openaiKey) {
      savePayload.openai_api_key = openaiKey;
    }
    if (anthropicKey) {
      savePayload.anthropic_api_key = anthropicKey;
    }

    const {response: saveResponse, data: saveData} = await settingsFetchJson("/settings/save", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(savePayload),
    }, 12000);
    if (!saveResponse.ok) {
      setProviderStatus(saveData.detail || "Verified, but saving failed.", "error");
      return;
    }
    setProviderStatus(data.detail || "Provider verified and saved.", "success");
  } catch (error) {
    const message = error?.name === "AbortError" ? "Provider validation timed out. Check the provider and try again." : `Provider validation failed: ${error.message || error}`;
    setProviderStatus(message, "error");
  } finally {
    if (validateButton) {
      validateButton.disabled = false;
      validateButton.textContent = "Validate Selected Provider";
    }
  }
}

async function connectGmailOAuth() {
  const form = document.getElementById("gmail-form");
  const status = document.getElementById("gmail-status");
  if (!form || !status) {
    return;
  }

  status.textContent = "Saving OAuth settings…";
  const savePayload = {
    gmail_oauth_client_id: (form.elements.gmail_oauth_client_id?.value || "").trim(),
    gmail_oauth_client_secret: (form.elements.gmail_oauth_client_secret?.value || "").trim(),
    gmail_label_filter: (form.elements.gmail_label_filter?.value || "").trim(),
    gmail_auto_sync: !!form.elements.gmail_auto_sync?.checked,
  };
  if (!savePayload.gmail_oauth_client_id) {
    status.textContent = "Paste OAuth Client ID first.";
    return;
  }

  const saveResp = await fetch("/settings/save", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(savePayload),
  });
  if (!saveResp.ok) {
    status.textContent = "✗ Could not save OAuth settings";
    return;
  }

  status.textContent = "Opening Google consent…";
  const response = await fetch("/gmail/oauth/start", {method: "POST"});
  const payload = await response.json();
  if (!response.ok || !payload.auth_url) {
    status.textContent = "✗ " + (payload.detail || "Could not start OAuth flow");
    return;
  }
  window.location.href = payload.auth_url;
}

async function disconnectGmailOAuth() {
  const status = document.getElementById("gmail-status");
  if (status) {
    status.textContent = "Disconnecting…";
  }
  const response = await fetch("/gmail/oauth/disconnect", {method: "POST"});
  if (response.ok) {
    if (status) {
      status.textContent = "✓ Gmail disconnected";
    }
    window.location.reload();
    return;
  }
  if (status) {
    status.textContent = "✗ Disconnect failed";
  }
}

async function reloadSettings() {
  const response = await fetch("/settings/reload", {method: "POST"});
  const status = document.getElementById("system-status");
  if (!status) {
    return;
  }
  status.textContent = response.ok ? "✓ Reloaded" : "✗ Failed";
}

async function copyShareLink() {
  const status = document.getElementById("share-status");
  try {
    await navigator.clipboard.writeText(settingsShareUrl);
    if (status) {
      status.textContent = "✓ Share link copied";
    }
  } catch (_error) {
    if (status) {
      status.textContent = "✗ Could not access clipboard";
    }
  }
}

function toggleDangerBox(id) {
  const el = document.getElementById(id);
  if (el) {
    el.classList.toggle("hidden");
  }
}

async function runWorkspaceDanger(action, inputId, expectedPhrase, statusId) {
  const input = document.getElementById(inputId);
  const status = document.getElementById(statusId);
  const phrase = input ? input.value.trim() : "";

  if (!phrase) {
    if (status) {
      status.textContent = "Enter the confirmation phrase first.";
    }
    return;
  }
  if (phrase !== expectedPhrase) {
    if (status) {
      status.textContent = `Type exactly: ${expectedPhrase}`;
    }
    return;
  }

  if (status) {
    status.textContent = "Working…";
  }
  const openBackups = action === "reset" && !!document.getElementById("reset-open-backups")?.checked;
  const response = await fetch(`/workspace/${action}`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({phrase}),
  });

  if (response.ok) {
    const target = action === "reset"
      ? `/ui/workspace-reset?mode=reset${openBackups ? "&open=1" : ""}`
      : "/ui/workspace-reset?mode=delete";
    window.location.href = target;
    return;
  }

  let detail = "Action failed";
  try {
    const payload = await response.json();
    detail = typeof payload.detail === "string" ? payload.detail : detail;
  } catch (_error) {
    // Keep default detail.
  }
  if (status) {
    status.textContent = "✗ " + detail;
  }
}

function syncRoleCount() {
  const queriesInput = document.querySelector('[name="jobspy_discover_queries"]');
  const roleCount = document.getElementById("role-count");
  if (!queriesInput || !roleCount) {
    return;
  }

  const count = queriesInput.value.split("\n").filter((line) => line.trim()).length;
  roleCount.textContent = String(count);
  queriesInput.style.borderColor = count > 4 ? "rgb(239,68,68)" : "";
}

document.addEventListener("DOMContentLoaded", () => {
  const queriesInput = document.querySelector('[name="jobspy_discover_queries"]');
  if (queriesInput) {
    queriesInput.addEventListener("input", syncRoleCount);
    syncRoleCount();
  }
  document.getElementById("suggest-discovery-roles")?.addEventListener("click", suggestDiscoveryRoles);

  ensureSettingsLanguageRows();
  syncRangeLabel("discovery_min_fit_score", "discovery-fit-value");
  syncRangeLabel("cv_pass_score", "cv-pass-value");
  syncRangeLabel("cv_revise_score", "cv-revise-value");
  const providerForm = document.getElementById("provider-form");
  providerForm?.elements.lm_studio_local_model?.addEventListener("change", () => syncSingleLocalModelFields(providerForm));
  providerForm?.elements.ollama_local_model?.addEventListener("change", () => syncSingleLocalModelFields(providerForm));

  const params = new URLSearchParams(window.location.search);
  const gmailOauth = params.get("gmail_oauth");
  const gmailStatus = document.getElementById("gmail-status");
  if (gmailStatus && gmailOauth === "connected") {
    gmailStatus.textContent = "✓ Gmail OAuth connected";
  }
});
