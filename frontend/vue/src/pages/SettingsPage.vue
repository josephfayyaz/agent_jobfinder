<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import AppPageHeader from "../components/AppPageHeader.vue";
import { vueApiFetch } from "../api/client";

const PROVIDER_LABELS = {
  local: "Local (LM Studio / Ollama)",
  lm_studio: "LM Studio (Local)",
  ollama: "Ollama (Local)",
  openai: "OpenAI",
  anthropic: "Claude (Anthropic)",
  gemini: "Google Gemini",
};

const loading = ref(true);
const error = ref("");
const payload = ref(null);

onMounted(async () => {
  try {
    payload.value = await vueApiFetch("/settings");
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

const providerMode = computed(() => responseData.value.provider_mode ?? "");
const providerModeLabel = computed(
  () => PROVIDER_LABELS[providerMode.value] || providerMode.value || "Not configured"
);
const providerReady = computed(() =>
  typeof responseData.value.provider_ready === "boolean" ? responseData.value.provider_ready : null
);
const providerConfigured = computed(() =>
  typeof responseData.value.provider_configured === "boolean" ? responseData.value.provider_configured : null
);

const openaiConfigured = computed(() =>
  typeof responseData.value.openai_configured === "boolean" ? responseData.value.openai_configured : null
);
const geminiConfigured = computed(() =>
  typeof responseData.value.gemini_configured === "boolean" ? responseData.value.gemini_configured : null
);
const anthropicConfigured = computed(() =>
  typeof responseData.value.anthropic_configured === "boolean" ? responseData.value.anthropic_configured : null
);
const lmStudioConfigured = computed(() =>
  typeof responseData.value.lm_studio_configured === "boolean" ? responseData.value.lm_studio_configured : null
);
const ollamaConfigured = computed(() =>
  typeof responseData.value.ollama_configured === "boolean" ? responseData.value.ollama_configured : null
);
const gmailConfigured = computed(() =>
  typeof responseData.value.gmail_configured === "boolean" ? responseData.value.gmail_configured : null
);
const yamlExists = computed(() =>
  typeof responseData.value.yaml_exists === "boolean" ? responseData.value.yaml_exists : null
);
const roleCount = computed(() =>
  typeof responseData.value.job_search_role_count === "number" ? responseData.value.job_search_role_count : null
);
const countryCount = computed(() =>
  typeof responseData.value.job_search_country_count === "number" ? responseData.value.job_search_country_count : null
);

const hasAnyData = computed(() => payload.value !== null && !error.value);
</script>

<template>
  <AppPageHeader
    title="Settings"
    description="A read-only status view of provider configuration and system setup. Secrets are never shown."
  />

  <section class="grid gap-6 lg:grid-cols-3">
    <div class="space-y-6 lg:col-span-2">

      <!-- Provider status -->
      <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Provider status</p>
        <h2 class="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
          Active provider
        </h2>

        <div v-if="loading" class="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
          Loading settings...
        </div>

        <div v-else-if="error" class="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          {{ error }}
        </div>

        <div v-else class="mt-4 space-y-4">
          <p v-if="responseMessage" class="text-sm leading-6 text-slate-600">
            {{ responseMessage }}
          </p>

          <div
            v-if="isPlaceholder"
            class="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"
          >
            The backend is returning placeholder settings data. Status indicators below are rendered safely from whatever is available.
          </div>

          <dl class="grid gap-4 text-sm md:grid-cols-2">
            <div v-if="providerMode" class="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <dt class="text-slate-500">Provider mode</dt>
              <dd class="mt-1 font-semibold text-slate-950">{{ providerModeLabel }}</dd>
            </div>

            <div v-if="providerReady !== null" class="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <dt class="text-slate-500">Provider ready</dt>
              <dd class="mt-1">
                <span
                  :class="[
                    'inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold',
                    providerReady
                      ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
                      : 'border-rose-200 bg-rose-50 text-rose-700'
                  ]"
                >
                  {{ providerReady ? "Ready" : "Not ready" }}
                </span>
              </dd>
            </div>

            <div v-if="providerConfigured !== null" class="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <dt class="text-slate-500">Provider configured</dt>
              <dd class="mt-1">
                <span
                  :class="[
                    'inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold',
                    providerConfigured
                      ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
                      : 'border-slate-200 bg-slate-50 text-slate-600'
                  ]"
                >
                  {{ providerConfigured ? "Yes" : "No" }}
                </span>
              </dd>
            </div>

            <div v-if="yamlExists !== null" class="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <dt class="text-slate-500">User settings file</dt>
              <dd class="mt-1">
                <span
                  :class="[
                    'inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold',
                    yamlExists
                      ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
                      : 'border-slate-200 bg-slate-50 text-slate-600'
                  ]"
                >
                  {{ yamlExists ? "Present" : "Not found" }}
                </span>
              </dd>
            </div>
          </dl>

          <!-- Cloud provider status -->
          <div>
            <p class="text-sm font-medium text-slate-500">Cloud provider configuration</p>
            <p class="mt-1 text-xs text-slate-400">Indicates whether a key is present — key values are never shown.</p>
            <dl class="mt-3 grid gap-3 text-sm md:grid-cols-3">
              <div v-if="openaiConfigured !== null" class="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
                <dt class="text-slate-600">OpenAI</dt>
                <dd>
                  <span
                    :class="[
                      'inline-flex items-center rounded border px-1.5 py-0.5 text-xs font-medium',
                      openaiConfigured
                        ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                        : 'border-slate-200 bg-white text-slate-500'
                    ]"
                  >
                    {{ openaiConfigured ? "Key present" : "Not set" }}
                  </span>
                </dd>
              </div>
              <div v-if="anthropicConfigured !== null" class="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
                <dt class="text-slate-600">Anthropic</dt>
                <dd>
                  <span
                    :class="[
                      'inline-flex items-center rounded border px-1.5 py-0.5 text-xs font-medium',
                      anthropicConfigured
                        ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                        : 'border-slate-200 bg-white text-slate-500'
                    ]"
                  >
                    {{ anthropicConfigured ? "Key present" : "Not set" }}
                  </span>
                </dd>
              </div>
              <div v-if="geminiConfigured !== null" class="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
                <dt class="text-slate-600">Gemini</dt>
                <dd>
                  <span
                    :class="[
                      'inline-flex items-center rounded border px-1.5 py-0.5 text-xs font-medium',
                      geminiConfigured
                        ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                        : 'border-slate-200 bg-white text-slate-500'
                    ]"
                  >
                    {{ geminiConfigured ? "Key present" : "Not set" }}
                  </span>
                </dd>
              </div>
            </dl>
          </div>
        </div>
      </article>

      <!-- Local inference -->
      <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Local inference</p>
        <h2 class="mt-2 text-xl font-semibold tracking-tight text-slate-950">Local model servers</h2>

        <div v-if="!loading && !error" class="mt-4 space-y-3">
          <p class="text-sm leading-6 text-slate-600">
            Local model servers run on your machine. No API key or network access is required.
          </p>

          <dl class="grid gap-3 text-sm md:grid-cols-2">
            <div v-if="lmStudioConfigured !== null" class="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
              <dt class="text-slate-600">LM Studio</dt>
              <dd>
                <span
                  :class="[
                    'inline-flex items-center rounded border px-1.5 py-0.5 text-xs font-medium',
                    lmStudioConfigured
                      ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                      : 'border-slate-200 bg-white text-slate-500'
                  ]"
                >
                  {{ lmStudioConfigured ? "URL configured" : "Not set" }}
                </span>
              </dd>
            </div>
            <div v-if="ollamaConfigured !== null" class="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
              <dt class="text-slate-600">Ollama</dt>
              <dd>
                <span
                  :class="[
                    'inline-flex items-center rounded border px-1.5 py-0.5 text-xs font-medium',
                    ollamaConfigured
                      ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                      : 'border-slate-200 bg-white text-slate-500'
                  ]"
                >
                  {{ ollamaConfigured ? "URL configured" : "Not set" }}
                </span>
              </dd>
            </div>
          </dl>

          <p
            v-if="lmStudioConfigured === null && ollamaConfigured === null"
            class="text-sm text-slate-600"
          >
            Local inference status not available.
          </p>
        </div>

        <div v-if="loading" class="mt-4 text-sm text-slate-600">Loading...</div>
      </article>

      <!-- Job search configuration -->
      <article
        v-if="!loading && !error && (roleCount !== null || countryCount !== null || gmailConfigured !== null)"
        class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
      >
        <p class="text-sm font-medium text-slate-500">Job search and integrations</p>
        <h2 class="mt-2 text-xl font-semibold tracking-tight text-slate-950">Discovery configuration</h2>

        <dl class="mt-4 grid gap-4 text-sm md:grid-cols-2">
          <div v-if="roleCount !== null" class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <dt class="text-slate-500">Search role queries</dt>
            <dd class="mt-1 text-xl font-bold text-slate-950">{{ roleCount }}</dd>
          </div>
          <div v-if="countryCount !== null" class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <dt class="text-slate-500">Search countries</dt>
            <dd class="mt-1 text-xl font-bold text-slate-950">{{ countryCount }}</dd>
          </div>
          <div v-if="gmailConfigured !== null" class="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
            <dt class="text-slate-600">Gmail OAuth</dt>
            <dd>
              <span
                :class="[
                  'inline-flex items-center rounded border px-1.5 py-0.5 text-xs font-medium',
                  gmailConfigured
                    ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                    : 'border-slate-200 bg-white text-slate-500'
                ]"
              >
                {{ gmailConfigured ? "Configured" : "Not set" }}
              </span>
            </dd>
          </div>
        </dl>
      </article>

      <!-- Security and secrets -->
      <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Security and secrets</p>
        <h2 class="mt-2 text-xl font-semibold tracking-tight text-slate-950">Secrets policy</h2>

        <div class="mt-4 space-y-3">
          <div class="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
            API keys, tokens, and credentials are never transmitted to this page. The backend settings contract exposes only boolean presence indicators — not key values, not masked values, not environment variable contents.
          </div>
          <dl class="grid gap-3 text-sm md:grid-cols-2">
            <div class="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
              <dt class="text-slate-600">Secrets exposed</dt>
              <dd>
                <span class="inline-flex items-center rounded border border-emerald-200 bg-emerald-50 px-1.5 py-0.5 text-xs font-semibold text-emerald-800">
                  Never
                </span>
              </dd>
            </div>
            <div class="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
              <dt class="text-slate-600">Paths exposed</dt>
              <dd>
                <span class="inline-flex items-center rounded border border-emerald-200 bg-emerald-50 px-1.5 py-0.5 text-xs font-semibold text-emerald-800">
                  Never
                </span>
              </dd>
            </div>
          </dl>
        </div>
      </article>

    </div>

    <!-- Sidebar -->
    <aside class="space-y-4">

      <!-- Read-only safety notice -->
      <div class="rounded-2xl border border-amber-200 bg-amber-50 p-6 shadow-sm">
        <p class="text-sm font-medium text-amber-900">Read-only safety</p>
        <p class="mt-2 text-sm leading-6 text-amber-800">
          Settings cannot be changed from this Vue page. Provider selection, API key entry, and model configuration happen through the legacy settings interface only.
        </p>
        <p class="mt-3 text-sm leading-6 text-amber-800">
          To configure your provider, visit <code class="rounded bg-amber-100 px-1 font-mono text-xs">/ui/settings</code> while Vue migration is in progress.
        </p>
      </div>

      <!-- Status and navigation -->
      <div class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div>
          <p class="text-sm font-medium text-slate-500">Next actions</p>
          <p class="mt-2 text-sm leading-6 text-slate-600">
            If your provider is not ready, complete onboarding to configure a model. Use the setup check to diagnose configuration issues.
          </p>
        </div>

        <dl class="mt-4 space-y-3 text-sm">
          <div class="flex items-start justify-between gap-4">
            <dt class="text-slate-500">Loading</dt>
            <dd class="font-medium text-slate-950">{{ loading ? "Yes" : "No" }}</dd>
          </div>
          <div class="flex items-start justify-between gap-4">
            <dt class="text-slate-500">Error</dt>
            <dd class="font-medium text-slate-950">{{ error ? "Present" : "None" }}</dd>
          </div>
          <div class="flex items-start justify-between gap-4">
            <dt class="text-slate-500">Placeholder</dt>
            <dd class="font-medium text-slate-950">{{ isPlaceholder ? "Yes" : "No" }}</dd>
          </div>
          <div v-if="providerReady !== null" class="flex items-start justify-between gap-4">
            <dt class="text-slate-500">Provider ready</dt>
            <dd>
              <span
                :class="[
                  'inline-flex items-center rounded border px-1.5 py-0.5 text-xs font-medium',
                  providerReady
                    ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                    : 'border-rose-200 bg-rose-50 text-rose-700'
                ]"
              >
                {{ providerReady ? "Ready" : "Not ready" }}
              </span>
            </dd>
          </div>
        </dl>

        <div class="mt-4 space-y-3">
          <RouterLink
            to="/onboarding"
            class="block rounded-xl bg-slate-950 px-4 py-2 text-center text-sm font-medium text-white hover:bg-slate-800"
          >
            Onboarding
          </RouterLink>
          <RouterLink
            to="/"
            class="block rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-center text-sm font-medium text-slate-900 hover:bg-slate-100"
          >
            Welcome
          </RouterLink>
        </div>
      </div>

    </aside>
  </section>
</template>
