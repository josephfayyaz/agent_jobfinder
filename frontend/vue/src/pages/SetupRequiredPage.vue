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
    payload.value = await vueApiFetch("/setup/state");
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Request failed";
  } finally {
    loading.value = false;
  }
});

const responseData = computed(() => payload.value?.data ?? {});
const responseMessage = computed(() => payload.value?.message ?? "");
const setupComplete = computed(() => Boolean(responseData.value.setup_complete));
const providerConfigured = computed(() => Boolean(responseData.value.provider_configured));
const requiresSetup = computed(() => Boolean(responseData.value.requires_setup));
const identityReady = computed(() => Boolean(responseData.value.identity_ready));
const factSheetReady = computed(() => Boolean(responseData.value.fact_sheet_ready));
const searchFocusReady = computed(() => Boolean(responseData.value.search_focus_ready));
const missingSteps = computed(() =>
  Array.isArray(responseData.value.missing_steps) ? responseData.value.missing_steps.filter(Boolean) : []
);
const summaryLabel = computed(() =>
  setupComplete.value ? "Setup appears complete." : "Setup still needs attention."
);
</script>

<template>
  <AppPageHeader
    title="Setup Required"
    description="Check whether the local setup is ready, then continue to onboarding or settings without adding any routing guards."
  />

  <section class="grid gap-6 lg:grid-cols-3">
    <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm lg:col-span-2">
      <p class="text-sm font-medium text-slate-500">Current setup state</p>
      <h2 class="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
        {{ summaryLabel }}
      </h2>

      <div v-if="loading" class="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
        Loading setup state...
      </div>

      <div v-else-if="error" class="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
        {{ error }}
      </div>

      <div v-else class="mt-4 space-y-4">
        <p class="text-sm leading-6 text-slate-600">
          {{ responseMessage || "The setup contract reports whether provider configuration and onboarding are ready." }}
        </p>

        <div class="grid gap-4 md:grid-cols-2">
          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-sm font-medium text-slate-500">Setup complete</p>
            <p class="mt-2 text-lg font-semibold text-slate-950">{{ setupComplete ? "Yes" : "No" }}</p>
          </div>

          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-sm font-medium text-slate-500">Provider configured</p>
            <p class="mt-2 text-lg font-semibold text-slate-950">{{ providerConfigured ? "Yes" : "No" }}</p>
          </div>

          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-sm font-medium text-slate-500">Setup required</p>
            <p class="mt-2 text-lg font-semibold text-slate-950">{{ requiresSetup ? "Yes" : "No" }}</p>
          </div>

          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-sm font-medium text-slate-500">Identity ready</p>
            <p class="mt-2 text-lg font-semibold text-slate-950">{{ identityReady ? "Yes" : "No" }}</p>
          </div>

          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-sm font-medium text-slate-500">Fact sheet ready</p>
            <p class="mt-2 text-lg font-semibold text-slate-950">{{ factSheetReady ? "Yes" : "No" }}</p>
          </div>

          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-sm font-medium text-slate-500">Search focus ready</p>
            <p class="mt-2 text-lg font-semibold text-slate-950">{{ searchFocusReady ? "Yes" : "No" }}</p>
          </div>
        </div>

        <div v-if="missingSteps.length" class="rounded-xl border border-amber-200 bg-amber-50 p-4">
          <p class="text-sm font-medium text-amber-900">Missing steps</p>
          <ul class="mt-3 space-y-2 text-sm leading-6 text-amber-950">
            <li v-for="step in missingSteps" :key="step" class="rounded-lg border border-amber-200 bg-white px-3 py-2">
              {{ step }}
            </li>
          </ul>
        </div>

        <div v-else class="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
          No missing setup steps were reported by the backend.
        </div>
      </div>
    </article>

    <aside class="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div>
        <p class="text-sm font-medium text-slate-500">Next actions</p>
        <p class="mt-2 text-sm leading-6 text-slate-600">
          Follow the setup flow or review settings. This page never enforces a guard or redirects automatically.
        </p>
      </div>

      <div v-if="setupComplete" class="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
        Setup appears complete. You can continue to the dashboard.
      </div>

      <div v-else class="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
        Setup is still incomplete. Continue with onboarding and then review settings.
      </div>

      <div class="space-y-3">
        <RouterLink
          to="/onboarding"
          class="block rounded-xl bg-slate-950 px-4 py-2 text-center text-sm font-medium text-white hover:bg-slate-800"
        >
          Go to Onboarding
        </RouterLink>

        <RouterLink
          to="/settings"
          class="block rounded-xl border border-slate-200 bg-white px-4 py-2 text-center text-sm font-medium text-slate-950 hover:bg-slate-50"
        >
          Open Settings
        </RouterLink>

        <RouterLink
          v-if="setupComplete"
          to="/dashboard"
          class="block rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2 text-center text-sm font-medium text-emerald-900 hover:bg-emerald-100"
        >
          Continue to Dashboard
        </RouterLink>
      </div>
    </aside>
  </section>
</template>
