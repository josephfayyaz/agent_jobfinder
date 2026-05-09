/*
 * Shared provider helpers used by onboarding and settings.
 *
 * This stays intentionally small: shared payload building, provider flags,
 * local-model defaults, and validation calls. DOM-specific visibility and
 * status rendering remain local to each screen.
 */

(() => {
  const controller = window.ProviderController || {};

  controller.nonEmbeddingModels = function nonEmbeddingModels(models) {
    return (models || []).filter((name) => !/embed/i.test(name));
  };

  controller.chooseLocalModelDefaults = function chooseLocalModelDefaults(models) {
    const chatModels = controller.nonEmbeddingModels(models);
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

  controller.buildProviderFlags = function buildProviderFlags(mode) {
    return {
      llm_provider_mode: mode,
      use_openai_review: mode === "openai",
      use_claude_final_review: mode === "anthropic",
    };
  };

  controller.buildValidationPayload = function buildValidationPayload(input = {}) {
    return {
      provider_mode: input.mode || "",
      openai_api_key: (input.openaiKey || "").trim(),
      gemini_api_key: (input.geminiKey || "").trim(),
      anthropic_api_key: (input.anthropicKey || "").trim(),
      lm_studio_base_url: (input.lmStudioUrl || "").trim(),
      ollama_base_url: (input.ollamaUrl || "").trim(),
    };
  };

  controller.buildBaseSavePayload = function buildBaseSavePayload(input = {}) {
    const mode = input.mode || "";
    const payload = {
      ...controller.buildProviderFlags(mode),
      lm_studio_base_url: (input.lmStudioUrl || "").trim() || "http://localhost:1234/v1",
      ollama_base_url: (input.ollamaUrl || "").trim() || "http://localhost:11434",
    };
    const openaiKey = (input.openaiKey || "").trim();
    const geminiKey = (input.geminiKey || "").trim();
    const anthropicKey = (input.anthropicKey || "").trim();
    if (openaiKey) {
      payload.openai_api_key = openaiKey;
    }
    if (geminiKey) {
      payload.gemini_api_key = geminiKey;
    }
    if (anthropicKey) {
      payload.anthropic_api_key = anthropicKey;
    }
    return payload;
  };

  controller.applyLocalProviderModels = function applyLocalProviderModels(options = {}) {
    const mode = options.mode || "";
    const payload = options.payload || {};
    const chosenModels = options.chosenModels || {small: "", writer: "", mid: ""};

    if (mode === "lm_studio") {
      const selectedModel = (options.selectedLmStudioModel || "").trim() || chosenModels.writer || chosenModels.small;
      if (!selectedModel) {
        return {ok: false, message: "LM Studio responded, but no usable chat models were found."};
      }
      payload.lm_studio_small_model = selectedModel;
      payload.lm_studio_writer_model = selectedModel;
      payload.lm_studio_mid_model = selectedModel;
      return {ok: true, selectedModel};
    }

    if (mode === "ollama") {
      const selectedModel = (options.selectedOllamaModel || "").trim() || chosenModels.writer || chosenModels.small;
      if (!selectedModel) {
        return {ok: false, message: "Ollama responded, but no usable chat models were found."};
      }
      payload.ollama_fast_model = selectedModel;
      payload.ollama_writer_model = selectedModel;
      return {ok: true, selectedModel};
    }

    return {ok: true, selectedModel: ""};
  };

  controller.validateProvider = async function validateProvider(payload, fetchJson, timeoutMs = 15000) {
    return fetchJson(
      "/providers/validate",
      {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload),
      },
      timeoutMs,
    );
  };

  window.ProviderController = controller;
})();
