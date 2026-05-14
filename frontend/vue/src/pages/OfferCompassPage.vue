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
    payload.value = await vueApiFetch("/offer-compass");
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
const items = computed(() => (Array.isArray(responseData.value.items) ? responseData.value.items.filter(Boolean) : []));
const total = computed(() => responseData.value.total ?? items.value.length ?? 0);

const offerCompany = (item) => item?.company || "Unknown company";
const offerTitle = (item) => item?.title || "Untitled offer";
const offerStatus = (item) => item?.status || "Status unavailable";
const offerId = (item) => item?.id || "";
const offerScore = (item) => (typeof item?.overall_score === "number" ? item.overall_score : null);
</script>

<template>
  <AppPageHeader
    title="Offer Compass"
    description="A read-only view of ranked offers and their comparison scores."
  />

  <section class="grid gap-6 lg:grid-cols-3">
    <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm lg:col-span-2">
      <p class="text-sm font-medium text-slate-500">Offer comparison status</p>
      <h2 class="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
        Ranked offers
      </h2>

      <div v-if="loading" class="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
        Loading offers...
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
          The backend is still returning placeholder offer compass data. The list below is rendered safely from whatever is available.
        </div>

        <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <p class="text-sm font-medium text-slate-500">Total</p>
            <p class="text-lg font-semibold text-slate-950">{{ total }}</p>
          </div>
        </div>

        <div v-if="items.length" class="space-y-3">
          <article
            v-for="item in items"
            :key="offerId(item) || offerTitle(item)"
            class="rounded-xl border border-slate-200 bg-white p-4"
          >
            <div class="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
              <div>
                <h3 class="text-sm font-semibold text-slate-950">{{ offerTitle(item) }}</h3>
                <p class="mt-1 text-sm text-slate-600">{{ offerCompany(item) }}</p>
              </div>
              <div class="flex items-center gap-3">
                <span
                  v-if="offerScore(item) !== null"
                  class="inline-flex items-center rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-sm font-semibold text-slate-950"
                >
                  {{ offerScore(item) }}/100
                </span>
                <p class="text-sm font-medium text-slate-900">{{ offerStatus(item) }}</p>
              </div>
            </div>

            <dl class="mt-4 grid gap-3 text-sm text-slate-600 md:grid-cols-2">
              <div v-if="offerId(item)">
                <dt class="text-slate-500">ID</dt>
                <dd class="mt-1 font-mono text-xs text-slate-950 break-all">{{ offerId(item) }}</dd>
              </div>
            </dl>
          </article>
        </div>

        <div
          v-else
          class="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-600"
        >
          No offers are currently available. Offer Compass ranks offers once you have active applications with offer status.
        </div>
      </div>
    </article>

    <aside class="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div>
        <p class="text-sm font-medium text-slate-500">Next actions</p>
        <p class="mt-2 text-sm leading-6 text-slate-600">
          Offer Compass compares active offers by score. Move applications to offer status in the applications list to populate this view.
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
