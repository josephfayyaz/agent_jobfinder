<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";

import { vueApiFetch } from "../api/client";

const router = useRouter();

const loading = ref(true);
const startPending = ref(false);
const error = ref("");
const payload = ref(null);

function firstBoolean(values) {
  const match = values.find((value) => typeof value === "boolean");
  return match ?? false;
}

function setupCompleteFromData(data) {
  return firstBoolean([
    data?.setup_complete,
    data?.complete,
    data?.onboarding_complete,
  ]);
}

async function loadSetupState() {
  const response = await vueApiFetch("/setup/state");
  payload.value = response;
  return response?.data ?? {};
}

onMounted(async () => {
  try {
    await loadSetupState();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Unable to load setup state.";
  } finally {
    loading.value = false;
  }
});

const setupData = computed(() => payload.value?.data ?? {});
const setupComplete = computed(() => setupCompleteFromData(setupData.value));
const missingSteps = computed(() =>
  Array.isArray(setupData.value.missing_steps) ? setupData.value.missing_steps.filter(Boolean) : []
);
const readinessItems = computed(() => [
  {
    label: "AI provider",
    ready: Boolean(setupData.value.provider_configured),
  },
  {
    label: "Fact sheet",
    ready: Boolean(setupData.value.fact_sheet_ready),
  },
  {
    label: "Search focus",
    ready: Boolean(setupData.value.search_focus_ready),
  },
]);
const startLabel = computed(() => (setupComplete.value ? "Open dashboard" : "Start setup"));
const setupStateLabel = computed(() => {
  if (loading.value) return "Checking setup";
  if (setupComplete.value) return "Ready";
  if (error.value) return "Setup state unavailable";
  return "Setup needed";
});

async function handleStart() {
  startPending.value = true;
  error.value = "";

  try {
    const data = await loadSetupState();
    if (setupCompleteFromData(data)) {
      await router.push("/dashboard");
      return;
    }
    await router.push("/onboarding");
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Unable to load setup state.";
  } finally {
    startPending.value = false;
  }
}
</script>

<template>
  <section data-testid="welcome-page" class="space-y-8 pb-10 pt-2">
    <header class="flex items-center justify-between gap-4">
      <div class="flex items-center gap-3">
        <span class="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-950 text-sm font-semibold text-white">
          AJ
        </span>
        <div>
          <p class="text-sm font-semibold text-slate-950">Agent Jobfinder</p>
          <p class="text-xs text-slate-500">Local-first career workspace</p>
        </div>
      </div>
      <RouterLink
        to="/dashboard"
        class="hidden rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-800 shadow-sm transition hover:border-slate-400 hover:bg-slate-50 sm:inline-flex"
      >
        Dashboard
      </RouterLink>
    </header>

    <div class="grid min-h-[560px] items-center gap-8 lg:grid-cols-[minmax(0,1.15fr)_minmax(360px,0.85fr)]">
      <section class="mx-auto max-w-4xl text-center lg:mx-0 lg:text-left">
        <p class="text-sm font-semibold uppercase tracking-wide text-sky-700">
          Search, draft, review, and track from one private workspace
        </p>
        <h1 class="mt-5 text-5xl font-semibold tracking-tight text-slate-950 sm:text-6xl lg:text-7xl">
          Build better applications from facts you can trust.
        </h1>
        <p class="mx-auto mt-6 max-w-2xl text-base leading-7 text-slate-600 sm:text-lg lg:mx-0">
          Agent Jobfinder turns your real experience into targeted job applications, grounded CV
          drafts, fit analysis, compliance material, and thesis or traineeship outreach while
          keeping local workflows first-class.
        </p>

        <div class="mt-8 flex flex-col justify-center gap-3 sm:flex-row lg:justify-start">
          <button
            type="button"
            data-testid="welcome-start-button"
            class="inline-flex items-center justify-center rounded-md bg-slate-950 px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
            :disabled="startPending"
            @click="handleStart"
          >
            {{ startPending ? "Checking..." : startLabel }}
          </button>
          <RouterLink
            to="/dashboard"
            class="inline-flex items-center justify-center rounded-md border border-slate-300 bg-white px-6 py-3 text-sm font-semibold text-slate-800 shadow-sm transition hover:border-slate-400 hover:bg-slate-50"
          >
            View dashboard
          </RouterLink>
        </div>

        <p class="mt-5 text-sm leading-6 text-slate-500">
          Connect your profile, define search focus, generate tracks, then manage jobs, drafts, and
          applications from the main workspace.
        </p>

        <p v-if="error" class="mx-auto mt-4 max-w-2xl rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800 lg:mx-0">
          {{ error }}
        </p>
      </section>

      <aside class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="text-sm font-medium text-slate-500">Setup status</p>
            <p class="mt-1 text-3xl font-semibold text-slate-950">{{ setupStateLabel }}</p>
          </div>
          <span
            :class="[
              'rounded-md border px-2 py-1 text-xs font-semibold',
              setupComplete
                ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
                : 'border-amber-200 bg-amber-50 text-amber-900'
            ]"
          >
            {{ setupComplete ? "Complete" : "Review" }}
          </span>
        </div>

        <div class="mt-6 space-y-3">
          <div
            v-for="item in readinessItems"
            :key="item.label"
            class="flex items-center justify-between gap-4 rounded-md border border-slate-200 bg-slate-50 px-3 py-2"
          >
            <span class="text-sm font-medium text-slate-700">{{ item.label }}</span>
            <span
              :class="[
                'rounded border px-1.5 py-0.5 text-xs font-semibold',
                item.ready
                  ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
                  : 'border-slate-200 bg-white text-slate-500'
              ]"
            >
              {{ item.ready ? "Ready" : "Pending" }}
            </span>
          </div>
        </div>

        <div v-if="missingSteps.length" class="mt-6 rounded-md border border-amber-200 bg-amber-50 p-4">
          <p class="text-sm font-semibold text-amber-950">Next setup steps</p>
          <ul class="mt-3 space-y-2 text-sm leading-6 text-amber-950">
            <li v-for="step in missingSteps" :key="step">{{ step }}</li>
          </ul>
        </div>

        <div class="mt-6 rounded-md border border-slate-200 bg-slate-50 p-4">
          <p class="text-sm font-semibold text-slate-950">Local-first by design</p>
          <p class="mt-2 text-sm leading-6 text-slate-600">
            Run with LM Studio or Ollama for local inference, or bring your own cloud key when that
            fits the work.
          </p>
        </div>
      </aside>
    </div>

    <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <article class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <p class="text-sm font-semibold text-slate-950">Grounded profile</p>
        <p class="mt-2 text-sm leading-6 text-slate-600">
          Build a reviewed fact sheet from CVs, notes, and profile material before drafting.
        </p>
      </article>
      <article class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <p class="text-sm font-semibold text-slate-950">Search focus</p>
        <p class="mt-2 text-sm leading-6 text-slate-600">
          Define target roles, locations, languages, and constraints for Italy, EU, or abroad.
        </p>
      </article>
      <article class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <p class="text-sm font-semibold text-slate-950">CV and track generation</p>
        <p class="mt-2 text-sm leading-6 text-slate-600">
          Generate role tracks, score job descriptions, and review every CV draft before use.
        </p>
      </article>
      <article class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <p class="text-sm font-semibold text-slate-950">Application control</p>
        <p class="mt-2 text-sm leading-6 text-slate-600">
          Manage jobs, companies, drafts, applications, and outreach from a single local workspace.
        </p>
      </article>
    </div>
  </section>
</template>
