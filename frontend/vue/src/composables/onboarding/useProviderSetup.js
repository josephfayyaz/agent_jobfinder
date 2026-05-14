import { computed, ref } from "vue";

import { saveSettings, validateProvider } from "../../services/onboardingApi";
import {
  applyLocalProviderModels as applyLocalProviderModelsToPayload,
  buildBaseSavePayload,
  buildValidationPayload as buildProviderValidationPayload,
  chooseLocalModelDefaults,
  nonEmbeddingModels,
} from "../settings/providerHelpers";

export { nonEmbeddingModels } from "../settings/providerHelpers";

const SHARED_PROVIDER_CONTRACT_FIELDS = [
  "provider_mode",
  "llm_provider_mode",
  "use_openai_review",
  "use_claude_final_review",
  "lm_studio_small_model",
  "lm_studio_writer_model",
  "lm_studio_mid_model",
  "ollama_fast_model",
  "ollama_writer_model",
];

export const PROVIDERS = [
  {
    value: "lm_studio",
    label: "Local Gateway",
    eyebrow: "LM Studio",
    description: "Use a local OpenAI-compatible gateway.",
  },
  {
    value: "ollama",
    label: "Ollama",
    eyebrow: "Local",
    description: "Use locally installed Ollama chat models.",
  },
  {
    value: "openai",
    label: "OpenAI",
    eyebrow: "Cloud",
    description: "Use your own OpenAI API key.",
  },
  {
    value: "anthropic",
    label: "Claude",
    eyebrow: "Cloud",
    description: "Use your own Anthropic API key.",
  },
  {
    value: "gemini",
    label: "Google Gemini",
    eyebrow: "Cloud",
    description: "Use your own Gemini API key.",
  },
];

export function useProviderSetup({ currentStep, setupData, onboardingData } = {}) {
  const selectedProvider = ref("");
  const providerBusy = ref(false);
  const providerStatus = ref("");
  const providerStatusError = ref(false);
  const providerSaved = ref(false);
  const lmStudioModels = ref([]);
  const ollamaModels = ref([]);

  const providerForm = ref({
    lmStudioUrl: "http://localhost:1234/v1",
    lmStudioModel: "",
    ollamaUrl: "http://localhost:11434",
    ollamaModel: "",
    openaiKey: "",
    anthropicKey: "",
    geminiKey: "",
  });

  const providerConfigured = computed(() =>
    Boolean(
      setupData?.value?.provider_ready ||
        setupData?.value?.provider_configured ||
        setupData?.value?.llm_provider_configured ||
        onboardingData?.value?.provider_ready ||
        onboardingData?.value?.provider_configured,
    ),
  );

  const providerReady = computed(() => providerSaved.value || providerConfigured.value);

  function setProviderStatus(message, isError = false) {
    providerStatus.value = message;
    providerStatusError.value = isError;
  }

  function selectProvider(provider) {
    selectedProvider.value = provider;
    providerSaved.value = false;
    setProviderStatus("");
  }

  function buildValidationPayload() {
    return buildProviderValidationPayload({
      mode: selectedProvider.value,
      openaiKey: providerForm.value.openaiKey,
      anthropicKey: providerForm.value.anthropicKey,
      geminiKey: providerForm.value.geminiKey,
      lmStudioUrl: providerForm.value.lmStudioUrl,
      ollamaUrl: providerForm.value.ollamaUrl,
    });
  }

  function buildSavePayload() {
    return buildBaseSavePayload({
      mode: selectedProvider.value,
      openaiKey: providerForm.value.openaiKey,
      anthropicKey: providerForm.value.anthropicKey,
      geminiKey: providerForm.value.geminiKey,
      lmStudioUrl: providerForm.value.lmStudioUrl,
      ollamaUrl: providerForm.value.ollamaUrl,
    });
  }

  function applyLocalProviderModels(payload) {
    const result = applyLocalProviderModelsToPayload({
      mode: selectedProvider.value,
      payload,
      chosenModels: chooseLocalModelDefaults(
        selectedProvider.value === "lm_studio" ? lmStudioModels.value : ollamaModels.value,
      ),
      selectedLmStudioModel: providerForm.value.lmStudioModel,
      selectedOllamaModel: providerForm.value.ollamaModel,
    });
    if (!result.ok && selectedProvider.value === "lm_studio") {
      throw new Error("No usable LM Studio chat model was found.");
    }
    if (!result.ok && selectedProvider.value === "ollama") {
      throw new Error("No usable Ollama chat model was found.");
    }
    if (selectedProvider.value === "lm_studio") {
      providerForm.value.lmStudioModel = result.selectedModel;
    }
    if (selectedProvider.value === "ollama") {
      providerForm.value.ollamaModel = result.selectedModel;
    }
  }

  function clearSubmittedApiKeys() {
    providerForm.value.openaiKey = "";
    providerForm.value.anthropicKey = "";
    providerForm.value.geminiKey = "";
  }

  async function validateAndSaveProvider() {
    if (!selectedProvider.value) {
      setProviderStatus("Select one provider before continuing.", true);
      currentStep.value = "ai";
      return;
    }

    providerBusy.value = true;
    providerSaved.value = false;
    setProviderStatus("Validating provider...");

    try {
      const validation = await validateProvider(buildValidationPayload());

      if (!validation?.ok) {
        setProviderStatus(validation?.detail || "Provider validation failed.", true);
        currentStep.value = "ai";
        return;
      }

      const discoveredModels = Array.isArray(validation.models) ? validation.models : [];

      if (selectedProvider.value === "lm_studio") {
        lmStudioModels.value = discoveredModels;
        const usableModels = nonEmbeddingModels(discoveredModels);
        const defaults = chooseLocalModelDefaults(usableModels);
        providerForm.value.lmStudioModel ||= defaults.writer || defaults.small;

        if (!usableModels.length) {
          setProviderStatus("No usable LM Studio chat model was found.", true);
          currentStep.value = "ai";
          return;
        }
      }

      if (selectedProvider.value === "ollama") {
        ollamaModels.value = discoveredModels;
        const usableModels = nonEmbeddingModels(discoveredModels);
        const defaults = chooseLocalModelDefaults(usableModels);
        providerForm.value.ollamaModel ||= defaults.writer || defaults.small;

        if (!usableModels.length) {
          setProviderStatus("No usable Ollama chat model was found.", true);
          currentStep.value = "ai";
          return;
        }
      }

      const savePayload = buildSavePayload();
      applyLocalProviderModels(savePayload);
      await saveSettings(savePayload);

      clearSubmittedApiKeys();
      providerSaved.value = true;
      setProviderStatus(validation.detail || "Provider ready.");
      currentStep.value = "facts";
    } catch (error) {
      setProviderStatus(error?.message || "Provider validation failed.", true);
      currentStep.value = "ai";
    } finally {
      providerBusy.value = false;
    }
  }

  return {
    PROVIDERS,
    selectedProvider,
    providerBusy,
    providerStatus,
    providerStatusError,
    providerSaved,
    providerReady,
    providerForm,
    lmStudioModels,
    ollamaModels,
    nonEmbeddingModels,
    selectProvider,
    validateAndSaveProvider,
  };
}
