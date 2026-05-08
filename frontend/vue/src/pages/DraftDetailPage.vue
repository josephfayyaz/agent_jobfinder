<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterLink, useRoute } from "vue-router";
import AppPageHeader from "../components/AppPageHeader.vue";
import { vueApiFetch } from "../api/client";

const route = useRoute();
const draftId = computed(() => String(route.params.id || ""));

const loading = ref(true);
const error = ref("");
const payload = ref(null);

onMounted(async () => {
  if (!draftId.value) {
    error.value = "No draft ID provided in route.";
    loading.value = false;
    return;
  }
  try {
    payload.value = await vueApiFetch(`/drafts/${draftId.value}`);
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
const detail = computed(() => responseData.value.item ?? {});

const detailLabel = computed(() => detail.value?.title || detail.value?.role || (draftId.value ? `Draft ${draftId.value.slice(0, 8)}` : "Untitled draft"));
const detailCompany = computed(() => detail.value?.company || "Unknown company");
const detailStatus = computed(() => detail.value?.status || "Status unavailable");
const detailScore = computed(() => (typeof detail.value?.score === "number" ? detail.value.score : null));
const detailApproved = computed(() => (typeof detail.value?.approved === "boolean" ? detail.value.approved : null));
const detailProvider = computed(() => detail.value?.provider || "");
const detailHasContent = computed(() => detail.value?.has_content ?? false);
const detailHasCoverLetter = computed(() => detail.value?.has_cover_letter ?? false);
const detailFeedbackKeys = computed(() => Array.isArray(detail.value?.review_feedback_keys) ? detail.value.review_feedback_keys : []);
const detailCreatedAt = computed(() => detail.value?.created_at || "");
const detailUpdatedAt = computed(() => detail.value?.updated_at || "");
</script>

<template>
  <AppPageHeader
    title="Draft Detail"
    :description="`Read-only view of draft ${draftId || '(unknown)'}.`"
  />

  <section class="grid gap-6 lg:grid-cols-3">
    <div class="space-y-6 lg:col-span-2">

      <!-- Draft metadata card -->
      <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Draft metadata</p>
        <h2 class="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
          {{ detailLabel }}
        </h2>

        <div v-if="loading" class="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
          Loading draft...
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
            The backend is still returning placeholder draft data. The detail below is rendered safely from whatever is available.
          </div>

          <dl class="grid gap-4 text-sm md:grid-cols-2">
            <div>
              <dt class="text-slate-500">Route ID</dt>
              <dd class="mt-1 font-mono text-slate-950 break-all">{{ draftId || "Not provided" }}</dd>
            </div>
            <div>
              <dt class="text-slate-500">Status</dt>
              <dd class="mt-1 font-medium text-slate-950">{{ detailStatus }}</dd>
            </div>
            <div>
              <dt class="text-slate-500">Company</dt>
              <dd class="mt-1 text-slate-950">{{ detailCompany }}</dd>
            </div>
            <div v-if="detailScore !== null">
              <dt class="text-slate-500">Score</dt>
              <dd class="mt-1 font-semibold text-slate-950">{{ detailScore }}</dd>
            </div>
            <div v-if="detailApproved !== null">
              <dt class="text-slate-500">Approved</dt>
              <dd class="mt-1 text-slate-950">{{ detailApproved ? "Yes" : "No" }}</dd>
            </div>
            <div v-if="detailProvider">
              <dt class="text-slate-500">Provider</dt>
              <dd class="mt-1 text-slate-950">{{ detailProvider }}</dd>
            </div>
            <div>
              <dt class="text-slate-500">Has content</dt>
              <dd class="mt-1 text-slate-950">{{ detailHasContent ? "Yes" : "No" }}</dd>
            </div>
            <div>
              <dt class="text-slate-500">Has cover letter</dt>
              <dd class="mt-1 text-slate-950">{{ detailHasCoverLetter ? "Yes" : "No" }}</dd>
            </div>
            <div v-if="detailCreatedAt">
              <dt class="text-slate-500">Created</dt>
              <dd class="mt-1 text-slate-950">{{ detailCreatedAt }}</dd>
            </div>
            <div v-if="detailUpdatedAt">
              <dt class="text-slate-500">Updated</dt>
              <dd class="mt-1 text-slate-950">{{ detailUpdatedAt }}</dd>
            </div>
          </dl>
        </div>
      </article>

      <!-- Read-only review card -->
      <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Read-only review</p>
        <h2 class="mt-2 text-xl font-semibold tracking-tight text-slate-950">Review feedback keys</h2>

        <div v-if="!loading && !error" class="mt-4">
          <div v-if="detailFeedbackKeys.length" class="flex flex-wrap gap-2">
            <span
              v-for="key in detailFeedbackKeys"
              :key="key"
              class="inline-flex items-center rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-700"
            >
              {{ key }}
            </span>
          </div>
          <p v-else class="text-sm text-slate-600">
            No review feedback keys available for this draft.
          </p>
        </div>

        <div v-if="loading" class="mt-4 text-sm text-slate-600">Loading...</div>
      </article>

      <!-- Future actions card -->
      <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Future actions</p>
        <h2 class="mt-2 text-xl font-semibold tracking-tight text-slate-950">Draft actions</h2>
        <p class="mt-2 text-sm leading-6 text-slate-600">
          These actions will be enabled in a future migration phase. They are shown here as disabled placeholders and do not call any endpoints.
        </p>

        <div class="mt-4 flex flex-wrap gap-3">
          <button
            type="button"
            disabled
            class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-500 opacity-50 cursor-not-allowed"
          >
            Revise draft
          </button>
          <button
            type="button"
            disabled
            class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-500 opacity-50 cursor-not-allowed"
          >
            Polish draft
          </button>
          <button
            type="button"
            disabled
            class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-500 opacity-50 cursor-not-allowed"
          >
            Approve draft
          </button>
        </div>
      </article>
    </div>

    <aside class="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div>
        <p class="text-sm font-medium text-slate-500">Navigation</p>
        <p class="mt-2 text-sm leading-6 text-slate-600">
          Return to the drafts list or browse applications. Revise, polish, and approve actions are not yet available in the Vue interface.
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
          <dt class="text-slate-500">Placeholder status</dt>
          <dd class="font-medium text-slate-950">{{ isPlaceholder ? "Yes" : "No" }}</dd>
        </div>
        <div class="flex items-start justify-between gap-4">
          <dt class="text-slate-500">Draft ID</dt>
          <dd class="font-mono text-xs text-slate-950 break-all">{{ draftId || "None" }}</dd>
        </div>
      </dl>

      <div class="space-y-3">
        <RouterLink
          to="/drafts"
          class="block rounded-xl bg-slate-950 px-4 py-2 text-center text-sm font-medium text-white hover:bg-slate-800"
        >
          Back to Drafts
        </RouterLink>
        <RouterLink
          to="/applications"
          class="block rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-center text-sm font-medium text-slate-900 hover:bg-slate-100"
        >
          Go to Applications
        </RouterLink>
      </div>
    </aside>
  </section>
</template>
