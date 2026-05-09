/*
 * Profile review stage.
 *
 * This stage turns extracted fact-sheet data into editable form controls before
 * the user commits the profile and search preferences.
 */

(() => {
  const app = window.OnboardingApp;

  app.reviewInput = function reviewInput(id, value, placeholder = "") {
    return `<input id="${id}" type="text" class="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm" value="${app.escapeHtml(value)}" placeholder="${app.escapeHtml(placeholder)}">`;
  };

  app.reviewTextarea = function reviewTextarea(id, value, rows = 3, placeholder = "") {
    return `<textarea id="${id}" rows="${rows}" class="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm" placeholder="${app.escapeHtml(placeholder)}">${app.escapeHtml(value)}</textarea>`;
  };

  app.renderReviewRows = function renderReviewRows(sectionId, items, fields, emptyLabel) {
    if (!items.length) {
      return `<div class="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-4 text-sm text-slate-400">${emptyLabel}</div>`;
    }
    return items.map((item, index) => `
      <article class="rounded-2xl border border-slate-200 bg-white p-4 space-y-3">
        <div class="flex items-center justify-between gap-3">
          <p class="text-sm font-semibold text-slate-800">${app.escapeHtml(item[fields[0].key] || `${sectionId} ${index + 1}`)}</p>
          <button type="button" class="app-button app-button--sm app-button--danger" onclick="removeReviewRow('${sectionId}', ${index})">Remove</button>
        </div>
        <div class="grid gap-3 md:grid-cols-2">
          ${fields.map((field) => `
            <label class="${field.full ? "md:col-span-2" : ""} block text-sm">
              <span class="mb-1 block font-medium text-slate-700">${field.label}</span>
              ${field.type === "textarea"
                ? app.reviewTextarea(`${sectionId}-${index}-${field.key}`, item[field.key] || "", field.rows || 3, field.placeholder || "")
                : app.reviewInput(`${sectionId}-${index}-${field.key}`, item[field.key] || "", field.placeholder || "")}
            </label>
          `).join("")}
        </div>
      </article>
    `).join("");
  };

  app.renderSkillsEditor = function renderSkillsEditor(skills) {
    return `
      <label class="block text-sm">
        <span class="mb-1 block font-medium text-slate-700">Core skills</span>
        ${app.reviewTextarea("review-skills", (skills || []).join("\n"), 6, "One skill per line")}
      </label>
    `;
  };

  app.renderLanguagesEditor = function renderLanguagesEditor(languages) {
    const rows = Array.isArray(languages) && languages.length ? languages : [{name: "English", level: "professional"}];
    return rows.map((item, index) => `
      <div class="grid gap-3 rounded-xl border border-slate-200 bg-white px-3 py-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]">
        ${app.reviewInput(`review-language-${index}-name`, item.name || "", "Language")}
        ${app.reviewInput(`review-language-${index}-level`, item.level || "", "Level")}
        <button type="button" class="app-button app-button--sm app-button--danger" onclick="removeReviewLanguage(${index})">Remove</button>
      </div>
    `).join("");
  };

  app.renderReadinessBanner = function renderReadinessBanner(readiness) {
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
      <p class="mt-1">${app.escapeHtml(reason)}${app.escapeHtml(missing)}</p>
    `;
  };

  app.readFromFactSheetSkills = function readFromFactSheetSkills(factSheet) {
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
  };

  app.hydrateReviewDerivedFields = function hydrateReviewDerivedFields() {
    (app.state.review.factSheet?.experience || []).forEach((item, index) => {
      const el = document.getElementById(`experience-${index}-responsibilities_text`);
      if (el) {
        const values = Array.isArray(item.responsibilities) ? item.responsibilities : [];
        el.value = values.join("\n");
      }
    });
    (app.state.review.factSheet?.projects || []).forEach((item, index) => {
      const el = document.getElementById(`projects-${index}-summary`);
      if (el && !el.value.trim() && Array.isArray(item.key_results) && item.key_results.length) {
        el.value = item.key_results.join("\n");
      }
    });
  };

  app.renderProfileReview = function renderProfileReview(factSheet, readiness) {
    app.state.review.factSheet = factSheet;
    app.renderReadinessBanner(readiness);
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
            ${app.reviewInput("review-full-name", person.full_name || "", "Full name")}
          </label>
          <label class="block text-sm">
            <span class="mb-1 block font-medium text-slate-700">Email</span>
            ${app.reviewInput("review-email", contact.email || "", "Email")}
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
        <div id="review-education-list">${app.renderReviewRows("education", factSheet?.education || [], [
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
        <div id="review-experience-list">${app.renderReviewRows("experience", factSheet?.experience || [], [
          {key: "role_title", label: "Role title"},
          {key: "organization", label: "Company / organisation"},
          {key: "start_date", label: "Start date"},
          {key: "end_date", label: "End date"},
          {key: "responsibilities_text", label: "Responsibilities", type: "textarea", rows: 4, full: true, placeholder: "One bullet per line"},
        ], "No experience extracted yet.")}</div>
      </section>

      <section class="rounded-2xl border border-slate-200 bg-white p-4 space-y-3">
        <div class="flex items-center justify-between gap-3">
          <div>
            <p class="text-sm font-semibold text-slate-900">Projects and evidence</p>
            <p class="text-xs text-slate-500">Keep short evidence-backed notes. One result per line.</p>
          </div>
          <button type="button" class="app-button app-button--sm" onclick="addReviewRow('projects')">Add evidence</button>
        </div>
        <div id="review-projects-list">${app.renderReviewRows("projects", factSheet?.projects || [], [
          {key: "name", label: "Title"},
          {key: "link", label: "Link"},
          {key: "summary", label: "Summary and evidence", type: "textarea", rows: 5, full: true},
        ], "No project or evidence items extracted yet.")}</div>
      </section>

      <section class="rounded-2xl border border-slate-200 bg-white p-4 space-y-3">
        <p class="text-sm font-semibold text-slate-900">Skills and languages</p>
        <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,0.9fr)]">
          <div>${app.renderSkillsEditor(app.readFromFactSheetSkills(factSheet))}</div>
          <div class="space-y-3">
            <div class="flex items-center justify-between gap-3">
              <p class="text-sm font-medium text-slate-700">Languages</p>
              <button type="button" class="app-button app-button--sm" onclick="addReviewLanguage()">Add language</button>
            </div>
            <div id="review-languages-list" class="space-y-3">${app.renderLanguagesEditor(factSheet?.languages || [])}</div>
          </div>
        </div>
      </section>
    `;
    app.hydrateReviewDerivedFields();
  };

  app.addReviewRow = function addReviewRow(sectionId) {
    if (!app.state.review.factSheet) {
      return;
    }
    if (!Array.isArray(app.state.review.factSheet[sectionId])) {
      app.state.review.factSheet[sectionId] = [];
    }
    if (sectionId === "education") {
      app.state.review.factSheet[sectionId].push({degree: "", field: "", institution: "", status: ""});
    } else if (sectionId === "experience") {
      app.state.review.factSheet[sectionId].push({role_title: "", organization: "", start_date: "", end_date: "", responsibilities: []});
    } else if (sectionId === "projects") {
      app.state.review.factSheet[sectionId].push({name: "", link: "", summary: ""});
    }
    app.renderProfileReview(app.state.review.factSheet, null);
  };

  app.removeReviewRow = function removeReviewRow(sectionId, index) {
    if (!app.state.review.factSheet || !Array.isArray(app.state.review.factSheet[sectionId])) {
      return;
    }
    app.state.review.factSheet[sectionId].splice(index, 1);
    app.renderProfileReview(app.state.review.factSheet, null);
  };

  app.addReviewLanguage = function addReviewLanguage() {
    if (!app.state.review.factSheet) {
      return;
    }
    if (!Array.isArray(app.state.review.factSheet.languages)) {
      app.state.review.factSheet.languages = [];
    }
    app.state.review.factSheet.languages.push({name: "", level: ""});
    app.renderProfileReview(app.state.review.factSheet, null);
  };

  app.removeReviewLanguage = function removeReviewLanguage(index) {
    if (!app.state.review.factSheet || !Array.isArray(app.state.review.factSheet.languages)) {
      return;
    }
    app.state.review.factSheet.languages.splice(index, 1);
    app.renderProfileReview(app.state.review.factSheet, null);
  };

  app.collectReviewRows = function collectReviewRows(prefix, keys) {
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
  };

  app.loadProfileReview = async function loadProfileReview() {
    if (!app.state.intake.candidateId) {
      return;
    }
    const response = await fetch(`/candidates/${app.state.intake.candidateId}/onboarding-review`);
    if (!response.ok) {
      app.setStatus("Could not load the extracted profile review.", true);
      return;
    }
    const data = await response.json();
    app.state.review.factSheet = data.fact_sheet;
    app.renderProfileReview(data.fact_sheet, data.readiness);
  };

  app.saveProfileReview = async function saveProfileReview() {
    if (!app.state.intake.candidateId || !app.state.review.factSheet) {
      app.setStatus("Run intake before saving the profile review.", true);
      return;
    }
    const experience = app.collectReviewRows("experience", ["role_title", "organization", "start_date", "end_date"]).map((row, index) => ({
      ...row,
      responsibilities: (document.getElementById(`experience-${index}-responsibilities_text`)?.value || "")
        .split("\n")
        .map((item) => item.trim())
        .filter(Boolean),
      tools: [],
      achievements: [],
      evidence_refs: [],
    })).filter((row) => row.role_title || row.organization || row.responsibilities.length);
    const projects = app.collectReviewRows("projects", ["name", "link", "summary"]).map((row) => ({
      ...row,
      tools: [],
    })).filter((row) => row.name || row.summary);
    const education = app.collectReviewRows("education", ["degree", "field", "institution", "status"])
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
      ...app.state.review.factSheet,
      person: {
        ...(app.state.review.factSheet.person || {}),
        full_name: document.getElementById("review-full-name")?.value?.trim() || "",
        contact: {
          ...((app.state.review.factSheet.person || {}).contact || {}),
          email: document.getElementById("review-email")?.value?.trim() || "",
        },
      },
      experience,
      projects,
      education,
      skills: {business_tools: skills},
      languages,
    };

    const response = await fetch(`/candidates/${app.state.intake.candidateId}/fact-sheet-json`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      app.setStatus(await response.text(), true);
      return;
    }
    await app.loadProfileReview();
    await app.hydrateSearchFocus(true);
    app.goToStep(5);
  };

  window.addReviewRow = app.addReviewRow;
  window.removeReviewRow = app.removeReviewRow;
  window.addReviewLanguage = app.addReviewLanguage;
  window.removeReviewLanguage = app.removeReviewLanguage;
  window.saveProfileReview = app.saveProfileReview;
})();
