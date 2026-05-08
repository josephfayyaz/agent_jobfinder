<script setup>
import { computed, onMounted, ref } from "vue";
import AppPageHeader from "../components/AppPageHeader.vue";
import { vueApiFetch } from "../api/client";

const loading = ref(true);
const error = ref("");
const payload = ref(null);

onMounted(async () => {
  try {
    payload.value = await vueApiFetch("/dashboard/summary");
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Request failed";
  } finally {
    loading.value = false;
  }
});

const responseData = computed(() => payload.value?.data ?? {});
const responseStatus = computed(() => payload.value?.status ?? "");
const responseMessage = computed(() => payload.value?.message ?? "");
const isPlaceholder = computed(() => responseStatus.value === "placeholder");
const cards = computed(() => (Array.isArray(responseData.value.cards) ? responseData.value.cards.filter(Boolean) : []));
const sections = computed(() => responseData.value.sections ?? {});

const fallbackMetrics = [
  { key: "jobs_tracked", label: "Jobs tracked", value: 0, description: "No jobs are being shown yet." },
  { key: "companies_tracked", label: "Companies tracked", value: 0, description: "No companies are being shown yet." },
  { key: "applications_tracked", label: "Applications tracked", value: 0, description: "No applications are being shown yet." },
  { key: "drafts_pending", label: "Drafts pending", value: 0, description: "No draft activity is being shown yet." }
];

const metricCards = computed(() => {
  if (!cards.value.length) {
    return fallbackMetrics;
  }

  return cards.value.map((card) => ({
    key: card.key || card.label || "metric",
    label: card.label || "Metric",
    value: card.value ?? 0,
    description: card.description || ""
  }));
});

const jobsSummary = computed(() => ({
  new24h: sections.value?.jobs?.new_24h ?? 0,
  highMatch: sections.value?.jobs?.high_match ?? 0,
  needsEnrichment: sections.value?.jobs?.needs_enrichment ?? 0
}));

const cvSummary = computed(() => ({
  pendingApprovals: sections.value?.cv?.pending_approvals ?? 0,
  pendingEnhancementApprovals: sections.value?.cv?.pending_enhancement_approvals ?? 0,
  approvedWithoutCoverLetter: sections.value?.cv?.approved_without_cover_letter ?? 0
}));

const systemSummary = computed(() => ({
  pdflatexAvailable: sections.value?.system?.pdflatex_available ?? false,
  lmStudioOnline: sections.value?.system?.lm_studio_online ?? false,
  lastJobIngested: sections.value?.system?.last_job_ingested ?? ""
}));

const configSummary = computed(() => ({
  targetSeniority: sections.value?.config?.target_seniority ?? "",
  matchMinScore: sections.value?.config?.match_min_score ?? 0,
  cvPassScore: sections.value?.config?.cv_pass_score ?? 0
}));
</script>

<template>
  <AppPageHeader
    title="Dashboard"
    description="A read-only overview of the current local job search workspace."
  />

  <section class="grid gap-12 lg:grid-cols-12">
    <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm lg:col-span-full">
      <h2 class="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
        Dashboard overview
      </h2>

      <div v-if="loading" class="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
        Loading dashboard summary...
      </div>

      <div v-else-if="error" class="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
        {{ error }}
      </div>

      <div v-else class="mt-4 space-y-4">
        <p class="text-sm leading-6 text-slate-600">
          {{ responseMessage || "" }}
        </p>

        <div
          v-if="isPlaceholder"
          class="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"
        >
          The backend is still returning placeholder dashboard data, so the page is using safe fallback values where needed.
        </div>

        <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <article
            v-for="card in metricCards"
            :key="card.key"
            class="rounded-xl border border-slate-200 bg-slate-50 p-4"
          >
            <p class="text-sm font-medium text-slate-500">{{ card.label }}</p>
            <p class="mt-2 text-3xl font-semibold tracking-tight text-slate-950">{{ card.value }}</p>
            <p v-if="card.description" class="mt-2 text-sm leading-6 text-slate-600">
              {{ card.description }}
            </p>
          </article>
        </div>

        <div class="grid gap-4 md:grid-cols-2">
          <article class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <h3 class="text-sm font-semibold text-slate-950">Job discovery status</h3>
            <dl class="mt-3 space-y-2 text-sm text-slate-600">
              <div class="flex items-center justify-between gap-4">
                <dt>New jobs in 24h</dt>
                <dd class="font-medium text-slate-950">{{ jobsSummary.new24h }}</dd>
              </div>
              <div class="flex items-center justify-between gap-4">
                <dt>High match jobs</dt>
                <dd class="font-medium text-slate-950">{{ jobsSummary.highMatch }}</dd>
              </div>
              <div class="flex items-center justify-between gap-4">
                <dt>Needs enrichment</dt>
                <dd class="font-medium text-slate-950">{{ jobsSummary.needsEnrichment }}</dd>
              </div>
            </dl>
          </article>

          <article class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <h3 class="text-sm font-semibold text-slate-950">Workflow status</h3>
            <dl class="mt-3 space-y-2 text-sm text-slate-600">
              <div class="flex items-center justify-between gap-4">
                <dt>Pending approvals</dt>
                <dd class="font-medium text-slate-950">{{ cvSummary.pendingApprovals }}</dd>
              </div>
              <div class="flex items-center justify-between gap-4">
                <dt>Pending enhancements</dt>
                <dd class="font-medium text-slate-950">{{ cvSummary.pendingEnhancementApprovals }}</dd>
              </div>
              <div class="flex items-center justify-between gap-4">
                <dt>Approved without cover letter</dt>
                <dd class="font-medium text-slate-950">{{ cvSummary.approvedWithoutCoverLetter }}</dd>
              </div>
            </dl>
          </article>

          <article class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <h3 class="text-sm font-semibold text-slate-950">System status</h3>
            <dl class="mt-3 space-y-2 text-sm text-slate-600">
              <div class="flex items-center justify-between gap-4">
                <dt>pdflatex available</dt>
                <dd class="font-medium text-slate-950">{{ systemSummary.pdflatexAvailable ? "Yes" : "No" }}</dd>
              </div>
              <div class="flex items-center justify-between gap-4">
                <dt>LM Studio online</dt>
                <dd class="font-medium text-slate-950">{{ systemSummary.lmStudioOnline ? "Yes" : "No" }}</dd>
              </div>
              <div class="flex items-center justify-between gap-4">
                <dt>Last job ingested</dt>
                <dd class="font-medium text-slate-950">
                  {{ systemSummary.lastJobIngested || "Not available" }}
                </dd>
              </div>
            </dl>
          </article>

          <article class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <h3 class="text-sm font-semibold text-slate-950">Configuration</h3>
            <dl class="mt-3 space-y-2 text-sm text-slate-600">
              <div class="flex items-center justify-between gap-4">
                <dt>Target seniority</dt>
                <dd class="font-medium text-slate-950">{{ configSummary.targetSeniority || "Not set" }}</dd>
              </div>
              <div class="flex items-center justify-between gap-4">
                <dt>Match minimum score</dt>
                <dd class="font-medium text-slate-950">{{ configSummary.matchMinScore }}</dd>
              </div>
              <div class="flex items-center justify-between gap-4">
                <dt>CV pass score</dt>
                <dd class="font-medium text-slate-950">{{ configSummary.cvPassScore }}</dd>
              </div>
            </dl>
          </article>
        </div>
      </div>
    </article>
  </section>
</template>
