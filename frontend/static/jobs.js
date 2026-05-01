const jobsPageData = (() => {
  const el = document.getElementById("jobs-page-data");
  if (!el || !el.textContent) {
    return {latestDiscoveryTask: null, queueView: {}};
  }
  try {
    return JSON.parse(el.textContent);
  } catch (_error) {
    return {latestDiscoveryTask: null, queueView: {}};
  }
})();

const discoveryStageLabels = {
  pending: "Preparing search",
  running: "Preparing search",
  querying: "Querying JobSpy",
  querying_ats: "Querying ATS feeds",
  fetching: "Querying JobSpy",
  fetching_descriptions: "Fetching descriptions",
  deduplicating: "Deduplicating",
  filtering: "Applying basic filters",
  scoring: "Scoring jobs",
  saving: "Saving results",
  completed_awaiting_enrichment: "Completed with jobs awaiting enrichment",
  completed: "Completed",
  completed_zero_results: "Completed with zero visible jobs",
  failed: "Failed",
};

const discoveryStageProgress = {
  pending: 6,
  running: 10,
  querying: 24,
  querying_ats: 34,
  fetching: 24,
  fetching_descriptions: 68,
  deduplicating: 42,
  filtering: 56,
  scoring: 78,
  saving: 92,
  completed_awaiting_enrichment: 100,
  completed: 100,
  completed_zero_results: 100,
  failed: 100,
};

let discoveryPollTimer = null;
let discoveryTaskId = null;

function discoveryElements() {
  return {
    button: document.getElementById("discover-jobspy-button"),
    panel: document.getElementById("job-discovery-panel"),
    stage: document.getElementById("job-discovery-stage-label"),
    message: document.getElementById("job-discovery-message"),
    progress: document.getElementById("job-discovery-progress-bar"),
    summary: document.getElementById("job-discovery-summary"),
    refresh: document.getElementById("job-discovery-refresh"),
  };
}

function discoveryTerminal(task) {
  if (!task) {
    return false;
  }
  const stage = String(task.result?.stage || task.status || "pending");
  return task.status === "failed" || stage === "completed" || stage === "completed_zero_results" || stage === "completed_awaiting_enrichment" || stage === "failed";
}

function discoveryStage(task) {
  if (!task) {
    return "pending";
  }
  return String(task.result?.stage || task.status || "pending");
}

function discoverySummaryRows(task) {
  const counts = task?.result?.counts || {};
  const filteredOut =
    Number(counts.duplicates || 0) +
    Number(counts.rejected_by_country || 0) +
    Number(counts.rejected_by_role || 0) +
    Number(counts.rejected_by_seniority || 0);
  return [
    `Roles queried: ${counts.roles_queried || 0}`,
    `Raw hits: ${counts.raw_hits || 0}`,
    `ATS sources scanned: ${counts.ats_sources_scanned || 0}`,
    `ATS hits: ${counts.ats_raw_hits || 0}`,
    `Duplicates: ${counts.duplicates || 0}`,
    `Filtered out: ${filteredOut}`,
    `Scored: ${counts.scored_jobs || 0}`,
    `Awaiting enrichment: ${counts.awaiting_enrichment_count || 0}`,
    `Provider scored: ${counts.provider_scored_count || 0}`,
    `Fallback scored: ${counts.fallback_scored_count || 0}`,
    `Ready for threshold: ${counts.ready_for_threshold_count || 0}`,
    `Saved: ${counts.saved_jobs || 0}`,
    `Visible after threshold: ${counts.visible_after_threshold || 0}`,
    `Visible in default view: ${counts.visible_in_default_view || 0}`,
  ];
}

function renderDiscoveryTask(task) {
  const els = discoveryElements();
  if (!els.panel) {
    return;
  }
  els.panel.classList.remove("hidden");
  const stage = discoveryStage(task);
  const label = discoveryStageLabels[stage] || "Preparing search";
  const message =
    task?.result?.message ||
    task?.error_message ||
    (task?.status === "failed" ? "Discovery failed." : "Discovery is in progress.");
  const progress = discoveryStageProgress[stage] || 6;

  if (els.stage) {
    els.stage.textContent = label;
  }
  if (els.message) {
    els.message.textContent = message;
  }
  if (els.progress) {
    els.progress.style.width = `${progress}%`;
    els.progress.classList.toggle("bg-rose-500", stage === "failed");
    els.progress.classList.toggle("bg-indigo-500", stage !== "failed");
  }
  if (els.summary) {
    els.summary.innerHTML = discoverySummaryRows(task)
      .map((row) => `<div class="rounded-xl border border-slate-100 bg-slate-50 px-3 py-2">${row}</div>`)
      .join("");
  }
  if (els.refresh) {
    els.refresh.classList.toggle("hidden", !discoveryTerminal(task));
  }
  if (els.button) {
    const busy = !discoveryTerminal(task);
    els.button.disabled = busy;
    els.button.textContent = busy ? "Discovery Running…" : "Discover Jobs";
  }
}

function stopDiscoveryPolling() {
  if (discoveryPollTimer) {
    window.clearTimeout(discoveryPollTimer);
    discoveryPollTimer = null;
  }
}

async function fetchDiscoveryTask(taskId) {
  const response = await fetch(`/tasks/${encodeURIComponent(taskId)}`, {cache: "no-store"});
  if (!response.ok) {
    throw new Error(`Task lookup failed (${response.status})`);
  }
  return response.json();
}

async function pollDiscoveryTask(taskId) {
  discoveryTaskId = taskId;
  try {
    const task = await fetchDiscoveryTask(taskId);
    renderDiscoveryTask(task);
    if (discoveryTerminal(task)) {
      stopDiscoveryPolling();
      sessionStorage.setItem("jobs:lastDiscoveryTask", taskId);
      return;
    }
    discoveryPollTimer = window.setTimeout(() => pollDiscoveryTask(taskId), 1500);
  } catch (error) {
    stopDiscoveryPolling();
    renderDiscoveryTask({
      status: "failed",
      error_message: error.message || "Discovery polling failed.",
      result: {
        stage: "failed",
        message: error.message || "Discovery polling failed.",
        counts: {},
      },
    });
  }
}

async function startDiscoveryRun() {
  const els = discoveryElements();
  if (els.button) {
    els.button.disabled = true;
    els.button.textContent = "Starting Discovery…";
  }
  renderDiscoveryTask({
    status: "running",
    result: {
      stage: "pending",
      message: "Submitting a discovery task.",
      counts: {},
    },
  });
  try {
    const response = await fetch("/ui/jobs/discover", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Could not start discovery.");
    }
    if (!payload.task_id) {
      throw new Error("Discovery response did not include a task id.");
    }
    sessionStorage.setItem("jobs:lastDiscoveryTask", payload.task_id);
    await pollDiscoveryTask(payload.task_id);
  } catch (error) {
    renderDiscoveryTask({
      status: "failed",
      error_message: error.message || "Could not start discovery.",
      result: {
        stage: "failed",
        message: error.message || "Could not start discovery.",
        counts: {},
      },
    });
  }
}

function initDiscoveryUi() {
  const els = discoveryElements();
  if (!els.button || !els.panel) {
    return;
  }
  els.button.addEventListener("click", () => {
    stopDiscoveryPolling();
    startDiscoveryRun();
  });
  if (els.refresh) {
    els.refresh.addEventListener("click", () => window.location.reload());
  }

  const latestTask = jobsPageData.latestDiscoveryTask;
  const rememberedTaskId = sessionStorage.getItem("jobs:lastDiscoveryTask");

  if (latestTask) {
    renderDiscoveryTask(latestTask);
    if (!discoveryTerminal(latestTask)) {
      pollDiscoveryTask(latestTask.id);
      return;
    }
  }

  if (rememberedTaskId && (!latestTask || latestTask.id !== rememberedTaskId || !discoveryTerminal(latestTask))) {
    pollDiscoveryTask(rememberedTaskId);
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initDiscoveryUi, { once: true });
} else {
  initDiscoveryUi();
}
