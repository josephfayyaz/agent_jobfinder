<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import AppPageHeader from "../components/AppPageHeader.vue";
import { vueApiFetch } from "../api/client";

const FALLBACK_STEPS = [
  { key: "provider", label: "Provider", complete: null },
  { key: "profile", label: "Profile", complete: null },
  { key: "fact_sheet", label: "Fact Sheet", complete: null },
  { key: "qa", label: "Q&A", complete: null },
  { key: "review", label: "Review", complete: null },
  { key: "search", label: "Search", complete: null },
  { key: "done", label: "Done", complete: null },
];

const BLOCKED_KEY_PATTERNS = [
  "api_key", "token", "secret", "password", "credential",
  "private_key", "access_key", "refresh_token", "auth",
  "keyring", "env", "environment", "path", "file_path",
  "absolute_path", "home", "root", "directory", "dir",
  "upload", "uploaded_file",
];

function isSafeKey(key) {
  const lower = String(key).toLowerCase();
  return !BLOCKED_KEY_PATTERNS.some((p) => lower.includes(p));
}

function isSafeStringValue(val) {
  if (typeof val !== "string") return true;
  return !val.startsWith("/") && !val.startsWith("~/") && !val.startsWith("file:");
}

const loading = ref(true);
const error = ref("");
const onboardingStatePayload = ref(null);
const onboardingStepsPayload = ref(null);
const setupStatePayload = ref(null);

onMounted(async () => {
  try {
    const [onboardingState, onboardingSteps, setupState] = await Promise.all([
      vueApiFetch("/onboarding/state"),
      vueApiFetch("/onboarding/steps"),
      vueApiFetch("/setup/state"),
    ]);
    onboardingStatePayload.value = onboardingState;
    onboardingStepsPayload.value = onboardingSteps;
    setupStatePayload.value = setupState;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Request failed";
  } finally {
    loading.value = false;
  }
});

// Setup state
const setupData = computed(() => setupStatePayload.value?.data ?? {});
const setupComplete = computed(() =>
  typeof setupData.value.setup_complete === "boolean" ? setupData.value.setup_complete : null
);
const providerConfigured = computed(() =>
  typeof setupData.value.provider_configured === "boolean" ? setupData.value.provider_configured : null
);
const requiresSetup = computed(() =>
  typeof setupData.value.requires_setup === "boolean" ? setupData.value.requires_setup : null
);
const identityReady = computed(() =>
  typeof setupData.value.identity_ready === "boolean" ? setupData.value.identity_ready : null
);
const factSheetReady = computed(() =>
  typeof setupData.value.fact_sheet_ready === "boolean" ? setupData.value.fact_sheet_ready : null
);
const searchFocusReady = computed(() =>
  typeof setupData.value.search_focus_ready === "boolean" ? setupData.value.search_focus_ready : null
);
const missingSteps = computed(() =>
  Array.isArray(setupData.value.missing_steps)
    ? setupData.value.missing_steps.filter(
        (s) => typeof s === "string" && isSafeKey(s) && isSafeStringValue(s)
      )
    : []
);

// Onboarding state
const onboardingData = computed(() => onboardingStatePayload.value?.data ?? {});
const candidateExists = computed(() =>
  typeof onboardingData.value.candidate_exists === "boolean" ? onboardingData.value.candidate_exists : null
);

// Onboarding steps
const stepsData = computed(() => onboardingStepsPayload.value?.data ?? {});
const stepsMsg = computed(() => onboardingStepsPayload.value?.message ?? "");
const isStepsPlaceholder = computed(() => (onboardingStepsPayload.value?.status ?? "") === "placeholder");

const apiSteps = computed(() => {
  const raw = Array.isArray(stepsData.value.items)
    ? stepsData.value.items
    : Array.isArray(stepsData.value.steps)
    ? stepsData.value.steps
    : [];
  return raw.filter(Boolean);
});

const displaySteps = computed(() =>
  apiSteps.value.length > 0 ? apiSteps.value : FALLBACK_STEPS
);

const usingFallback = computed(() => apiSteps.value.length === 0);

const completedCount = computed(() =>
  displaySteps.value.filter((s) => s.complete === true).length
);

// Any placeholder status
const isAnyPlaceholder = computed(() =>
  (onboardingStatePayload.value?.status ?? "") === "placeholder" ||
  (setupStatePayload.value?.status ?? "") === "placeholder" ||
  isStepsPlaceholder.value
);

function stepLabel(step) {
  return step?.label || step?.name || step?.title || "Untitled step";
}
function stepKey(step) {
  return step?.key || step?.id || "";
}
</script>

<template>
  <AppPageHeader
    title="Onboarding"
    description="A read-only status view of onboarding progress and setup readiness. No settings or data are saved from this page."
  />

  <section class="grid gap-6 lg:grid-cols-3">
    <div class="space-y-6 lg:col-span-2">

      <!-- Setup readiness -->
      <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Setup readiness</p>
        <h2 class="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
          Configuration status
        </h2>

        <div v-if="loading" class="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
          Loading onboarding state...
        </div>

        <div v-else-if="error" class="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          {{ error }}
        </div>

        <div v-else class="mt-4 space-y-4">
          <div
            v-if="isAnyPlaceholder"
            class="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"
          >
            One or more onboarding endpoints are returning placeholder data. Status indicators below are rendered safely from whatever is available.
          </div>

          <!-- Overall status banner -->
          <div
            :class="[
              'rounded-xl border p-4 text-sm font-medium',
              setupComplete === true
                ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
                : requiresSetup === true
                ? 'border-amber-200 bg-amber-50 text-amber-900'
                : 'border-slate-200 bg-slate-50 text-slate-700'
            ]"
          >
            <span v-if="setupComplete === true">Setup is complete. You can use the full job agent.</span>
            <span v-else-if="requiresSetup === true">Setup is incomplete. Complete the steps below to continue.</span>
            <span v-else>Setup status unavailable.</span>
          </div>

          <dl class="grid gap-4 text-sm md:grid-cols-2">
            <div v-if="providerConfigured !== null" class="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
              <dt class="text-slate-600">AI provider</dt>
              <dd>
                <span :class="['inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold', providerConfigured ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-slate-200 bg-white text-slate-500']">
                  {{ providerConfigured ? "Configured" : "Not set" }}
                </span>
              </dd>
            </div>

            <div v-if="identityReady !== null" class="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
              <dt class="text-slate-600">Identity / profile</dt>
              <dd>
                <span :class="['inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold', identityReady ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-slate-200 bg-white text-slate-500']">
                  {{ identityReady ? "Ready" : "Incomplete" }}
                </span>
              </dd>
            </div>

            <div v-if="factSheetReady !== null" class="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
              <dt class="text-slate-600">Fact sheet</dt>
              <dd>
                <span :class="['inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold', factSheetReady ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-slate-200 bg-white text-slate-500']">
                  {{ factSheetReady ? "Ready" : "Incomplete" }}
                </span>
              </dd>
            </div>

            <div v-if="searchFocusReady !== null" class="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
              <dt class="text-slate-600">Search focus</dt>
              <dd>
                <span :class="['inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold', searchFocusReady ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-slate-200 bg-white text-slate-500']">
                  {{ searchFocusReady ? "Ready" : "Incomplete" }}
                </span>
              </dd>
            </div>

            <div v-if="candidateExists !== null" class="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
              <dt class="text-slate-600">Candidate profile</dt>
              <dd>
                <span :class="['inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold', candidateExists ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-slate-200 bg-white text-slate-500']">
                  {{ candidateExists ? "Exists" : "Not created" }}
                </span>
              </dd>
            </div>
          </dl>

          <!-- Missing steps -->
          <div v-if="missingSteps.length">
            <p class="text-sm font-medium text-slate-500">Incomplete steps</p>
            <div class="mt-2 flex flex-wrap gap-1.5">
              <span
                v-for="step in missingSteps"
                :key="step"
                class="inline-flex items-center rounded-md border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-800"
              >
                {{ step }}
              </span>
            </div>
          </div>
        </div>
      </article>

      <!-- Onboarding steps -->
      <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Onboarding steps</p>
        <h2 class="mt-2 text-xl font-semibold tracking-tight text-slate-950">
          Step progress
        </h2>

        <div v-if="loading" class="mt-4 text-sm text-slate-600">Loading steps...</div>

        <div v-else class="mt-4 space-y-4">
          <p v-if="stepsMsg" class="text-sm leading-6 text-slate-600">{{ stepsMsg }}</p>

          <div
            v-if="isStepsPlaceholder"
            class="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"
          >
            Steps data is returning placeholder content.
          </div>

          <div
            v-if="usingFallback"
            class="rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-500"
          >
            Showing default step list — live step progress not available from the API.
          </div>

          <div v-if="!usingFallback" class="mb-2 text-sm text-slate-600">
            {{ completedCount }} of {{ displaySteps.length }} steps complete
          </div>

          <ol class="space-y-2">
            <li
              v-for="(step, index) in displaySteps"
              :key="stepKey(step) || index"
              class="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm"
            >
              <!-- Step number / completion indicator -->
              <span
                :class="[
                  'flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-xs font-semibold',
                  step.complete === true
                    ? 'border-emerald-300 bg-emerald-100 text-emerald-800'
                    : step.complete === false
                    ? 'border-slate-300 bg-white text-slate-500'
                    : 'border-slate-200 bg-slate-50 text-slate-400'
                ]"
              >
                {{ step.complete === true ? "✓" : index + 1 }}
              </span>

              <!-- Step label -->
              <span class="flex-1 font-medium text-slate-950">{{ stepLabel(step) }}</span>

              <!-- Status badge -->
              <span
                v-if="step.complete !== null"
                :class="[
                  'inline-flex items-center rounded border px-1.5 py-0.5 text-xs font-medium',
                  step.complete === true
                    ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                    : 'border-slate-200 bg-slate-50 text-slate-500'
                ]"
              >
                {{ step.complete === true ? "Complete" : "Pending" }}
              </span>
            </li>
          </ol>
        </div>
      </article>

    </div>

    <!-- Sidebar -->
    <aside class="space-y-4">

      <!-- Read-only safety notice -->
      <div class="rounded-2xl border border-amber-200 bg-amber-50 p-6 shadow-sm">
        <p class="text-sm font-medium text-amber-900">Read-only safety</p>
        <p class="mt-2 text-sm leading-6 text-amber-800">
          This Vue page shows onboarding status only. No provider settings, profile data, Q&amp;A answers, or verified facts are saved from here.
        </p>
        <p class="mt-3 text-sm leading-6 text-amber-800">
          To complete onboarding, use the legacy interface at
          <code class="rounded bg-amber-100 px-1 font-mono text-xs">/ui/onboarding</code>
          while Vue migration is in progress.
        </p>
      </div>

      <!-- Status and navigation -->
      <div class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div>
          <p class="text-sm font-medium text-slate-500">Next actions</p>
          <p class="mt-2 text-sm leading-6 text-slate-600">
            If setup is incomplete, use the setup check to diagnose the issue. Once setup is complete, go to the dashboard.
          </p>
        </div>

        <dl class="mt-4 space-y-3 text-sm">
          <div v-if="setupComplete !== null" class="flex items-start justify-between gap-4">
            <dt class="text-slate-500">Setup complete</dt>
            <dd>
              <span :class="['inline-flex items-center rounded border px-1.5 py-0.5 text-xs font-medium', setupComplete ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-amber-200 bg-amber-50 text-amber-700']">
                {{ setupComplete ? "Yes" : "No" }}
              </span>
            </dd>
          </div>
          <div v-if="!usingFallback" class="flex items-start justify-between gap-4">
            <dt class="text-slate-500">Steps done</dt>
            <dd class="font-medium text-slate-950">{{ completedCount }} / {{ displaySteps.length }}</dd>
          </div>
        </dl>

        <div class="mt-4 space-y-3">
          <RouterLink
            to="/setup-required"
            class="block rounded-xl bg-slate-950 px-4 py-2 text-center text-sm font-medium text-white hover:bg-slate-800"
          >
            Setup check
          </RouterLink>
          <RouterLink
            to="/dashboard"
            class="block rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-center text-sm font-medium text-slate-900 hover:bg-slate-100"
          >
            Go to Dashboard
          </RouterLink>
          <RouterLink
            to="/settings"
            class="block rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-center text-sm font-medium text-slate-900 hover:bg-slate-100"
          >
            Settings
          </RouterLink>
          <RouterLink
            to="/verified-facts"
            class="block rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2 text-center text-sm font-medium text-emerald-900 hover:bg-emerald-100"
          >
            Verified Facts
          </RouterLink>
        </div>
      </div>

    </aside>
  </section>
</template>
