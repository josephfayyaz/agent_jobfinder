/*
 * Provider settings controller.
 */

(() => {
  const app = window.SettingsApp;
  const providerController = window.ProviderController;

  app.setProviderStatus = function setProviderStatus(message, tone = "neutral") {
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
  };

  app.refreshLocalModelChoices = function refreshLocalModelChoices(models) {
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
  };

  app.syncSingleLocalModelFields = function syncSingleLocalModelFields(form) {
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
  };

  app.providerFlags = function providerFlags(form) {
    const selected = form.querySelector('input[name="provider_mode"]:checked');
    const mode = selected ? selected.value : "";
    return providerController.buildProviderFlags(mode);
  };

  app.syncProviderVisibility = function syncProviderVisibility(form = document.getElementById("provider-form")) {
    if (!form) {
      return;
    }
    const mode = form.querySelector('input[name="provider_mode"]:checked')?.value || "";

    form.querySelectorAll("[data-provider-panel]").forEach((panel) => {
      const visibleModes = String(panel.dataset.providerPanel || "")
        .split(/\s+/)
        .map((item) => item.trim())
        .filter(Boolean);
      const shouldHide = visibleModes.length ? !visibleModes.includes(mode) : false;
      panel.classList.toggle("hidden", shouldHide);
      panel.hidden = shouldHide;
    });

    form.querySelectorAll("[data-provider-action]").forEach((button) => {
      const visibleFor = String(button.dataset.providerAction || "").trim();
      const shouldHide = Boolean(visibleFor) && visibleFor !== mode;
      button.classList.toggle("hidden", shouldHide);
      button.hidden = shouldHide;
    });
  };

  app.saveSection = async function saveSection(formId, fields) {
    const form = document.getElementById(formId);
    if (!form) {
      return;
    }
    const data = {};

    for (const field of fields) {
      if (field === "job_search_languages") {
        data[field] = app.readSettingsLanguageRows();
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
      const mode = form.querySelector('input[name="provider_mode"]:checked')?.value || "";
      Object.assign(
        data,
        providerController.buildBaseSavePayload({
          mode,
          openaiKey: form.elements.openai_api_key?.value || "",
          geminiKey: form.elements.gemini_api_key?.value || "",
          anthropicKey: form.elements.anthropic_api_key?.value || "",
          lmStudioUrl: form.elements.lm_studio_base_url?.value || "",
          ollamaUrl: form.elements.ollama_base_url?.value || "",
        }),
      );
      app.syncSingleLocalModelFields(form);
      const lmStudioLocal = (form.elements.lm_studio_local_model?.value || "").trim();
      const ollamaLocal = (form.elements.ollama_local_model?.value || "").trim();
      providerController.applyLocalProviderModels({
        mode,
        payload: data,
        selectedLmStudioModel: lmStudioLocal,
        selectedOllamaModel: ollamaLocal,
      });
    }

    const status = document.getElementById(formId.replace("-form", "-status")) || document.getElementById("system-status");
    try {
      const {response, data: payload} = await app.settingsFetchJson("/settings/save", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data),
      }, 12000);

      if (response.ok) {
        app.syncProviderVisibility(document.getElementById(formId));
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
  };

  app.testLmStudio = async function testLmStudio() {
    const input = document.querySelector('#provider-form [name="lm_studio_base_url"]');
    const url = input ? input.value.trim() : "";
    app.setProviderStatus("Checking LM Studio...");
    try {
      const {response, data} = await app.settingsFetchJson(`/lm-studio/models?base_url=${encodeURIComponent(url)}`, {}, 8000);
      if (!response.ok) {
        app.setProviderStatus(data.detail || "LM Studio check failed.", "error");
        return;
      }
      app.refreshLocalModelChoices(data.models || []);
      if (data.online && (data.models || []).length) {
        app.setProviderStatus(`LM Studio online — ${(data.models || []).length} models found.`, "success");
        return;
      }
      app.setProviderStatus("LM Studio reachable, but no models were found. Load at least one chat model in LM Studio.", "error");
    } catch (error) {
      const message = error?.name === "AbortError" ? "LM Studio check timed out." : `LM Studio check failed: ${error.message || error}`;
      app.setProviderStatus(message, "error");
    }
  };

  app.testOllama = async function testOllama() {
    const input = document.querySelector('#provider-form [name="ollama_base_url"]');
    const url = input ? input.value.trim() : "";
    app.setProviderStatus("Checking Ollama...");
    try {
      const {response, data} = await app.settingsFetchJson(`/ollama/models?base_url=${encodeURIComponent(url)}`, {}, 8000);
      if (!response.ok) {
        app.setProviderStatus(data.detail || "Ollama check failed.", "error");
        return;
      }
      if (data.online && (data.models || []).length) {
        app.setProviderStatus(`Ollama online — ${(data.models || []).length} models found.`, "success");
        return;
      }
      app.setProviderStatus("Ollama reachable, but no models were found. Pull a model first.", "error");
    } catch (error) {
      const message = error?.name === "AbortError" ? "Ollama check timed out." : `Ollama check failed: ${error.message || error}`;
      app.setProviderStatus(message, "error");
    }
  };

  app.validateProviderForm = async function validateProviderForm() {
    const form = document.getElementById("provider-form");
    if (!form) {
      return;
    }
    const validateButton = Array.from(form.querySelectorAll("button")).find((button) => button.textContent.includes("Validate Selected Provider"));
    const mode = form.querySelector('input[name="provider_mode"]:checked')?.value || "";
    const openaiKey = (form.elements.openai_api_key?.value || "").trim();
    const geminiKey = (form.elements.gemini_api_key?.value || "").trim();
    const anthropicKey = (form.elements.anthropic_api_key?.value || "").trim();
    const lmStudioUrl = (form.elements.lm_studio_base_url?.value || "").trim();
    const ollamaUrl = (form.elements.ollama_base_url?.value || "").trim();
    const lmStudioLocal = (form.elements.lm_studio_local_model?.value || "").trim();
    const ollamaLocal = (form.elements.ollama_local_model?.value || "").trim();

    app.setProviderStatus("Validating…");
    if (validateButton) {
      validateButton.disabled = true;
      validateButton.innerHTML = '<span class="spin"></span> Validating…';
    }

    try {
      const validationPayload = providerController.buildValidationPayload({
        mode,
        openaiKey,
        geminiKey,
        anthropicKey,
        lmStudioUrl,
        ollamaUrl,
      });
      const {response, data} = await providerController.validateProvider(
        validationPayload,
        app.settingsFetchJson,
        15000,
      );
      if (!response.ok || !data.ok) {
        app.setProviderStatus(data.detail || "Provider not ready.", "error");
        return;
      }

      const savePayload = providerController.buildBaseSavePayload({
        mode,
        openaiKey,
        geminiKey,
        anthropicKey,
        lmStudioUrl,
        ollamaUrl,
      });
      const discoveredModels = Array.isArray(data.models) ? data.models.filter(Boolean) : [];
      const chosen = app.chooseLocalModelDefaults(discoveredModels);
      if (mode === "lm_studio") {
        app.refreshLocalModelChoices(discoveredModels);
        const result = providerController.applyLocalProviderModels({
          mode,
          payload: savePayload,
          chosenModels: chosen,
          selectedLmStudioModel: lmStudioLocal,
        });
        if (!result.ok) {
          app.setProviderStatus(result.message, "error");
          return;
        }
        if (form.elements.lm_studio_local_model) {
          form.elements.lm_studio_local_model.value = result.selectedModel;
        }
      }
      if (mode === "ollama") {
        const result = providerController.applyLocalProviderModels({
          mode,
          payload: savePayload,
          chosenModels: chosen,
          selectedOllamaModel: ollamaLocal,
        });
        if (!result.ok) {
          app.setProviderStatus(result.message, "error");
          return;
        }
        if (form.elements.ollama_local_model) {
          form.elements.ollama_local_model.value = result.selectedModel;
        }
      }

      const {response: saveResponse, data: saveData} = await app.settingsFetchJson("/settings/save", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(savePayload),
      }, 12000);
      if (!saveResponse.ok) {
        app.setProviderStatus(saveData.detail || "Verified, but saving failed.", "error");
        return;
      }
      app.syncProviderVisibility(form);
      app.setProviderStatus(data.detail || "Provider verified and saved.", "success");
    } catch (error) {
      const message = error?.name === "AbortError" ? "Provider validation timed out. Check the provider and try again." : `Provider validation failed: ${error.message || error}`;
      app.setProviderStatus(message, "error");
    } finally {
      if (validateButton) {
        validateButton.disabled = false;
        validateButton.textContent = "Validate Selected Provider";
      }
    }
  };

  window.saveSection = app.saveSection;
  window.testLmStudio = app.testLmStudio;
  window.testOllama = app.testOllama;
  window.validateProviderForm = app.validateProviderForm;
})();
