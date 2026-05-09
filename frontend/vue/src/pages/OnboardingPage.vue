<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";

import { apiFetch, vueApiFetch } from "../api/client";
import AppPageHeader from "../components/AppPageHeader.vue";

const SETUP_STEPS = [
  {
    key: "ai",
    label: "AI",
    title: "Connect an AI provider",
    description: "Validate and save the provider used by the local job agent.",
  },
  {
    key: "facts",
    label: "Facts",
    title: "Add your fact sheet",
    description: "This step remains available in the legacy onboarding flow.",
  },
  {
    key: "questions",
    label: "Questions",
    title: "Answer follow-up questions",
    description: "This step remains available in the legacy onboarding flow.",
  },
  {
    key: "review",
    label: "Review",
    title: "Review your profile",
    description: "This step remains available in the legacy onboarding flow.",
  },
  {
    key: "search",
    label: "Search",
    title: "Configure search focus",
    description: "This step remains available in the legacy onboarding flow.",
  },
];

const PROVIDERS = [
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

const SUPPORTED_SOURCE_EXTENSIONS = [".pdf", ".txt", ".md", ".rst"];
const SUPPORTED_SOURCE_TYPES = ["application/pdf", "text/plain", "text/markdown"];

const currentStep = ref("ai");
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
const candidateId = ref("");
const sourceFileInput = ref(null);
const sourceFiles = ref([]);
const profileNotes = ref("");
const factsBusy = ref(false);
const factsStatus = ref("");
const factsStatusError = ref(false);
const factsSaved = ref(false);
const intakeQuestions = ref([]);
const questionAnswers = ref({});
const questionsBusy = ref(false);
const questionsStatus = ref("");
const questionsStatusError = ref(false);
const questionsAnswered = ref(false);
const reviewFactSheet = ref(null);
const reviewReadiness = ref(null);
const reviewForm = ref(createEmptyReviewForm());
const reviewBusy = ref(false);
const reviewSaving = ref(false);
const reviewStatus = ref("");
const reviewStatusError = ref(false);
const reviewSaved = ref(false);

const onboardingState = ref(null);
const onboardingSteps = ref(null);
const setupState = ref(null);
const loadError = ref("");
const isLoading = ref(true);

const onboardingData = computed(() => onboardingState.value?.data || onboardingState.value || {});
const onboardingStepsData = computed(() => onboardingSteps.value?.data || onboardingSteps.value || {});
const setupData = computed(() => setupState.value?.data || setupState.value || {});

const stepStateByKey = computed(() => {
  const state = new Map();
  const steps = Array.isArray(onboardingStepsData.value?.items)
    ? onboardingStepsData.value.items
    : onboardingStepsData.value?.steps;
  if (Array.isArray(steps)) {
    steps.forEach((step) => {
      const key = step.key || step.id || step.name;
      if (key) {
        state.set(key, step);
      }
    });
  }
  return state;
});

const providerConfigured = computed(() =>
  Boolean(
    setupData.value?.provider_ready ||
      setupData.value?.provider_configured ||
      setupData.value?.llm_provider_configured ||
      onboardingData.value?.provider_ready ||
      onboardingData.value?.provider_configured,
  ),
);

const providerReady = computed(() => providerSaved.value || providerConfigured.value);

const factsReady = computed(() =>
  Boolean(
    factsSaved.value ||
      setupData.value?.facts_ready ||
      setupData.value?.fact_sheet_ready ||
      onboardingData.value?.facts_ready ||
      onboardingData.value?.fact_sheet_ready,
  ),
);

const questionsReady = computed(() =>
  Boolean(
    questionsAnswered.value ||
      setupData.value?.questions_ready ||
      onboardingData.value?.questions_ready,
  ),
);

const reviewReady = computed(() =>
  Boolean(reviewSaved.value || setupData.value?.review_ready || onboardingData.value?.review_ready),
);

const searchReady = computed(() =>
  Boolean(
    setupData.value?.search_ready ||
      setupData.value?.search_focus_ready ||
      onboardingData.value?.search_ready ||
      onboardingData.value?.search_focus_ready,
  ),
);

const readinessByStep = computed(() => ({
  ai: providerReady.value,
  facts: factsReady.value,
  questions: questionsReady.value,
  review: reviewReady.value,
  search: searchReady.value,
}));

const displaySteps = computed(() =>
  SETUP_STEPS.map((step, index) => {
    const apiStep = stepStateByKey.value.get(step.key) || {};
    const completed =
      readinessByStep.value[step.key] ||
      Boolean(apiStep.completed || apiStep.done || apiStep.ready);
    return {
      ...step,
      index: index + 1,
      active: currentStep.value === step.key,
      completed,
      statusText: completed ? "Ready" : "Pending",
    };
  }),
);

const selectedFileNames = computed(() =>
  sourceFiles.value.map((file) => `${file.name} (${formatFileSize(file.size)})`),
);

const normalizedQuestions = computed(() =>
  intakeQuestions.value.map((question, index) => normalizeQuestion(question, index)),
);

const readinessBanner = computed(() => {
  const readiness = reviewReadiness.value;
  if (!readiness) {
    return null;
  }

  const status = readiness.status || "usable_with_warnings";
  const missing = Array.isArray(readiness.missing_sections) && readiness.missing_sections.length
    ? ` Missing: ${readiness.missing_sections.join(", ")}.`
    : "";
  const reason = (Array.isArray(readiness.reasons) && readiness.reasons[0]) ||
    "Review the extracted profile before continuing.";

  if (status === "ready") {
    return {
      title: "Profile Readiness: Ready",
      message: `${reason}${missing}`,
      tone: "border-emerald-200 bg-emerald-50 text-emerald-800",
    };
  }

  if (status === "insufficient_profile_data") {
    return {
      title: "Profile Readiness: Needs more evidence",
      message: `${reason}${missing}`,
      tone: "border-rose-200 bg-rose-50 text-rose-800",
    };
  }

  return {
    title: "Profile Readiness: Usable with warnings",
    message: `${reason}${missing}`,
    tone: "border-amber-200 bg-amber-50 text-amber-800",
  };
});

const setupStatus = computed(() => {
  if (providerReady.value && factsReady.value && questionsReady.value && reviewReady.value) {
    return "Setup is mostly ready. Search configuration may still need review.";
  }

  if (providerReady.value && factsReady.value && intakeQuestions.value.length) {
    return "Profile intake needs follow-up questions.";
  }

  if (providerReady.value && factsReady.value) {
    return "Profile intake is ready for review.";
  }

  if (providerReady.value) {
    return "AI provider is ready. Continue setup from the Facts step.";
  }

  if (setupState.value || onboardingState.value) {
    return "AI provider is not ready yet.";
  }

  return "Setup status is loading from the existing onboarding APIs.";
});

function nonEmbeddingModels(models) {
  return (models || []).filter((model) => !/embed/i.test(String(model)));
}

function chooseLocalModelDefaults(models) {
  const chatModels = nonEmbeddingModels(models);
  const avoidLarge = (model) =>
    !/(27b|32b|70b|72b|405b|671b|claude-4\\.6-opus-distilled)/i.test(String(model));
  const practicalModels = chatModels.filter(avoidLarge);
  const pool = practicalModels.length ? practicalModels : chatModels;
  const find = (pattern) => pool.find((model) => pattern.test(String(model)));

  const gptOss = find(/gpt-oss/i);
  const compact = find(/mini|small|7b|8b|9b|10b|11b|12b|14b/i);
  const writer = find(/writer|instruct|chat/i) || gptOss || compact || pool[0] || "";
  const small = gptOss || compact || writer || "";
  const mid = pool.find((model) => model !== writer && model !== small) || writer || small || "";

  return { small, writer, mid };
}

function buildProviderFlags(mode) {
  return {
    llm_provider_mode: mode,
    use_openai_review: mode === "openai",
    use_claude_final_review: mode === "anthropic",
  };
}

function buildValidationPayload() {
  return {
    provider: selectedProvider.value,
    openai_api_key: providerForm.value.openaiKey,
    anthropic_api_key: providerForm.value.anthropicKey,
    gemini_api_key: providerForm.value.geminiKey,
    lm_studio_base_url: providerForm.value.lmStudioUrl,
    ollama_base_url: providerForm.value.ollamaUrl,
  };
}

function buildBaseSavePayload() {
  const payload = {
    ...buildProviderFlags(selectedProvider.value),
    lm_studio_base_url: providerForm.value.lmStudioUrl || "http://localhost:1234/v1",
    ollama_base_url: providerForm.value.ollamaUrl || "http://localhost:11434",
  };

  if (providerForm.value.openaiKey) {
    payload.openai_api_key = providerForm.value.openaiKey;
  }

  if (providerForm.value.anthropicKey) {
    payload.anthropic_api_key = providerForm.value.anthropicKey;
  }

  if (providerForm.value.geminiKey) {
    payload.gemini_api_key = providerForm.value.geminiKey;
  }

  return payload;
}

function applyLocalProviderModels(payload) {
  if (selectedProvider.value === "lm_studio") {
    const chosen = chooseLocalModelDefaults(lmStudioModels.value);
    const model = providerForm.value.lmStudioModel || chosen.writer || chosen.small;

    if (!model) {
      throw new Error("No usable LM Studio chat model was found.");
    }

    providerForm.value.lmStudioModel = model;
    payload.lm_studio_small_model = model;
    payload.lm_studio_writer_model = model;
    payload.lm_studio_mid_model = model;
  }

  if (selectedProvider.value === "ollama") {
    const chosen = chooseLocalModelDefaults(ollamaModels.value);
    const model = providerForm.value.ollamaModel || chosen.writer || chosen.small;

    if (!model) {
      throw new Error("No usable Ollama chat model was found.");
    }

    providerForm.value.ollamaModel = model;
    payload.ollama_fast_model = model;
    payload.ollama_writer_model = model;
  }
}

function setProviderStatus(message, isError = false) {
  providerStatus.value = message;
  providerStatusError.value = isError;
}

function selectProvider(provider) {
  selectedProvider.value = provider;
  providerSaved.value = false;
  setProviderStatus("");
}

function selectStep(stepKey) {
  if (stepKey === "review") {
    void openReviewStep();
    return;
  }
  currentStep.value = stepKey;
}

function clearSubmittedApiKeys() {
  providerForm.value.openaiKey = "";
  providerForm.value.anthropicKey = "";
  providerForm.value.geminiKey = "";
}

function formatFileSize(size) {
  const bytes = Number(size) || 0;
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${Math.round(bytes / 1024)} KB`;
  }
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function isSupportedSourceFile(file) {
  const name = String(file?.name || "").toLowerCase();
  const type = String(file?.type || "").toLowerCase();
  return (
    SUPPORTED_SOURCE_EXTENSIONS.some((extension) => name.endsWith(extension)) ||
    SUPPORTED_SOURCE_TYPES.includes(type)
  );
}

function handleSourceFiles(event) {
  sourceFiles.value = Array.from(event.target?.files || []);
  factsSaved.value = false;
  setIntakeQuestions([]);
  setFactsStatus("");
}

async function responseDetail(response, fallback) {
  const contentType = response.headers.get("content-type") || "";
  const text = await response.text();

  if (contentType.includes("application/json") && text) {
    try {
      const payload = JSON.parse(text);
      return payload.detail || payload.message || fallback;
    } catch (_error) {
      return fallback;
    }
  }

  return text || fallback;
}

async function legacyFetchJson(path, options = {}, fallback = "Request failed.") {
  const response = await fetch(path, {
    credentials: "same-origin",
    ...options,
  });

  if (!response.ok) {
    throw new Error(await responseDetail(response, fallback));
  }

  const contentType = response.headers.get("content-type") || "";
  if (response.status === 204) {
    return null;
  }
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

function setFactsStatus(message, isError = false) {
  factsStatus.value = message;
  factsStatusError.value = isError;
}

function normalizeQuestion(question, index) {
  const questionObj =
    typeof question === "string"
      ? {id: `q${index + 1}`, prompt: question, kind: "text", options: [], allow_free_text: true}
      : question || {};
  const kind = ["text", "single_select", "multi_select"].includes(questionObj.kind)
    ? questionObj.kind
    : "text";

  return {
    id: String(questionObj.id || `q${index + 1}`),
    prompt: String(questionObj.prompt || questionObj.question || questionObj.id || `Question ${index + 1}`),
    kind,
    options: Array.isArray(questionObj.options) ? questionObj.options.filter(Boolean).map(String) : [],
    allow_free_text: Boolean(questionObj.allow_free_text),
    required: questionObj.required !== false,
  };
}

function createEmptyQuestionAnswer() {
  return {text: "", selected: "", choices: []};
}

function setIntakeQuestions(questions) {
  const nextQuestions = Array.isArray(questions) ? questions : [];
  const nextAnswers = {};

  nextQuestions.forEach((question, index) => {
    const normalized = normalizeQuestion(question, index);
    nextAnswers[normalized.id] = createEmptyQuestionAnswer();
  });

  intakeQuestions.value = nextQuestions;
  questionAnswers.value = nextAnswers;
  questionsAnswered.value = false;
  reviewSaved.value = false;
  setQuestionsStatus("");
}

function setQuestionsStatus(message, isError = false) {
  questionsStatus.value = message;
  questionsStatusError.value = isError;
}

function createEmptyReviewForm() {
  return {
    fullName: "",
    email: "",
    education: [],
    experience: [],
    projects: [],
    skillsText: "",
    languages: [],
  };
}

function clonePlainObject(value) {
  return JSON.parse(JSON.stringify(value || {}));
}

function splitLines(value) {
  return String(value || "")
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function readFromFactSheetSkills(factSheet) {
  const skills = factSheet?.skills;
  if (!skills || typeof skills !== "object") {
    return [];
  }

  const rows = [];
  Object.values(skills).forEach((value) => {
    if (!Array.isArray(value)) {
      return;
    }
    value.forEach((item) => {
      const text = String(item || "").trim();
      if (text && !rows.includes(text)) {
        rows.push(text);
      }
    });
  });
  return rows;
}

function buildReviewForm(factSheet) {
  const person = factSheet?.person || {};
  const contact = person.contact || {};
  const education = Array.isArray(factSheet?.education)
    ? factSheet.education.map((item) => ({
        ...clonePlainObject(item),
        degree: item?.degree || "",
        field: item?.field || "",
        institution: item?.institution || "",
        status: item?.status || "",
      }))
    : [];
  const experience = Array.isArray(factSheet?.experience)
    ? factSheet.experience.map((item) => ({
        ...clonePlainObject(item),
        role_title: item?.role_title || "",
        organization: item?.organization || "",
        start_date: item?.start_date || "",
        end_date: item?.end_date || "",
        responsibilities_text: Array.isArray(item?.responsibilities)
          ? item.responsibilities.join("\n")
          : String(item?.responsibilities || ""),
      }))
    : [];
  const projects = Array.isArray(factSheet?.projects)
    ? factSheet.projects.map((item) => ({
        ...clonePlainObject(item),
        name: item?.name || "",
        link: item?.link || "",
        summary:
          item?.summary ||
          (Array.isArray(item?.key_results) ? item.key_results.join("\n") : ""),
      }))
    : [];
  const languages = Array.isArray(factSheet?.languages) && factSheet.languages.length
    ? factSheet.languages.map((item) => ({
        ...clonePlainObject(item),
        name: item?.name || "",
        level: item?.level || "professional",
      }))
    : [{name: "English", level: "professional"}];

  return {
    fullName: person.full_name || "",
    email: contact.email || "",
    education,
    experience,
    projects,
    skillsText: readFromFactSheetSkills(factSheet).join("\n"),
    languages,
  };
}

function setReviewStatus(message, isError = false) {
  reviewStatus.value = message;
  reviewStatusError.value = isError;
}

function addReviewRow(sectionId) {
  if (sectionId === "education") {
    reviewForm.value.education.push({degree: "", field: "", institution: "", status: ""});
    return;
  }

  if (sectionId === "experience") {
    reviewForm.value.experience.push({
      role_title: "",
      organization: "",
      start_date: "",
      end_date: "",
      responsibilities_text: "",
      responsibilities: [],
    });
    return;
  }

  if (sectionId === "projects") {
    reviewForm.value.projects.push({name: "", link: "", summary: ""});
  }
}

function removeReviewRow(sectionId, index) {
  if (!Array.isArray(reviewForm.value[sectionId])) {
    return;
  }
  reviewForm.value[sectionId].splice(index, 1);
}

function addReviewLanguage() {
  reviewForm.value.languages.push({name: "", level: "professional"});
}

function removeReviewLanguage(index) {
  reviewForm.value.languages.splice(index, 1);
  if (!reviewForm.value.languages.length) {
    addReviewLanguage();
  }
}

function buildReviewedFactSheetPayload() {
  const base = clonePlainObject(reviewFactSheet.value);
  const form = reviewForm.value;

  const education = form.education
    .map((row) => ({
      ...clonePlainObject(row),
      degree: String(row.degree || "").trim(),
      field: String(row.field || "").trim(),
      institution: String(row.institution || "").trim(),
      status: String(row.status || "").trim(),
    }))
    .filter((row) => row.degree || row.field || row.institution);

  const experience = form.experience
    .map((row) => ({
      ...clonePlainObject(row),
      role_title: String(row.role_title || "").trim(),
      organization: String(row.organization || "").trim(),
      start_date: String(row.start_date || "").trim(),
      end_date: String(row.end_date || "").trim(),
      responsibilities: splitLines(row.responsibilities_text),
      tools: Array.isArray(row.tools) ? row.tools : [],
      achievements: Array.isArray(row.achievements) ? row.achievements : [],
      evidence_refs: Array.isArray(row.evidence_refs) ? row.evidence_refs : [],
    }))
    .filter((row) => row.role_title || row.organization || row.responsibilities.length);

  const projects = form.projects
    .map((row) => ({
      ...clonePlainObject(row),
      name: String(row.name || "").trim(),
      link: String(row.link || "").trim(),
      summary: String(row.summary || "").trim(),
      tools: Array.isArray(row.tools) ? row.tools : [],
    }))
    .filter((row) => row.name || row.summary);

  const languages = form.languages
    .map((row) => ({
      ...clonePlainObject(row),
      name: String(row.name || "").trim(),
      level: String(row.level || "").trim() || "professional",
    }))
    .filter((row) => row.name);

  return {
    ...base,
    person: {
      ...(base.person || {}),
      full_name: form.fullName.trim(),
      contact: {
        ...((base.person || {}).contact || {}),
        email: form.email.trim(),
      },
    },
    education,
    experience,
    projects,
    skills: {business_tools: splitLines(form.skillsText)},
    languages,
  };
}

function buildAnswersPayload() {
  const answers = {};
  const missingPrompts = [];

  normalizedQuestions.value.forEach((question) => {
    const answer = questionAnswers.value[question.id] || createEmptyQuestionAnswer();

    if (question.kind === "single_select") {
      const note = String(answer.text || "").trim();
      const value = note || answer.selected || "";
      answers[question.id] = value;
      if (question.required && !value) {
        missingPrompts.push(question.prompt);
      }
      return;
    }

    if (question.kind === "multi_select") {
      const choices = Array.isArray(answer.choices) ? answer.choices.filter(Boolean) : [];
      const note = String(answer.text || "").trim();
      const value = note ? [...choices, note] : choices;
      answers[question.id] = value;
      if (question.required && !value.length) {
        missingPrompts.push(question.prompt);
      }
      return;
    }

    const value = String(answer.text || "").trim();
    answers[question.id] = value;
    if (question.required && !value) {
      missingPrompts.push(question.prompt);
    }
  });

  return {answers, missingPrompts};
}

async function ensureCandidateShell() {
  if (candidateId.value) {
    return candidateId.value;
  }

  const candidate = await apiFetch("/candidates/ensure-owner", {
    method: "POST",
  });
  candidateId.value = candidate?.id || "";

  if (!candidateId.value) {
    throw new Error("Could not prepare the onboarding profile shell.");
  }

  return candidateId.value;
}

async function uploadSourceFiles(files) {
  if (!files.length) {
    return;
  }

  const uploadData = new FormData();
  uploadData.append("replace_existing", "1");
  files.forEach((file) => {
    uploadData.append("files", file);
  });

  await legacyFetchJson(
    `/candidates/${candidateId.value}/sources/upload`,
    {
      method: "POST",
      body: uploadData,
    },
    "Uploading source files failed.",
  );
}

async function startIntake(notes) {
  return legacyFetchJson(
    `/candidates/${candidateId.value}/intake/start`,
    {
      method: "POST",
      headers: {"Content-Type": "application/x-www-form-urlencoded"},
      body: new URLSearchParams({profile_notes: notes}),
    },
    "The AI provider could not complete intake. Check your provider key in Settings.",
  );
}

async function runFactsIntake() {
  setFactsStatus("");
  factsSaved.value = false;
  setIntakeQuestions([]);

  try {
    await ensureCandidateShell();
  } catch (error) {
    setFactsStatus(error?.message || "Could not prepare the onboarding profile shell.", true);
    return;
  }

  const files = sourceFiles.value;
  const notes = profileNotes.value.trim();

  if (!files.length && !notes) {
    setFactsStatus("Upload at least one CV file (PDF/TXT/MD/RST) or add manual notes.", true);
    return;
  }

  const invalidFiles = files.filter((file) => !isSupportedSourceFile(file));
  if (invalidFiles.length) {
    setFactsStatus("Only PDF, TXT, MD, or RST files are accepted in onboarding intake.", true);
    return;
  }

  factsBusy.value = true;
  setFactsStatus("Analysing your profile...");

  try {
    await uploadSourceFiles(files);
    const intakeData = await startIntake(notes);
    factsSaved.value = true;

    if (intakeData?.status === "questions_needed" && Array.isArray(intakeData.questions) && intakeData.questions.length) {
      setIntakeQuestions(intakeData.questions);
      setFactsStatus("Profile intake saved. Answer the remaining questions.");
      currentStep.value = "questions";
      return;
    }

    setFactsStatus("Profile intake saved.");
    await openReviewStep();
  } catch (error) {
    setFactsStatus(error?.message || "Profile intake failed.", true);
    currentStep.value = "facts";
  } finally {
    factsBusy.value = false;
  }
}

async function submitQuestionAnswers() {
  if (!candidateId.value) {
    setQuestionsStatus("Could not find the onboarding profile shell. Return to Facts and run intake again.", true);
    currentStep.value = "questions";
    return;
  }

  const {answers, missingPrompts} = buildAnswersPayload();

  if (missingPrompts.length) {
    setQuestionsStatus(`Please answer the required questions first. Missing: ${missingPrompts[0]}`, true);
    currentStep.value = "questions";
    return;
  }

  questionsBusy.value = true;
  setQuestionsStatus("Saving your answers...");

  try {
    const data = await apiFetch(`/candidates/${candidateId.value}/intake/answer`, {
      method: "POST",
      body: JSON.stringify({answers}),
    });

    if (data?.status === "questions_needed" && Array.isArray(data.questions) && data.questions.length) {
      setIntakeQuestions(data.questions);
      setQuestionsStatus("More detail is still needed. Answer the updated questions below.");
      currentStep.value = "questions";
      return;
    }

    questionAnswers.value = {};
    intakeQuestions.value = [];
    setQuestionsStatus("Answers saved.");
    await openReviewStep();
  } catch (error) {
    setQuestionsStatus(error?.message || "Saving answers failed.", true);
    currentStep.value = "questions";
  } finally {
    questionsBusy.value = false;
  }
}

async function loadProfileReview() {
  if (!candidateId.value) {
    reviewFactSheet.value = null;
    reviewReadiness.value = null;
    reviewForm.value = createEmptyReviewForm();
    setReviewStatus("Run intake before loading the profile review.", true);
    return false;
  }

  reviewBusy.value = true;
  setReviewStatus("Loading extracted profile review...");

  try {
    const data = await apiFetch(`/candidates/${candidateId.value}/onboarding-review`);
    reviewFactSheet.value = data?.fact_sheet || {};
    reviewReadiness.value = data?.readiness || null;
    reviewForm.value = buildReviewForm(reviewFactSheet.value);
    questionsAnswered.value = true;
    setReviewStatus("");
    return true;
  } catch (error) {
    reviewFactSheet.value = null;
    reviewReadiness.value = null;
    reviewForm.value = createEmptyReviewForm();
    setReviewStatus(error?.message || "Could not load the extracted profile review.", true);
    return false;
  } finally {
    reviewBusy.value = false;
  }
}

async function openReviewStep() {
  currentStep.value = "review";
  await loadProfileReview();
}

async function saveProfileReview() {
  if (!candidateId.value || !reviewFactSheet.value) {
    setReviewStatus("Run intake before saving the profile review.", true);
    currentStep.value = "review";
    return;
  }

  reviewSaving.value = true;
  setReviewStatus("Saving profile review...");

  try {
    const payload = buildReviewedFactSheetPayload();
    await apiFetch(`/candidates/${candidateId.value}/fact-sheet-json`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    reviewSaved.value = true;
    setReviewStatus("Profile review saved.");
    await loadProfileReview();
    currentStep.value = "search";
  } catch (error) {
    setReviewStatus(error?.message || "Saving profile review failed.", true);
    currentStep.value = "review";
  } finally {
    reviewSaving.value = false;
  }
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
    const validation = await apiFetch("/providers/validate", {
      method: "POST",
      body: JSON.stringify(buildValidationPayload()),
    });

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

    const savePayload = buildBaseSavePayload();
    applyLocalProviderModels(savePayload);

    await apiFetch("/settings/save", {
      method: "POST",
      body: JSON.stringify(savePayload),
    });

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

async function loadOnboardingState() {
  isLoading.value = true;
  loadError.value = "";

  try {
    const [onboarding, steps, setup] = await Promise.all([
      vueApiFetch("/onboarding/state"),
      vueApiFetch("/onboarding/steps"),
      vueApiFetch("/setup/state"),
    ]);

    onboardingState.value = onboarding;
    onboardingSteps.value = steps;
    setupState.value = setup;
  } catch (error) {
    loadError.value = error?.message || "Unable to load onboarding state.";
  } finally {
    isLoading.value = false;
  }
}

onMounted(loadOnboardingState);
</script>

<template>
  <section class="space-y-8">
    <AppPageHeader
      eyebrow="Setup"
      title="Onboarding"
      description="The Vue onboarding flow is being migrated in small phases. The AI provider, Facts, and Questions steps are available here; use the legacy flow for the remaining setup steps."
    >
      <template #actions>
        <a
          class="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50"
          href="/ui/onboarding"
        >
          Complete setup in legacy UI
        </a>
      </template>
    </AppPageHeader>

    <div
      v-if="loadError"
      class="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
    >
      {{ loadError }}
    </div>

    <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Current setup status
          </p>
          <p class="mt-1 text-base font-semibold text-slate-950">
            {{ isLoading ? "Loading setup state..." : setupStatus }}
          </p>
        </div>

        <RouterLink
          class="text-sm font-semibold text-sky-700 transition hover:text-sky-800"
          to="/settings"
        >
          View settings
        </RouterLink>
      </div>
    </section>

    <section class="grid gap-3 md:grid-cols-5">
      <button
        v-for="step in displaySteps"
        :key="step.key"
        type="button"
        class="rounded-lg border bg-white p-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-sky-300 hover:shadow-md"
        :class="[
          step.active ? 'border-sky-500 ring-2 ring-sky-100' : 'border-slate-200',
          step.completed ? 'bg-emerald-50/60' : '',
        ]"
        @click="selectStep(step.key)"
      >
        <div class="flex items-center justify-between gap-2">
          <span class="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Step {{ step.index }}
          </span>
          <span
            class="rounded-full px-2 py-0.5 text-xs font-semibold"
            :class="
              step.completed
                ? 'bg-emerald-100 text-emerald-800'
                : 'bg-slate-100 text-slate-600'
            "
          >
            {{ step.statusText }}
          </span>
        </div>
        <h2 class="mt-3 text-xl font-semibold text-slate-950">{{ step.label }}</h2>
        <p class="mt-1 text-sm text-slate-600">{{ step.title }}</p>
      </button>
    </section>

    <section
      v-if="currentStep === 'ai'"
      class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
    >
      <div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">
            AI provider
          </p>
          <h2 class="mt-1 text-2xl font-semibold text-slate-950">
            Choose and validate a provider
          </h2>
        </div>
        <a class="text-sm font-semibold text-sky-700 hover:text-sky-800" href="/ui/onboarding">
          Finish setup in legacy UI
        </a>
      </div>

      <div class="mt-5 grid gap-3 md:grid-cols-5">
        <button
          v-for="provider in PROVIDERS"
          :key="provider.value"
          type="button"
          class="setup-provider-card rounded-lg border bg-white p-4 text-left transition hover:border-sky-300 hover:bg-sky-50/50"
          :class="
            selectedProvider === provider.value
              ? 'border-sky-500 bg-sky-50 ring-2 ring-sky-100'
              : 'border-slate-200'
          "
          @click="selectProvider(provider.value)"
        >
          <span class="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {{ provider.eyebrow }}
          </span>
          <span class="mt-2 block text-base font-semibold text-slate-950">
            {{ provider.label }}
          </span>
          <span class="mt-1 block text-sm leading-5 text-slate-600">
            {{ provider.description }}
          </span>
        </button>
      </div>

      <div class="mt-6 rounded-lg border border-slate-200 bg-slate-50 p-4">
        <p v-if="!selectedProvider" class="text-sm text-slate-600">
          Select a provider to show its connection fields.
        </p>

        <div v-if="selectedProvider === 'lm_studio'" class="grid gap-4 md:grid-cols-2">
          <label class="block">
            <span class="text-sm font-medium text-slate-700">Gateway URL</span>
            <input
              v-model.trim="providerForm.lmStudioUrl"
              class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
              type="url"
              autocomplete="off"
            />
          </label>

          <label class="block">
            <span class="text-sm font-medium text-slate-700">Chat model</span>
            <select
              v-model="providerForm.lmStudioModel"
              class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
            >
              <option value="">Auto-select after validation</option>
              <option v-for="model in nonEmbeddingModels(lmStudioModels)" :key="model" :value="model">
                {{ model }}
              </option>
            </select>
          </label>
        </div>

        <div v-if="selectedProvider === 'ollama'" class="grid gap-4 md:grid-cols-2">
          <label class="block">
            <span class="text-sm font-medium text-slate-700">Ollama URL</span>
            <input
              v-model.trim="providerForm.ollamaUrl"
              class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
              type="url"
              autocomplete="off"
            />
          </label>

          <label class="block">
            <span class="text-sm font-medium text-slate-700">Chat model</span>
            <input
              v-model.trim="providerForm.ollamaModel"
              class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
              type="text"
              list="ollama-model-options"
              placeholder="Auto-select after validation"
              autocomplete="off"
            />
            <datalist id="ollama-model-options">
              <option v-for="model in nonEmbeddingModels(ollamaModels)" :key="model" :value="model" />
            </datalist>
          </label>
        </div>

        <div v-if="selectedProvider === 'openai'" class="max-w-xl">
          <label class="block">
            <span class="text-sm font-medium text-slate-700">OpenAI API key</span>
            <input
              v-model.trim="providerForm.openaiKey"
              class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
              type="password"
              placeholder="Leave blank to keep the existing key"
              autocomplete="off"
            />
          </label>
        </div>

        <div v-if="selectedProvider === 'anthropic'" class="max-w-xl">
          <label class="block">
            <span class="text-sm font-medium text-slate-700">Anthropic API key</span>
            <input
              v-model.trim="providerForm.anthropicKey"
              class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
              type="password"
              placeholder="Leave blank to keep the existing key"
              autocomplete="off"
            />
          </label>
        </div>

        <div v-if="selectedProvider === 'gemini'" class="max-w-xl">
          <label class="block">
            <span class="text-sm font-medium text-slate-700">Gemini API key</span>
            <input
              v-model.trim="providerForm.geminiKey"
              class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
              type="password"
              placeholder="Leave blank to keep the existing key"
              autocomplete="off"
            />
          </label>
        </div>
      </div>

      <div class="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p
          class="min-h-5 text-sm"
          :class="providerStatusError ? 'text-red-700' : 'text-emerald-700'"
        >
          {{ providerStatus }}
        </p>
        <button
          type="button"
          class="rounded-md bg-sky-700 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-sky-800 disabled:cursor-not-allowed disabled:bg-slate-400"
          :disabled="providerBusy"
          @click="validateAndSaveProvider"
        >
          {{ providerBusy ? "Validating..." : "Validate & Continue" }}
        </button>
      </div>
    </section>

    <section
      v-else-if="currentStep === 'facts'"
      class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
    >
      <div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Facts
          </p>
          <h2 class="mt-1 text-2xl font-semibold text-slate-950">
            Build your fact sheet
          </h2>
          <p class="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            Upload one or more CV files and add optional notes for recent updates not included in
            those files.
          </p>
        </div>
        <a class="text-sm font-semibold text-sky-700 hover:text-sky-800" href="/ui/onboarding">
          Finish setup in legacy UI
        </a>
      </div>

      <div class="mt-6 space-y-5">
        <label class="block">
          <span class="text-sm font-medium text-slate-700">Source files</span>
          <input
            ref="sourceFileInput"
            class="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm file:mr-4 file:rounded-md file:border-0 file:bg-slate-100 file:px-3 file:py-2 file:text-sm file:font-semibold file:text-slate-700 hover:file:bg-slate-200 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
            type="file"
            multiple
            accept=".pdf,.txt,.md,.rst,application/pdf,text/plain,text/markdown"
            :disabled="factsBusy"
            @change="handleSourceFiles"
          />
        </label>

        <div
          v-if="selectedFileNames.length"
          class="rounded-md border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700"
        >
          <p class="font-semibold text-slate-900">Selected files</p>
          <ul class="mt-2 space-y-1">
            <li v-for="name in selectedFileNames" :key="name">{{ name }}</li>
          </ul>
        </div>

        <label class="block">
          <span class="text-sm font-medium text-slate-700">Optional manual notes</span>
          <textarea
            v-model="profileNotes"
            class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
            rows="7"
            placeholder="Recent roles, tools, projects, education, languages, achievements..."
            :disabled="factsBusy"
          ></textarea>
        </label>

        <div
          v-if="factsBusy"
          class="space-y-3 rounded-md border border-slate-200 bg-slate-50 p-4"
          aria-busy="true"
          aria-label="Loading profile analysis"
        >
          <div class="h-5 w-48 animate-pulse rounded bg-slate-200" aria-hidden="true"></div>
          <div class="h-4 w-full animate-pulse rounded bg-slate-200" aria-hidden="true"></div>
          <div class="h-4 w-3/4 animate-pulse rounded bg-slate-200" aria-hidden="true"></div>
          <div class="h-4 w-full animate-pulse rounded bg-slate-200" aria-hidden="true"></div>
          <div class="h-4 w-2/3 animate-pulse rounded bg-slate-200" aria-hidden="true"></div>
        </div>

        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p
            class="min-h-5 text-sm"
            :class="factsStatusError ? 'text-red-700' : 'text-slate-600'"
          >
            {{ factsStatus }}
          </p>
          <div class="flex gap-3">
            <button
              type="button"
              class="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
              :disabled="factsBusy"
              @click="selectStep('ai')"
            >
              Back
            </button>
            <button
              type="button"
              class="rounded-md bg-sky-700 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-sky-800 disabled:cursor-not-allowed disabled:bg-slate-400"
              :disabled="factsBusy"
              @click="runFactsIntake"
            >
              {{ factsBusy ? "Analysing..." : "Analyse my profile" }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <section
      v-else-if="currentStep === 'questions'"
      class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
    >
      <div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Questions
          </p>
          <h2 class="mt-1 text-2xl font-semibold text-slate-950">
            Answer only what is missing
          </h2>
          <p class="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            Short answers are enough. Skip anything you cannot confirm truthfully unless it is
            marked as required.
          </p>
        </div>
        <a class="text-sm font-semibold text-sky-700 hover:text-sky-800" href="/ui/onboarding">
          Finish setup in legacy UI
        </a>
      </div>

      <div v-if="!normalizedQuestions.length" class="mt-6 rounded-md border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
        No follow-up questions are loaded. Return to the Facts step to run intake.
      </div>

      <div v-else class="mt-6 space-y-5">
        <div
          v-for="(question, questionIndex) in normalizedQuestions"
          :key="question.id"
          class="rounded-md border border-slate-200 bg-slate-50 p-4"
        >
          <div class="flex flex-col gap-1">
            <label
              class="text-sm font-semibold text-slate-900"
              :for="`answer-${question.id}`"
            >
              {{ question.prompt }}
            </label>
            <p
              v-if="question.required"
              class="text-xs font-semibold uppercase tracking-wide text-amber-700"
            >
              Required to build a usable fact sheet
            </p>
          </div>

          <div v-if="question.kind === 'single_select'" class="mt-3 space-y-2">
            <label
              v-for="(option, optionIndex) in question.options"
              :key="`${question.id}-${option}`"
              class="flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700"
              :for="`answer-${question.id}-${optionIndex}`"
            >
              <input
                :id="`answer-${question.id}-${optionIndex}`"
                v-model="questionAnswers[question.id].selected"
                type="radio"
                :name="`answer-${question.id}`"
                :value="option"
                :disabled="questionsBusy"
              />
              <span>{{ option }}</span>
            </label>
          </div>

          <div v-if="question.kind === 'multi_select'" class="mt-3 space-y-2">
            <label
              v-for="(option, optionIndex) in question.options"
              :key="`${question.id}-${option}`"
              class="flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700"
              :for="`answer-${question.id}-${optionIndex}`"
            >
              <input
                :id="`answer-${question.id}-${optionIndex}`"
                v-model="questionAnswers[question.id].choices"
                type="checkbox"
                :value="option"
                :disabled="questionsBusy"
              />
              <span>{{ option }}</span>
            </label>
          </div>

          <textarea
            v-if="question.kind === 'text' || question.allow_free_text"
            :id="`answer-${question.id}`"
            v-model="questionAnswers[question.id].text"
            class="mt-3 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
            :rows="question.kind === 'text' ? 3 : 2"
            :placeholder="question.kind === 'text' ? 'Type your answer' : 'Optional note'"
            :disabled="questionsBusy"
          ></textarea>

          <p class="mt-3 text-xs text-slate-500">
            Question {{ questionIndex + 1 }} of {{ normalizedQuestions.length }}
          </p>
        </div>

        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p
            class="min-h-5 text-sm"
            :class="questionsStatusError ? 'text-red-700' : 'text-slate-600'"
          >
            {{ questionsStatus }}
          </p>
          <div class="flex gap-3">
            <button
              type="button"
              class="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
              :disabled="questionsBusy"
              @click="selectStep('facts')"
            >
              Back
            </button>
            <button
              type="button"
              class="rounded-md bg-sky-700 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-sky-800 disabled:cursor-not-allowed disabled:bg-slate-400"
              :disabled="questionsBusy"
              @click="submitQuestionAnswers"
            >
              {{ questionsBusy ? "Saving..." : "Save answers" }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <section
      v-else-if="currentStep === 'review'"
      class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
    >
      <div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Review
          </p>
          <h2 class="mt-1 text-2xl font-semibold text-slate-950">
            Review your extracted profile
          </h2>
          <p class="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            Check the facts Job Agent extracted before the search focus step. Edit anything that is
            incomplete, too vague, or incorrectly grouped.
          </p>
        </div>
        <a class="text-sm font-semibold text-sky-700 hover:text-sky-800" href="/ui/onboarding">
          Finish setup in legacy UI
        </a>
      </div>

      <div
        v-if="readinessBanner"
        class="mt-5 rounded-lg border px-4 py-3 text-sm"
        :class="readinessBanner.tone"
      >
        <p class="font-semibold">{{ readinessBanner.title }}</p>
        <p class="mt-1">{{ readinessBanner.message }}</p>
      </div>

      <div
        v-if="reviewBusy"
        class="mt-6 space-y-3 rounded-md border border-slate-200 bg-slate-50 p-4"
        aria-busy="true"
        aria-label="Loading profile review"
      >
        <div class="h-5 w-56 animate-pulse rounded bg-slate-200" aria-hidden="true"></div>
        <div class="h-4 w-full animate-pulse rounded bg-slate-200" aria-hidden="true"></div>
        <div class="h-4 w-3/4 animate-pulse rounded bg-slate-200" aria-hidden="true"></div>
        <div class="h-28 w-full animate-pulse rounded bg-slate-200" aria-hidden="true"></div>
      </div>

      <div
        v-else-if="!reviewFactSheet"
        class="mt-6 rounded-md border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600"
      >
        Your extracted profile review will appear here after intake finishes.
      </div>

      <div v-else class="mt-6 space-y-5">
        <section class="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p class="text-sm font-semibold text-slate-900">Identity</p>
          <div class="mt-3 grid gap-4 md:grid-cols-2">
            <label class="block">
              <span class="text-sm font-medium text-slate-700">Full name</span>
              <input
                v-model.trim="reviewForm.fullName"
                class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
                type="text"
                :disabled="reviewSaving"
              />
            </label>
            <label class="block">
              <span class="text-sm font-medium text-slate-700">Email</span>
              <input
                v-model.trim="reviewForm.email"
                class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
                type="email"
                :disabled="reviewSaving"
              />
            </label>
          </div>
        </section>

        <section class="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <div class="flex items-center justify-between gap-3">
            <div>
              <p class="text-sm font-semibold text-slate-900">Education</p>
              <p class="text-xs text-slate-500">Keep only real entries that support your target roles.</p>
            </div>
            <button
              type="button"
              class="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-semibold text-slate-700 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
              :disabled="reviewSaving"
              @click="addReviewRow('education')"
            >
              Add education
            </button>
          </div>

          <div v-if="!reviewForm.education.length" class="mt-3 rounded-md border border-dashed border-slate-300 bg-white px-4 py-4 text-sm text-slate-500">
            No education extracted yet.
          </div>

          <div v-else class="mt-3 space-y-3">
            <article
              v-for="(row, index) in reviewForm.education"
              :key="`education-${index}`"
              class="rounded-md border border-slate-200 bg-white p-4"
            >
              <div class="flex items-center justify-between gap-3">
                <p class="text-sm font-semibold text-slate-900">
                  {{ row.degree || `Education ${index + 1}` }}
                </p>
                <button
                  type="button"
                  class="rounded-md border border-red-200 px-3 py-1.5 text-sm font-semibold text-red-700 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                  :disabled="reviewSaving"
                  @click="removeReviewRow('education', index)"
                >
                  Remove
                </button>
              </div>
              <div class="mt-3 grid gap-3 md:grid-cols-2">
                <label class="block">
                  <span class="text-sm font-medium text-slate-700">Degree</span>
                  <input v-model.trim="row.degree" class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" type="text" :disabled="reviewSaving" />
                </label>
                <label class="block">
                  <span class="text-sm font-medium text-slate-700">Field</span>
                  <input v-model.trim="row.field" class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" type="text" :disabled="reviewSaving" />
                </label>
                <label class="block">
                  <span class="text-sm font-medium text-slate-700">Institution</span>
                  <input v-model.trim="row.institution" class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" type="text" :disabled="reviewSaving" />
                </label>
                <label class="block">
                  <span class="text-sm font-medium text-slate-700">Status / year</span>
                  <input v-model.trim="row.status" class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" type="text" :disabled="reviewSaving" />
                </label>
              </div>
            </article>
          </div>
        </section>

        <section class="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <div class="flex items-center justify-between gap-3">
            <div>
              <p class="text-sm font-semibold text-slate-900">Experience</p>
              <p class="text-xs text-slate-500">Use grounded roles only. One responsibility per line.</p>
            </div>
            <button
              type="button"
              class="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-semibold text-slate-700 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
              :disabled="reviewSaving"
              @click="addReviewRow('experience')"
            >
              Add experience
            </button>
          </div>

          <div v-if="!reviewForm.experience.length" class="mt-3 rounded-md border border-dashed border-slate-300 bg-white px-4 py-4 text-sm text-slate-500">
            No experience extracted yet.
          </div>

          <div v-else class="mt-3 space-y-3">
            <article
              v-for="(row, index) in reviewForm.experience"
              :key="`experience-${index}`"
              class="rounded-md border border-slate-200 bg-white p-4"
            >
              <div class="flex items-center justify-between gap-3">
                <p class="text-sm font-semibold text-slate-900">
                  {{ row.role_title || `Experience ${index + 1}` }}
                </p>
                <button
                  type="button"
                  class="rounded-md border border-red-200 px-3 py-1.5 text-sm font-semibold text-red-700 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                  :disabled="reviewSaving"
                  @click="removeReviewRow('experience', index)"
                >
                  Remove
                </button>
              </div>
              <div class="mt-3 grid gap-3 md:grid-cols-2">
                <label class="block">
                  <span class="text-sm font-medium text-slate-700">Role title</span>
                  <input v-model.trim="row.role_title" class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" type="text" :disabled="reviewSaving" />
                </label>
                <label class="block">
                  <span class="text-sm font-medium text-slate-700">Company / organisation</span>
                  <input v-model.trim="row.organization" class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" type="text" :disabled="reviewSaving" />
                </label>
                <label class="block">
                  <span class="text-sm font-medium text-slate-700">Start date</span>
                  <input v-model.trim="row.start_date" class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" type="text" :disabled="reviewSaving" />
                </label>
                <label class="block">
                  <span class="text-sm font-medium text-slate-700">End date</span>
                  <input v-model.trim="row.end_date" class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" type="text" :disabled="reviewSaving" />
                </label>
                <label class="block md:col-span-2">
                  <span class="text-sm font-medium text-slate-700">Responsibilities</span>
                  <textarea
                    v-model="row.responsibilities_text"
                    class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                    rows="4"
                    placeholder="One responsibility per line"
                    :disabled="reviewSaving"
                  ></textarea>
                </label>
              </div>
            </article>
          </div>
        </section>

        <section class="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <div class="flex items-center justify-between gap-3">
            <div>
              <p class="text-sm font-semibold text-slate-900">Projects and evidence</p>
              <p class="text-xs text-slate-500">Keep short evidence-backed notes.</p>
            </div>
            <button
              type="button"
              class="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-semibold text-slate-700 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
              :disabled="reviewSaving"
              @click="addReviewRow('projects')"
            >
              Add evidence
            </button>
          </div>

          <div v-if="!reviewForm.projects.length" class="mt-3 rounded-md border border-dashed border-slate-300 bg-white px-4 py-4 text-sm text-slate-500">
            No project or evidence items extracted yet.
          </div>

          <div v-else class="mt-3 space-y-3">
            <article
              v-for="(row, index) in reviewForm.projects"
              :key="`projects-${index}`"
              class="rounded-md border border-slate-200 bg-white p-4"
            >
              <div class="flex items-center justify-between gap-3">
                <p class="text-sm font-semibold text-slate-900">
                  {{ row.name || `Evidence ${index + 1}` }}
                </p>
                <button
                  type="button"
                  class="rounded-md border border-red-200 px-3 py-1.5 text-sm font-semibold text-red-700 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                  :disabled="reviewSaving"
                  @click="removeReviewRow('projects', index)"
                >
                  Remove
                </button>
              </div>
              <div class="mt-3 grid gap-3 md:grid-cols-2">
                <label class="block">
                  <span class="text-sm font-medium text-slate-700">Title</span>
                  <input v-model.trim="row.name" class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" type="text" :disabled="reviewSaving" />
                </label>
                <label class="block">
                  <span class="text-sm font-medium text-slate-700">Link</span>
                  <input v-model.trim="row.link" class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" type="text" :disabled="reviewSaving" />
                </label>
                <label class="block md:col-span-2">
                  <span class="text-sm font-medium text-slate-700">Summary and evidence</span>
                  <textarea
                    v-model="row.summary"
                    class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                    rows="5"
                    :disabled="reviewSaving"
                  ></textarea>
                </label>
              </div>
            </article>
          </div>
        </section>

        <section class="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p class="text-sm font-semibold text-slate-900">Skills and languages</p>
          <div class="mt-3 grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,0.9fr)]">
            <label class="block">
              <span class="text-sm font-medium text-slate-700">Core skills</span>
              <textarea
                v-model="reviewForm.skillsText"
                class="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950"
                rows="6"
                placeholder="One skill per line"
                :disabled="reviewSaving"
              ></textarea>
            </label>

            <div class="space-y-3">
              <div class="flex items-center justify-between gap-3">
                <p class="text-sm font-medium text-slate-700">Languages</p>
                <button
                  type="button"
                  class="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-semibold text-slate-700 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
                  :disabled="reviewSaving"
                  @click="addReviewLanguage"
                >
                  Add language
                </button>
              </div>

              <div class="space-y-3">
                <div
                  v-for="(row, index) in reviewForm.languages"
                  :key="`language-${index}`"
                  class="grid gap-3 rounded-md border border-slate-200 bg-white p-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]"
                >
                  <label class="block">
                    <span class="text-sm font-medium text-slate-700">Language</span>
                    <input v-model.trim="row.name" class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" type="text" :disabled="reviewSaving" />
                  </label>
                  <label class="block">
                    <span class="text-sm font-medium text-slate-700">Level</span>
                    <input v-model.trim="row.level" class="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" type="text" placeholder="professional" :disabled="reviewSaving" />
                  </label>
                  <button
                    type="button"
                    class="self-end rounded-md border border-red-200 px-3 py-2 text-sm font-semibold text-red-700 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                    :disabled="reviewSaving"
                    @click="removeReviewLanguage(index)"
                  >
                    Remove
                  </button>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>

      <div class="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p
          class="min-h-5 text-sm"
          :class="reviewStatusError ? 'text-red-700' : 'text-slate-600'"
        >
          {{ reviewStatus }}
        </p>
        <div class="flex gap-3">
          <button
            type="button"
            class="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="reviewBusy || reviewSaving"
            @click="selectStep(normalizedQuestions.length ? 'questions' : 'facts')"
          >
            Back
          </button>
          <button
            type="button"
            class="rounded-md bg-sky-700 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-sky-800 disabled:cursor-not-allowed disabled:bg-slate-400"
            :disabled="reviewBusy || reviewSaving || !reviewFactSheet"
            @click="saveProfileReview"
          >
            {{ reviewSaving ? "Saving..." : "Save profile review" }}
          </button>
        </div>
      </div>
    </section>

    <section
      v-else
      class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
    >
      <div class="max-w-2xl">
        <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {{ displaySteps.find((step) => step.key === currentStep)?.label }}
        </p>
        <h2 class="mt-2 text-2xl font-semibold text-slate-950">
          {{ displaySteps.find((step) => step.key === currentStep)?.title }}
        </h2>
        <p class="mt-2 text-sm leading-6 text-slate-600">
          This Vue step is still read-only during the migration. Continue in the legacy onboarding
          page to complete setup.
        </p>
        <a
          class="mt-4 inline-flex rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50"
          href="/ui/onboarding"
        >
          Open legacy onboarding
        </a>
      </div>
    </section>
  </section>
</template>
