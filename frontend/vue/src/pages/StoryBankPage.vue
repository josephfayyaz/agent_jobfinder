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
    payload.value = await vueApiFetch("/story-bank");
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

const storyTitle = (item) => item?.title || "Untitled story";
const storyContext = (item) => item?.context || "";
const storySource = (item) => item?.confidence_source || "";
const storyTags = (item) => (Array.isArray(item?.role_family_tags) ? item.role_family_tags : []);
const storyId = (item) => item?.id || "";
const storyUpdatedAt = (item) => item?.updated_at || "";
</script>

<template>
  <AppPageHeader
    title="Story Bank"
    description="A read-only view of saved STAR narratives and reusable candidate stories."
  />

  <section class="grid gap-6 lg:grid-cols-3">
    <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm lg:col-span-2">
      <p class="text-sm font-medium text-slate-500">Narrative library status</p>
      <h2 class="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
        Saved stories
      </h2>

      <div v-if="loading" class="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
        Loading stories...
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
          The backend is still returning placeholder story bank data. The list below is rendered safely from whatever is available.
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
            :key="storyId(item) || storyTitle(item)"
            class="rounded-xl border border-slate-200 bg-white p-4"
          >
            <h3 class="text-sm font-semibold text-slate-950">{{ storyTitle(item) }}</h3>

            <p v-if="storyContext(item)" class="mt-2 text-sm leading-6 text-slate-600">
              {{ storyContext(item) }}
            </p>

            <div v-if="storyTags(item).length" class="mt-3 flex flex-wrap gap-1.5">
              <span
                v-for="tag in storyTags(item)"
                :key="tag"
                class="inline-flex items-center rounded-md border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs font-medium text-slate-700"
              >
                {{ tag }}
              </span>
            </div>

            <dl class="mt-3 grid gap-3 text-sm text-slate-600 md:grid-cols-2">
              <div v-if="storyId(item)">
                <dt class="text-slate-500">ID</dt>
                <dd class="mt-1 font-mono text-xs text-slate-950 break-all">{{ storyId(item) }}</dd>
              </div>
              <div v-if="storySource(item)">
                <dt class="text-slate-500">Source</dt>
                <dd class="mt-1 text-slate-950">{{ storySource(item) }}</dd>
              </div>
              <div v-if="storyUpdatedAt(item)">
                <dt class="text-slate-500">Updated</dt>
                <dd class="mt-1 text-slate-950">{{ storyUpdatedAt(item) }}</dd>
              </div>
            </dl>
          </article>
        </div>

        <div
          v-else
          class="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-600"
        >
          No stories are currently available in the contract response.
        </div>
      </div>
    </article>

    <aside class="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div>
        <p class="text-sm font-medium text-slate-500">Next actions</p>
        <p class="mt-2 text-sm leading-6 text-slate-600">
          Stories are gathered from the intake Q&amp;A and your verified profile. Use the apply flow to select relevant stories for a draft.
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
          to="/apply"
          class="block rounded-xl bg-slate-950 px-4 py-2 text-center text-sm font-medium text-white hover:bg-slate-800"
        >
          Open Apply
        </RouterLink>
        <RouterLink
          to="/verified-facts"
          class="block rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-center text-sm font-medium text-slate-900 hover:bg-slate-100"
        >
          Verified Facts
        </RouterLink>
        <RouterLink
          to="/applications"
          class="block rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2 text-center text-sm font-medium text-emerald-900 hover:bg-emerald-100"
        >
          Go to Applications
        </RouterLink>
      </div>
    </aside>
  </section>
</template>
