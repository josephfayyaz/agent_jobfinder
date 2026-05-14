<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterLink, useRoute } from "vue-router";
import AppPageHeader from "../components/AppPageHeader.vue";
import { vueApiFetch } from "../api/client";

const route = useRoute();
const jobId = computed(() => String(route.params.id || ""));

const loading = ref(true);
const error = ref("");
const payload = ref(null);

onMounted(async () => {
  if (!jobId.value) {
    error.value = "No job ID provided in route.";
    loading.value = false;
    return;
  }

  try {
    payload.value = await vueApiFetch(`/jobs/${jobId.value}`);
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Request failed";
  } finally {
    loading.value = false;
  }
});

const detail = computed(() => payload.value?.data?.item ?? {});
const detailTitle = computed(() => detail.value?.title || detail.value?.role_family || "Untitled job");
const detailCompany = computed(() => detail.value?.company || "Unknown company");
const detailLocation = computed(() => detail.value?.location || "");
const detailStatus = computed(() => detail.value?.status || "Status unavailable");
const detailSource = computed(() => detail.value?.source_name || "");
const detailCreatedAt = computed(() => detail.value?.created_at || "");
const detailUpdatedAt = computed(() => detail.value?.updated_at || "");
const companyRecord = computed(() => detail.value?.company_record ?? null);
const companyTarget = computed(() => (
  detail.value?.company_id ? `/companies/${detail.value.company_id}` : "/companies"
));
const companyLinkLabel = computed(() => (
  detail.value?.company_id ? "View company" : "View companies"
));
</script>

<template>
  <AppPageHeader
    title="Job Detail"
    :description="`Review job context for ${jobId || '(unknown)'}.`"
  />

  <section class="grid gap-6 lg:grid-cols-3">
    <div class="space-y-6 lg:col-span-2">
      <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Job detail</p>
        <h2 class="mt-2 text-2xl font-semibold tracking-tight text-slate-950">{{ detailTitle }}</h2>

        <div v-if="loading" class="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
          Loading job...
        </div>

        <div v-else-if="error" class="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          {{ error }}
        </div>

        <dl v-else class="mt-4 grid gap-4 text-sm md:grid-cols-2">
          <div>
            <dt class="text-slate-500">Company</dt>
            <dd class="mt-1 text-slate-950">{{ detailCompany }}</dd>
          </div>
          <div>
            <dt class="text-slate-500">Status</dt>
            <dd class="mt-1 font-medium text-slate-950">{{ detailStatus }}</dd>
          </div>
          <div v-if="detailLocation">
            <dt class="text-slate-500">Location</dt>
            <dd class="mt-1 text-slate-950">{{ detailLocation }}</dd>
          </div>
          <div v-if="detailSource">
            <dt class="text-slate-500">Source</dt>
            <dd class="mt-1 text-slate-950">{{ detailSource }}</dd>
          </div>
          <div>
            <dt class="text-slate-500">Job ID</dt>
            <dd class="mt-1 font-mono text-xs text-slate-950 break-all">{{ jobId || "Not provided" }}</dd>
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
      </article>

      <article class="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-medium text-slate-500">Company/context</p>
        <h2 class="mt-2 text-xl font-semibold tracking-tight text-slate-950">Company context</h2>

        <div class="mt-4 grid gap-4 text-sm md:grid-cols-2">
          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-xs font-semibold uppercase text-slate-500">Company</p>
            <p class="mt-2 text-sm font-medium text-slate-950">{{ detailCompany }}</p>
            <p v-if="detailLocation" class="mt-1 text-xs text-slate-500">{{ detailLocation }}</p>
          </div>

          <div class="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p class="text-xs font-semibold uppercase text-slate-500">Company source</p>
            <p class="mt-2 text-sm font-medium text-slate-950">
              {{ companyRecord?.name || detailCompany }}
            </p>
            <p class="mt-1 text-xs text-slate-500">
              Career page stored: {{ companyRecord?.career_page_url_available ? "Yes" : "No" }}
            </p>
          </div>
        </div>
      </article>
    </div>

    <aside class="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div>
        <p class="text-sm font-medium text-slate-500">Related workflow</p>
        <p class="mt-2 text-sm leading-6 text-slate-600">
          Move between saved jobs, tracked applications, drafts, and company context without leaving the Vue app.
        </p>
      </div>

      <div class="space-y-3">
        <RouterLink
          to="/jobs"
          class="block rounded-xl bg-slate-950 px-4 py-2 text-center text-sm font-medium text-white hover:bg-slate-800"
        >
          Back to jobs
        </RouterLink>
        <RouterLink
          to="/applications"
          class="block rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-center text-sm font-medium text-slate-900 hover:bg-slate-100"
        >
          View applications
        </RouterLink>
        <RouterLink
          to="/drafts"
          class="block rounded-xl border border-slate-200 bg-white px-4 py-2 text-center text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          View drafts
        </RouterLink>
        <RouterLink
          :to="companyTarget"
          class="block rounded-xl border border-slate-200 bg-white px-4 py-2 text-center text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          {{ companyLinkLabel }}
        </RouterLink>
      </div>
    </aside>
  </section>
</template>
