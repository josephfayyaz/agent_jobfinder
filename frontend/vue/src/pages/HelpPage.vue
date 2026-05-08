<script setup>
import { computed, onMounted, ref } from "vue";
import AppPageHeader from "../components/AppPageHeader.vue";
import { vueApiFetch } from "../api/client";

const loading = ref(true);
const error = ref("");
const payload = ref(null);

onMounted(async () => {
  try {
    payload.value = await vueApiFetch("/help");
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Request failed";
  } finally {
    loading.value = false;
  }
});

const responseData = computed(() => payload.value?.data ?? {});
const responseStatus = computed(() => payload.value?.status ?? "");
const responseMessage = computed(() => payload.value?.message ?? "");
const apiSections = computed(() =>
  Array.isArray(responseData.value.sections) ? responseData.value.sections.filter(Boolean) : []
);
const title = computed(() => responseData.value.title || "Help");
const placeholderNotice = computed(() =>
  responseStatus.value === "placeholder"
    ? "The backend is still returning placeholder guidance for this contract."
    : "The backend is returning live help content."
);

const helpSections = [
  {
    title: "Getting started",
    body:
      "Start from the dashboard, then move into jobs, apply, and drafts once the data you need is visible."
  },
  {
    title: "Job discovery",
    body:
      "Use the jobs and companies areas to review saved postings and company sources before you spend time on a role."
  },
  {
    title: "CV drafts",
    body:
      "Drafts are the review workspace for CV generation, revision, and approval. This page does not trigger any generation action."
  },
  {
    title: "Verified facts",
    body:
      "Verified facts keep the candidate profile grounded in approved source material and should stay editable only through the intended onboarding flow."
  },
  {
    title: "Troubleshooting",
    body:
      "If a page looks empty, confirm the backend is running and check whether the contract layer returned placeholder data or a network error."
  }
];
</script>

<template>
  <AppPageHeader
    title="Help"
    description="Practical guidance for using the local-first Vue shell without changing the legacy workflow or calling generation endpoints."
  />

  <section class="grid gap-6 lg:grid-cols-3">
    <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm lg:col-span-2">
      <p class="text-sm font-medium text-slate-500">Help</p>
      <h2 class="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
        {{ title }}
      </h2>

      <div v-if="loading" class="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
        Loading help content...
      </div>

      <div v-else-if="error" class="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
        {{ error }}
      </div>

      <div v-else class="mt-4 space-y-4">
        <p class="text-sm leading-6 text-slate-600">
          {{ responseMessage || placeholderNotice }}
        </p>

        <div v-if="apiSections.length" class="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <p class="text-sm font-medium text-slate-500">API-provided guidance</p>
          <ul class="mt-3 space-y-2 text-sm leading-6 text-slate-600">
            <li v-for="item in apiSections" :key="item" class="rounded-lg border border-slate-200 bg-white px-3 py-2">
              {{ item }}
            </li>
          </ul>
        </div>

        <div class="grid gap-4 md:grid-cols-2">
          <article
            v-for="section in helpSections"
            :key="section.title"
            class="rounded-xl border border-slate-200 bg-slate-50 p-4"
          >
            <h3 class="text-sm font-semibold text-slate-950">{{ section.title }}</h3>
            <p class="mt-2 text-sm leading-6 text-slate-600">{{ section.body }}</p>
          </article>
        </div>
      </div>
    </article>

    <aside class="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div>
        <p class="text-sm font-medium text-slate-500">Troubleshooting</p>
        <p class="mt-2 text-sm leading-6 text-slate-600">
          This page is read-only. It only fetches the help contract and never calls LLMs or write endpoints.
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
          <dt class="text-slate-500">Placeholder content</dt>
          <dd class="font-medium text-slate-950">{{ responseStatus === "placeholder" ? "Yes" : "No" }}</dd>
        </div>
      </dl>

      <div class="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
        If the backend is offline, the page still renders the core help sections so the app remains usable.
      </div>
    </aside>
  </section>
</template>
