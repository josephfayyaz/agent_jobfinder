<script setup>
import { computed, onMounted, ref } from "vue";
import AppPageHeader from "../components/AppPageHeader.vue";
import { vueApiFetch } from "../api/client";

const loading = ref(true);
const error = ref("");
const payload = ref(null);

onMounted(async () => {
  try {
    payload.value = await vueApiFetch("/about");
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Request failed";
  } finally {
    loading.value = false;
  }
});

const responseData = computed(() => payload.value?.data ?? {});
const responseStatus = computed(() => payload.value?.status ?? "");
const responseMessage = computed(() => payload.value?.message ?? "");
const contractVersion = computed(() => payload.value?.contract_version ?? 1);
const title = computed(() => responseData.value.title || "About Local LLM Job Agent");
const summary = computed(
  () =>
    responseData.value.summary ||
    "A local-first job search and CV optimization app that keeps the main workflow on your machine."
);
const localFirst = computed(() => responseData.value.local_first !== false);
const migrationStatus = computed(() =>
  responseStatus.value === "placeholder"
    ? "Vue migration contract placeholder"
    : "Vue page backed by the current contract layer"
);
</script>

<template>
  <AppPageHeader
    title="About Local LLM Job Agent"
    description="A local-first, privacy-first job search workspace that is being migrated page by page without changing the legacy /ui routes."
  />

  <section class="grid gap-6 lg:grid-cols-3">
    <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm lg:col-span-2">
      <p class="text-sm font-medium text-slate-500">Local-first workflow</p>
      <h2 class="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
        {{ title }}
      </h2>

      <div v-if="loading" class="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
        Loading about details...
      </div>

      <div v-else-if="error" class="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
        {{ error }}
      </div>

      <div v-else class="mt-4 space-y-4">
        <p class="max-w-3xl text-sm leading-6 text-slate-600">
          {{ summary }}
        </p>

        <div class="grid gap-4 md:grid-cols-2">
          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-sm font-medium text-slate-500">Local-first workflow</p>
            <p class="mt-2 text-sm leading-6 text-slate-600">
              The app is designed to keep your job search, notes, and CV work on your own machine whenever possible.
            </p>
            <p class="mt-3 text-sm font-medium text-slate-900">
              {{ localFirst ? "The backend reports a local-first mode." : "The backend does not currently report local-first mode." }}
            </p>
          </div>

          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-sm font-medium text-slate-500">Privacy and control</p>
            <p class="mt-2 text-sm leading-6 text-slate-600">
              This migration keeps private data in the existing local workflow and avoids exposing secrets or filesystem paths in the page UI.
            </p>
          </div>
        </div>

        <div class="rounded-xl border border-slate-200 bg-white p-4">
          <p class="text-sm font-medium text-slate-500">API details</p>
          <dl class="mt-3 grid gap-4 text-sm md:grid-cols-3">
            <div>
              <dt class="text-slate-500">Contract version</dt>
              <dd class="mt-1 font-medium text-slate-950">{{ contractVersion }}</dd>
            </div>
            <div>
              <dt class="text-slate-500">Status</dt>
              <dd class="mt-1 font-medium text-slate-950">{{ migrationStatus }}</dd>
            </div>
            <div>
              <dt class="text-slate-500">Message</dt>
              <dd class="mt-1 font-medium text-slate-950">
                {{ responseMessage || "No additional message was returned." }}
              </dd>
            </div>
          </dl>
        </div>
      </div>
    </article>

    <aside class="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div>
        <p class="text-sm font-medium text-slate-500">Vue migration status</p>
        <p class="mt-2 text-sm leading-6 text-slate-600">
          This page is now a real Vue route and consumes the about contract directly.
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
          <dt class="text-slate-500">Fallback ready</dt>
          <dd class="font-medium text-slate-950">Yes</dd>
        </div>
      </dl>

      <div class="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
        If the backend only returns placeholder content, the page still explains the local-first workflow and privacy model.
      </div>
    </aside>
  </section>
</template>
