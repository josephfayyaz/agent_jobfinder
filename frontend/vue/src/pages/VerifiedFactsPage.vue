<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import AppPageHeader from "../components/AppPageHeader.vue";
import { vueApiFetch } from "../api/client";

const BLOCKED_KEY_PATTERNS = [
  "api_key", "token", "secret", "password", "credential",
  "private_key", "access_key", "refresh_token", "auth",
  "file_path", "absolute_path",
];

function isSafeKey(key) {
  const lower = String(key).toLowerCase();
  return !BLOCKED_KEY_PATTERNS.some((pattern) => lower.includes(pattern));
}

const loading = ref(true);
const error = ref("");
const factsPayload = ref(null);
const schemaPayload = ref(null);

onMounted(async () => {
  try {
    const [facts, schema] = await Promise.all([
      vueApiFetch("/verified-facts"),
      vueApiFetch("/verified-facts/schema"),
    ]);
    factsPayload.value = facts;
    schemaPayload.value = schema;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Request failed";
  } finally {
    loading.value = false;
  }
});

const factsData = computed(() => factsPayload.value?.data ?? {});
const factsStatus = computed(() => factsPayload.value?.status ?? "");
const factsMessage = computed(() => factsPayload.value?.message ?? "");
const isFactsPlaceholder = computed(() => factsStatus.value === "placeholder");

const schemaData = computed(() => schemaPayload.value?.data ?? {});
const schemaStatus = computed(() => schemaPayload.value?.status ?? "");
const schemaMessage = computed(() => schemaPayload.value?.message ?? "");
const isSchemaPlaceholder = computed(() => schemaStatus.value === "placeholder");

const items = computed(() =>
  Array.isArray(factsData.value.items) ? factsData.value.items.filter(Boolean) : []
);
const total = computed(() => factsData.value.total ?? items.value.length ?? 0);

const schemaFactTypes = computed(() =>
  Array.isArray(schemaData.value.fact_types) ? schemaData.value.fact_types : []
);
const schemaFields = computed(() =>
  Array.isArray(schemaData.value.fields) ? schemaData.value.fields.filter(Boolean) : []
);

const factLabel = (item) => (isSafeKey("gap_label") ? item?.gap_label || "Untitled fact" : "Untitled fact");
const factType = (item) => item?.fact_type || "Unknown category";
const factEvidence = (item) => item?.evidence || "";
const factId = (item) => item?.id || "";
const factCreatedAt = (item) => item?.created_at || "";
const factSourceDraftId = (item) => item?.source_draft_id || "";
const factSourceJobId = (item) => item?.source_job_id || "";
const factIsActive = (item) => (typeof item?.is_active === "boolean" ? item.is_active : null);
</script>

<template>
  <AppPageHeader
    title="Verified Facts"
    description="A read-only view of approved candidate facts used in CV generation."
  />

  <section class="grid gap-6 lg:grid-cols-3">
    <div class="space-y-6 lg:col-span-2">

      <!-- Approved fact records -->
      <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Fact traceability status</p>
        <h2 class="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
          Approved fact records
        </h2>

        <div v-if="loading" class="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
          Loading verified facts...
        </div>

        <div v-else-if="error" class="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          {{ error }}
        </div>

        <div v-else class="mt-4 space-y-4">
          <p v-if="factsMessage" class="text-sm leading-6 text-slate-600">
            {{ factsMessage }}
          </p>

          <div
            v-if="isFactsPlaceholder"
            class="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"
          >
            The backend is returning placeholder verified-facts data. The list below is rendered safely from whatever is available.
          </div>

          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <div class="flex flex-wrap items-center justify-between gap-3">
              <p class="text-sm font-medium text-slate-500">Total active facts</p>
              <p class="text-lg font-semibold text-slate-950">{{ total }}</p>
            </div>
          </div>

          <div v-if="items.length" class="space-y-3">
            <article
              v-for="item in items"
              :key="factId(item) || factLabel(item)"
              class="rounded-xl border border-slate-200 bg-white p-4"
            >
              <div class="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                <div>
                  <h3 class="text-sm font-semibold text-slate-950">{{ factLabel(item) }}</h3>
                  <span class="mt-1 inline-flex items-center rounded-md border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs font-medium text-slate-700">
                    {{ factType(item) }}
                  </span>
                </div>
                <span
                  v-if="factIsActive(item) !== null"
                  :class="[
                    'inline-flex shrink-0 items-center rounded-md border px-2 py-0.5 text-xs font-medium',
                    factIsActive(item)
                      ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
                      : 'border-slate-200 bg-slate-50 text-slate-600'
                  ]"
                >
                  {{ factIsActive(item) ? "Active" : "Inactive" }}
                </span>
              </div>

              <p v-if="factEvidence(item)" class="mt-3 text-sm leading-6 text-slate-600">
                {{ factEvidence(item) }}
              </p>

              <dl class="mt-3 grid gap-3 text-sm text-slate-600 md:grid-cols-2">
                <div v-if="factId(item)">
                  <dt class="text-slate-500">ID</dt>
                  <dd class="mt-1 font-mono text-xs text-slate-950 break-all">{{ factId(item) }}</dd>
                </div>
                <div v-if="factCreatedAt(item)">
                  <dt class="text-slate-500">Created</dt>
                  <dd class="mt-1 text-slate-950">{{ factCreatedAt(item) }}</dd>
                </div>
                <div v-if="factSourceDraftId(item)">
                  <dt class="text-slate-500">Source draft</dt>
                  <dd class="mt-1 font-mono text-xs text-slate-950 break-all">
                    <RouterLink
                      :to="`/drafts/${factSourceDraftId(item)}`"
                      class="underline decoration-slate-300 underline-offset-2 hover:text-slate-950"
                    >
                      {{ String(factSourceDraftId(item)).slice(0, 8) }}
                    </RouterLink>
                  </dd>
                </div>
                <div v-if="factSourceJobId(item)">
                  <dt class="text-slate-500">Source job</dt>
                  <dd class="mt-1 font-mono text-xs text-slate-950 break-all">
                    {{ String(factSourceJobId(item)).slice(0, 8) }}
                  </dd>
                </div>
              </dl>
            </article>
          </div>

          <div
            v-else
            class="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-600"
          >
            No verified facts are currently active. Facts are approved through the intake Q&amp;A flow and human review.
          </div>
        </div>
      </article>

      <!-- Fact schema -->
      <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Fact schema</p>
        <h2 class="mt-2 text-xl font-semibold tracking-tight text-slate-950">Field definitions</h2>

        <div v-if="loading" class="mt-4 text-sm text-slate-600">Loading schema...</div>

        <div v-else class="mt-4 space-y-4">
          <p v-if="schemaMessage" class="text-sm text-slate-600">{{ schemaMessage }}</p>

          <div
            v-if="isSchemaPlaceholder"
            class="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"
          >
            Schema metadata is not yet available from the backend.
          </div>

          <div v-if="schemaFactTypes.length">
            <p class="text-sm font-medium text-slate-500">Allowed fact types</p>
            <div class="mt-2 flex flex-wrap gap-1.5">
              <span
                v-for="ft in schemaFactTypes"
                :key="ft"
                class="inline-flex items-center rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-700"
              >
                {{ ft }}
              </span>
            </div>
          </div>

          <div v-if="schemaFields.length">
            <p class="text-sm font-medium text-slate-500">Required fields</p>
            <div class="mt-2 space-y-2">
              <div
                v-for="field in schemaFields"
                :key="field.key"
                class="flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm"
              >
                <span class="font-mono font-medium text-slate-950">{{ field.key }}</span>
                <span class="text-slate-500">{{ field.type }}</span>
                <span
                  v-if="field.required"
                  class="inline-flex items-center rounded border border-rose-200 bg-rose-50 px-1.5 py-0.5 text-xs font-medium text-rose-700"
                >
                  required
                </span>
              </div>
            </div>
          </div>

          <p
            v-if="!schemaFactTypes.length && !schemaFields.length && !isSchemaPlaceholder"
            class="text-sm text-slate-600"
          >
            No schema metadata available.
          </p>
        </div>
      </article>

    </div>

    <!-- Sidebar -->
    <aside class="space-y-4">

      <!-- Read-only safety notice -->
      <div class="rounded-2xl border border-amber-200 bg-amber-50 p-6 shadow-sm">
        <p class="text-sm font-medium text-amber-900">Read-only safety</p>
        <p class="mt-2 text-sm leading-6 text-amber-800">
          Verified facts cannot be created, edited, deleted, or promoted from this Vue page. Fact validation and approval happen through the backend intake workflow only.
        </p>
        <p class="mt-3 text-sm leading-6 text-amber-800">
          To manage facts, use the legacy interface at <code class="rounded bg-amber-100 px-1 font-mono text-xs">/ui/verified-facts</code> while Vue migration is in progress.
        </p>
      </div>

      <!-- Navigation -->
      <div class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div>
          <p class="text-sm font-medium text-slate-500">Next actions</p>
          <p class="mt-2 text-sm leading-6 text-slate-600">
            Facts are collected during onboarding and intake. Use the apply flow to use verified facts in a CV draft.
          </p>
        </div>

        <dl class="mt-4 space-y-3 text-sm">
          <div class="flex items-start justify-between gap-4">
            <dt class="text-slate-500">Facts placeholder</dt>
            <dd class="font-medium text-slate-950">{{ isFactsPlaceholder ? "Yes" : "No" }}</dd>
          </div>
          <div class="flex items-start justify-between gap-4">
            <dt class="text-slate-500">Active facts</dt>
            <dd class="font-medium text-slate-950">{{ total }}</dd>
          </div>
        </dl>

        <div class="mt-4 space-y-3">
          <RouterLink
            to="/apply"
            class="block rounded-xl bg-slate-950 px-4 py-2 text-center text-sm font-medium text-white hover:bg-slate-800"
          >
            Open Apply
          </RouterLink>
          <RouterLink
            to="/onboarding"
            class="block rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-center text-sm font-medium text-slate-900 hover:bg-slate-100"
          >
            Onboarding
          </RouterLink>
          <RouterLink
            to="/drafts"
            class="block rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-center text-sm font-medium text-slate-900 hover:bg-slate-100"
          >
            Go to Drafts
          </RouterLink>
          <RouterLink
            to="/settings"
            class="block rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2 text-center text-sm font-medium text-emerald-900 hover:bg-emerald-100"
          >
            Settings
          </RouterLink>
        </div>
      </div>

    </aside>
  </section>
</template>
