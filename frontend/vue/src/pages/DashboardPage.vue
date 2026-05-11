<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import AppPageHeader from "../components/AppPageHeader.vue";
import { vueApiFetch } from "../api/client";

const pageDescription = "Review system readiness, priority jobs, workflow blockers, and the next best action for your local job-search workspace.";

const loading = ref(true);
const error = ref("");
const payload = ref(null);

const ROUTES = Object.freeze({
  applications: "/applications",
  companies: "/companies",
  drafts: "/drafts",
  jobs: "/jobs",
  onboarding: "/onboarding",
  settings: "/settings"
});

const fallbackMetrics = [
  { key: "jobs_tracked", label: "Jobs tracked", value: 0, description: "No jobs are being shown yet." },
  { key: "companies_tracked", label: "Companies tracked", value: 0, description: "No companies are being shown yet." },
  { key: "applications_tracked", label: "Applications tracked", value: 0, description: "No applications are being shown yet." },
  { key: "drafts_pending", label: "Drafts pending", value: 0, description: "No draft activity is being shown yet." }
];

const metricRouteByKey = Object.freeze({
  active_applications: ROUTES.applications,
  applications_tracked: ROUTES.applications,
  companies_tracked: ROUTES.companies,
  drafts_pending: ROUTES.drafts,
  high_match_jobs: ROUTES.jobs,
  jobs_tracked: ROUTES.jobs,
  new_jobs_24h: ROUTES.jobs,
  pending_approvals: ROUTES.drafts
});

async function loadDashboardSummary() {
  loading.value = true;
  error.value = "";
  try {
    payload.value = await vueApiFetch("/dashboard/summary");
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Request failed";
  } finally {
    loading.value = false;
  }
}

onMounted(loadDashboardSummary);

function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function objectValue(value) {
  return isPlainObject(value) ? value : {};
}

function hasOwn(value, key) {
  return Object.prototype.hasOwnProperty.call(value, key);
}

function normalizeKey(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

function numberOrNull(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function numberOrZero(value) {
  return numberOrNull(value) ?? 0;
}

function displayValue(value) {
  if (value === null || value === undefined || value === "") {
    return "Not set";
  }
  return value;
}

function formatDateTime(value) {
  if (!value) {
    return "Not available";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short"
  });
}

function pluralize(count, singular, plural = `${singular}s`) {
  return `${count} ${count === 1 ? singular : plural}`;
}

function defaultMetricDescription(key) {
  const descriptions = {
    active_applications: "Application records currently tracked.",
    applications_tracked: "Application records currently tracked.",
    companies_tracked: "Companies available from the current dashboard summary.",
    drafts_pending: "Drafts waiting for review or follow-up.",
    high_match_jobs: "Jobs above the current match threshold.",
    jobs_tracked: "Saved jobs available in the local workspace.",
    new_jobs_24h: "Roles discovered in the last 24 hours.",
    pending_approvals: "Drafts waiting for approval."
  };
  return descriptions[key] || "Signal reported by the dashboard summary.";
}

function statusBadgeClass(tone) {
  const classes = {
    amber: "border-amber-200 bg-amber-50 text-amber-800",
    green: "border-green-200 bg-green-50 text-green-700",
    indigo: "border-indigo-200 bg-indigo-50 text-indigo-700",
    rose: "border-rose-200 bg-rose-50 text-rose-700",
    slate: "border-slate-200 bg-slate-50 text-slate-600"
  };
  return classes[tone] || classes.slate;
}

function panelToneClass(tone) {
  const classes = {
    amber: "border-amber-200 bg-amber-50",
    green: "border-green-200 bg-green-50",
    indigo: "border-indigo-200 bg-indigo-50",
    rose: "border-rose-200 bg-rose-50",
    slate: "border-slate-200 bg-white"
  };
  return classes[tone] || classes.slate;
}

function actionClass(variant) {
  if (variant === "primary") {
    return "rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2";
  }
  return "rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2";
}

function metricCardClass(card) {
  const base = "rounded-2xl border bg-white p-5 shadow-sm";
  if (!card.to) {
    return `${base} border-slate-200`;
  }
  return `${base} border-slate-200 transition hover:border-indigo-300 hover:bg-indigo-50/50 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2`;
}

function metricCardAttrs(card) {
  if (!card.to) {
    return {};
  }
  return {
    to: card.to,
    "aria-label": `Open ${card.label}`
  };
}

function firstBoolean(values) {
  const found = values.find((value) => typeof value === "boolean");
  return typeof found === "boolean" ? found : null;
}

function checklistState(value) {
  if (value === true) {
    return { statusLabel: "Ready", tone: "green" };
  }
  if (value === false) {
    return { statusLabel: "Needs attention", tone: "amber" };
  }
  return { statusLabel: "Unknown", tone: "slate" };
}

const responseData = computed(() => objectValue(payload.value?.data));
const responseStatus = computed(() => payload.value?.status ?? "");
const responseMessage = computed(() => payload.value?.message ?? "");
const isPlaceholder = computed(() => responseStatus.value === "placeholder");
const cards = computed(() => (Array.isArray(responseData.value.cards) ? responseData.value.cards.filter(Boolean) : []));
const sections = computed(() => objectValue(responseData.value.sections));
const jobsSection = computed(() => objectValue(sections.value.jobs));
const cvSection = computed(() => objectValue(sections.value.cv));
const systemSection = computed(() => objectValue(sections.value.system));
const configSection = computed(() => objectValue(sections.value.config));
const setupSection = computed(() => objectValue(responseData.value.setup || sections.value.setup));

const metricCards = computed(() => {
  const sourceCards = cards.value.length ? cards.value : fallbackMetrics;

  return sourceCards.map((card, index) => {
    const key = normalizeKey(card.key || card.label || `metric_${index}`);
    const label = card.label || "Metric";
    const route = metricRouteByKey[key] || "";
    return {
      key,
      label,
      value: card.value ?? 0,
      rawValue: card.value,
      description: card.description || defaultMetricDescription(key),
      to: route
    };
  });
});

const jobsTrackedFromCards = computed(() => {
  const card = metricCards.value.find((item) => item.key === "jobs_tracked");
  if (!card) {
    return null;
  }
  return numberOrNull(card.rawValue) ?? 0;
});

const jobsSummary = computed(() => ({
  new24h: numberOrZero(jobsSection.value.new_24h),
  highMatch: numberOrZero(jobsSection.value.high_match),
  needsEnrichment: numberOrZero(jobsSection.value.needs_enrichment)
}));

const cvSummary = computed(() => ({
  pendingApprovals: numberOrZero(cvSection.value.pending_approvals),
  pendingEnhancementApprovals: numberOrZero(cvSection.value.pending_enhancement_approvals),
  approvedWithoutCoverLetter: numberOrZero(cvSection.value.approved_without_cover_letter)
}));

const systemSummary = computed(() => ({
  pdflatexAvailable: typeof systemSection.value.pdflatex_available === "boolean" ? systemSection.value.pdflatex_available : null,
  lmStudioOnline: typeof systemSection.value.lm_studio_online === "boolean" ? systemSection.value.lm_studio_online : null,
  lastJobIngested: systemSection.value.last_job_ingested ?? ""
}));

const configSummary = computed(() => ({
  targetSeniority: configSection.value.target_seniority ?? "",
  matchMinScore: hasOwn(configSection.value, "match_min_score") ? configSection.value.match_min_score : "",
  cvPassScore: hasOwn(configSection.value, "cv_pass_score") ? configSection.value.cv_pass_score : ""
}));

const hasLastJobIngestedField = computed(() => hasOwn(systemSection.value, "last_job_ingested"));
const approvalBlockers = computed(() => cvSummary.value.pendingApprovals + cvSummary.value.pendingEnhancementApprovals);
const targetSeniorityMissing = computed(() => !String(configSummary.value.targetSeniority || "").trim());
const noKnownJobActivity = computed(() => {
  if (jobsTrackedFromCards.value !== null) {
    return jobsTrackedFromCards.value === 0;
  }
  if (!hasLastJobIngestedField.value) {
    return false;
  }
  return !String(systemSummary.value.lastJobIngested || "").trim()
    && jobsSummary.value.new24h === 0
    && jobsSummary.value.highMatch === 0
    && jobsSummary.value.needsEnrichment === 0;
});

const dataSourceStatus = computed(() => responseStatus.value || "No status provided");
const dataSourceMessage = computed(() => responseMessage.value || "No endpoint message provided.");

const lmStudioHealth = computed(() => {
  if (systemSummary.value.lmStudioOnline === true) {
    return {
      badge: "Ready",
      detail: "LM Studio reports online.",
      tone: "green",
      value: "Online"
    };
  }
  if (systemSummary.value.lmStudioOnline === false) {
    return {
      badge: "Blocking",
      detail: "Fix or select workflow AI before generating drafts.",
      tone: "rose",
      value: "Offline"
    };
  }
  return {
    badge: "Unknown",
    detail: "No workflow AI status was reported.",
    tone: "slate",
    value: "Unknown"
  };
});

const pdflatexHealth = computed(() => {
  if (systemSummary.value.pdflatexAvailable === true) {
    return {
      badge: "Ready",
      detail: "PDF generation dependency is available.",
      tone: "green",
      value: "Ready"
    };
  }
  if (systemSummary.value.pdflatexAvailable === false) {
    return {
      badge: "Limited",
      detail: "pdflatex is missing; PDF generation may be limited.",
      tone: "amber",
      value: "Missing"
    };
  }
  return {
    badge: "Unknown",
    detail: "No pdflatex status was reported.",
    tone: "slate",
    value: "Unknown"
  };
});

const lastJobHealth = computed(() => {
  if (!hasLastJobIngestedField.value) {
    return {
      badge: "Unknown",
      detail: "No intake timestamp was reported.",
      tone: "slate",
      value: "Unknown"
    };
  }
  if (systemSummary.value.lastJobIngested) {
    return {
      badge: "Recorded",
      detail: "Latest intake timestamp from the summary endpoint.",
      tone: "green",
      value: formatDateTime(systemSummary.value.lastJobIngested)
    };
  }
  return {
    badge: "No intake",
    detail: "No ingested jobs are visible yet.",
    tone: "amber",
    value: "Never"
  };
});

const jobDiscoveryRecommendation = computed(() => {
  if (jobsSummary.value.highMatch > 0) {
    return `${pluralize(jobsSummary.value.highMatch, "high-match job")} ready for review. Start with the strongest fit.`;
  }
  if (jobsSummary.value.needsEnrichment > 0) {
    return `${pluralize(jobsSummary.value.needsEnrichment, "job")} ${jobsSummary.value.needsEnrichment === 1 ? "needs" : "need"} enrichment before scoring or drafting.`;
  }
  if (jobsSummary.value.new24h > 0) {
    return "New intake exists, but no high-match jobs are surfaced yet. Review source quality and thresholds.";
  }
  if (noKnownJobActivity.value) {
    return "No recent job activity is visible. Check search focus, Gmail sync, or source scans.";
  }
  return "Discovery looks quiet. Keep reviewing saved jobs and source coverage.";
});

const jobDiscoveryRows = computed(() => [
  {
    label: "New jobs in 24h",
    value: jobsSummary.value.new24h,
    badge: jobsSummary.value.new24h > 0 ? "Active" : "Quiet",
    tone: jobsSummary.value.new24h > 0 ? "green" : "slate"
  },
  {
    label: "High match jobs",
    value: jobsSummary.value.highMatch,
    badge: jobsSummary.value.highMatch > 0 ? "Review" : "None",
    tone: jobsSummary.value.highMatch > 0 ? "green" : "slate"
  },
  {
    label: "Needs enrichment",
    value: jobsSummary.value.needsEnrichment,
    badge: jobsSummary.value.needsEnrichment > 0 ? "Needs work" : "Clear",
    tone: jobsSummary.value.needsEnrichment > 0 ? "amber" : "green"
  }
]);

const workflowRows = computed(() => [
  {
    label: "Pending approvals",
    value: cvSummary.value.pendingApprovals,
    badge: cvSummary.value.pendingApprovals > 0 ? "Review" : "Healthy",
    tone: cvSummary.value.pendingApprovals > 0 ? "amber" : "green"
  },
  {
    label: "Pending enhancements",
    value: cvSummary.value.pendingEnhancementApprovals,
    badge: cvSummary.value.pendingEnhancementApprovals > 0 ? "Review" : "Healthy",
    tone: cvSummary.value.pendingEnhancementApprovals > 0 ? "amber" : "green"
  },
  {
    label: "Approved without cover letter",
    value: cvSummary.value.approvedWithoutCoverLetter,
    badge: cvSummary.value.approvedWithoutCoverLetter > 0 ? "Follow up" : "Healthy",
    tone: cvSummary.value.approvedWithoutCoverLetter > 0 ? "amber" : "green"
  }
]);

const systemHealthRows = computed(() => [
  {
    label: "LM Studio",
    ...lmStudioHealth.value
  },
  {
    label: "pdflatex",
    ...pdflatexHealth.value
  },
  {
    label: "Last job ingested",
    ...lastJobHealth.value
  }
]);

const searchConfigRows = computed(() => [
  {
    label: "Target seniority",
    value: displayValue(configSummary.value.targetSeniority),
    badge: targetSeniorityMissing.value ? "Setup needed" : "Set",
    tone: targetSeniorityMissing.value ? "amber" : "green"
  },
  {
    label: "Match minimum score",
    value: displayValue(configSummary.value.matchMinScore),
    badge: displayValue(configSummary.value.matchMinScore) === "Not set" ? "Not set" : "Set",
    tone: displayValue(configSummary.value.matchMinScore) === "Not set" ? "slate" : "green"
  },
  {
    label: "CV pass score",
    value: displayValue(configSummary.value.cvPassScore),
    badge: displayValue(configSummary.value.cvPassScore) === "Not set" ? "Not set" : "Set",
    tone: displayValue(configSummary.value.cvPassScore) === "Not set" ? "slate" : "green"
  }
]);

const onboardingReady = computed(() => firstBoolean([
  responseData.value.onboarding_complete,
  responseData.value.setup_complete,
  setupSection.value.onboarding_complete,
  setupSection.value.setup_complete,
  setupSection.value.candidate_profile_ready,
  setupSection.value.profile_ready
]));

const searchFocusReady = computed(() => {
  if (!hasOwn(configSection.value, "target_seniority")) {
    return null;
  }
  return !targetSeniorityMissing.value;
});

const intakeReady = computed(() => {
  if (!hasLastJobIngestedField.value) {
    return null;
  }
  return Boolean(systemSummary.value.lastJobIngested);
});

const checklistItems = computed(() => {
  const onboarding = checklistState(onboardingReady.value);
  const workflowAi = checklistState(systemSummary.value.lmStudioOnline);
  const searchFocus = checklistState(searchFocusReady.value);
  const jobIntake = checklistState(intakeReady.value);
  const pdf = checklistState(systemSummary.value.pdflatexAvailable);

  return [
    {
      label: "Candidate profile / onboarding configured",
      detail: onboardingReady.value === null ? "Dashboard summary does not report onboarding readiness." : "Profile readiness signal is available.",
      ...onboarding
    },
    {
      label: "Workflow AI provider ready",
      detail: systemSummary.value.lmStudioOnline === null ? "No workflow AI status was reported." : lmStudioHealth.value.detail,
      ...workflowAi
    },
    {
      label: "Search focus configured",
      detail: searchFocusReady.value === null ? "Target seniority was not reported." : (searchFocusReady.value ? "Target seniority is set." : "Target seniority is not set."),
      ...searchFocus
    },
    {
      label: "Job intake has recent activity",
      detail: intakeReady.value === null ? "No intake timestamp was reported." : (intakeReady.value ? "At least one intake timestamp is recorded." : "No job intake timestamp is visible."),
      ...jobIntake
    },
    {
      label: "PDF generation ready",
      detail: systemSummary.value.pdflatexAvailable === null ? "No PDF dependency status was reported." : pdflatexHealth.value.detail,
      ...pdf
    }
  ];
});

const nextAction = computed(() => {
  if (loading.value) {
    return {
      badge: "Checking",
      explanation: "Reading the local dashboard summary before recommending the next move.",
      title: "Checking workspace readiness",
      tone: "indigo",
      actions: []
    };
  }

  if (error.value) {
    return {
      badge: "Recovery",
      explanation: "The summary request failed. Check the local API service or provider settings, then refresh the dashboard.",
      title: "Dashboard summary could not load",
      tone: "rose",
      actions: [
        { label: "Open settings", to: ROUTES.settings, variant: "primary" }
      ]
    };
  }

  if (isPlaceholder.value) {
    return {
      badge: "Data setup",
      explanation: "The dashboard is showing scaffolded backend data. Use the structure for orientation, but finish setup before trusting the counts.",
      title: "Connect dashboard data before acting on counts",
      tone: "amber",
      actions: [
        { label: "Open onboarding", to: ROUTES.onboarding, variant: "primary" },
        { label: "Review settings", to: ROUTES.settings, variant: "secondary" },
        { label: "Open jobs", to: ROUTES.jobs, variant: "secondary" }
      ]
    };
  }

  if (systemSummary.value.lmStudioOnline === false) {
    return {
      badge: "Blocking",
      explanation: "LM Studio is offline, so draft and review workflows may not have a ready local AI provider.",
      title: "Fix or select workflow AI",
      tone: "rose",
      actions: [
        { label: "Open settings", to: ROUTES.settings, variant: "primary" },
        { label: "Open onboarding", to: ROUTES.onboarding, variant: "secondary" },
        { label: "Review jobs", to: ROUTES.jobs, variant: "secondary" }
      ]
    };
  }

  if (approvalBlockers.value > 0) {
    return {
      badge: "Workflow",
      explanation: `${pluralize(approvalBlockers.value, "approval")} waiting across drafts and enhancements.`,
      title: "Review pending CV approvals",
      tone: "amber",
      actions: [
        { label: "Open drafts", to: ROUTES.drafts, variant: "primary" },
        { label: "Open applications", to: ROUTES.applications, variant: "secondary" },
        { label: "Open jobs", to: ROUTES.jobs, variant: "secondary" }
      ]
    };
  }

  if (jobsSummary.value.highMatch > 0) {
    return {
      badge: "Opportunity",
      explanation: `${pluralize(jobsSummary.value.highMatch, "job")} ${jobsSummary.value.highMatch === 1 ? "clears" : "already clear"} the current match threshold.`,
      title: "Review high-match jobs",
      tone: "green",
      actions: [
        { label: "Open jobs", to: ROUTES.jobs, variant: "primary" },
        { label: "Open drafts", to: ROUTES.drafts, variant: "secondary" },
        { label: "Open applications", to: ROUTES.applications, variant: "secondary" }
      ]
    };
  }

  if (jobsSummary.value.needsEnrichment > 0) {
    return {
      badge: "Data quality",
      explanation: `${pluralize(jobsSummary.value.needsEnrichment, "job")} ${jobsSummary.value.needsEnrichment === 1 ? "needs" : "need"} richer descriptions before scoring or drafting will be reliable.`,
      title: "Enrich jobs before drafting",
      tone: "amber",
      actions: [
        { label: "Open jobs", to: ROUTES.jobs, variant: "primary" },
        { label: "Review settings", to: ROUTES.settings, variant: "secondary" }
      ]
    };
  }

  if (noKnownJobActivity.value) {
    return {
      badge: "Intake",
      explanation: "No saved job activity is visible yet. Set the search focus, sync Gmail, or scan sources to start the pipeline.",
      title: "Start job intake",
      tone: "indigo",
      actions: [
        { label: "Set search focus", to: ROUTES.settings, variant: "primary" },
        { label: "Open onboarding", to: ROUTES.onboarding, variant: "secondary" },
        { label: "Open jobs", to: ROUTES.jobs, variant: "secondary" }
      ]
    };
  }

  return {
    badge: "Stable",
    explanation: "No blocking workflow signals are visible. Keep the search loop moving by reviewing recent jobs and applications.",
    title: "Workspace looks stable",
    tone: "green",
    actions: [
      { label: "Review jobs", to: ROUTES.jobs, variant: "primary" },
      { label: "Open applications", to: ROUTES.applications, variant: "secondary" },
      { label: "Review settings", to: ROUTES.settings, variant: "secondary" }
    ]
  };
});

const skeletonCards = computed(() => Array.from({ length: 4 }, (_, index) => index));
const skeletonPanels = computed(() => Array.from({ length: 4 }, (_, index) => index));
</script>

<template>
  <AppPageHeader
    title="Dashboard"
    :description="pageDescription"
  />
  <p class="-mt-4 mb-6 max-w-3xl text-sm leading-6 text-slate-600">
    {{ pageDescription }}
  </p>

  <section class="space-y-6">
    <article
      :class="[
        'rounded-2xl border p-6 shadow-sm',
        panelToneClass(nextAction.tone)
      ]"
    >
      <div class="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div class="max-w-3xl">
          <span
            :class="[
              'inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold',
              statusBadgeClass(nextAction.tone)
            ]"
          >
            Next Best Action · {{ nextAction.badge }}
          </span>
          <h2 class="mt-4 text-2xl font-semibold tracking-tight text-slate-950">
            {{ nextAction.title }}
          </h2>
          <p class="mt-2 text-sm leading-6 text-slate-700">
            {{ nextAction.explanation }}
          </p>
        </div>

        <div v-if="nextAction.actions.length" class="flex flex-wrap gap-3 lg:justify-end">
          <RouterLink
            v-for="action in nextAction.actions"
            :key="action.label"
            :to="action.to"
            :class="actionClass(action.variant)"
          >
            {{ action.label }}
          </RouterLink>
        </div>
      </div>
    </article>

    <div v-if="loading" class="space-y-6">
      <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <article
          v-for="item in skeletonCards"
          :key="item"
          class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
        >
          <div class="h-3 w-24 rounded-full bg-slate-200"></div>
          <div class="mt-4 h-8 w-16 rounded-lg bg-slate-200"></div>
          <div class="mt-4 h-3 w-full rounded-full bg-slate-100"></div>
          <div class="mt-2 h-3 w-2/3 rounded-full bg-slate-100"></div>
        </article>
      </div>

      <div class="grid gap-4 xl:grid-cols-2">
        <article
          v-for="item in skeletonPanels"
          :key="item"
          class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
        >
          <div class="h-4 w-40 rounded-full bg-slate-200"></div>
          <div class="mt-5 space-y-3">
            <div class="h-10 rounded-xl bg-slate-100"></div>
            <div class="h-10 rounded-xl bg-slate-100"></div>
            <div class="h-10 rounded-xl bg-slate-100"></div>
          </div>
        </article>
      </div>
    </div>

    <article
      v-else-if="error"
      class="rounded-2xl border border-rose-200 bg-white p-6 shadow-sm"
    >
      <div class="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <h2 class="text-lg font-semibold text-slate-950">Dashboard data unavailable</h2>
          <p class="mt-2 text-sm leading-6 text-rose-700">
            {{ error }}
          </p>
          <p class="mt-2 text-sm leading-6 text-slate-600">
            The dashboard stayed mounted, but the cockpit cannot calculate reliable operational status until the summary endpoint responds.
          </p>
        </div>
        <RouterLink
          :to="ROUTES.settings"
          :class="actionClass('secondary')"
        >
          Open settings
        </RouterLink>
      </div>
    </article>

    <div v-else class="space-y-6">
      <div
        :class="[
          'flex flex-col gap-2 rounded-2xl border bg-white p-4 text-sm shadow-sm sm:flex-row sm:items-center sm:justify-between',
          isPlaceholder ? 'border-amber-200' : 'border-slate-200'
        ]"
      >
        <div class="flex flex-wrap items-center gap-2">
          <span class="font-semibold text-slate-950">Data source status</span>
          <span
            :class="[
              'rounded-full border px-2.5 py-1 text-xs font-semibold',
              statusBadgeClass(isPlaceholder ? 'amber' : 'slate')
            ]"
          >
            {{ dataSourceStatus }}
          </span>
        </div>
        <p class="text-slate-600">{{ dataSourceMessage }}</p>
      </div>

      <div
        v-if="isPlaceholder"
        class="rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm leading-6 text-amber-900 shadow-sm"
      >
        Dashboard is currently showing scaffolded backend data. Treat counts as structural placeholders until the summary endpoint is connected to real records.
      </div>

      <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <component
          :is="card.to ? RouterLink : 'article'"
          v-for="card in metricCards"
          :key="card.key"
          v-bind="metricCardAttrs(card)"
          :class="metricCardClass(card)"
        >
          <div class="flex items-start justify-between gap-3">
            <p class="text-sm font-medium text-slate-500">{{ card.label }}</p>
            <span
              v-if="card.to"
              class="rounded-full bg-indigo-50 px-2 py-1 text-xs font-semibold text-indigo-700"
            >
              Open
            </span>
          </div>
          <p class="mt-3 text-3xl font-semibold tracking-tight text-slate-950">{{ card.value }}</p>
          <p class="mt-2 text-sm leading-6 text-slate-600">
            {{ card.description }}
          </p>
        </component>
      </div>

      <div class="grid gap-4 xl:grid-cols-2">
        <article class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div class="flex items-start justify-between gap-4">
            <div>
              <h2 class="text-base font-semibold text-slate-950">Job Discovery</h2>
              <p class="mt-1 text-sm leading-6 text-slate-600">Intake quality and match signals for the active search loop.</p>
            </div>
            <RouterLink
              :to="ROUTES.jobs"
              class="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
            >
              Open jobs
            </RouterLink>
          </div>

          <dl class="mt-5 space-y-3">
            <div
              v-for="row in jobDiscoveryRows"
              :key="row.label"
              class="flex items-center justify-between gap-4 rounded-xl border border-slate-100 bg-slate-50 px-4 py-3"
            >
              <dt class="text-sm font-medium text-slate-600">{{ row.label }}</dt>
              <dd class="flex items-center gap-3">
                <span class="text-lg font-semibold text-slate-950">{{ row.value }}</span>
                <span
                  :class="[
                    'rounded-full border px-2.5 py-1 text-xs font-semibold',
                    statusBadgeClass(row.tone)
                  ]"
                >
                  {{ row.badge }}
                </span>
              </dd>
            </div>
          </dl>

          <p class="mt-4 rounded-xl border border-indigo-100 bg-indigo-50 px-4 py-3 text-sm leading-6 text-indigo-900">
            {{ jobDiscoveryRecommendation }}
          </p>
        </article>

        <article class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div class="flex items-start justify-between gap-4">
            <div>
              <h2 class="text-base font-semibold text-slate-950">Draft &amp; Application Workflow</h2>
              <p class="mt-1 text-sm leading-6 text-slate-600">Review gates that can slow submissions or follow-up work.</p>
            </div>
            <RouterLink
              :to="ROUTES.drafts"
              class="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
            >
              Open drafts
            </RouterLink>
          </div>

          <dl class="mt-5 space-y-3">
            <div
              v-for="row in workflowRows"
              :key="row.label"
              class="flex items-center justify-between gap-4 rounded-xl border border-slate-100 bg-slate-50 px-4 py-3"
            >
              <dt class="text-sm font-medium text-slate-600">{{ row.label }}</dt>
              <dd class="flex items-center gap-3">
                <span class="text-lg font-semibold text-slate-950">{{ row.value }}</span>
                <span
                  :class="[
                    'rounded-full border px-2.5 py-1 text-xs font-semibold',
                    statusBadgeClass(row.tone)
                  ]"
                >
                  {{ row.badge }}
                </span>
              </dd>
            </div>
          </dl>
        </article>

        <article class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div>
            <h2 class="text-base font-semibold text-slate-950">System Health</h2>
            <p class="mt-1 text-sm leading-6 text-slate-600">Runtime checks that affect local drafting, exports, and intake confidence.</p>
          </div>

          <dl class="mt-5 space-y-3">
            <div
              v-for="row in systemHealthRows"
              :key="row.label"
              class="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3"
            >
              <div class="flex items-center justify-between gap-4">
                <dt class="text-sm font-medium text-slate-600">{{ row.label }}</dt>
                <dd class="flex items-center gap-3">
                  <span class="text-sm font-semibold text-slate-950">{{ row.value }}</span>
                  <span
                    :class="[
                      'rounded-full border px-2.5 py-1 text-xs font-semibold',
                      statusBadgeClass(row.tone)
                    ]"
                  >
                    {{ row.badge }}
                  </span>
                </dd>
              </div>
              <p class="mt-2 text-xs leading-5 text-slate-500">{{ row.detail }}</p>
            </div>
          </dl>
        </article>

        <article class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div class="flex items-start justify-between gap-4">
            <div>
              <h2 class="text-base font-semibold text-slate-950">Search Configuration</h2>
              <p class="mt-1 text-sm leading-6 text-slate-600">Thresholds and targeting signals currently visible to the dashboard.</p>
            </div>
            <RouterLink
              :to="ROUTES.settings"
              class="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
            >
              Open settings
            </RouterLink>
          </div>

          <dl class="mt-5 space-y-3">
            <div
              v-for="row in searchConfigRows"
              :key="row.label"
              class="flex items-center justify-between gap-4 rounded-xl border border-slate-100 bg-slate-50 px-4 py-3"
            >
              <dt class="text-sm font-medium text-slate-600">{{ row.label }}</dt>
              <dd class="flex items-center gap-3 text-right">
                <span class="text-sm font-semibold text-slate-950">{{ row.value }}</span>
                <span
                  :class="[
                    'rounded-full border px-2.5 py-1 text-xs font-semibold',
                    statusBadgeClass(row.tone)
                  ]"
                >
                  {{ row.badge }}
                </span>
              </dd>
            </div>
          </dl>

          <p
            v-if="targetSeniorityMissing"
            class="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-900"
          >
            Target seniority is not set. Configure search focus before scaling discovery.
          </p>
        </article>
      </div>

      <article class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div class="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 class="text-base font-semibold text-slate-950">Setup / Reliability Checklist</h2>
            <p class="mt-1 text-sm leading-6 text-slate-600">Compact readiness checks based only on fields visible in the dashboard summary.</p>
          </div>
          <RouterLink
            :to="ROUTES.onboarding"
            class="self-start rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 sm:self-auto"
          >
            Open onboarding
          </RouterLink>
        </div>

        <div class="mt-5 grid gap-3 lg:grid-cols-2">
          <div
            v-for="item in checklistItems"
            :key="item.label"
            class="rounded-xl border border-slate-100 bg-slate-50 p-4"
          >
            <div class="flex items-start justify-between gap-3">
              <h3 class="text-sm font-semibold text-slate-950">{{ item.label }}</h3>
              <span
                :class="[
                  'shrink-0 rounded-full border px-2.5 py-1 text-xs font-semibold',
                  statusBadgeClass(item.tone)
                ]"
              >
                {{ item.statusLabel }}
              </span>
            </div>
            <p class="mt-2 text-xs leading-5 text-slate-500">{{ item.detail }}</p>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>
