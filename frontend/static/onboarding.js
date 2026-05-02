/*
 * Onboarding screen controller.
 *
 * This file currently handles the entire intake journey: source upload,
 * follow-up questions, extracted-data review, and final search setup. The
 * planned frontend refactor should split those concerns into smaller modules.
 */

let candidateId = "";
let questions = [];
let searchRecommendationsLoaded = false;
let onboardingLanguageOptions = [{code: "en", name: "English"}];
let onboardingLevelOptions = [
  {value: "basic", label: "Basic"},
  {value: "working", label: "Working"},
  {value: "professional", label: "Professional"},
  {value: "fluent", label: "Fluent"},
];
let onboardingLanguagesTouched = false;
let onboardingReviewFactSheet = null;

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function onboardingSelect(options, selectedValue, className) {
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

// Language rows are reused across the review and search-setup stages.
function addOnboardingLanguageRow(
  value = {name: "English", level: "professional"},
  {markTouched = true} = {},
) {
  const container = document.getElementById("onboarding-language-rows");
  if (!container) {
    return;
  }
  const row = document.createElement("div");
  row.className = "grid gap-3 rounded-xl border border-slate-300 bg-white px-3 py-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]";

  const nameSelect = onboardingSelect(
    onboardingLanguageOptions,
    value.name || "English",
    "onboarding-job-language-name w-full rounded-xl border border-slate-300 px-3 py-2 text-sm",
  );
  const levelSelect = onboardingSelect(
    onboardingLevelOptions,
    value.level || "professional",
    "onboarding-job-language-level w-full rounded-xl border border-slate-300 px-3 py-2 text-sm",
  );
  nameSelect.addEventListener("change", () => {
    onboardingLanguagesTouched = true;
  });
  levelSelect.addEventListener("change", () => {
    onboardingLanguagesTouched = true;
  });

  const removeButton = document.createElement("button");
  removeButton.type = "button";
  removeButton.className = "app-button app-button--sm app-button--danger";
  removeButton.textContent = "Remove";
  removeButton.addEventListener("click", () => {
    row.remove();
    onboardingLanguagesTouched = true;
    if (!container.children.length) {
      addOnboardingLanguageRow({name: "English", level: "professional"}, {markTouched: false});
    }
  });

  row.appendChild(nameSelect);
  row.appendChild(levelSelect);
  row.appendChild(removeButton);
  container.appendChild(row);
  if (markTouched) {
    onboardingLanguagesTouched = true;
  }
}

function readOnboardingLanguageRows() {
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
}

// Rehydrate saved language preferences into editable rows for review/search setup.
function renderOnboardingLanguageRows(values = [], {markTouched = false} = {}) {
  const container = document.getElementById("onboarding-language-rows");
  if (!container) {
    return;
  }
  container.innerHTML = "";
  const rows = Array.isArray(values) && values.length ? values : [{name: "English", level: "professional"}];
  rows.forEach((item) => addOnboardingLanguageRow(item, {markTouched}));
}

function isSupportedSourceFile(file) {
  const name = (file?.name || "").toLowerCase();
  const type = (file?.type || "").toLowerCase();
  if (name.endsWith(".pdf") || name.endsWith(".txt") || name.endsWith(".md") || name.endsWith(".rst")) {
    return true;
  }
  return type === "application/pdf" || type === "text/plain" || type === "text/markdown";
}

function onboardingTimeoutSignal(timeoutMs = 15000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  return {
    signal: controller.signal,
    cancel() {
      clearTimeout(timer);
    },
  };
}

async function onboardingFetchJson(url, options = {}, timeoutMs = 15000) {
  const timeout = onboardingTimeoutSignal(timeoutMs);
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

function selectedProvider() {
  return document.querySelector('input[name="provider"]:checked')?.value || "openai";
}

function toggleProviderFields() {
  const provider = selectedProvider();
  document.getElementById("onboard-openai-fields")?.classList.toggle("hidden", provider !== "openai");
  document.getElementById("onboard-anthropic-fields")?.classList.toggle("hidden", provider !== "anthropic");
  document.getElementById("onboard-lmstudio-fields")?.classList.toggle("hidden", provider !== "lm_studio");
  document.getElementById("onboard-ollama-fields")?.classList.toggle("hidden", provider !== "ollama");
}

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
  if (step === 6) {
    hydrateSearchFocus();
  }
  setStatus("");
}

function selectProviderRadio(provider) {
  const target = document.querySelector(`input[name="provider"][value="${provider}"]`);
  if (!target) {
    return;
  }
  target.checked = true;
  toggleProviderFields();
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
      if (!current.includes(role) && current.length < 4) {
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
    const pill = document.createElement("span");
    pill.className = "inline-flex rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-sm text-slate-700";
    pill.title = source.why || "";
    pill.textContent = source.name;
    list.appendChild(pill);
  });
}

function reviewInput(id, value, placeholder = "") {
  return `<input id="${id}" type="text" class="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm" value="${escapeHtml(value)}" placeholder="${escapeHtml(placeholder)}">`;
}

function reviewTextarea(id, value, rows = 3, placeholder = "") {
  return `<textarea id="${id}" rows="${rows}" class="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm" placeholder="${escapeHtml(placeholder)}">${escapeHtml(value)}</textarea>`;
}

function renderReviewRows(sectionId, items, fields, emptyLabel) {
  if (!items.length) {
    return `<div class="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-4 text-sm text-slate-400">${emptyLabel}</div>`;
  }
  return items.map((item, index) => `
    <article class="rounded-2xl border border-slate-200 bg-white p-4 space-y-3">
      <div class="flex items-center justify-between gap-3">
        <p class="text-sm font-semibold text-slate-800">${escapeHtml(item[fields[0].key] || `${sectionId} ${index + 1}`)}</p>
        <button type="button" class="app-button app-button--sm app-button--danger" onclick="removeReviewRow('${sectionId}', ${index})">Remove</button>
      </div>
      <div class="grid gap-3 md:grid-cols-2">
        ${fields.map((field) => `
          <label class="${field.full ? "md:col-span-2" : ""} block text-sm">
            <span class="mb-1 block font-medium text-slate-700">${field.label}</span>
            ${field.type === "textarea"
              ? reviewTextarea(`${sectionId}-${index}-${field.key}`, item[field.key] || "", field.rows || 3, field.placeholder || "")
              : reviewInput(`${sectionId}-${index}-${field.key}`, item[field.key] || "", field.placeholder || "")}
          </label>
        `).join("")}
      </div>
    </article>
  `).join("");
}

function renderSkillsEditor(skills) {
  return `
    <label class="block text-sm">
      <span class="mb-1 block font-medium text-slate-700">Core skills</span>
      ${reviewTextarea("review-skills", (skills || []).join("\n"), 6, "One skill per line")}
    </label>
  `;
}

function renderLanguagesEditor(languages) {
  const rows = Array.isArray(languages) && languages.length ? languages : [{name: "English", level: "professional"}];
  return rows.map((item, index) => `
    <div class="grid gap-3 rounded-xl border border-slate-200 bg-white px-3 py-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]">
      ${reviewInput(`review-language-${index}-name`, item.name || "", "Language")}
      ${reviewInput(`review-language-${index}-level`, item.level || "", "Level")}
      <button type="button" class="app-button app-button--sm app-button--danger" onclick="removeReviewLanguage(${index})">Remove</button>
    </div>
  `).join("");
}

function renderReadinessBanner(readiness) {
  const banner = document.getElementById("profile-readiness-banner");
  if (!banner) {
    return;
  }
  if (!readiness) {
    banner.classList.add("hidden");
    return;
  }
  const status = readiness.status || "usable_with_warnings";
  const tone = status === "ready"
    ? "border-emerald-200 bg-emerald-50 text-emerald-800"
    : status === "insufficient_profile_data"
      ? "border-rose-200 bg-rose-50 text-rose-800"
      : "border-amber-200 bg-amber-50 text-amber-800";
  banner.className = `rounded-2xl border px-4 py-3 text-sm ${tone}`;
  banner.classList.remove("hidden");
  const reason = (readiness.reasons || [])[0] || "Review the extracted profile before continuing.";
  const missing = Array.isArray(readiness.missing_sections) && readiness.missing_sections.length
    ? ` Missing: ${readiness.missing_sections.join(", ")}.`
    : "";
  banner.innerHTML = `
    <p class="font-semibold">${status === "ready" ? "Profile Readiness: Ready" : status === "insufficient_profile_data" ? "Profile Readiness: Needs more evidence" : "Profile Readiness: Usable with warnings"}</p>
    <p class="mt-1">${escapeHtml(reason)}${escapeHtml(missing)}</p>
  `;
}

function renderProfileReview(factSheet, readiness) {
  onboardingReviewFactSheet = factSheet;
  renderReadinessBanner(readiness);
  const shell = document.getElementById("onboarding-review-shell");
  if (!shell) {
    return;
  }
  const person = factSheet?.person || {};
  const contact = person.contact || {};
  shell.innerHTML = `
    <section class="rounded-2xl border border-slate-200 bg-white p-4 space-y-3">
      <div class="flex items-center justify-between gap-3">
        <div>
          <p class="text-sm font-semibold text-slate-900">Identity</p>
          <p class="text-xs text-slate-500">Confirm the person details that will appear in CVs and application packages.</p>
        </div>
      </div>
      <div class="grid gap-3 md:grid-cols-2">
        <label class="block text-sm">
          <span class="mb-1 block font-medium text-slate-700">Full name</span>
          ${reviewInput("review-full-name", person.full_name || "", "Full name")}
        </label>
        <label class="block text-sm">
          <span class="mb-1 block font-medium text-slate-700">Email</span>
          ${reviewInput("review-email", contact.email || "", "Email")}
        </label>
      </div>
    </section>

    <section class="rounded-2xl border border-slate-200 bg-white p-4 space-y-3">
      <div class="flex items-center justify-between gap-3">
        <div>
          <p class="text-sm font-semibold text-slate-900">Education</p>
          <p class="text-xs text-slate-500">Keep only real entries that support your target roles.</p>
        </div>
        <button type="button" class="app-button app-button--sm" onclick="addReviewRow('education')">Add education</button>
      </div>
      <div id="review-education-list">${renderReviewRows("education", factSheet?.education || [], [
        {key: "degree", label: "Degree"},
        {key: "field", label: "Field"},
        {key: "institution", label: "Institution"},
        {key: "status", label: "Status / year"},
      ], "No education extracted yet.")}</div>
    </section>

    <section class="rounded-2xl border border-slate-200 bg-white p-4 space-y-3">
      <div class="flex items-center justify-between gap-3">
        <div>
          <p class="text-sm font-semibold text-slate-900">Experience</p>
          <p class="text-xs text-slate-500">Use grounded roles only. One responsibility per line.</p>
        </div>
        <button type="button" class="app-button app-button--sm" onclick="addReviewRow('experience')">Add experience</button>
      </div>
      <div id="review-experience-list">${renderReviewRows("experience", factSheet?.experience || [], [
        {key: "role_title", label: "Role title"},
        {key: "organization", label: "Company / organisation"},
        {key: "start_date", label: "Start date"},
        {key: "end_date", label: "End date"},
        {key: "responsibilities_text", label: "Responsibilities", type: "textarea", rows: 4, full: true, placeholder: "One bullet per line"},
      ].map((field) => field.key === "responsibilities_text"
        ? field
        : field), "No experience extracted yet.")}</div>
    </section>

    <section class="rounded-2xl border border-slate-200 bg-white p-4 space-y-3">
      <div class="flex items-center justify-between gap-3">
        <div>
          <p class="text-sm font-semibold text-slate-900">Projects and evidence</p>
          <p class="text-xs text-slate-500">Keep short evidence-backed notes. One result per line.</p>
        </div>
        <button type="button" class="app-button app-button--sm" onclick="addReviewRow('projects')">Add evidence</button>
      </div>
      <div id="review-projects-list">${renderReviewRows("projects", factSheet?.projects || [], [
        {key: "name", label: "Title"},
        {key: "link", label: "Link"},
        {key: "summary", label: "Summary and evidence", type: "textarea", rows: 5, full: true},
      ], "No project or evidence items extracted yet.")}</div>
    </section>

    <section class="rounded-2xl border border-slate-200 bg-white p-4 space-y-3">
      <p class="text-sm font-semibold text-slate-900">Skills and languages</p>
      <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,0.9fr)]">
        <div>${renderSkillsEditor(readFromFactSheetSkills(factSheet))}</div>
        <div class="space-y-3">
          <div class="flex items-center justify-between gap-3">
            <p class="text-sm font-medium text-slate-700">Languages</p>
            <button type="button" class="app-button app-button--sm" onclick="addReviewLanguage()">Add language</button>
          </div>
          <div id="review-languages-list" class="space-y-3">${renderLanguagesEditor(factSheet?.languages || [])}</div>
        </div>
      </div>
    </section>
  `;
  hydrateReviewDerivedFields();
}

function readFromFactSheetSkills(factSheet) {
  const skills = factSheet?.skills;
  if (!skills || typeof skills !== "object") {
    return [];
  }
  const rows = [];
  Object.values(skills).forEach((value) => {
    if (Array.isArray(value)) {
      value.forEach((item) => {
        const text = String(item || "").trim();
        if (text && !rows.includes(text)) {
          rows.push(text);
        }
      });
    }
  });
  return rows;
}

function hydrateReviewDerivedFields() {
  (onboardingReviewFactSheet?.experience || []).forEach((item, index) => {
    const el = document.getElementById(`experience-${index}-responsibilities_text`);
    if (el) {
      const values = Array.isArray(item.responsibilities) ? item.responsibilities : [];
      el.value = values.join("\n");
    }
  });
  (onboardingReviewFactSheet?.projects || []).forEach((item, index) => {
    const el = document.getElementById(`projects-${index}-summary`);
    if (el && !el.value.trim() && Array.isArray(item.key_results) && item.key_results.length) {
      el.value = item.key_results.join("\n");
    }
  });
}

function addReviewRow(sectionId) {
  if (!onboardingReviewFactSheet) {
    return;
  }
  if (!Array.isArray(onboardingReviewFactSheet[sectionId])) {
    onboardingReviewFactSheet[sectionId] = [];
  }
  if (sectionId === "education") {
    onboardingReviewFactSheet[sectionId].push({degree: "", field: "", institution: "", status: ""});
  } else if (sectionId === "experience") {
    onboardingReviewFactSheet[sectionId].push({role_title: "", organization: "", start_date: "", end_date: "", responsibilities: []});
  } else if (sectionId === "projects") {
    onboardingReviewFactSheet[sectionId].push({name: "", link: "", summary: ""});
  }
  renderProfileReview(onboardingReviewFactSheet, null);
}

function removeReviewRow(sectionId, index) {
  if (!onboardingReviewFactSheet || !Array.isArray(onboardingReviewFactSheet[sectionId])) {
    return;
  }
  onboardingReviewFactSheet[sectionId].splice(index, 1);
  renderProfileReview(onboardingReviewFactSheet, null);
}

function addReviewLanguage() {
  if (!onboardingReviewFactSheet) {
    return;
  }
  if (!Array.isArray(onboardingReviewFactSheet.languages)) {
    onboardingReviewFactSheet.languages = [];
  }
  onboardingReviewFactSheet.languages.push({name: "", level: ""});
  renderProfileReview(onboardingReviewFactSheet, null);
}

function removeReviewLanguage(index) {
  if (!onboardingReviewFactSheet || !Array.isArray(onboardingReviewFactSheet.languages)) {
    return;
  }
  onboardingReviewFactSheet.languages.splice(index, 1);
  renderProfileReview(onboardingReviewFactSheet, null);
}

function collectReviewRows(prefix, keys) {
  const rows = [];
  let index = 0;
  while (document.getElementById(`${prefix}-${index}-${keys[0]}`)) {
    const row = {};
    keys.forEach((key) => {
      row[key] = document.getElementById(`${prefix}-${index}-${key}`)?.value?.trim() || "";
    });
    rows.push(row);
    index += 1;
  }
  return rows;
}

async function loadProfileReview() {
  if (!candidateId) {
    return;
  }
  const response = await fetch(`/candidates/${candidateId}/onboarding-review`);
  if (!response.ok) {
    setStatus("Could not load the extracted profile review.", true);
    return;
  }
  const data = await response.json();
  onboardingReviewFactSheet = data.fact_sheet;
  renderProfileReview(data.fact_sheet, data.readiness);
}

async function saveProfileReview() {
  if (!candidateId || !onboardingReviewFactSheet) {
    setStatus("Run intake before saving the profile review.", true);
    return;
  }
  const experience = collectReviewRows("experience", ["role_title", "organization", "start_date", "end_date"]).map((row, index) => ({
    ...row,
    responsibilities: (document.getElementById(`experience-${index}-responsibilities_text`)?.value || "")
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean),
    tools: [],
    achievements: [],
    evidence_refs: [],
  })).filter((row) => row.role_title || row.organization || row.responsibilities.length);
  const projects = collectReviewRows("projects", ["name", "link", "summary"]).map((row) => ({
    ...row,
    tools: [],
  })).filter((row) => row.name || row.summary);
  const education = collectReviewRows("education", ["degree", "field", "institution", "status"])
    .filter((row) => row.degree || row.field || row.institution);
  const skills = (document.getElementById("review-skills")?.value || "")
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
  const languages = [];
  let languageIndex = 0;
  while (document.getElementById(`review-language-${languageIndex}-name`)) {
    const name = document.getElementById(`review-language-${languageIndex}-name`)?.value?.trim();
    const level = document.getElementById(`review-language-${languageIndex}-level`)?.value?.trim();
    if (name) {
      languages.push({name, level: level || "professional"});
    }
    languageIndex += 1;
  }

  const payload = {
    ...onboardingReviewFactSheet,
    person: {
      ...(onboardingReviewFactSheet.person || {}),
      full_name: document.getElementById("review-full-name")?.value?.trim() || "",
      contact: {
        ...((onboardingReviewFactSheet.person || {}).contact || {}),
        email: document.getElementById("review-email")?.value?.trim() || "",
      },
    },
    experience,
    projects,
    education,
    skills: {business_tools: skills},
    languages,
  };

  const response = await fetch(`/candidates/${candidateId}/fact-sheet-json`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    setStatus(await response.text(), true);
    return;
  }
  await loadProfileReview();
  await hydrateSearchFocus(true);
  goToStep(6);
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
    onboardingLanguageOptions = Array.isArray(data.language_options) && data.language_options.length
      ? data.language_options
      : onboardingLanguageOptions;
    onboardingLevelOptions = Array.isArray(data.level_options) && data.level_options.length
      ? data.level_options
      : onboardingLevelOptions;
    const countriesEl = document.getElementById("search-countries");
    if (countriesEl && !countriesEl.dataset.userEdited) {
      const country = (data.countries || ["Italy"])[0] || "Italy";
      countriesEl.value = country;
    }

    const rolesEl = document.getElementById("target-roles");
    if (rolesEl && !rolesEl.dataset.userEdited && (data.suggested_roles || []).length) {
      rolesEl.value = data.suggested_roles.slice(0, 4).join("\n");
    }
    if (!onboardingLanguagesTouched) {
      renderOnboardingLanguageRows(data.selected_languages || [], {markTouched: false});
    }

    renderSuggestedRoles(data.suggested_roles || []);
    renderRecommendedSources(data.recommended_sources || []);
    searchRecommendationsLoaded = true;
  } catch (_error) {
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
  goToStep(3);
}

async function validateAndSaveProvider() {
  const provider = selectedProvider();
  const openaiKey = document.getElementById("openai-key").value.trim();
  const anthropicKey = document.getElementById("anthropic-key").value.trim();
  const lmStudioUrl = document.getElementById("lmstudio-url")?.value.trim() || "";
  const ollamaUrl = document.getElementById("ollama-url")?.value.trim() || "";
  const status = document.getElementById("provider-validate-status");
  const button = Array.from(document.querySelectorAll("button")).find((el) => el.textContent.includes("Validate & Continue"));
  if (status) {
    status.textContent = "Validating...";
    status.className = "text-sm text-slate-500";
  }
  if (button) {
    button.disabled = true;
  }

  try {
    const {response: validationResponse, data: validation} = await onboardingFetchJson("/providers/validate", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        provider_mode: provider,
        openai_api_key: openaiKey,
        anthropic_api_key: anthropicKey,
        openai_review_model: "gpt-4o-mini",
        lm_studio_base_url: lmStudioUrl,
        ollama_base_url: ollamaUrl,
      }),
    }, 15000);
    if (!validationResponse.ok || !validation.ok) {
      const detail = validation?.detail || "Provider validation failed.";
      if (status) {
        status.textContent = detail;
        status.className = "text-sm text-red-600";
      }
      return;
    }

    const payload = {
      llm_provider_mode: provider,
      use_openai_review: provider === "openai",
      use_claude_final_review: provider === "anthropic",
      lm_studio_base_url: lmStudioUrl || "http://localhost:1234/v1",
      ollama_base_url: ollamaUrl || "http://localhost:11434",
      openai_review_model: "gpt-4o-mini",
      openai_escalation_model: "gpt-4o",
    };
    const discoveredModels = Array.isArray(validation.models) ? validation.models.filter(Boolean) : [];
    const chosen = chooseLocalModelDefaults(discoveredModels);
    if (provider === "lm_studio" && !nonEmbeddingModels(discoveredModels).length) {
      if (status) {
        status.textContent = "LM Studio responded, but no usable chat models were found. Load a non-embedding model first.";
        status.className = "text-sm text-red-600";
      }
      return;
    }
    if (provider === "ollama") {
      const singleLocalModel = chosen.writer || chosen.small;
      payload.ollama_fast_model = singleLocalModel;
      payload.ollama_writer_model = singleLocalModel;
      if (!singleLocalModel) {
        if (status) {
          status.textContent = "Ollama responded, but no usable chat models were found. Pull a model first.";
          status.className = "text-sm text-red-600";
        }
        return;
      }
    }
    if (provider === "lm_studio") {
      const singleLocalModel = chosen.writer || chosen.small;
      payload.lm_studio_small_model = singleLocalModel;
      payload.lm_studio_writer_model = singleLocalModel;
      payload.lm_studio_mid_model = singleLocalModel;
    }
    if (openaiKey) {
      payload.openai_api_key = openaiKey;
    }
    if (anthropicKey) {
      payload.anthropic_api_key = anthropicKey;
    }
    const {response, data} = await onboardingFetchJson("/settings/save", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload),
    }, 12000);
    if (!response.ok) {
      const detail = data?.detail || "Saving provider settings failed.";
      if (status) {
        status.textContent = detail;
        status.className = "text-sm text-red-600";
      }
      return;
    }
    if (status) {
      status.textContent = validation.detail || "Provider ready.";
      status.className = "text-sm text-emerald-700";
    }
    goToStep(2);
  } catch (error) {
    if (status) {
      status.textContent = error?.name === "AbortError"
        ? "Provider validation timed out. Check the provider and try again."
        : `Provider validation failed: ${error.message || error}`;
      status.className = "text-sm text-red-600";
    }
  } finally {
    if (button) {
      button.disabled = false;
    }
  }
}

async function runIntake() {
  const files = document.getElementById("source-files").files;
  const notes = document.getElementById("profile-notes").value.trim();
  if (!candidateId) {
    setStatus("Create your profile first.", true);
    goToStep(2);
    return;
  }
  if (!files.length && !notes) {
    setStatus("Upload at least one CV file (PDF/TXT) or add manual notes.", true);
    return;
  }
  if (files.length) {
    const invalid = Array.from(files).filter((file) => !isSupportedSourceFile(file));
    if (invalid.length) {
      setStatus("Only PDF or plain-text files are accepted in onboarding intake.", true);
      return;
    }
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
    let errMsg = "The AI provider could not complete intake. Check your provider key in Settings.";
    try {
      const errData = await intakeResponse.json();
      if (errData.detail) errMsg = errData.detail;
    } catch (_) {}
    setStatus(errMsg, true);
    return;
  }
  const data = await intakeResponse.json();
  if (data.status === "questions_needed" && (data.questions || []).length) {
    questions = data.questions || [];
    renderQuestions();
    goToStep(4);
  } else {
    const setupReady = await ensureFactSheetReady();
    if (!setupReady) {
      goToStep(3);
      return;
    }
    await loadProfileReview();
    goToStep(5);
  }
}

function renderQuestions() {
  const container = document.getElementById("questions-container");
  container.innerHTML = "";
  questions.forEach((question, index) => {
    const questionObj = typeof question === "string"
      ? {id: `q${index + 1}`, prompt: question, kind: "text", options: [], allow_free_text: true}
      : question;
    const questionId = questionObj.id || `q${index + 1}`;
    const label = document.createElement("label");
    label.className = "block text-sm";
    const span = document.createElement("span");
    span.className = "mb-1 block font-medium text-slate-700";
    span.textContent = questionObj.prompt || questionObj.question || questionId;
    label.appendChild(span);
    if (questionObj.required !== false) {
      const hint = document.createElement("p");
      hint.className = "mb-2 text-xs font-medium uppercase tracking-wide text-amber-700";
      hint.textContent = "Required to build a usable fact sheet";
      label.appendChild(hint);
    }

    const kind = questionObj.kind || "text";
    const options = Array.isArray(questionObj.options) ? questionObj.options : [];

    if (kind === "single_select" && options.length) {
      const list = document.createElement("div");
      list.className = "space-y-2";
      options.forEach((option, optionIndex) => {
        const optionLabel = document.createElement("label");
        optionLabel.className = "flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2";
        const input = document.createElement("input");
        input.type = "radio";
        input.name = `answer-${questionId}`;
        input.value = option;
        input.id = `answer-${questionId}-${optionIndex}`;
        optionLabel.appendChild(input);
        const text = document.createElement("span");
        text.textContent = option;
        optionLabel.appendChild(text);
        list.appendChild(optionLabel);
      });
      label.appendChild(list);
    } else if (kind === "multi_select" && options.length) {
      const list = document.createElement("div");
      list.className = "space-y-2";
      options.forEach((option, optionIndex) => {
        const optionLabel = document.createElement("label");
        optionLabel.className = "flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2";
        const input = document.createElement("input");
        input.type = "checkbox";
        input.value = option;
        input.id = `answer-${questionId}-${optionIndex}`;
        input.dataset.questionId = questionId;
        optionLabel.appendChild(input);
        const text = document.createElement("span");
        text.textContent = option;
        optionLabel.appendChild(text);
        list.appendChild(optionLabel);
      });
      label.appendChild(list);
    }

    if (kind === "text" || questionObj.allow_free_text) {
      const textarea = document.createElement("textarea");
      textarea.rows = kind === "text" ? 3 : 2;
      textarea.id = `answer-${questionId}`;
      textarea.className = "mt-2 w-full rounded-xl border border-slate-300 px-3 py-2";
      textarea.placeholder = kind === "text" ? "Type your answer" : "Optional note";
      label.appendChild(textarea);
    }

    container.appendChild(label);
  });
}

async function submitAnswers() {
  const answers = {};
  const missingPrompts = [];
  questions.forEach((question, index) => {
    const questionObj = typeof question === "string"
      ? {id: `q${index + 1}`, prompt: question, kind: "text", options: [], allow_free_text: true, required: true}
      : question;
    const questionId = questionObj.id || `q${index + 1}`;
    const kind = questionObj.kind || "text";
    const required = questionObj.required !== false;

    if (kind === "single_select") {
      const selected = document.querySelector(`input[name="answer-${questionId}"]:checked`);
      const note = document.getElementById(`answer-${questionId}`)?.value?.trim();
      const value = note || selected?.value || "";
      answers[questionId] = value;
      if (required && !value) {
        missingPrompts.push(questionObj.prompt || questionId);
      }
      return;
    }

    if (kind === "multi_select") {
      const values = Array.from(document.querySelectorAll(`input[data-question-id="${questionId}"]:checked`))
        .map((input) => input.value)
        .filter(Boolean);
      const note = document.getElementById(`answer-${questionId}`)?.value?.trim();
      const value = note ? [...values, note] : values;
      answers[questionId] = value;
      if (required && !value.length) {
        missingPrompts.push(questionObj.prompt || questionId);
      }
      return;
    }

    const value = document.getElementById(`answer-${questionId}`)?.value?.trim() || "";
    answers[questionId] = value;
    if (required && !value) {
      missingPrompts.push(questionObj.prompt || questionId);
    }
  });

  if (missingPrompts.length) {
    setStatus(`Please answer the required questions first. Missing: ${missingPrompts[0]}`, true);
    return;
  }

  const response = await fetch(`/candidates/${candidateId}/intake/answer`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({answers}),
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
    const setupReady = await ensureFactSheetReady();
    if (!setupReady) {
      goToStep(3);
      return;
    }
    await loadProfileReview();
    goToStep(5);
  }
}

async function ensureFactSheetReady() {
  try {
    const response = await fetch("/setup/status");
    if (!response.ok) {
      return true;
    }
    const data = await response.json();
    if (data?.fact_sheet_ready) {
      return true;
    }
    const missing = Array.isArray(data?.missing_steps) ? data.missing_steps : [];
    const hint = missing.length ? ` Missing: ${missing.join(", ")}.` : "";
    setStatus(`Intake finished but your fact sheet is still incomplete.${hint} Upload a richer CV or add more details.`, true);
    return false;
  } catch (_error) {
    return true;
  }
}

async function saveSearchFocus() {
  const roles = document.getElementById("target-roles").value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean)
    .slice(0, 4);
  const countries = document.getElementById("search-countries").value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean)
    .slice(0, 1);
  const country = countries[0] || "Italy";
  const languages = readOnboardingLanguageRows();
  if (!roles.length) {
    setStatus("Add at least one target role.", true);
    return;
  }
  const payload = {
    jobspy_discover_queries: roles,
    job_search_countries: [country],
    jobspy_discover_location: country,
    target_job_seniority: document.getElementById("target-seniority").value,
    job_search_languages: languages,
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

async function hydrateOnboardingState() {
  try {
    const [setupResponse, settingsResponse, candidatesResponse] = await Promise.all([
      fetch("/setup/status"),
      fetch("/settings/current"),
      fetch("/candidates"),
    ]);
    if (!setupResponse.ok || !settingsResponse.ok || !candidatesResponse.ok) {
      goToStep(1);
      return;
    }

    const setup = await setupResponse.json();
    const currentSettings = await settingsResponse.json();
    const candidates = await candidatesResponse.json();
    const candidate = Array.isArray(candidates) && candidates.length ? candidates[0] : null;

    const providerMode = currentSettings.llm_provider_mode || "openai";
    selectProviderRadio(providerMode);
    if (providerMode === "lm_studio") {
      const lmUrl = document.getElementById("lmstudio-url");
      if (lmUrl) {
        lmUrl.value = currentSettings.lm_studio_base_url || lmUrl.value;
      }
    }
    if (providerMode === "ollama") {
      const ollamaUrl = document.getElementById("ollama-url");
      if (ollamaUrl) {
        ollamaUrl.value = currentSettings.ollama_base_url || ollamaUrl.value;
      }
    }

    if (candidate) {
      candidateId = candidate.id || "";
      const fullNameInput = document.getElementById("full-name");
      const emailInput = document.getElementById("email");
      if (fullNameInput && !fullNameInput.value) {
        fullNameInput.value = candidate.full_name || "";
      }
      if (emailInput && !emailInput.value) {
        emailInput.value = candidate.email || "";
      }
    }

    if (setup.complete) {
      const rolesEl = document.getElementById("target-roles");
      const countriesEl = document.getElementById("search-countries");
      if (rolesEl) {
        rolesEl.value = (currentSettings.jobspy_discover_queries || []).join("\n");
      }
      if (countriesEl) {
        countriesEl.value = (currentSettings.job_search_countries || ["Italy"])[0] || "Italy";
      }
      if (!onboardingLanguagesTouched) {
        renderOnboardingLanguageRows(currentSettings.job_search_languages || [], {markTouched: false});
      }
      const seniorityEl = document.getElementById("target-seniority");
      if (seniorityEl && currentSettings.target_job_seniority) {
        seniorityEl.value = currentSettings.target_job_seniority;
      }
      document.querySelectorAll(".setup-step").forEach((section) => section.classList.add("hidden"));
      document.getElementById("done-panel").classList.remove("hidden");
      return;
    }

    if (candidateId) {
      const intakeResponse = await fetch(`/candidates/${candidateId}/intake/status`);
      if (intakeResponse.ok) {
        const intake = await intakeResponse.json();
        if (intake.status === "questions_needed" && (intake.questions || []).length) {
          questions = intake.questions || [];
          renderQuestions();
          goToStep(4);
          return;
        }
      }
    }

    if (setup.fact_sheet_ready) {
      const rolesEl = document.getElementById("target-roles");
      const countriesEl = document.getElementById("search-countries");
      if (rolesEl) {
        rolesEl.value = (currentSettings.jobspy_discover_queries || []).join("\n");
      }
      if (countriesEl) {
        countriesEl.value = (currentSettings.job_search_countries || ["Italy"])[0] || "Italy";
      }
      if (!onboardingLanguagesTouched) {
        renderOnboardingLanguageRows(currentSettings.job_search_languages || [], {markTouched: false});
      }
      const seniorityEl = document.getElementById("target-seniority");
      if (seniorityEl && currentSettings.target_job_seniority) {
        seniorityEl.value = currentSettings.target_job_seniority;
      }
      await loadProfileReview();
      await hydrateSearchFocus(true);
      goToStep(6);
      return;
    }

    if (candidateId) {
      goToStep(3);
      return;
    }
    if (setup.provider?.ready) {
      goToStep(2);
      return;
    }
    goToStep(1);
  } catch (_error) {
    goToStep(1);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll('input[name="provider"]').forEach((input) => {
    input.addEventListener("change", toggleProviderFields);
  });
  document.querySelectorAll("[data-step-tab]").forEach((tab) => {
    tab.addEventListener("click", () => {
      const step = Number(tab.dataset.stepTab || "1");
      if (!Number.isNaN(step) && step >= 1 && step <= 6) {
        goToStep(step);
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
    addOnboardingLanguageRow();
  });
  renderOnboardingLanguageRows([], {markTouched: false});
  toggleProviderFields();
  hydrateOnboardingState();
});
