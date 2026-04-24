let candidateId = "";
let questions = [];
let searchRecommendationsLoaded = false;
let languageOptions = [
  {code: "en", name: "English"},
  {code: "it", name: "Italian"},
  {code: "de", name: "German"},
  {code: "fr", name: "French"},
  {code: "es", name: "Spanish"},
  {code: "pt", name: "Portuguese"},
  {code: "nl", name: "Dutch"},
];
let languageLevelOptions = [
  {value: "basic", label: "Basic"},
  {value: "working", label: "Working"},
  {value: "professional", label: "Professional"},
  {value: "fluent", label: "Fluent"},
];

function setStatus(message, isError = false) {
  const el = document.getElementById("setup-status");
  el.textContent = message || "";
  el.className = isError ? "text-sm text-red-600" : "text-sm text-slate-500";
}

function goToStep(step) {
  document.querySelectorAll(".setup-step").forEach((section) => {
    section.classList.toggle("hidden", section.dataset.step !== String(step));
  });
  document.querySelectorAll("[data-step-tab]").forEach((tab) => {
    const active = tab.dataset.stepTab === String(step);
    tab.className = active
      ? "rounded-xl border border-indigo-600 bg-indigo-50 px-3 py-3 text-left text-sm font-semibold text-indigo-700"
      : "rounded-xl border border-slate-200 bg-white px-3 py-3 text-left text-sm text-slate-500";
  });
  if (step === 5) {
    hydrateSearchFocus();
  }
  setStatus("");
}

function createSelect(options, selectedValue) {
  const select = document.createElement("select");
  select.className = "rounded-xl border border-slate-300 px-3 py-2 text-sm";
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

function addJobLanguageRow(value = {name: "English", level: "professional"}) {
  const container = document.getElementById("job-language-rows");
  if (!container) {
    return;
  }

  const row = document.createElement("div");
  row.className = "grid gap-3 rounded-xl border border-slate-200 bg-white px-3 py-3 md:grid-cols-[minmax(0,1fr)_12rem_auto]";

  const languageSelect = createSelect(languageOptions, value.name || "English");
  languageSelect.classList.add("job-language-name");

  const levelSelect = createSelect(languageLevelOptions, value.level || "professional");
  levelSelect.classList.add("job-language-level");

  const removeButton = document.createElement("button");
  removeButton.type = "button";
  removeButton.className = "rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-500 hover:bg-slate-50";
  removeButton.textContent = "Remove";
  removeButton.addEventListener("click", () => row.remove());

  row.appendChild(languageSelect);
  row.appendChild(levelSelect);
  row.appendChild(removeButton);
  container.appendChild(row);
}

function setJobLanguageRows(items) {
  const container = document.getElementById("job-language-rows");
  if (!container) {
    return;
  }
  container.innerHTML = "";
  (items || []).forEach((item) => addJobLanguageRow(item));
  if (!container.children.length) {
    addJobLanguageRow();
  }
}

function readJobLanguageRows() {
  const rows = [];
  document.querySelectorAll("#job-language-rows > div").forEach((row) => {
    const name = row.querySelector(".job-language-name")?.value?.trim();
    const level = row.querySelector(".job-language-level")?.value?.trim();
    if (!name || rows.some((item) => item.name === name)) {
      return;
    }
    rows.push({name, level: level || "professional"});
  });
  return rows;
}

function renderSuggestedRoles(roles) {
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
      if (!current.includes(role) && current.length < 5) {
        current.push(role);
        textarea.value = current.join("\n");
      }
    });
    list.appendChild(button);
  });
}

function renderRecommendedSources(sources) {
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
    const card = document.createElement("article");
    card.className = "rounded-xl border border-slate-200 bg-slate-50 px-4 py-3";

    const title = document.createElement("p");
    title.className = "font-medium text-slate-900";
    title.textContent = source.name;

    const why = document.createElement("p");
    why.className = "mt-1 text-sm text-slate-500";
    why.textContent = source.why;

    card.appendChild(title);
    card.appendChild(why);
    list.appendChild(card);
  });
}

async function hydrateSearchFocus(force = false) {
  if (!candidateId || (searchRecommendationsLoaded && !force)) {
    return;
  }
  try {
    const response = await fetch(`/search/preferences/recommendations?candidate_id=${encodeURIComponent(candidateId)}`);
    if (!response.ok) {
      return;
    }
    const data = await response.json();
    languageOptions = data.language_options || languageOptions;
    languageLevelOptions = data.level_options || languageLevelOptions;

    const countriesEl = document.getElementById("search-countries");
    if (countriesEl && !countriesEl.dataset.userEdited) {
      countriesEl.value = (data.countries || ["Italy"]).join("\n");
    }

    const rolesEl = document.getElementById("target-roles");
    if (rolesEl && !rolesEl.dataset.userEdited && (data.suggested_roles || []).length) {
      rolesEl.value = data.suggested_roles.slice(0, 5).join("\n");
    }

    setJobLanguageRows(data.selected_languages || []);
    renderSuggestedRoles(data.suggested_roles || []);
    renderRecommendedSources(data.recommended_sources || []);
    searchRecommendationsLoaded = true;
  } catch (_error) {
    setJobLanguageRows([]);
    renderRecommendedSources([]);
  }
}

async function createProfile() {
  const fullName = document.getElementById("full-name").value.trim();
  const email = document.getElementById("email").value.trim();
  if (!fullName || !email) {
    setStatus("Please enter your full name and email.", true);
    return;
  }
  const response = await fetch("/candidates", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({full_name: fullName, email}),
  });
  if (!response.ok) {
    setStatus(await response.text(), true);
    return;
  }
  const data = await response.json();
  candidateId = data.id;
  goToStep(2);
}

async function saveProvider() {
  const provider = document.querySelector('input[name="provider"]:checked')?.value || "openai";
  const openaiKey = document.getElementById("openai-key").value.trim();
  const anthropicKey = document.getElementById("anthropic-key").value.trim();
  if (provider === "openai" && !openaiKey) {
    setStatus("Paste an OpenAI API key, or choose Claude/local instead.", true);
    return;
  }
  if (provider === "anthropic" && !anthropicKey) {
    setStatus("Paste an Anthropic API key, or choose OpenAI/local instead.", true);
    return;
  }
  const payload = {
    llm_provider_mode: provider,
    use_openai_review: provider === "openai" || provider === "mixed",
    use_claude_final_review: provider === "anthropic" || provider === "mixed",
  };
  if (openaiKey) {
    payload.openai_api_key = openaiKey;
  }
  if (anthropicKey) {
    payload.anthropic_api_key = anthropicKey;
  }
  const response = await fetch("/settings/save", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    setStatus(await response.text(), true);
    return;
  }
  goToStep(3);
}

async function runIntake() {
  const files = document.getElementById("source-files").files;
  const notes = document.getElementById("profile-notes").value.trim();
  if (!candidateId) {
    setStatus("Create your profile first.", true);
    goToStep(1);
    return;
  }
  if (!files.length && !notes) {
    setStatus("Upload at least one file or paste manual notes.", true);
    return;
  }
  setStatus("Analysing your profile...");
  if (files.length) {
    const uploadData = new FormData();
    for (const file of files) {
      uploadData.append("files", file);
    }
    const uploadResponse = await fetch(`/candidates/${candidateId}/sources/upload`, {
      method: "POST",
      body: uploadData,
    });
    if (!uploadResponse.ok) {
      setStatus(await uploadResponse.text(), true);
      return;
    }
  }
  const intakeResponse = await fetch(`/candidates/${candidateId}/intake/start`, {
    method: "POST",
    headers: {"Content-Type": "application/x-www-form-urlencoded"},
    body: new URLSearchParams({profile_notes: notes}),
  });
  if (!intakeResponse.ok) {
    setStatus("The AI provider could not complete intake yet. Check your provider key in Settings, then try again.", true);
    return;
  }
  const data = await intakeResponse.json();
  if (data.status === "questions_needed" && (data.questions || []).length) {
    questions = data.questions || [];
    renderQuestions();
    goToStep(4);
  } else {
    await hydrateSearchFocus(true);
    goToStep(5);
  }
}

function renderQuestions() {
  const container = document.getElementById("questions-container");
  container.innerHTML = "";
  questions.forEach((question, index) => {
    const label = document.createElement("label");
    label.className = "block text-sm";
    const span = document.createElement("span");
    span.className = "mb-1 block font-medium text-slate-700";
    span.textContent = question;
    const textarea = document.createElement("textarea");
    textarea.rows = 3;
    textarea.id = "answer-" + index;
    textarea.className = "w-full rounded-xl border border-slate-300 px-3 py-2";
    label.appendChild(span);
    label.appendChild(textarea);
    container.appendChild(label);
  });
}

async function submitAnswers() {
  const params = new URLSearchParams();
  questions.forEach((question, index) => {
    params.append(`answers[${question}]`, document.getElementById("answer-" + index).value.trim());
  });
  const response = await fetch(`/candidates/${candidateId}/intake/answer`, {
    method: "POST",
    headers: {"Content-Type": "application/x-www-form-urlencoded"},
    body: params,
  });
  if (!response.ok) {
    setStatus(await response.text(), true);
    return;
  }
  const data = await response.json();
  if (data.status === "questions_needed" && (data.questions || []).length) {
    questions = data.questions || [];
    renderQuestions();
  } else {
    await hydrateSearchFocus(true);
    goToStep(5);
  }
}

async function saveSearchFocus() {
  const roles = document.getElementById("target-roles").value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean)
    .slice(0, 5);
  const countries = document.getElementById("search-countries").value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean)
    .slice(0, 5);
  const jobLanguages = readJobLanguageRows().slice(0, 6);

  if (!roles.length) {
    setStatus("Add at least one target role.", true);
    return;
  }
  const payload = {
    jobspy_discover_queries: roles,
    job_search_countries: countries.length ? countries : ["Italy"],
    jobspy_discover_location: countries[0] || "Italy",
    job_search_languages: jobLanguages,
    target_job_seniority: document.getElementById("target-seniority").value,
  };
  const response = await fetch("/settings/save", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    setStatus(await response.text(), true);
    return;
  }
  document.querySelectorAll(".setup-step").forEach((section) => section.classList.add("hidden"));
  document.getElementById("done-panel").classList.remove("hidden");
  setStatus("");
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("target-roles")?.addEventListener("input", (event) => {
    event.currentTarget.dataset.userEdited = "1";
  });
  document.getElementById("search-countries")?.addEventListener("input", (event) => {
    event.currentTarget.dataset.userEdited = "1";
  });

  setJobLanguageRows([]);
  goToStep(1);
});
