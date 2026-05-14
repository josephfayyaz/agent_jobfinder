export const PROVIDERS = [
  {
    value: "openai",
    label: "OpenAI",
    eyebrow: "Cloud",
    description: "Use your OpenAI API key for future AI work.",
  },
  {
    value: "gemini",
    label: "Google Gemini",
    eyebrow: "Cloud",
    description: "Use your Gemini API key through Google AI Studio.",
  },
  {
    value: "anthropic",
    label: "Claude",
    eyebrow: "Cloud",
    description: "Use your Anthropic API key for Claude.",
  },
  {
    value: "lm_studio",
    label: "LM Studio",
    eyebrow: "Local",
    description: "Use an OpenAI-compatible local gateway.",
  },
  {
    value: "ollama",
    label: "Ollama",
    eyebrow: "Local",
    description: "Use locally installed Ollama chat models.",
  },
];

export function nonEmbeddingModels(models) {
  return (models || []).filter((name) => !/embed/i.test(String(name)));
}

export function chooseLocalModelDefaults(models) {
  const chatModels = nonEmbeddingModels(models);
  if (!chatModels.length) {
    return { small: "", writer: "", mid: "" };
  }

  const safeChatModels = chatModels.filter(
    (name) => !/(27b|32b|70b|72b|405b|671b|claude-4\.6-opus-distilled)/i.test(String(name)),
  );
  const preferred = safeChatModels.length ? safeChatModels : chatModels;
  const gptOss = preferred.find((name) => /gpt-oss/i.test(String(name)));
  const compact = preferred.find((name) => /(mini|small|7b|8b|9b|10b|11b|12b|14b)/i.test(String(name)));

  const small = gptOss || compact || preferred[0];
  const writer =
    gptOss ||
    preferred.find((name) => /(writer|instruct|chat)/i.test(String(name))) ||
    compact ||
    preferred[0];
  const mid = preferred.find((name) => name !== small && name !== writer) || writer || small;

  return { small, writer, mid };
}

export function buildProviderFlags(mode) {
  return {
    llm_provider_mode: mode,
    use_openai_review: mode === "openai",
    use_claude_final_review: mode === "anthropic",
  };
}

export function buildValidationPayload(input = {}) {
  return {
    provider_mode: input.mode || "",
    openai_api_key: String(input.openaiKey || "").trim(),
    gemini_api_key: String(input.geminiKey || "").trim(),
    anthropic_api_key: String(input.anthropicKey || "").trim(),
    lm_studio_base_url: String(input.lmStudioUrl || "").trim(),
    ollama_base_url: String(input.ollamaUrl || "").trim(),
  };
}

export function buildBaseSavePayload(input = {}) {
  const mode = input.mode || "";
  const payload = {
    ...buildProviderFlags(mode),
    lm_studio_base_url: String(input.lmStudioUrl || "").trim() || "http://localhost:1234/v1",
    ollama_base_url: String(input.ollamaUrl || "").trim() || "http://localhost:11434",
  };
  const openaiKey = String(input.openaiKey || "").trim();
  const geminiKey = String(input.geminiKey || "").trim();
  const anthropicKey = String(input.anthropicKey || "").trim();
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
}

export function applyLocalProviderModels(options = {}) {
  const mode = options.mode || "";
  const payload = options.payload || {};
  const chosenModels = options.chosenModels || { small: "", writer: "", mid: "" };

  if (mode === "lm_studio") {
    const selectedModel = String(options.selectedLmStudioModel || "").trim() || chosenModels.writer || chosenModels.small;
    if (!selectedModel) {
      return { ok: false, message: "LM Studio responded, but no usable chat models were found." };
    }
    payload.lm_studio_small_model = selectedModel;
    payload.lm_studio_writer_model = selectedModel;
    payload.lm_studio_mid_model = selectedModel;
    return { ok: true, selectedModel };
  }

  if (mode === "ollama") {
    const selectedModel = String(options.selectedOllamaModel || "").trim() || chosenModels.writer || chosenModels.small;
    if (!selectedModel) {
      return { ok: false, message: "Ollama responded, but no usable chat models were found." };
    }
    payload.ollama_fast_model = selectedModel;
    payload.ollama_writer_model = selectedModel;
    return { ok: true, selectedModel };
  }

  return { ok: true, selectedModel: "" };
}
