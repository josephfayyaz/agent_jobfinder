<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import AppPageHeader from "../components/AppPageHeader.vue";
import { vueApiFetch } from "../api/client";

const loading = ref(true);
const error = ref("");
const payload = ref(null);

onMounted(async () => {
  try {
    payload.value = await vueApiFetch("/analytics/summary");
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

// Analytics has a different shape — detect real data by checking for funnel key
const hasRealData = computed(() => responseData.value.funnel !== undefined);
const funnel = computed(() => responseData.value.funnel ?? {});
const scoreAnalysis = computed(() => responseData.value.score_analysis ?? {});
const skillGaps = computed(() =>
  Array.isArray(responseData.value.skill_gaps) ? responseData.value.skill_gaps : []
);
const weeklyActivity = computed(() =>
  Array.isArray(responseData.value.weekly_activity) ? responseData.value.weekly_activity : []
);
</script>

<template>
  <AppPageHeader
    title="Analytics"
    description="A read-only view of application pipeline analytics, score analysis, and skill gaps."
  />

  <section class="grid gap-6 lg:grid-cols-3">
    <div class="space-y-6 lg:col-span-2">

      <!-- Main analytics card -->
      <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Pipeline analytics</p>
        <h2 class="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
          Application funnel
        </h2>

        <div v-if="loading" class="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
          Loading analytics...
        </div>

        <div v-else-if="error" class="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          {{ error }}
        </div>

        <div v-else-if="!hasRealData" class="mt-4 space-y-4">
          <div class="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
            Not enough data yet — analytics require at least 5 applications with non-pending status.
            <span v-if="responseMessage" class="mt-1 block opacity-75">{{ responseMessage }}</span>
          </div>
          <p class="text-sm leading-6 text-slate-600">
            Use the apply flow to submit applications. Once you have 5 or more tracked applications, the full analytics dashboard will appear here.
          </p>
        </div>

        <div v-else class="mt-4 space-y-4">
          <!-- Funnel counts -->
          <dl class="grid gap-4 text-sm md:grid-cols-3">
            <div v-if="funnel.total !== undefined" class="rounded-xl border border-slate-200 bg-slate-50 p-3">
              <dt class="text-slate-500">Total</dt>
              <dd class="mt-1 text-xl font-bold text-slate-950">{{ funnel.total }}</dd>
            </div>
            <div v-if="funnel.responded !== undefined" class="rounded-xl border border-slate-200 bg-slate-50 p-3">
              <dt class="text-slate-500">Responded</dt>
              <dd class="mt-1 text-xl font-bold text-slate-950">{{ funnel.responded }}</dd>
            </div>
            <div v-if="funnel.interview !== undefined" class="rounded-xl border border-slate-200 bg-slate-50 p-3">
              <dt class="text-slate-500">Interview</dt>
              <dd class="mt-1 text-xl font-bold text-slate-950">{{ funnel.interview }}</dd>
            </div>
            <div v-if="funnel.offer !== undefined" class="rounded-xl border border-slate-200 bg-slate-50 p-3">
              <dt class="text-slate-500">Offer</dt>
              <dd class="mt-1 text-xl font-bold text-slate-950">{{ funnel.offer }}</dd>
            </div>
            <div v-if="funnel.rejected !== undefined" class="rounded-xl border border-slate-200 bg-slate-50 p-3">
              <dt class="text-slate-500">Rejected</dt>
              <dd class="mt-1 text-xl font-bold text-slate-950">{{ funnel.rejected }}</dd>
            </div>
            <div v-if="funnel.discarded !== undefined" class="rounded-xl border border-slate-200 bg-slate-50 p-3">
              <dt class="text-slate-500">Discarded</dt>
              <dd class="mt-1 text-xl font-bold text-slate-950">{{ funnel.discarded }}</dd>
            </div>
          </dl>

          <!-- Rate metrics -->
          <dl class="grid gap-4 text-sm md:grid-cols-3">
            <div v-if="funnel.response_rate_pct !== undefined">
              <dt class="text-slate-500">Response rate</dt>
              <dd class="mt-1 font-semibold text-slate-950">{{ funnel.response_rate_pct }}%</dd>
            </div>
            <div v-if="funnel.interview_rate_pct !== undefined">
              <dt class="text-slate-500">Interview rate</dt>
              <dd class="mt-1 font-semibold text-slate-950">{{ funnel.interview_rate_pct }}%</dd>
            </div>
            <div v-if="funnel.offer_rate_pct !== undefined">
              <dt class="text-slate-500">Offer rate</dt>
              <dd class="mt-1 font-semibold text-slate-950">{{ funnel.offer_rate_pct }}%</dd>
            </div>
          </dl>
        </div>
      </article>

      <!-- Score analysis card -->
      <article v-if="hasRealData" class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Score analysis</p>
        <h2 class="mt-2 text-xl font-semibold tracking-tight text-slate-950">CV score thresholds</h2>

        <dl class="mt-4 grid gap-4 text-sm md:grid-cols-2">
          <div v-if="scoreAnalysis.current_threshold !== undefined">
            <dt class="text-slate-500">Current threshold</dt>
            <dd class="mt-1 font-semibold text-slate-950">{{ scoreAnalysis.current_threshold }}</dd>
          </div>
          <div v-if="scoreAnalysis.recommended_threshold !== undefined">
            <dt class="text-slate-500">Recommended threshold</dt>
            <dd class="mt-1 font-semibold text-slate-950">{{ scoreAnalysis.recommended_threshold }}</dd>
          </div>
          <div v-if="scoreAnalysis.threshold_note" class="md:col-span-2">
            <dt class="text-slate-500">Note</dt>
            <dd class="mt-1 leading-6 text-slate-950">{{ scoreAnalysis.threshold_note }}</dd>
          </div>
        </dl>
      </article>

      <!-- Skill gaps card -->
      <article v-if="hasRealData" class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Skill gaps</p>
        <h2 class="mt-2 text-xl font-semibold tracking-tight text-slate-950">Missing ATS keywords</h2>

        <div class="mt-4">
          <div v-if="skillGaps.length" class="space-y-2">
            <div
              v-for="gap in skillGaps"
              :key="gap.gap"
              class="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm"
            >
              <span class="font-medium text-slate-950">{{ gap.gap }}</span>
              <span class="text-slate-500">{{ gap.occurrences }} {{ gap.occurrences === 1 ? "occurrence" : "occurrences" }}</span>
            </div>
          </div>
          <p v-else class="text-sm text-slate-600">No skill gap data available.</p>
        </div>
      </article>

      <!-- Weekly activity card -->
      <article v-if="hasRealData" class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Weekly activity</p>
        <h2 class="mt-2 text-xl font-semibold tracking-tight text-slate-950">Applications over time</h2>

        <div class="mt-4">
          <div v-if="weeklyActivity.length" class="space-y-2">
            <div
              v-for="week in weeklyActivity"
              :key="week.week"
              class="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm"
            >
              <span class="font-mono text-slate-700">{{ week.week }}</span>
              <span class="font-semibold text-slate-950">{{ week.applied }} applied</span>
            </div>
          </div>
          <p v-else class="text-sm text-slate-600">No weekly activity data available.</p>
        </div>
      </article>

    </div>

    <aside class="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div>
        <p class="text-sm font-medium text-slate-500">Next actions</p>
        <p class="mt-2 text-sm leading-6 text-slate-600">
          Analytics are computed from your tracked applications. Add more applications via the apply flow to see richer insights.
        </p>
      </div>

      <dl class="space-y-3 text-sm">
        <div class="flex items-start justify-between gap-4">
          <dt class="text-slate-500">Loading</dt>
          <dd class="font-medium text-slate-950">{{ loading ? "Yes" : "No" }}</dd>
        </div>
        <div class="flex items-start justify-between gap-4">
          <dt class="text-slate-500">Error</dt>
          <dd class="font-medium text-slate-950">{{ error ? "Present" : "None" }}</dd>
        </div>
        <div class="flex items-start justify-between gap-4">
          <dt class="text-slate-500">Has real data</dt>
          <dd class="font-medium text-slate-950">{{ hasRealData ? "Yes" : "No" }}</dd>
        </div>
        <div class="flex items-start justify-between gap-4">
          <dt class="text-slate-500">Placeholder status</dt>
          <dd class="font-medium text-slate-950">{{ isPlaceholder ? "Yes" : "No" }}</dd>
        </div>
      </dl>

      <div class="space-y-3">
        <RouterLink
          to="/applications"
          class="block rounded-xl bg-slate-950 px-4 py-2 text-center text-sm font-medium text-white hover:bg-slate-800"
        >
          Go to Applications
        </RouterLink>
        <RouterLink
          to="/drafts"
          class="block rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-center text-sm font-medium text-slate-900 hover:bg-slate-100"
        >
          Go to Drafts
        </RouterLink>
        <RouterLink
          to="/jobs"
          class="block rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2 text-center text-sm font-medium text-emerald-900 hover:bg-emerald-100"
        >
          Go to Jobs
        </RouterLink>
      </div>
    </aside>
  </section>
</template>
