/*
 * Jobs screen controller.
 *
 * Screen ownership:
 * - discovery polling and progress rendering
 * - manual target intake
 * - queue refresh side effects
 *
 * This file stays intentionally small and imperative because the page still
 * renders server-side. Keep state transitions grouped by concern so the next
 * UI pass can move them into smaller modules without changing behavior.
 */

function parseJobsPageData() {
  const el = document.getElementById("jobs-page-data");
  if (!el || !el.textContent) {
    return {latestDiscoveryTask: null, queueView: {}};
  }
  try {
    return JSON.parse(el.textContent);
  } catch (_error) {
    return {latestDiscoveryTask: null, queueView: {}};
  }
}

const jobsPageData = parseJobsPageData();

function notifyJobsAction(message, type = "info") {
  if (typeof window.showToast === "function") {
    window.showToast(message, type);
  }
}

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
  return (
    task.status === "failed" ||
    stage === "completed" ||
    stage === "completed_zero_results" ||
    stage === "completed_awaiting_enrichment" ||
    stage === "failed"
  );
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
    Number(counts.rejected_by_region || 0) +
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

function injectQueueSkeleton() {
  if (document.getElementById("queue-skeleton")) {
    return;
  }
  const panel = document.getElementById("job-discovery-panel");
  if (!panel) {
    return;
  }
  const skeleton = document.createElement("div");
  skeleton.id = "queue-skeleton";
  skeleton.className = "mt-4 space-y-2";
  skeleton.setAttribute("aria-busy", "true");
  skeleton.setAttribute("aria-label", "Loading job queue…");
  skeleton.innerHTML = Array.from({length: 4}).map(() => `
    <div class="flex items-center gap-3 rounded-xl border border-slate-100 bg-white px-4 py-3">
      <div class="h-4 w-32 rounded bg-slate-100 animate-pulse" aria-hidden="true"></div>
      <div class="h-4 w-48 rounded bg-slate-100 animate-pulse flex-1" aria-hidden="true"></div>
      <div class="h-8 w-8 rounded-full bg-slate-100 animate-pulse" aria-hidden="true"></div>
      <div class="h-4 w-24 rounded bg-slate-100 animate-pulse" aria-hidden="true"></div>
      <div class="flex gap-2">
        <div class="h-6 w-16 rounded bg-slate-100 animate-pulse" aria-hidden="true"></div>
        <div class="h-6 w-16 rounded bg-slate-100 animate-pulse" aria-hidden="true"></div>
      </div>
    </div>
  `).join("");
  panel.insertAdjacentElement("afterend", skeleton);
}

function removeQueueSkeleton() {
  const skeleton = document.getElementById("queue-skeleton");
  if (skeleton) {
    skeleton.remove();
  }
}

function jobDetailElements() {
  return {
    dialog: document.getElementById("job-detail-dialog"),
    title: document.getElementById("job-detail-title"),
    content: document.getElementById("job-detail-content"),
    close: document.getElementById("job-detail-close"),
  };
}

async function openJobDetail(jobId, title) {
  const els = jobDetailElements();
  if (!els.dialog || !els.content) {
    return;
  }
  if (els.title) {
    els.title.textContent = title || "Job description";
  }
  els.content.innerHTML = '<p class="text-sm text-[var(--text-muted)]">Loading job details…</p>';
  if (!els.dialog.open) {
    els.dialog.showModal();
  }
  try {
    const response = await fetch(`/ui/jobs/${encodeURIComponent(jobId)}/detail`, {cache: "no-store"});
    if (!response.ok) {
      throw new Error("Could not load the full job description.");
    }
    els.content.innerHTML = await response.text();
  } catch (error) {
    els.content.innerHTML = `<div class="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">${error.message || "Could not load the full job description."}</div>`;
  }
}

function closeJobDetail() {
  const els = jobDetailElements();
  if (els.dialog?.open) {
    els.dialog.close();
  }
}

function createDiscoveryController() {
  let pollTimer = null;
  let taskId = null;

  function stopPolling() {
    if (pollTimer) {
      window.clearTimeout(pollTimer);
      pollTimer = null;
    }
  }

  function renderTask(task) {
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
      els.progress.classList.toggle("bg-red-600", stage === "failed");
      els.progress.classList.toggle("bg-indigo-600", stage !== "failed");
    }
    if (els.summary) {
      if (discoveryTerminal(task)) {
        els.summary.innerHTML = discoverySummaryRows(task)
          .map((row) => `<div class="rounded-xl border border-slate-100 bg-slate-50 px-3 py-2">${row}</div>`)
          .join("");
      } else {
        els.summary.setAttribute("aria-busy", "true");
        els.summary.setAttribute("aria-label", "Loading discovery summary…");
        els.summary.innerHTML = Array.from({length: 14})
          .map(() => `<div class="h-9 rounded-xl bg-slate-100 animate-pulse" aria-hidden="true"></div>`)
          .join("");
      }
    }
    if (els.refresh) {
      els.refresh.classList.toggle("hidden", !discoveryTerminal(task));
    }
    if (discoveryTerminal(task)) {
      removeQueueSkeleton();
    }
    if (els.button) {
      const busy = !discoveryTerminal(task);
      els.button.disabled = busy;
      els.button.textContent = busy ? "Discovery Running…" : "Discover Jobs";
      els.button.setAttribute("aria-busy", busy ? "true" : "false");
    }
  }

  async function fetchTaskStatus(currentTaskId) {
    const response = await fetch(`/tasks/${encodeURIComponent(currentTaskId)}`, {cache: "no-store"});
    if (!response.ok) {
      throw new Error(`Task lookup failed (${response.status})`);
    }
    return response.json();
  }

  async function pollTask(currentTaskId) {
    taskId = currentTaskId;
    try {
      const task = await fetchTaskStatus(currentTaskId);
      renderTask(task);
      if (discoveryTerminal(task)) {
        stopPolling();
        sessionStorage.setItem("jobs:lastDiscoveryTask", currentTaskId);
        return;
      }
      pollTimer = window.setTimeout(() => pollTask(currentTaskId), 1500);
    } catch (error) {
      stopPolling();
      renderTask({
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

  async function startRun() {
    const discoveryEnabled = jobsPageData.discoveryEnabled !== false;
    const searchFocus = Array.isArray(jobsPageData.searchFocus) ? jobsPageData.searchFocus : [];
    if (!discoveryEnabled) {
      const message = "Job discovery is disabled. Enable JobSpy for explicit searches in Settings before running search.";
      renderTask({
        status: "failed",
        error_message: message,
        result: {
          stage: "failed",
          message,
          counts: {},
        },
      });
      notifyJobsAction(message, "error");
      return;
    }
    if (!searchFocus.length) {
      const message = "Set at least one desired role in Settings before running discovery.";
      renderTask({
        status: "failed",
        error_message: message,
        result: {
          stage: "failed",
          message,
          counts: {},
        },
      });
      notifyJobsAction(message, "error");
      return;
    }
    const els = discoveryElements();
    if (els.button) {
      els.button.disabled = true;
      els.button.textContent = "Starting Discovery…";
    }
    renderTask({
      status: "running",
      result: {
        stage: "pending",
        message: "Submitting a discovery task.",
        counts: {},
      },
    });
    injectQueueSkeleton();
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
      await pollTask(payload.task_id);
    } catch (error) {
      renderTask({
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

  function resumeLatestTask() {
    const latestTask = jobsPageData.latestDiscoveryTask;
    const rememberedTaskId = sessionStorage.getItem("jobs:lastDiscoveryTask");

    if (latestTask) {
      renderTask(latestTask);
      if (!discoveryTerminal(latestTask)) {
        pollTask(latestTask.id);
        return;
      }
    }

    if (
      rememberedTaskId &&
      (!latestTask || latestTask.id !== rememberedTaskId || !discoveryTerminal(latestTask))
    ) {
      pollTask(rememberedTaskId);
    }
  }

  function bind() {
    const els = discoveryElements();
    if (els.button && els.panel) {
      els.button.addEventListener("click", () => {
        stopPolling();
        startRun();
      });
    }
    if (els.refresh) {
      els.refresh.addEventListener("click", () => {
        removeQueueSkeleton();
        window.location.reload();
      });
    }
    if (els.button && els.panel) {
      resumeLatestTask();
    }
  }

  return {
    bind,
    stopPolling,
    get taskId() {
      return taskId;
    },
  };
}

function createManualTargetController() {
  let latestAnalysis = null;

  function elements() {
    return {
      text: document.getElementById("manual-jd-text"),
      url: document.getElementById("manual-jd-url"),
      status: document.getElementById("manual-jd-status"),
      button: document.getElementById("manual-jd-submit"),
      result: document.getElementById("manual-jd-result"),
      title: document.getElementById("manual-jd-title"),
      summary: document.getElementById("manual-jd-summary"),
      score: document.getElementById("manual-jd-score"),
      matched: document.getElementById("manual-jd-matched"),
      gaps: document.getElementById("manual-jd-gaps"),
      continueButton: document.getElementById("manual-jd-continue"),
      addQueueButton: document.getElementById("manual-jd-add-queue"),
      clearButton: document.getElementById("manual-jd-clear"),
    };
  }

  function renderAnalysis(data) {
    const els = elements();
    latestAnalysis = data;
    els.result?.classList.remove("hidden");

    if (els.title) {
      const title = data.job?.title || "Manual target";
      const company = data.job?.company ? ` @ ${data.job.company}` : "";
      els.title.textContent = `${title}${company}`;
    }
    if (els.summary) {
      els.summary.textContent = data.summary || "Manual target analyzed.";
    }
    if (els.score) {
      els.score.textContent = `${data.score ?? 0}/100`;
    }
    if (els.matched) {
      els.matched.innerHTML = "";
      (data.matched || []).slice(0, 6).forEach((item) => {
        const li = document.createElement("li");
        li.textContent = item;
        els.matched.appendChild(li);
      });
      if (!els.matched.children.length) {
        const li = document.createElement("li");
        li.textContent = "No strong aligned evidence detected yet.";
        els.matched.appendChild(li);
      }
    }
    if (els.gaps) {
      els.gaps.innerHTML = "";
      (data.gaps || []).slice(0, 6).forEach((item) => {
        const li = document.createElement("li");
        li.textContent = item;
        els.gaps.appendChild(li);
      });
      if (!els.gaps.children.length) {
        const li = document.createElement("li");
        li.textContent = "No major gap flagged in the first pass.";
        els.gaps.appendChild(li);
      }
    }
  }

  async function analyze() {
    const els = elements();
    const text = els.text?.value?.trim() || "";
    const url = els.url?.value?.trim() || "";
    const status = els.status;
    const button = els.button;

    if (!text && !url) {
      if (status) {
        status.textContent = "Paste a job description or provide a job URL first.";
        status.className = "text-sm text-rose-600";
      }
      return;
    }

    if (button) {
      button.disabled = true;
      button.textContent = "Analyzing…";
    }
    if (status) {
      status.textContent = "Scoring this target without adding it to the queue…";
      status.className = "text-sm text-slate-500";
    }

    try {
      const response = await fetch("/ui/jobs/manual-target/analyze", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({text, url}),
      });
      let data = null;
      const contentType = response.headers.get("content-type") || "";
      if (contentType.includes("application/json")) {
        data = await response.json();
      } else {
        const rawText = await response.text();
        data = {detail: rawText || "Could not analyze this job description."};
      }
      if (!response.ok) {
        throw new Error(data.detail || "Could not analyze this job description.");
      }
      renderAnalysis(data);
      if (status) {
        status.textContent = "Score ready. Continue to the CV workflow or add this target to the queue manually.";
        status.className = "text-sm text-emerald-700";
      }
    } catch (error) {
      if (status) {
        status.textContent = error.message || "Could not analyze this target.";
        status.className = "text-sm text-rose-600";
      }
    } finally {
      if (button) {
        button.disabled = false;
        button.textContent = "Analyze Job Description";
      }
    }
  }

  function continueToCvWorkflow() {
    if (!latestAnalysis) {
      return;
    }
    sessionStorage.setItem("jobAgent:manualAnalysis", JSON.stringify(latestAnalysis));
    window.location.href = "/ui/apply";
  }

  async function addToQueue() {
    const els = elements();
    if (!latestAnalysis) {
      return;
    }
    const button = els.addQueueButton;
    const status = els.status;
    const text = els.text?.value?.trim() || "";
    const url = els.url?.value?.trim() || "";

    try {
      if (button) {
        button.disabled = true;
        button.textContent = "Adding…";
      }
      const endpoint = text ? "/jobs/from-text" : "/jobs/add";
      const payload = text ? {text: latestAnalysis.raw_text || text} : {url};
      const response = await fetch(endpoint, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Could not add this job to the queue.");
      }
      if (status) {
        status.textContent = `${data.title || "Manual target"} was added to the Jobs queue.`;
        status.className = "text-sm text-emerald-700";
      }
      window.setTimeout(() => window.location.reload(), 500);
    } catch (error) {
      if (status) {
        status.textContent = error.message || "Could not add this target to the queue.";
        status.className = "text-sm text-rose-600";
      }
      if (button) {
        button.disabled = false;
        button.textContent = "Add to Jobs Queue";
      }
    }
  }

  function clear() {
    latestAnalysis = null;
    const els = elements();
    if (els.text) els.text.value = "";
    if (els.url) els.url.value = "";
    if (els.status) {
      els.status.textContent = "";
      els.status.className = "text-sm text-slate-500";
    }
    els.result?.classList.add("hidden");
    sessionStorage.removeItem("jobAgent:manualAnalysis");
  }

  function bind() {
    document.getElementById("manual-jd-submit")?.addEventListener("click", analyze);
    document.getElementById("manual-jd-continue")?.addEventListener("click", continueToCvWorkflow);
    document.getElementById("manual-jd-add-queue")?.addEventListener("click", addToQueue);
    document.getElementById("manual-jd-clear")?.addEventListener("click", clear);
  }

  return {bind};
}

function initJobsUi() {
  const discovery = createDiscoveryController();
  const manualTarget = createManualTargetController();
  discovery.bind();
  manualTarget.bind();

  const detailEls = jobDetailElements();
  if (detailEls.close) {
    detailEls.close.addEventListener("click", closeJobDetail);
  }
  if (detailEls.dialog) {
    detailEls.dialog.addEventListener("click", (event) => {
      if (event.target === detailEls.dialog) {
        closeJobDetail();
      }
    });
  }
  document.body.addEventListener("click", (event) => {
    const trigger = event.target.closest("[data-job-detail-open]");
    if (!trigger) {
      return;
    }
    event.preventDefault();
    openJobDetail(trigger.dataset.jobDetailOpen, trigger.dataset.jobDetailTitle || "Job description");
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initJobsUi, {once: true});
} else {
  initJobsUi();
}
