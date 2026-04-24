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

function syncRangeLabel(inputId, labelId) {
  const input = document.getElementById(inputId);
  const label = document.getElementById(labelId);
  if (input && label) {
    label.textContent = input.value;
  }
}

function providerFlags(form) {
  const selected = form.querySelector('input[name="provider_mode"]:checked');
  const mode = selected ? selected.value : "local";
  return {
    llm_provider_mode: mode,
    use_openai_review: mode === "openai" || mode === "mixed",
    use_claude_final_review: mode === "anthropic" || mode === "mixed",
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
  row.className = "grid gap-3 rounded-xl border border-slate-200 bg-white px-3 py-3 md:grid-cols-[minmax(0,1fr)_12rem_auto]";

  const nameSelect = settingsSelect(
    settingsLanguageOptions,
    value.name || "English",
    "settings-job-language-name rounded-xl border border-slate-300 px-3 py-2 text-sm"
  );
  const levelSelect = settingsSelect(
    settingsLanguageLevelOptions,
    value.level || "professional",
    "settings-job-language-level rounded-xl border border-slate-300 px-3 py-2 text-sm"
  );

  const removeButton = document.createElement("button");
  removeButton.type = "button";
  removeButton.className = "rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-500 hover:bg-slate-50";
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
    const level = row.querySelector(".settings-job-language-level")?.value?.trim();
    if (!name || rows.some((item) => item.name === name)) {
      return;
    }
    rows.push({name, level: level || "professional"});
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

    if (field === "jobspy_discover_queries" || field === "job_search_countries") {
      data[field] = value.split("\n").map((item) => item.trim()).filter(Boolean);
    } else if (["match_min_score", "cv_pass_score", "cv_revise_score", "bullet_clarify_word_limit"].includes(field)) {
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
  }

  const status = document.getElementById(formId.replace("-form", "-status")) || document.getElementById("system-status");
  const response = await fetch("/settings/save", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(data),
  });

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
    status.textContent = "✗ Save failed";
  }
}

async function testLmStudio() {
  const input = document.querySelector('#provider-form [name="lm_studio_base_url"]');
  const url = input ? input.value.trim() : "";
  const response = await fetch(`/lm-studio/models?base_url=${encodeURIComponent(url)}`);
  const data = await response.json();
  const status = document.getElementById("provider-status");
  if (!status) {
    return;
  }
  status.textContent = data.online ? `✓ Online — ${data.models.length} models` : "✗ LM Studio not reachable";
}

async function testGmail() {
  const form = document.getElementById("gmail-form");
  const email = form.elements.gmail_email.value.trim();
  const password = form.elements.gmail_app_password.value.trim();
  const status = document.getElementById("gmail-status");

  if (!email || !password) {
    status.textContent = "Enter email and app password first.";
    return;
  }

  status.textContent = "Testing…";
  const params = new URLSearchParams({email, app_password: password});
  const response = await fetch("/gmail/test-connection?" + params.toString(), {method: "POST"});
  const data = await response.json();
  status.textContent = data.ok ? "✓ Connection successful" : "✗ " + (data.error || "Failed");
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
  queriesInput.style.borderColor = count > 5 ? "rgb(239,68,68)" : "";
}

document.addEventListener("DOMContentLoaded", () => {
  const queriesInput = document.querySelector('[name="jobspy_discover_queries"]');
  if (queriesInput) {
    queriesInput.addEventListener("input", syncRoleCount);
    syncRoleCount();
  }

  ensureSettingsLanguageRows();
  syncRangeLabel("match_min_score", "match-score-value");
  syncRangeLabel("cv_pass_score", "cv-pass-value");
  syncRangeLabel("cv_revise_score", "cv-revise-value");
});
