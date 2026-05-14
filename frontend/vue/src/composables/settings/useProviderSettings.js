import { computed, reactive, ref } from "vue";

import {
  fetchLmStudioModels,
  fetchOllamaModels,
  saveSettings,
  validateProvider,
} from "../../api/providerApi";
import { useSettingsData } from "./useSettingsData";
import {
  PROVIDERS,
  applyLocalProviderModels,
  buildBaseSavePayload,
  buildValidationPayload,
  chooseLocalModelDefaults,
  nonEmbeddingModels,
} from "./providerHelpers";

const DEFAULT_LM_STUDIO_URL = "http://localhost:1234/v1";
const DEFAULT_OLLAMA_URL = "http://localhost:11434";

function providerFromPayload(payload) {
  return payload?.data?.provider || payload?.provider || {};
}

function cleanModels(models) {
  return nonEmbeddingModels(Array.isArray(models) ? models.filter(Boolean) : []);
}

export function useProviderSettings() {
  const { settingsPayload, settingsLoading, settingsError, loadSettings } = useSettingsData();

  const selectedProvider = ref("openai");
  const saving = ref(false);
  const validating = ref(false);
  const lmStudioLoading = ref(false);
  const ollamaLoading = ref(false);
  const lmStudioModels = ref([]);
  const ollamaModels = ref([]);
  const status = reactive({ message: "", tone: "neutral" });
  const configured = reactive({
    openai: false,
    gemini: false,
    anthropic: false,
    lmStudio: false,
    ollama: false,
  });
  const providerForm = reactive({
    lmStudioUrl: DEFAULT_LM_STUDIO_URL,
    lmStudioModel: "",
    ollamaUrl: DEFAULT_OLLAMA_URL,
    ollamaModel: "",
    openaiKey: "",
    geminiKey: "",
    anthropicKey: "",
  });

  const busy = computed(
    () => saving.value || validating.value || lmStudioLoading.value || ollamaLoading.value,
  );
  const providerLabel = computed(
    () => PROVIDERS.find((item) => item.value === selectedProvider.value)?.label || "AI provider",
  );

  function setStatus(message, tone = "neutral") {
    status.message = message;
    status.tone = tone;
  }

  function providerInput() {
    return {
      mode: selectedProvider.value,
      openaiKey: providerForm.openaiKey,
      geminiKey: providerForm.geminiKey,
      anthropicKey: providerForm.anthropicKey,
      lmStudioUrl: providerForm.lmStudioUrl,
      ollamaUrl: providerForm.ollamaUrl,
    };
  }

  function clearSubmittedApiKeys() {
    providerForm.openaiKey = "";
    providerForm.geminiKey = "";
    providerForm.anthropicKey = "";
  }

  function hydrateProviderSettings(payload) {
    const provider = providerFromPayload(payload);
    selectedProvider.value = provider.llm_provider_mode || provider.provider_mode || "openai";
    configured.openai = Boolean(provider.openai_configured);
    configured.gemini = Boolean(provider.gemini_configured);
    configured.anthropic = Boolean(provider.anthropic_configured);
    configured.lmStudio = Boolean(provider.lm_studio_configured);
    configured.ollama = Boolean(provider.ollama_configured);
    providerForm.lmStudioUrl = provider.lm_studio_base_url || DEFAULT_LM_STUDIO_URL;
    providerForm.ollamaUrl = provider.ollama_base_url || DEFAULT_OLLAMA_URL;
    providerForm.lmStudioModel =
      provider.lm_studio_writer_model || provider.lm_studio_small_model || provider.lm_studio_mid_model || "";
    providerForm.ollamaModel = provider.ollama_writer_model || provider.ollama_fast_model || "";
  }

  async function loadProviderSettings() {
    setStatus("");
    try {
      const payload = await loadSettings();
      hydrateProviderSettings(payload);
    } catch (error) {
      setStatus(error?.message || "Settings could not be loaded.", "error");
    }
  }

  function applyLocalModelsToPayload(payload) {
    const mode = selectedProvider.value;
    const models = mode === "lm_studio" ? lmStudioModels.value : ollamaModels.value;
    const chosenModels = chooseLocalModelDefaults(models);
    const result = applyLocalProviderModels({
      mode,
      payload,
      chosenModels,
      selectedLmStudioModel: providerForm.lmStudioModel,
      selectedOllamaModel: providerForm.ollamaModel,
    });
    if (!result.ok) {
      throw new Error(result.message);
    }
    if (mode === "lm_studio") {
      providerForm.lmStudioModel = result.selectedModel;
    }
    if (mode === "ollama") {
      providerForm.ollamaModel = result.selectedModel;
    }
    return payload;
  }

  async function testLmStudio() {
    lmStudioLoading.value = true;
    setStatus("Checking LM Studio...");
    try {
      const data = await fetchLmStudioModels(providerForm.lmStudioUrl);
      lmStudioModels.value = cleanModels(data?.models);
      const defaults = chooseLocalModelDefaults(lmStudioModels.value);
      providerForm.lmStudioModel ||= defaults.writer || defaults.small;
      if (data?.online && lmStudioModels.value.length) {
        setStatus(`LM Studio online - ${lmStudioModels.value.length} chat models found.`, "success");
      } else if (data?.online) {
        setStatus("LM Studio responded, but no usable chat models were found.", "error");
      } else {
        setStatus(data?.error || "LM Studio is not reachable.", "error");
      }
    } catch (error) {
      setStatus(error?.message || "LM Studio check failed.", "error");
    } finally {
      lmStudioLoading.value = false;
    }
  }

  async function testOllama() {
    ollamaLoading.value = true;
    setStatus("Checking Ollama...");
    try {
      const data = await fetchOllamaModels(providerForm.ollamaUrl);
      ollamaModels.value = cleanModels(data?.models);
      const defaults = chooseLocalModelDefaults(ollamaModels.value);
      providerForm.ollamaModel ||= defaults.writer || defaults.small;
      if (data?.online && ollamaModels.value.length) {
        setStatus(`Ollama online - ${ollamaModels.value.length} chat models found.`, "success");
      } else if (data?.online) {
        setStatus("Ollama responded, but no usable chat models were found.", "error");
      } else {
        setStatus(data?.error || "Ollama is not reachable.", "error");
      }
    } catch (error) {
      setStatus(error?.message || "Ollama check failed.", "error");
    } finally {
      ollamaLoading.value = false;
    }
  }

  async function saveProviderSettings() {
    saving.value = true;
    setStatus("Saving provider settings...");
    try {
      const payload = buildBaseSavePayload(providerInput());
      applyLocalModelsToPayload(payload);
      await saveSettings(payload);
      clearSubmittedApiKeys();
      setStatus(`${providerLabel.value} settings saved.`, "success");
    } catch (error) {
      setStatus(error?.message || "Provider settings could not be saved.", "error");
    } finally {
      saving.value = false;
    }
  }

  async function validateSelectedProvider() {
    if (!selectedProvider.value) {
      setStatus("Select a provider first.", "error");
      return;
    }

    validating.value = true;
    setStatus("Validating selected provider...");
    try {
      const validation = await validateProvider(buildValidationPayload(providerInput()));
      if (!validation?.ok) {
        setStatus(validation?.detail || "Provider not ready.", "error");
        return;
      }

      const discoveredModels = cleanModels(validation.models);
      if (selectedProvider.value === "lm_studio") {
        lmStudioModels.value = discoveredModels;
        const defaults = chooseLocalModelDefaults(discoveredModels);
        providerForm.lmStudioModel ||= defaults.writer || defaults.small;
      }
      if (selectedProvider.value === "ollama") {
        ollamaModels.value = discoveredModels;
        const defaults = chooseLocalModelDefaults(discoveredModels);
        providerForm.ollamaModel ||= defaults.writer || defaults.small;
      }

      const payload = buildBaseSavePayload(providerInput());
      applyLocalModelsToPayload(payload);
      await saveSettings(payload);
      clearSubmittedApiKeys();
      setStatus(validation.detail || `${providerLabel.value} verified and saved.`, "success");
    } catch (error) {
      setStatus(error?.message || "Provider validation failed.", "error");
    } finally {
      validating.value = false;
    }
  }

  function updateProviderField(field, value) {
    if (Object.prototype.hasOwnProperty.call(providerForm, field)) {
      providerForm[field] = value;
    }
  }

  return {
    PROVIDERS,
    selectedProvider,
    providerForm,
    configured,
    status,
    settingsPayload,
    settingsLoading,
    settingsError,
    saving,
    validating,
    busy,
    lmStudioLoading,
    ollamaLoading,
    lmStudioModels,
    ollamaModels,
    nonEmbeddingModels,
    loadProviderSettings,
    updateProviderField,
    saveProviderSettings,
    validateSelectedProvider,
    testLmStudio,
    testOllama,
  };
}
